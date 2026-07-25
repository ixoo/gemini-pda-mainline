#!/usr/bin/env python3
"""Validate a complete Candidate AA artifact and rerun its component gates."""

from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import re
import stat
import subprocess
import sys


IMAGE_GZ_SHA256 = "d69b2cdc0a2dca05919e5e0dc25c54920a509af89eb1a7f16336e82d368fda41"
DTB_SHA256 = "bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f"
INPUT_HELPER_SHA256 = "b9b555ce176a8bb29b492a73f06288784baf4f54786bed514ff1230efd732602"
KEYMAP_SHA256 = "02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c"
UNICODE_SOURCE_SHA256 = "4a3f8064dddb5845886453bc0fdc5753e87b3f6ef8ce064c0c2a32fb7c7bf357"
UNICODE_HELPER_SHA256 = "5949ee28aedeb8f8ba7b5486abbec7714034f7b833265bace9a1438b8a1dd650"
VERIFIER_SOURCE_SHA256 = "70d70bcef6e403d850c32b85f4bab928b2eb1444fae68ec3f629d7ff7c22785d"
# CALIBRATION: replace from the pinned recovery VM after verifier source is final.
KEYMAP_VERIFIER_SHA256 = "29735d212e74d0b0040a3ead173a83223b89ce5d947b697a115707eb3d23b238"
EXPECTED_FILES = {
    "SHA256SUMS",
    "Image.gz",
    "boot-build.txt",
    "boot-validation.txt",
    "console-unicode-mode",
    "console-keymap-verify",
    "gemini-keyboard-console-map-initramfs.img",
    "gemini-keyboard-console-map.boot.img",
    "gemini-us.bkeymap",
    "initramfs-build.txt",
    "initramfs-validation.txt",
    "input-event-capture",
    "input-tree.sha256",
    "keymap-test.txt",
    "keymap-validation.txt",
    "keymap-verifier-test.txt",
    "lk-analysis.txt",
    "mt6797-gemini-pda-keyboard-console-map.dtb",
    "provenance.txt",
    "source-build.json",
    "z-baseline-validation.txt",
}
SOURCE_PATHS = (
    "initramfs/init",
    "initramfs/local-shell",
    "initramfs/x-record",
    "src/console-unicode-mode.c",
    "src/console-keymap-verify.c",
    "scripts/generate-console-keymap.py",
    "scripts/validate-console-keymap.py",
    "scripts/test-console-keymap.py",
    "scripts/test-keymap-verifier.py",
    "scripts/validate-z-baseline.py",
    "scripts/build-initramfs.sh",
    "scripts/validate-initramfs.py",
    "scripts/build-boot-from-z.py",
    "scripts/validate-boot.py",
    "scripts/validate-final-artifact.py",
    "scripts/build-keyboard-console-map-candidate.sh",
    "scripts/test-validator-mutations.py",
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_regular(path: pathlib.Path, mode: int = 0o600) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode):
        raise ValueError(f"not a regular non-symlink file: {path.name}")
    if stat.S_IMODE(info.st_mode) != mode:
        raise ValueError(f"unexpected mode for {path.name}")
    return path.read_bytes()


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


def parse_provenance(data: bytes) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in data.decode("utf-8").splitlines():
        if "=" not in line:
            raise ValueError("malformed provenance line")
        key, value = line.split("=", 1)
        if not re.fullmatch(r"[a-z0-9_]+", key) or key in fields:
            raise ValueError("invalid or duplicate provenance key")
        fields[key] = value
    return fields


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=pathlib.Path, required=True)
    parser.add_argument("--baseline", type=pathlib.Path, required=True)
    parser.add_argument("--defkeymap", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        artifact = args.artifact
        if artifact.is_symlink() or not artifact.is_dir():
            raise ValueError("artifact is not a regular directory")
        if stat.S_IMODE(artifact.stat().st_mode) != 0o700:
            raise ValueError("artifact directory mode is not 0700")
        if {item.name for item in artifact.iterdir()} != EXPECTED_FILES:
            raise ValueError("final artifact inventory mismatch")
        contents: dict[str, bytes] = {}
        for name in EXPECTED_FILES:
            mode = (
                0o755
                if name
                in {"console-keymap-verify", "console-unicode-mode", "input-event-capture"}
                else 0o600
            )
            contents[name] = read_regular(artifact / name, mode)

        manifest: dict[str, str] = {}
        for line in contents["SHA256SUMS"].decode("ascii").splitlines():
            fields = line.split(maxsplit=1)
            if len(fields) != 2:
                raise ValueError("malformed final manifest")
            checksum, name = fields
            name = name.removeprefix("*").removeprefix("./")
            if not re.fullmatch(r"[0-9a-f]{64}", checksum) or name in manifest:
                raise ValueError("invalid or duplicate final manifest entry")
            manifest[name] = checksum
        if set(manifest) != EXPECTED_FILES - {"SHA256SUMS"}:
            raise ValueError("final manifest inventory mismatch")
        for name, expected in manifest.items():
            if digest(contents[name]) != expected:
                raise ValueError(f"final manifest checksum mismatch: {name}")

        boot_name = "gemini-keyboard-console-map.boot.img"
        initramfs_name = "gemini-keyboard-console-map-initramfs.img"
        dtb_name = "mt6797-gemini-pda-keyboard-console-map.dtb"
        boot_hash = digest(contents[boot_name])
        if artifact.name != f"candidate-AA-keyboard-console-map-final-{boot_hash[:8]}":
            raise ValueError("artifact basename does not match its boot hash")
        if digest(contents["Image.gz"]) != IMAGE_GZ_SHA256:
            raise ValueError("exact Candidate Z Image.gz changed")
        if digest(contents[dtb_name]) != DTB_SHA256:
            raise ValueError("exact Candidate Z DTB changed")
        if digest(contents["input-event-capture"]) != INPUT_HELPER_SHA256:
            raise ValueError("exact Candidate Z input helper changed")
        if digest(contents["gemini-us.bkeymap"]) != KEYMAP_SHA256:
            raise ValueError("Gemini keymap changed")
        if digest(contents["console-unicode-mode"]) != UNICODE_HELPER_SHA256:
            raise ValueError("console Unicode helper changed")
        if digest(contents["console-keymap-verify"]) != KEYMAP_VERIFIER_SHA256:
            raise ValueError("console keymap verifier changed")
        if contents["source-build.json"] != read_regular(args.baseline / "source-build.json"):
            raise ValueError("source-build provenance differs from exact Candidate Z")

        script_dir = pathlib.Path(__file__).resolve().parent
        experiment_dir = script_dir.parent
        repo_root = experiment_dir.parent.parent
        if digest((experiment_dir / "src/console-unicode-mode.c").read_bytes()) != UNICODE_SOURCE_SHA256:
            raise ValueError("console Unicode helper source changed")
        if digest((experiment_dir / "src/console-keymap-verify.c").read_bytes()) != VERIFIER_SOURCE_SHA256:
            raise ValueError("console keymap verifier source changed")
        analyzer = repo_root / "experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
        if digest(analyzer.read_bytes()) != "aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95":
            raise ValueError("LK analyzer identity mismatch")
        z_boot = args.baseline / "gemini-keyboard-reboot-dispatch.boot.img"
        z_initramfs = args.baseline / "gemini-keyboard-reboot-dispatch-initramfs.img"

        expected_baseline = run([
            sys.executable,
            os.fspath(script_dir / "validate-z-baseline.py"),
            "--baseline",
            os.fspath(args.baseline),
        ])
        if expected_baseline != contents["z-baseline-validation.txt"]:
            raise ValueError("saved exact-Z validation differs from fresh output")
        expected_keymap = run([
            sys.executable,
            os.fspath(script_dir / "validate-console-keymap.py"),
            "--source",
            os.fspath(args.defkeymap),
            "--keymap",
            os.fspath(artifact / "gemini-us.bkeymap"),
        ])
        if expected_keymap != contents["keymap-validation.txt"]:
            raise ValueError("saved keymap validation differs from fresh output")
        expected_keymap_test = run([
            sys.executable,
            os.fspath(script_dir / "test-console-keymap.py"),
            "--source",
            os.fspath(args.defkeymap),
        ])
        if expected_keymap_test != contents["keymap-test.txt"]:
            raise ValueError("saved keymap tests differ from fresh output")
        expected_verifier_test = run([
            sys.executable,
            os.fspath(script_dir / "test-keymap-verifier.py"),
            "--verifier",
            os.fspath(artifact / "console-keymap-verify"),
            "--keymap",
            os.fspath(artifact / "gemini-us.bkeymap"),
        ])
        if expected_verifier_test != contents["keymap-verifier-test.txt"]:
            raise ValueError("saved keymap verifier tests differ from fresh output")
        expected_initramfs = run([
            sys.executable,
            os.fspath(script_dir / "validate-initramfs.py"),
            "--baseline",
            os.fspath(z_initramfs),
            "--candidate",
            os.fspath(artifact / initramfs_name),
            "--source-dir",
            os.fspath(experiment_dir / "initramfs"),
            "--keymap",
            os.fspath(artifact / "gemini-us.bkeymap"),
            "--unicode-helper",
            os.fspath(artifact / "console-unicode-mode"),
            "--keymap-verifier",
            os.fspath(artifact / "console-keymap-verify"),
        ])
        if expected_initramfs != contents["initramfs-validation.txt"]:
            raise ValueError("saved initramfs validation differs from fresh output")
        expected_boot = run([
            sys.executable,
            os.fspath(script_dir / "validate-boot.py"),
            "--z-boot",
            os.fspath(z_boot),
            "--z-initramfs",
            os.fspath(z_initramfs),
            "--aa-boot",
            os.fspath(artifact / boot_name),
            "--aa-initramfs",
            os.fspath(artifact / initramfs_name),
            "--dtb",
            os.fspath(artifact / dtb_name),
        ])
        if expected_boot != contents["boot-validation.txt"]:
            raise ValueError("saved boot validation differs from fresh output")
        expected_lk = run([
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
            "bootopt=64S3,32N2,64N2",
            os.fspath(artifact / boot_name),
        ])
        if expected_lk != contents["lk-analysis.txt"] or expected_lk.count(b"gate_") != 32:
            raise ValueError("saved LK analysis differs or lacks 32 gates")

        expected_input_tree = "".join(
            f"{digest(read_regular(experiment_dir / relative, 0o755 if relative.startswith(('initramfs/', 'scripts/')) else 0o644))}  {relative}\n"
            for relative in SOURCE_PATHS
        ).encode("ascii")
        if contents["input-tree.sha256"] != expected_input_tree:
            raise ValueError("saved input tree differs from current build sources")

        provenance = parse_provenance(contents["provenance.txt"])
        required = {
            "experiment": "2026-07-20-keyboard-console-map-diagnostic",
            "candidate_label": "AA",
            "candidate_revision": "r1",
            "marker": "GEMINI_KEYBOARD_CONSOLE_MAP_20260720_AA_R1",
            "kernel_field": "byte-exact-candidate-z",
            "dtb_lineage": "byte-exact-candidate-z",
            "config_lineage": "byte-exact-candidate-z",
            "candidate_initramfs_sha256": digest(contents[initramfs_name]),
            "candidate_sha256": boot_hash,
            "candidate_size": str(len(contents[boot_name])),
            "keymap_sha256": KEYMAP_SHA256,
            "unicode_helper_source_sha256": UNICODE_SOURCE_SHA256,
            "unicode_helper_sha256": UNICODE_HELPER_SHA256,
            "keymap_verifier_source_sha256": VERIFIER_SOURCE_SHA256,
            "keymap_verifier_sha256": KEYMAP_VERIFIER_SHA256,
            "keymap_runtime_gate": (
                "sha256-K_UNICODE-existing-KDG-or-preflight-load-"
                "KDGKBENT-2048-kernel-entries"
            ),
            "keyboard_matrix": "byte-exact-candidate-z",
            "reboot_dispatch": "byte-exact-candidate-z",
            "watchdog_recovery": "byte-exact-candidate-z",
            "runtime_result": "not-tested",
        }
        for name, expected in required.items():
            if provenance.get(name) != expected:
                raise ValueError(f"provenance mismatch: {name}")

        print("validation=candidate-aa-final-artifact")
        print(f"artifact={artifact.name}")
        print(f"candidate_sha256={boot_hash}")
        print(f"candidate_size={len(contents[boot_name])}")
        print(f"candidate_initramfs_sha256={digest(contents[initramfs_name])}")
        print(f"keymap_sha256={KEYMAP_SHA256}")
        print(f"keymap_verifier_sha256={KEYMAP_VERIFIER_SHA256}")
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
