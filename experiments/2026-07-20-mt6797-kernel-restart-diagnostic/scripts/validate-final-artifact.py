#!/usr/bin/env python3
"""Validate a complete Candidate AB artifact and replay every component gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import stat
import subprocess
import sys
import tempfile

from ab_contract import (
    AA_ARTIFACT_NAME,
    AA_BOOT_SHA256,
    AA_DTB_SHA256,
    AA_INITRAMFS_SHA256,
    AA_INPUT_HELPER_SHA256,
    AA_KEYMAP_SHA256,
    AA_KEYMAP_VERIFIER_SHA256,
    AA_UNICODE_HELPER_SHA256,
    BOOT2_CAPACITY,
    CANDIDATE,
    CONFIG_INPUTS_SHA256,
    CONFIG_SHA256,
    EXPERIMENT,
    IMAGE_GZ_SHA256,
    IMAGE_SHA256,
    KERNEL_BUILD_SCRIPT_SHA256,
    KERNEL_MANIFEST_SHA256,
    MARKER,
    PACKAGE_DTB_SHA256,
    PACKAGE_NAME,
    PATCHSET_SHA256,
    PATCH_0087_SHA256,
    SERIES_SHA256,
    SOURCE_SHA256,
    SYSTEM_MAP_SHA256,
    digest_bytes,
    read_regular,
)


EXPECTED_FILES = frozenset(
    {
        "SHA256SUMS",
        "Image.gz",
        "System.map",
        "aa-baseline-validation.txt",
        "analysis.txt",
        "ash-dispatch-validation.txt",
        "boot-validation.txt",
        "console-keymap-verify",
        "console-unicode-mode",
        "gemini-mt6797-kernel-restart-initramfs.img",
        "gemini-mt6797-kernel-restart.boot.img",
        "gemini-us.bkeymap",
        "initramfs-build.txt",
        "initramfs-validation.txt",
        "input-event-capture",
        "input-tree.sha256",
        "mt6797-gemini-pda-kernel-restart.dtb",
        "package-foundation.txt",
        "package-validation.txt",
        "provenance.txt",
        "serializer.txt",
        "source-build.json",
    }
)
EXECUTABLE_FILES = frozenset(
    {"console-keymap-verify", "console-unicode-mode", "input-event-capture"}
)


def run(command: list[str]) -> bytes:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(command, check=False, capture_output=True, env=environment)
    if result.returncode:
        raise ValueError(
            f"validator failed ({result.returncode}): {' '.join(command)}: "
            f"{result.stderr.decode('utf-8', errors='replace').strip()}"
        )
    return result.stdout


def normalize_log(
    data: bytes,
    *,
    package: pathlib.Path,
    baseline: pathlib.Path,
    repo_root: pathlib.Path,
    workdir: pathlib.Path | None = None,
) -> bytes:
    text = data.decode("utf-8")
    replacements = (
        (os.fspath(package), "@PACKAGE@"),
        (os.fspath(baseline), "@CANDIDATE_AA_R1@"),
        (os.fspath(repo_root), "@REPOSITORY@"),
    )
    if workdir is not None:
        replacements = ((os.fspath(workdir), "@WORK@"),) + replacements
    output: list[str] = []
    for line in text.splitlines():
        for old, new in replacements:
            line = line.replace(old, new)
        if line.startswith("generated_utc="):
            line = "generated_utc=@PACKAGE_GENERATED_UTC@"
        elif line.startswith("build_json_sha256="):
            line = "build_json_sha256=@TIMESTAMP_VARIANT@"
        elif line.startswith("package_sums_sha256="):
            line = "package_sums_sha256=@TIMESTAMP_VARIANT@"
        output.append(line)
    return ("\n".join(output) + "\n").encode("utf-8")


def normalize_build_json(data: bytes) -> bytes:
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("package build provenance is not valid JSON") from exc
    if not isinstance(value, dict) or "generated_utc" not in value:
        raise ValueError("package build provenance lacks generated_utc")
    del value["generated_utc"]
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode("utf-8")


def parse_provenance(data: bytes) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in data.decode("utf-8").splitlines():
        if "=" not in line:
            raise ValueError("malformed AB provenance line")
        key, value = line.split("=", 1)
        if not re.fullmatch(r"[a-z0-9_]+", key) or key in fields:
            raise ValueError("invalid or duplicate AB provenance key")
        fields[key] = value
    return fields


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=pathlib.Path, required=True)
    parser.add_argument("--baseline", type=pathlib.Path, required=True)
    parser.add_argument("--package", type=pathlib.Path, required=True)
    parser.add_argument("--manifest", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        artifact = args.artifact
        baseline = args.baseline.resolve(strict=True)
        package = args.package.resolve(strict=True)
        manifest = args.manifest.resolve(strict=True)
        if artifact.is_symlink() or not artifact.is_dir():
            raise ValueError("AB artifact is not a regular directory")
        if stat.S_IMODE(artifact.stat().st_mode) != 0o700:
            raise ValueError("AB artifact directory mode is not 0700")
        if {entry.name for entry in artifact.iterdir()} != EXPECTED_FILES:
            raise ValueError("AB artifact inventory changed")
        contents: dict[str, bytes] = {}
        for name in EXPECTED_FILES:
            mode = 0o755 if name in EXECUTABLE_FILES else 0o600
            contents[name] = read_regular(artifact / name, f"AB {name}", mode)

        checksums: dict[str, str] = {}
        for line in contents["SHA256SUMS"].decode("ascii").splitlines():
            fields = line.split(maxsplit=1)
            if len(fields) != 2 or re.fullmatch(r"[0-9a-f]{64}", fields[0]) is None:
                raise ValueError("malformed AB manifest line")
            name = fields[1].removeprefix("*").removeprefix("./")
            if name in checksums:
                raise ValueError("duplicate AB manifest entry")
            checksums[name] = fields[0]
        if set(checksums) != EXPECTED_FILES - {"SHA256SUMS"}:
            raise ValueError("AB manifest inventory changed")
        for name, expected in checksums.items():
            if digest_bytes(contents[name]) != expected:
                raise ValueError(f"AB manifest checksum mismatch: {name}")
        canonical_manifest = "".join(
            f"{digest_bytes(contents[name])}  ./{name}\n"
            for name in sorted(EXPECTED_FILES - {"SHA256SUMS"})
        ).encode("ascii")
        if contents["SHA256SUMS"] != canonical_manifest:
            raise ValueError("AB manifest serialization is not canonical")

        boot_name = "gemini-mt6797-kernel-restart.boot.img"
        initramfs_name = "gemini-mt6797-kernel-restart-initramfs.img"
        dtb_name = "mt6797-gemini-pda-kernel-restart.dtb"
        boot_hash = digest_bytes(contents[boot_name])
        expected_name = f"candidate-AB-mt6797-kernel-restart-final-{boot_hash[:8]}"
        if artifact.name != expected_name:
            raise ValueError("AB artifact basename does not match its boot hash")
        if not 0 < len(contents[boot_name]) <= BOOT2_CAPACITY:
            raise ValueError("AB boot size is invalid or exceeds boot2")
        exact = (
            ("Image.gz", IMAGE_GZ_SHA256),
            ("System.map", SYSTEM_MAP_SHA256),
            (dtb_name, AA_DTB_SHA256),
            ("gemini-us.bkeymap", AA_KEYMAP_SHA256),
            ("console-keymap-verify", AA_KEYMAP_VERIFIER_SHA256),
            ("console-unicode-mode", AA_UNICODE_HELPER_SHA256),
            ("input-event-capture", AA_INPUT_HELPER_SHA256),
        )
        for name, expected in exact:
            if digest_bytes(contents[name]) != expected:
                raise ValueError(f"exact AB artifact member changed: {name}")

        script_dir = pathlib.Path(__file__).resolve().parent
        experiment_dir = script_dir.parent
        repo_root = experiment_dir.parent.parent
        aa_validator = script_dir / "validate-aa-baseline.py"
        package_validator = script_dir / "validate-package.py"
        initramfs_builder = script_dir / "build-initramfs.sh"
        initramfs_validator = script_dir / "validate-initramfs.py"
        boot_validator = script_dir / "validate-boot.py"
        input_hasher = script_dir / "hash-input-tree.py"
        artifact_validator = repo_root / "scripts/validate-kernel-artifact"
        serializer = (
            repo_root
            / "experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
        )
        analyzer = (
            repo_root
            / "experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
        )
        dispatch_validator = (
            repo_root
            / "experiments/2026-07-19-keyboard-reboot-dispatch-diagnostic/scripts/validate-ash-dispatch.py"
        )

        expected_aa = normalize_log(
            run([sys.executable, os.fspath(aa_validator), "--artifact", os.fspath(baseline)]),
            package=package,
            baseline=baseline,
            repo_root=repo_root,
        )
        if expected_aa != contents["aa-baseline-validation.txt"]:
            raise ValueError("saved AA baseline validation differs from fresh output")
        expected_generic_package = normalize_log(
            run([os.fspath(artifact_validator), os.fspath(package)]),
            package=package,
            baseline=baseline,
            repo_root=repo_root,
        )
        if expected_generic_package != contents["package-validation.txt"]:
            raise ValueError("saved generic package validation differs from fresh output")
        expected_package = normalize_log(
            run(
                [
                    sys.executable,
                    os.fspath(package_validator),
                    "--package",
                    os.fspath(package),
                    "--manifest",
                    os.fspath(manifest),
                ]
            ),
            package=package,
            baseline=baseline,
            repo_root=repo_root,
        )
        if expected_package != contents["package-foundation.txt"]:
            raise ValueError("saved exact package validation differs from fresh output")

        aa_initramfs = baseline / "gemini-keyboard-console-map-initramfs.img"
        expected_initramfs = normalize_log(
            run(
                [
                    sys.executable,
                    os.fspath(initramfs_validator),
                    "--baseline",
                    os.fspath(aa_initramfs),
                    "--candidate",
                    os.fspath(artifact / initramfs_name),
                    "--source-dir",
                    os.fspath(experiment_dir / "initramfs"),
                ]
            ),
            package=package,
            baseline=baseline,
            repo_root=repo_root,
        )
        if expected_initramfs != contents["initramfs-validation.txt"]:
            raise ValueError("saved initramfs validation differs from fresh output")
        dispatch_result = run(
            [
                sys.executable,
                os.fspath(dispatch_validator),
                "--initramfs",
                os.fspath(artifact / initramfs_name),
                "--verify-saved",
                os.fspath(artifact / "ash-dispatch-validation.txt"),
            ]
        )
        if b"saved_dispatch_validation=passed\n" not in dispatch_result:
            raise ValueError("saved ash dispatch validation did not pass")

        image = package / "Image"
        expected_boot = normalize_log(
            run(
                [
                    sys.executable,
                    os.fspath(boot_validator),
                    "--candidate",
                    os.fspath(artifact / boot_name),
                    "--image",
                    os.fspath(image),
                    "--image-gz",
                    os.fspath(artifact / "Image.gz"),
                    "--dtb",
                    os.fspath(artifact / dtb_name),
                    "--initramfs",
                    os.fspath(artifact / initramfs_name),
                ]
            ),
            package=package,
            baseline=baseline,
            repo_root=repo_root,
        )
        if expected_boot != contents["boot-validation.txt"]:
            raise ValueError("saved boot validation differs from fresh output")

        bootopt = "bootopt=64S3,32N2,64N2"
        expected_analysis = normalize_log(
            run(
                [
                    sys.executable,
                    os.fspath(analyzer),
                    "--validate-lk",
                    "--expected-image-gz",
                    os.fspath(artifact / "Image.gz"),
                    "--expected-ramdisk",
                    os.fspath(artifact / initramfs_name),
                    "--expected-dtb",
                    os.fspath(artifact / dtb_name),
                    "--expected-name",
                    "gemini-obs-L",
                    "--expected-cmdline",
                    bootopt,
                    os.fspath(artifact / boot_name),
                ]
            ),
            package=package,
            baseline=baseline,
            repo_root=repo_root,
        )
        if expected_analysis != contents["analysis.txt"] or expected_analysis.count(b"gate_") != 32:
            raise ValueError("saved LK analysis differs or lacks 32 gates")

        with tempfile.TemporaryDirectory(prefix="candidate-ab-final-validation.") as raw_temp:
            temp = pathlib.Path(raw_temp)
            rebuilt_initramfs = temp / "rebuilt-initramfs.img"
            initramfs_build_output = run(
                [
                    os.fspath(initramfs_builder),
                    "--baseline",
                    os.fspath(aa_initramfs),
                    "--output",
                    os.fspath(rebuilt_initramfs),
                ]
            )
            if rebuilt_initramfs.read_bytes() != contents[initramfs_name]:
                raise ValueError("fresh initramfs reconstruction differs from AB archive")
            expected_initramfs_build = normalize_log(
                initramfs_build_output,
                package=package,
                baseline=baseline,
                repo_root=repo_root,
                workdir=temp,
            )
            if expected_initramfs_build != contents["initramfs-build.txt"]:
                raise ValueError("saved initramfs build output differs from fresh output")

            rebuilt = temp / "rebuilt.boot.img"
            serializer_output = run(
                [
                    sys.executable,
                    os.fspath(serializer),
                    "--kernel",
                    os.fspath(artifact / "Image.gz"),
                    "--ramdisk",
                    os.fspath(artifact / initramfs_name),
                    "--dtb",
                    os.fspath(artifact / dtb_name),
                    "--output",
                    os.fspath(rebuilt),
                    "--name",
                    "gemini-obs-L",
                    "--cmdline",
                    bootopt,
                    "--kernel-addr",
                    "0x40200000",
                    "--ramdisk-addr",
                    "0x45000000",
                    "--second-addr",
                    "0x40f00000",
                    "--tags-addr",
                    "0x44000000",
                    "--lk-android8",
                ]
            )
            if rebuilt.read_bytes() != contents[boot_name]:
                raise ValueError("fresh serializer reconstruction differs from AB boot")
            serializer_lines = [
                line for line in serializer_output.splitlines() if not line.startswith(b"output=")
            ]
            expected_serializer = normalize_log(
                b"\n".join(serializer_lines) + b"\n",
                package=package,
                baseline=baseline,
                repo_root=repo_root,
                workdir=temp,
            )
            if expected_serializer != contents["serializer.txt"]:
                raise ValueError("saved serializer output differs from fresh output")

        expected_source_build = normalize_build_json(
            read_regular(package / "provenance/build.json", "package build provenance")
        )
        if expected_source_build != contents["source-build.json"]:
            raise ValueError("normalized package build provenance changed")
        expected_input_tree = run(
            [sys.executable, os.fspath(input_hasher), "--repo-root", os.fspath(repo_root)]
        )
        if expected_input_tree != contents["input-tree.sha256"]:
            raise ValueError("saved repository input tree differs from current sources")

        provenance = parse_provenance(contents["provenance.txt"])
        required_provenance = {
            "experiment": EXPERIMENT,
            "candidate_label": CANDIDATE,
            "marker": MARKER,
            "aa_artifact": AA_ARTIFACT_NAME,
            "aa_boot_sha256": AA_BOOT_SHA256,
            "aa_initramfs_sha256": AA_INITRAMFS_SHA256,
            "aa_dtb_sha256": AA_DTB_SHA256,
            "aa_keymap_sha256": AA_KEYMAP_SHA256,
            "aa_keymap_verifier_sha256": AA_KEYMAP_VERIFIER_SHA256,
            "kernel_package": PACKAGE_NAME,
            "source_sha256": SOURCE_SHA256,
            "kernel_manifest_sha256": KERNEL_MANIFEST_SHA256,
            "kernel_build_script_sha256": KERNEL_BUILD_SCRIPT_SHA256,
            "patchset_sha256": PATCHSET_SHA256,
            "series_sha256": SERIES_SHA256,
            "patch_0087_sha256": PATCH_0087_SHA256,
            "config_inputs_sha256": CONFIG_INPUTS_SHA256,
            "config_sha256": CONFIG_SHA256,
            "image_sha256": IMAGE_SHA256,
            "image_gz_sha256": IMAGE_GZ_SHA256,
            "system_map_sha256": SYSTEM_MAP_SHA256,
            "package_dtb_sha256": PACKAGE_DTB_SHA256,
            "source_build_normalized_sha256": digest_bytes(contents["source-build.json"]),
            "candidate_dtb_sha256": AA_DTB_SHA256,
            "dtb_lineage": "byte-exact-hardware-passed-aa-r1",
            "candidate_initramfs_sha256": digest_bytes(contents[initramfs_name]),
            "candidate_sha256": boot_hash,
            "candidate_size": str(len(contents[boot_name])),
            "boot2_capacity": str(BOOT2_CAPACITY),
            "initramfs_delta": "init,bin/local-shell,bin/reboot,bin/x-record",
            "keymap_and_gate": "exact-aa-r1-with-attribution-only-shell-transform",
            "reboot_dispatch": "ENV-alias-absolute-wrapper",
            "manual_reboot": "busybox-reboot-no-sync-force",
            "watchdog_userspace": (
                "start-none,open-none,ping-none,countdown-none,fallback-none"
            ),
            "automatic_reboot": "none",
            "kernel_restart_priority": "MT6797-255,other-MediaTek-128",
            "kernel_virtual_console": "none",
            "serial_console": "ttyS0,921600n8",
            "font": "TER16x32",
            "fbcon_rotation": "3",
            "deterministic_replica": "initramfs-and-android-v0-byte-identical",
            "storage_access": "none",
            "runtime_networking": "none",
            "hardware_write": "none",
            "flash": "none",
            "runtime_result": "not-tested",
        }
        for key, expected in required_provenance.items():
            if provenance.get(key) != expected:
                raise ValueError(f"AB provenance mismatch: {key}")
        revision = provenance.get("repo_revision", "")
        if re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", revision) is None:
            raise ValueError("AB provenance repository revision is malformed")
        if set(provenance) != set(required_provenance) | {"repo_revision"}:
            raise ValueError("AB provenance field inventory changed")

        print("validation=candidate-ab-final-artifact")
        print(f"artifact={artifact.name}")
        print(f"candidate_sha256={boot_hash}")
        print(f"candidate_size={len(contents[boot_name])}")
        print(f"candidate_initramfs_sha256={digest_bytes(contents[initramfs_name])}")
        print(f"image_gz_sha256={IMAGE_GZ_SHA256}")
        print(f"dtb_sha256={AA_DTB_SHA256}")
        print(f"keymap_sha256={AA_KEYMAP_SHA256}")
        print("component_validators=passed")
        print("deterministic_reconstruction=passed")
        print("lk_gates=32-of-32")
        print("manifest_inventory_modes=passed")
        print("hardware_write=none")
        return 0
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
