#!/usr/bin/env python3
"""Validate Candidate Y's complete final artifact and rerun every component gate."""

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
EXPECTED_FILES = {
    "SHA256SUMS",
    "Image.gz",
    "boot-build.txt",
    "boot-validation.txt",
    "gemini-keyboard-typed-watchdog-reboot-initramfs.img",
    "gemini-keyboard-typed-watchdog-reboot.boot.img",
    "initramfs-build.txt",
    "initramfs-validation.txt",
    "input-event-capture",
    "input-tree.sha256",
    "lk-analysis.txt",
    "mt6797-gemini-pda-keyboard-typed-watchdog-reboot.dtb",
    "provenance.txt",
    "source-build.json",
    "x-baseline-validation.txt",
}
HEX256 = re.compile(r"^[0-9a-f]{64}$")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_regular(path: pathlib.Path, mode: int) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode):
        raise ValueError(f"artifact entry is not regular: {path.name}")
    if stat.S_IMODE(info.st_mode) != mode:
        raise ValueError(f"artifact mode mismatch: {path.name}")
    return path.read_bytes()


def run(command: list[str]) -> bytes:
    completed = subprocess.run(command, check=False, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
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

        boot = contents["gemini-keyboard-typed-watchdog-reboot.boot.img"]
        boot_hash = digest(boot)
        expected_basename = f"candidate-Y-keyboard-typed-watchdog-reboot-final-{boot_hash[:8]}"
        if artifact.name != expected_basename:
            raise ValueError("final artifact basename does not match its boot hash")

        script_dir = pathlib.Path(__file__).resolve().parent
        experiment_dir = script_dir.parent
        repo_root = experiment_dir.parent.parent
        analyzer = repo_root / "experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
        if analyzer.is_symlink() or digest(analyzer.read_bytes()) != ANALYZER_SHA256:
            raise ValueError("LK analyzer identity mismatch")
        x_validator = script_dir / "validate-x-baseline.py"
        initramfs_validator = script_dir / "validate-initramfs.py"
        boot_validator = script_dir / "validate-boot.py"
        y_initramfs = artifact / "gemini-keyboard-typed-watchdog-reboot-initramfs.img"
        y_boot = artifact / "gemini-keyboard-typed-watchdog-reboot.boot.img"
        dtb = artifact / "mt6797-gemini-pda-keyboard-typed-watchdog-reboot.dtb"
        x_boot = args.baseline / "gemini-keyboard-manual-reboot.boot.img"
        x_initramfs = args.baseline / "gemini-keyboard-manual-reboot-initramfs.img"

        expected_x = run([sys.executable, os.fspath(x_validator), "--baseline", os.fspath(args.baseline)])
        if expected_x != contents["x-baseline-validation.txt"]:
            raise ValueError("saved exact-X validation differs from a fresh run")
        expected_initramfs = run([
            sys.executable, os.fspath(initramfs_validator), "--baseline", os.fspath(x_initramfs),
            "--candidate", os.fspath(y_initramfs), "--source-dir", os.fspath(experiment_dir / "initramfs"),
        ])
        if expected_initramfs != contents["initramfs-validation.txt"]:
            raise ValueError("saved initramfs validation differs from a fresh run")
        expected_boot = run([
            sys.executable, os.fspath(boot_validator), "--x-boot", os.fspath(x_boot),
            "--x-initramfs", os.fspath(x_initramfs), "--y-boot", os.fspath(y_boot),
            "--y-initramfs", os.fspath(y_initramfs), "--dtb", os.fspath(dtb),
        ])
        if expected_boot != contents["boot-validation.txt"]:
            raise ValueError("saved boot validation differs from a fresh run")
        expected_lk = run([
            sys.executable, os.fspath(analyzer), "--validate-lk",
            "--expected-image-gz", os.fspath(artifact / "Image.gz"),
            "--expected-ramdisk", os.fspath(y_initramfs), "--expected-dtb", os.fspath(dtb),
            "--expected-name", "gemini-obs-L", "--expected-cmdline", "bootopt=64S3,32N2,64N2",
            os.fspath(y_boot),
        ])
        if expected_lk != contents["lk-analysis.txt"]:
            raise ValueError("saved LK analysis differs from a fresh 32-gate run")
        if expected_lk.count(b"gate_") != 32 or b"lk_validation=passed" not in expected_lk:
            raise ValueError("LK analyzer did not report all 32 passing gates")

        provenance = contents["provenance.txt"].decode("utf-8")
        for token in (
            f"candidate_sha256={boot_hash}",
            f"candidate_initramfs_sha256={digest(contents['gemini-keyboard-typed-watchdog-reboot-initramfs.img'])}",
            "kernel_field=byte-exact-candidate-x",
            "dtb_lineage=byte-exact-candidate-x",
            "watchdog_ownership=typed-only",
            "watchdog_userspace_ping_count=one",
            "software_reboot_fallback=none",
        ):
            if token not in provenance:
                raise ValueError(f"final provenance token absent: {token}")

        print("validation=candidate-y-final-artifact")
        print(f"artifact={artifact.name}")
        print(f"candidate_sha256={boot_hash}")
        print(f"candidate_size={len(boot)}")
        print("component_validators=passed")
        print("lk_gates=32-of-32")
        print("manifest_inventory_modes=passed")
        print("hardware_write=none")
        return 0
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
