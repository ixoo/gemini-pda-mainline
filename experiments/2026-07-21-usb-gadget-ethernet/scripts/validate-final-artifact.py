#!/usr/bin/env python3
"""Replay and validate a complete Candidate AC artifact."""

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

from ac_contract import (
    AB_ARTIFACT_NAME,
    AB_BOOT_SHA256,
    AB_DTB_FILE,
    AB_DTB_SHA256,
    AB_IMAGE_GZ_FILE,
    AB_IMAGE_GZ_SHA256,
    AB_INITRAMFS_FILE,
    AB_INITRAMFS_SHA256,
    AB_INPUT_HELPER_SHA256,
    AB_KEYMAP_FILE,
    AB_KEYMAP_SHA256,
    AB_KEYMAP_VERIFIER_SHA256,
    AB_MANIFEST_SHA256,
    AB_SOURCE_BUILD_SHA256,
    AB_SYSTEM_MAP_SHA256,
    AB_UNICODE_HELPER_SHA256,
    AC_BOOT_FILE,
    AC_DTB_FILE,
    AC_INITRAMFS_FILE,
    BOOT2_CAPACITY,
    CANDIDATE,
    DEVICE_ADDRESS,
    DEVICE_INTERFACE,
    DEVICE_MAC,
    EXPERIMENT,
    HOST_ADDRESS,
    HOST_MAC,
    MARKER,
    TCP_PORT,
    digest_bytes,
    digest_path,
    read_regular,
)


EXPECTED_FILES = frozenset(
    {
        "SHA256SUMS",
        "Image.gz",
        "System.map",
        "ab-baseline-validation.txt",
        "analysis.txt",
        "boot-validation.txt",
        "console-keymap-verify",
        "console-unicode-mode",
        AC_INITRAMFS_FILE,
        AC_BOOT_FILE,
        AB_KEYMAP_FILE,
        "initramfs-build.txt",
        "initramfs-validation.txt",
        "input-event-capture",
        "input-tree.sha256",
        AC_DTB_FILE,
        "provenance.txt",
        "serializer.txt",
        "source-build.json",
    }
)
EXECUTABLE_FILES = frozenset(
    {"console-keymap-verify", "console-unicode-mode", "input-event-capture"}
)

REPOSITORY_INPUTS = (
    "experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py",
    "experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py",
    "experiments/2026-07-21-usb-gadget-ethernet/initramfs/ac-record",
    "experiments/2026-07-21-usb-gadget-ethernet/initramfs/init",
    "experiments/2026-07-21-usb-gadget-ethernet/initramfs/usb-net",
    "experiments/2026-07-21-usb-gadget-ethernet/initramfs/usb-shell",
    "experiments/2026-07-21-usb-gadget-ethernet/scripts/ac_contract.py",
    "experiments/2026-07-21-usb-gadget-ethernet/scripts/build-candidate-ac.sh",
    "experiments/2026-07-21-usb-gadget-ethernet/scripts/build-initramfs.sh",
    "experiments/2026-07-21-usb-gadget-ethernet/scripts/test-container-mutations.py",
    "experiments/2026-07-21-usb-gadget-ethernet/scripts/validate-ab-baseline.py",
    "experiments/2026-07-21-usb-gadget-ethernet/scripts/validate-boot.py",
    "experiments/2026-07-21-usb-gadget-ethernet/scripts/validate-final-artifact.py",
    "experiments/2026-07-21-usb-gadget-ethernet/scripts/validate-initramfs.py",
)


def repository_input_tree(repo_root: pathlib.Path) -> bytes:
    lines: list[str] = []
    for relative in REPOSITORY_INPUTS:
        path = repo_root / relative
        if path.is_symlink() or not path.is_file() or not path.stat().st_size:
            raise ValueError(f"repository input missing, empty, or unsafe: {relative}")
        lines.append(f"{digest_path(path)}  {relative}\n")
    return "".join(lines).encode("ascii")


def run(command: list[str]) -> bytes:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        command, check=False, capture_output=True, env=environment
    )
    if completed.returncode:
        stderr = completed.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(
            f"validator failed ({completed.returncode}): {' '.join(command)}: {stderr}"
        )
    return completed.stdout


def normalize_log(
    data: bytes,
    *,
    baseline: pathlib.Path,
    repo_root: pathlib.Path,
    workdir: pathlib.Path | None = None,
) -> bytes:
    text = data.decode("utf-8")
    replacements: tuple[tuple[str, str], ...] = (
        (os.fspath(baseline), "@CANDIDATE_AB@"),
        (os.fspath(repo_root), "@REPOSITORY@"),
    )
    if workdir is not None:
        replacements = ((os.fspath(workdir), "@WORK@"),) + replacements
    output: list[str] = []
    for line in text.splitlines():
        for old, new in replacements:
            line = line.replace(old, new)
        output.append(line)
    return ("\n".join(output) + "\n").encode("utf-8")


def parse_provenance(data: bytes) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in data.decode("utf-8").splitlines():
        if "=" not in line:
            raise ValueError("malformed AC provenance line")
        key, value = line.split("=", 1)
        if not re.fullmatch(r"[a-z0-9_]+", key) or key in fields:
            raise ValueError("invalid or duplicate AC provenance field")
        fields[key] = value
    return fields


def validate_manifest(contents: dict[str, bytes]) -> None:
    checksums: dict[str, str] = {}
    for line in contents["SHA256SUMS"].decode("ascii").splitlines():
        fields = line.split(maxsplit=1)
        if len(fields) != 2 or re.fullmatch(r"[0-9a-f]{64}", fields[0]) is None:
            raise ValueError("malformed AC manifest line")
        name = fields[1].removeprefix("*").removeprefix("./")
        if name in checksums:
            raise ValueError("duplicate AC manifest entry")
        checksums[name] = fields[0]
    if set(checksums) != EXPECTED_FILES - {"SHA256SUMS"}:
        raise ValueError("AC manifest inventory changed")
    for name, expected in checksums.items():
        if digest_bytes(contents[name]) != expected:
            raise ValueError(f"AC manifest checksum mismatch: {name}")
    canonical = "".join(
        f"{digest_bytes(contents[name])}  ./{name}\n"
        for name in sorted(EXPECTED_FILES - {"SHA256SUMS"})
    ).encode("ascii")
    if contents["SHA256SUMS"] != canonical:
        raise ValueError("AC manifest serialization is not canonical")


def validate_artifact(artifact: pathlib.Path, baseline: pathlib.Path) -> None:
    artifact_info = artifact.lstat()
    if artifact.is_symlink() or not stat.S_ISDIR(artifact_info.st_mode):
        raise ValueError("AC artifact is not a regular directory")
    if stat.S_IMODE(artifact_info.st_mode) != 0o700:
        raise ValueError("AC artifact directory mode is not 0700")
    if {entry.name for entry in artifact.iterdir()} != EXPECTED_FILES:
        raise ValueError("AC artifact inventory changed")

    contents: dict[str, bytes] = {}
    for name in EXPECTED_FILES:
        mode = 0o755 if name in EXECUTABLE_FILES else 0o600
        contents[name] = read_regular(artifact / name, f"AC {name}", mode)
    validate_manifest(contents)

    boot_hash = digest_bytes(contents[AC_BOOT_FILE])
    expected_name = f"candidate-AC-usb-gadget-ethernet-final-{boot_hash[:8]}"
    if artifact.name != expected_name:
        raise ValueError("AC artifact basename does not match its boot hash")
    if not 0 < len(contents[AC_BOOT_FILE]) <= BOOT2_CAPACITY:
        raise ValueError("AC boot size is invalid or exceeds boot2")

    exact_hashes = (
        ("Image.gz", AB_IMAGE_GZ_SHA256),
        ("System.map", AB_SYSTEM_MAP_SHA256),
        (AC_DTB_FILE, AB_DTB_SHA256),
        (AB_KEYMAP_FILE, AB_KEYMAP_SHA256),
        ("console-keymap-verify", AB_KEYMAP_VERIFIER_SHA256),
        ("console-unicode-mode", AB_UNICODE_HELPER_SHA256),
        ("input-event-capture", AB_INPUT_HELPER_SHA256),
        ("source-build.json", AB_SOURCE_BUILD_SHA256),
    )
    for name, expected in exact_hashes:
        if digest_bytes(contents[name]) != expected:
            raise ValueError(f"exact inherited AB artifact member changed: {name}")

    baseline = baseline.resolve(strict=True)
    script_dir = pathlib.Path(__file__).resolve().parent
    experiment_dir = script_dir.parent
    repo_root = experiment_dir.parent.parent
    baseline_validator = script_dir / "validate-ab-baseline.py"
    initramfs_builder = script_dir / "build-initramfs.sh"
    initramfs_validator = script_dir / "validate-initramfs.py"
    boot_validator = script_dir / "validate-boot.py"
    serializer = (
        repo_root
        / "experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
    )
    analyzer = (
        repo_root
        / "experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
    )

    expected_baseline = normalize_log(
        run(
            [
                sys.executable,
                os.fspath(baseline_validator),
                "--artifact",
                os.fspath(baseline),
            ]
        ),
        baseline=baseline,
        repo_root=repo_root,
    )
    if contents["ab-baseline-validation.txt"] != expected_baseline:
        raise ValueError("saved AB baseline validation differs from fresh output")

    ac_initramfs = artifact / AC_INITRAMFS_FILE
    ab_initramfs = baseline / AB_INITRAMFS_FILE
    source_dir = experiment_dir / "initramfs"
    expected_initramfs = normalize_log(
        run(
            [
                sys.executable,
                os.fspath(initramfs_validator),
                "--baseline",
                os.fspath(ab_initramfs),
                "--candidate",
                os.fspath(ac_initramfs),
                "--source-dir",
                os.fspath(source_dir),
            ]
        ),
        baseline=baseline,
        repo_root=repo_root,
    )
    if contents["initramfs-validation.txt"] != expected_initramfs:
        raise ValueError("saved AC initramfs validation differs from fresh output")

    expected_boot = normalize_log(
        run(
            [
                sys.executable,
                os.fspath(boot_validator),
                "--candidate",
                os.fspath(artifact / AC_BOOT_FILE),
                "--image-gz",
                os.fspath(artifact / "Image.gz"),
                "--dtb",
                os.fspath(artifact / AC_DTB_FILE),
                "--initramfs",
                os.fspath(ac_initramfs),
            ]
        ),
        baseline=baseline,
        repo_root=repo_root,
    )
    if contents["boot-validation.txt"] != expected_boot:
        raise ValueError("saved AC boot validation differs from fresh output")

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
                os.fspath(ac_initramfs),
                "--expected-dtb",
                os.fspath(artifact / AC_DTB_FILE),
                "--expected-name",
                "gemini-obs-L",
                "--expected-cmdline",
                bootopt,
                os.fspath(artifact / AC_BOOT_FILE),
            ]
        ),
        baseline=baseline,
        repo_root=repo_root,
    )
    if contents["analysis.txt"] != expected_analysis:
        raise ValueError("saved LK analysis differs from fresh output")
    if sum(line.startswith(b"gate_") for line in expected_analysis.splitlines()) != 32:
        raise ValueError("saved LK analysis does not contain exactly 32 gates")

    with tempfile.TemporaryDirectory(prefix="candidate-ac-final-validation.") as raw:
        workdir = pathlib.Path(raw)
        rebuilt_initramfs = workdir / AC_INITRAMFS_FILE
        initramfs_build = run(
            [
                os.fspath(initramfs_builder),
                "--baseline",
                os.fspath(ab_initramfs),
                "--output",
                os.fspath(rebuilt_initramfs),
            ]
        )
        if rebuilt_initramfs.read_bytes() != contents[AC_INITRAMFS_FILE]:
            raise ValueError("fresh AC initramfs reconstruction differs")
        expected_initramfs_build = normalize_log(
            initramfs_build,
            baseline=baseline,
            repo_root=repo_root,
            workdir=workdir,
        )
        if contents["initramfs-build.txt"] != expected_initramfs_build:
            raise ValueError("saved initramfs build log differs from fresh output")

        rebuilt_boot = workdir / AC_BOOT_FILE
        serializer_output = run(
            [
                sys.executable,
                os.fspath(serializer),
                "--kernel",
                os.fspath(artifact / "Image.gz"),
                "--ramdisk",
                os.fspath(ac_initramfs),
                "--dtb",
                os.fspath(artifact / AC_DTB_FILE),
                "--output",
                os.fspath(rebuilt_boot),
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
        if rebuilt_boot.read_bytes() != contents[AC_BOOT_FILE]:
            raise ValueError("fresh Android-v0 reconstruction differs")
        serializer_lines = [
            line
            for line in serializer_output.splitlines()
            if not line.startswith(b"output=")
        ]
        expected_serializer = normalize_log(
            b"\n".join(serializer_lines) + b"\n",
            baseline=baseline,
            repo_root=repo_root,
            workdir=workdir,
        )
        if contents["serializer.txt"] != expected_serializer:
            raise ValueError("saved serializer log differs from fresh output")

    expected_tree = repository_input_tree(repo_root)
    if contents["input-tree.sha256"] != expected_tree:
        raise ValueError("saved repository input tree differs from current sources")
    if contents["source-build.json"] != read_regular(
        baseline / "source-build.json", "AB source-build", 0o600
    ):
        raise ValueError("normalized AB source-build bytes changed")
    if json.loads(contents["source-build.json"].decode("utf-8")).get(
        "build_profile"
    ) != "observability-fbcon-rotation-keyboard-wrrd-manual-reboot":
        raise ValueError("inherited source-build profile changed")

    provenance = parse_provenance(contents["provenance.txt"])
    required_provenance = {
        "experiment": EXPERIMENT,
        "candidate_label": CANDIDATE,
        "marker": MARKER,
        "ab_artifact": AB_ARTIFACT_NAME,
        "ab_manifest_sha256": AB_MANIFEST_SHA256,
        "ab_boot_sha256": AB_BOOT_SHA256,
        "ab_initramfs_sha256": AB_INITRAMFS_SHA256,
        "ab_image_gz_sha256": AB_IMAGE_GZ_SHA256,
        "ab_dtb_sha256": AB_DTB_SHA256,
        "ab_keymap_sha256": AB_KEYMAP_SHA256,
        "ab_system_map_sha256": AB_SYSTEM_MAP_SHA256,
        "ab_source_build_sha256": AB_SOURCE_BUILD_SHA256,
        "candidate_image_gz_sha256": AB_IMAGE_GZ_SHA256,
        "candidate_dtb_sha256": AB_DTB_SHA256,
        "candidate_system_map_sha256": AB_SYSTEM_MAP_SHA256,
        "candidate_source_build_sha256": AB_SOURCE_BUILD_SHA256,
        "candidate_keymap_sha256": AB_KEYMAP_SHA256,
        "candidate_keymap_verifier_sha256": AB_KEYMAP_VERIFIER_SHA256,
        "candidate_unicode_helper_sha256": AB_UNICODE_HELPER_SHA256,
        "candidate_input_helper_sha256": AB_INPUT_HELPER_SHA256,
        "candidate_initramfs_sha256": digest_bytes(contents[AC_INITRAMFS_FILE]),
        "candidate_sha256": boot_hash,
        "candidate_size": str(len(contents[AC_BOOT_FILE])),
        "boot2_capacity": str(BOOT2_CAPACITY),
        "input_tree_sha256": digest_bytes(contents["input-tree.sha256"]),
        "kernel_lineage": "byte-exact-hardware-passed-ab",
        "dtb_lineage": "byte-exact-hardware-passed-ab",
        "source_build_lineage": "byte-exact-hardware-passed-ab",
        "initramfs_delta": "init,bin/ac-record,bin/usb-net,bin/usb-shell,bin/ip,bin/nc,bin/ping",
        "local_console": "exact-ab",
        "keymap_and_gate": "exact-ab",
        "reboot_dispatch": "exact-ab-ENV-alias-absolute-wrapper",
        "manual_reboot": "exact-ab-busybox-reboot-no-sync-force",
        "usb_interface": DEVICE_INTERFACE,
        "device_address": DEVICE_ADDRESS,
        "host_address": HOST_ADDRESS,
        "device_mac": DEVICE_MAC,
        "host_mac": HOST_MAC,
        "tcp_port": str(TCP_PORT),
        "usb0_wait_seconds": "30",
        "tcp_service": "busybox-nc--ll--p-2323--e-/bin/usb-shell",
        "tcp_shell": "unauthenticated-root-direct-trusted-link-only",
        "listener_lifetime": "persistent-until-reboot",
        "usb_descriptor": "exact-ab-g_ether",
        "runtime_networking": "usb0-static-ipv4-direct-link",
        "network_side_paths": "dhcp-none,route-none,bridge-none,ipv6-none",
        "storage_access": "none",
        "watchdog_userspace": "start-none,open-none,ping-none,countdown-none,fallback-none",
        "automatic_reboot": "none",
        "deterministic_replica": "initramfs-and-android-v0-byte-identical",
        "hardware_write": "none",
        "flash": "none",
        "runtime_result": "not-tested",
    }
    revision = provenance.get("repo_revision", "")
    if re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", revision) is None:
        raise ValueError("AC provenance repository revision is malformed")
    required_provenance["repo_revision"] = revision
    if provenance != required_provenance:
        differing = sorted(
            key
            for key in set(provenance) | set(required_provenance)
            if provenance.get(key) != required_provenance.get(key)
        )
        raise ValueError(f"AC provenance mismatch: {','.join(differing)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=pathlib.Path)
    parser.add_argument("--baseline", type=pathlib.Path)
    parser.add_argument("--hash-input-tree", action="store_true")
    parser.add_argument("--repo-root", type=pathlib.Path)
    args = parser.parse_args()
    try:
        if args.hash_input_tree:
            if args.artifact is not None or args.baseline is not None:
                raise ValueError("input-tree mode does not accept artifact arguments")
            if args.repo_root is None:
                raise ValueError("input-tree mode requires --repo-root")
            sys.stdout.buffer.write(repository_input_tree(args.repo_root.resolve(strict=True)))
            return 0
        if args.repo_root is not None:
            raise ValueError("--repo-root is valid only with --hash-input-tree")
        if args.artifact is None or args.baseline is None:
            raise ValueError("artifact validation requires --artifact and --baseline")
        validate_artifact(args.artifact, args.baseline)
        print("validation=candidate-ac-final-artifact")
        print(f"artifact={args.artifact.name}")
        print(f"candidate_sha256={digest_path(args.artifact / AC_BOOT_FILE)}")
        print(f"candidate_size={(args.artifact / AC_BOOT_FILE).stat().st_size}")
        print(f"image_gz_sha256={AB_IMAGE_GZ_SHA256}")
        print(f"dtb_sha256={AB_DTB_SHA256}")
        print(f"keymap_sha256={AB_KEYMAP_SHA256}")
        print("baseline=exact-hardware-passed-ab")
        print("component_validators=passed")
        print("deterministic_reconstruction=passed")
        print("lk_gates=32-of-32")
        print("manifest_inventory_modes=passed")
        print("hardware_write=none")
        return 0
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
