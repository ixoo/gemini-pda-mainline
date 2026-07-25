#!/usr/bin/env python3
"""Validate Candidate Z's complete final artifact and rerun every component gate."""

from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import re
import stat
import subprocess
import sys


ANALYZER_SHA256 = "aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95"
Y_MANIFEST_SHA256 = "310ac503b4bbd8c5a3d5c31bcecb473064d5207ff30ad73111325ffe1a1c56a6"
Y_BOOT_SHA256 = "94edd593924c52f0224f1ba2134120b54516e622aee3c52de2781a4ec8e889ee"
Y_INITRAMFS_SHA256 = "11b0a8ecb144ebde0c9802e0cf7357b2d74b95e8ba44fbf6007a9f4d0d8bf3e2"
Y_DTB_SHA256 = "bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f"
EXPECTED_FILES = {
    "SHA256SUMS",
    "Image.gz",
    "ash-dispatch-validation.txt",
    "boot-build.txt",
    "boot-validation.txt",
    "gemini-keyboard-reboot-dispatch-initramfs.img",
    "gemini-keyboard-reboot-dispatch.boot.img",
    "initramfs-build.txt",
    "initramfs-validation.txt",
    "input-event-capture",
    "input-tree.sha256",
    "lk-analysis.txt",
    "mt6797-gemini-pda-keyboard-reboot-dispatch.dtb",
    "provenance.txt",
    "source-build.json",
    "y-baseline-validation.txt",
}
HEX256 = re.compile(r"^[0-9a-f]{64}$")
SOURCE_PATHS = (
    "initramfs/init",
    "initramfs/local-shell",
    "initramfs/reboot",
    "initramfs/x-record",
    "initramfs/reboot-dispatch.env",
    "scripts/validate-y-baseline.py",
    "scripts/build-initramfs.sh",
    "scripts/validate-initramfs.py",
    "scripts/validate-ash-dispatch.py",
    "scripts/build-boot-from-y.py",
    "scripts/validate-boot.py",
    "scripts/validate-final-artifact.py",
    "scripts/build-keyboard-reboot-dispatch-candidate.sh",
    "scripts/test-validator-mutations.sh",
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_regular(path: pathlib.Path, mode: int) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode):
        raise ValueError(f"artifact entry is not regular: {path.name}")
    if stat.S_IMODE(info.st_mode) != mode:
        raise ValueError(f"artifact mode mismatch: {path.name}")
    return path.read_bytes()


def read_source(path: pathlib.Path) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode):
        raise ValueError(f"build source is not regular: {path}")
    return path.read_bytes()


def run(command: list[str]) -> bytes:
    completed = subprocess.run(
        command, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", "replace").strip()
        raise ValueError(f"component validator failed: {detail}")
    return completed.stdout


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=pathlib.Path, required=True)
    parser.add_argument("--baseline", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        artifact = args.artifact
        if artifact.is_symlink() or not artifact.is_dir():
            raise ValueError("artifact is not a regular directory")
        if stat.S_IMODE(artifact.stat().st_mode) != 0o700:
            raise ValueError("artifact directory mode is not 0700")
        inventory = {item.name for item in artifact.iterdir()}
        if inventory != EXPECTED_FILES:
            raise ValueError("final artifact inventory mismatch")
        contents: dict[str, bytes] = {}
        for name in EXPECTED_FILES:
            mode = 0o755 if name == "input-event-capture" else 0o600
            contents[name] = read_regular(artifact / name, mode)

        manifest: dict[str, str] = {}
        for line in contents["SHA256SUMS"].decode("ascii").splitlines():
            fields = line.split(maxsplit=1)
            if len(fields) != 2:
                raise ValueError("malformed final SHA256SUMS")
            checksum, name = fields
            name = name.removeprefix("*").removeprefix("./")
            if not HEX256.fullmatch(checksum) or name in manifest:
                raise ValueError("invalid or duplicate final manifest entry")
            manifest[name] = checksum
        if set(manifest) != EXPECTED_FILES - {"SHA256SUMS"}:
            raise ValueError("final manifest inventory mismatch")
        for name, expected in manifest.items():
            if digest(contents[name]) != expected:
                raise ValueError(f"final manifest checksum mismatch: {name}")

        boot_name = "gemini-keyboard-reboot-dispatch.boot.img"
        initramfs_name = "gemini-keyboard-reboot-dispatch-initramfs.img"
        dtb_name = "mt6797-gemini-pda-keyboard-reboot-dispatch.dtb"
        boot = contents[boot_name]
        boot_hash = digest(boot)
        expected_basename = f"candidate-Z-keyboard-reboot-dispatch-final-{boot_hash[:8]}"
        if artifact.name != expected_basename:
            raise ValueError("final artifact basename does not match its boot hash")

        script_dir = pathlib.Path(__file__).resolve().parent
        experiment_dir = script_dir.parent
        repo_root = experiment_dir.parent.parent
        analyzer = repo_root / (
            "experiments/2026-07-12-boot-contract-recovery/"
            "scripts/analyze-lk-boot-image.py"
        )
        if analyzer.is_symlink() or digest(analyzer.read_bytes()) != ANALYZER_SHA256:
            raise ValueError("LK analyzer identity mismatch")
        y_validator = script_dir / "validate-y-baseline.py"
        initramfs_validator = script_dir / "validate-initramfs.py"
        dispatch_validator = script_dir / "validate-ash-dispatch.py"
        boot_validator = script_dir / "validate-boot.py"
        z_initramfs = artifact / initramfs_name
        z_boot = artifact / boot_name
        dtb = artifact / dtb_name
        y_boot = args.baseline / "gemini-keyboard-typed-watchdog-reboot.boot.img"
        y_initramfs = (
            args.baseline / "gemini-keyboard-typed-watchdog-reboot-initramfs.img"
        )

        expected_y = run([
            sys.executable, os.fspath(y_validator), "--baseline",
            os.fspath(args.baseline),
        ])
        if expected_y != contents["y-baseline-validation.txt"]:
            raise ValueError("saved exact-Y validation differs from a fresh run")
        baseline_helper = read_regular(
            args.baseline / "input-event-capture", 0o755
        )
        baseline_source_build = read_regular(
            args.baseline / "source-build.json", 0o600
        )
        if contents["input-event-capture"] != baseline_helper:
            raise ValueError("input helper differs from exact Candidate Y")
        if contents["source-build.json"] != baseline_source_build:
            raise ValueError("source-build provenance differs from exact Candidate Y")
        expected_input_tree = "".join(
            f"{digest(read_source(experiment_dir / relative))}  {relative}\n"
            for relative in SOURCE_PATHS
        ).encode("ascii")
        if contents["input-tree.sha256"] != expected_input_tree:
            raise ValueError("saved input tree differs from current exact build sources")
        expected_initramfs = run([
            sys.executable, os.fspath(initramfs_validator), "--baseline",
            os.fspath(y_initramfs), "--candidate", os.fspath(z_initramfs),
            "--source-dir", os.fspath(experiment_dir / "initramfs"),
        ])
        if expected_initramfs != contents["initramfs-validation.txt"]:
            raise ValueError("saved initramfs validation differs from a fresh run")
        dispatch_check = run([
            sys.executable, os.fspath(dispatch_validator), "--initramfs",
            os.fspath(z_initramfs), "--verify-saved",
            os.fspath(artifact / "ash-dispatch-validation.txt"),
        ])
        if b"saved_dispatch_validation=passed\n" not in dispatch_check:
            raise ValueError("saved exact-BusyBox dispatch validation was not accepted")
        expected_boot = run([
            sys.executable, os.fspath(boot_validator), "--y-boot",
            os.fspath(y_boot), "--y-initramfs", os.fspath(y_initramfs),
            "--z-boot", os.fspath(z_boot), "--z-initramfs",
            os.fspath(z_initramfs), "--dtb", os.fspath(dtb),
        ])
        if expected_boot != contents["boot-validation.txt"]:
            raise ValueError("saved boot validation differs from a fresh run")
        expected_lk = run([
            sys.executable, os.fspath(analyzer), "--validate-lk",
            "--expected-image-gz", os.fspath(artifact / "Image.gz"),
            "--expected-ramdisk", os.fspath(z_initramfs),
            "--expected-dtb", os.fspath(dtb), "--expected-name", "gemini-obs-L",
            "--expected-cmdline", "bootopt=64S3,32N2,64N2", os.fspath(z_boot),
        ])
        if expected_lk != contents["lk-analysis.txt"]:
            raise ValueError("saved LK analysis differs from a fresh 32-gate run")
        if expected_lk.count(b"gate_") != 32 or \
                b"lk_validation=passed" not in expected_lk:
            raise ValueError("LK analyzer did not report all 32 passing gates")

        provenance = contents["provenance.txt"].decode("utf-8")
        provenance_fields: dict[str, str] = {}
        for line in provenance.splitlines():
            if "=" not in line:
                raise ValueError("malformed final provenance line")
            key, value = line.split("=", 1)
            if not re.fullmatch(r"[a-z0-9_]+", key) or key in provenance_fields:
                raise ValueError("invalid or duplicate final provenance key")
            provenance_fields[key] = value
        repo_revision = run([
            "git", "-C", os.fspath(repo_root), "rev-parse", "HEAD",
        ]).decode("ascii").strip()
        expected_provenance = {
            "experiment": "2026-07-19-keyboard-reboot-dispatch-diagnostic",
            "candidate_label": "Z",
            "marker": "GEMINI_KEYBOARD_REBOOT_DISPATCH_20260719_Z",
            "repo_revision": repo_revision,
            "y_artifact_manifest_sha256": Y_MANIFEST_SHA256,
            "y_boot_sha256": Y_BOOT_SHA256,
            "y_initramfs_sha256": Y_INITRAMFS_SHA256,
            "y_dtb_sha256": Y_DTB_SHA256,
            "kernel_package": "byte-exact-candidate-y",
            "kernel_field": "byte-exact-candidate-y",
            "dtb_lineage": "byte-exact-candidate-y",
            "config_lineage": "byte-exact-candidate-y",
            "candidate_initramfs_sha256": digest(contents[initramfs_name]),
            "candidate_sha256": boot_hash,
            "candidate_size": str(len(boot)),
            "initramfs_delta": (
                "init,bin/local-shell,bin/reboot,bin/x-record,"
                "+bin/reboot-dispatch.env:0444"
            ),
            "reboot_dispatch": "ENV-alias-absolute-wrapper",
            "runtime_dispatch_oracle": "inherited-exported-ENV",
            "dispatch_validation": "exact-busybox-dynamic-linux-aarch64",
            "clean_tty1_background": "yes",
            "watchdog_ownership": "typed-only",
            "watchdog_timeout_seconds": "31",
            "watchdog_userspace_ping_count": "one",
            "software_reboot_fallback": "none",
            "deterministic_replica": (
                "initramfs-dispatch-result-and-android-v0-byte-identical"
            ),
            "boot2_capacity": "16777216",
            "storage_access": "none",
            "runtime_networking": "none",
            "hardware_write": "none",
            "flash": "none",
            "runtime_result": "not-tested",
        }
        if provenance_fields != expected_provenance:
            raise ValueError("final provenance field inventory or value mismatch")
        for token in (
            f"candidate_sha256={boot_hash}",
            f"candidate_initramfs_sha256={digest(contents[initramfs_name])}",
            "kernel_field=byte-exact-candidate-y",
            "dtb_lineage=byte-exact-candidate-y",
            "initramfs_delta=init,bin/local-shell,bin/reboot,bin/x-record,+bin/reboot-dispatch.env:0444",
            "reboot_dispatch=ENV-alias-absolute-wrapper",
            "runtime_dispatch_oracle=inherited-exported-ENV",
            "dispatch_validation=exact-busybox-dynamic-linux-aarch64",
            "clean_tty1_background=yes",
            "watchdog_ownership=typed-only",
            "watchdog_userspace_ping_count=one",
            "software_reboot_fallback=none",
        ):
            if token not in provenance:
                raise ValueError(f"final provenance token absent: {token}")

        print("validation=candidate-z-final-artifact")
        print(f"artifact={artifact.name}")
        print(f"candidate_sha256={boot_hash}")
        print(f"candidate_size={len(boot)}")
        if b"ash_dispatch_rerun=skipped-incompatible-host\n" in dispatch_check:
            print("ash_dispatch_rerun=skipped-incompatible-host")
        elif b"ash_dispatch_rerun=passed\n" in dispatch_check:
            print("ash_dispatch_rerun=passed")
        else:
            raise ValueError("dispatch validator did not report rerun disposition")
        print("component_validators=passed")
        print("lk_gates=32-of-32")
        print("manifest_inventory_modes=passed")
        print("exact_y_payloads=input-event-capture,source-build")
        print("input_tree=current-exact-build-sources")
        print("hardware_write=none")
        return 0
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
