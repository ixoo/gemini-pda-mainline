#!/usr/bin/env python3
"""Require Candidate AA validators to reject focused corruptions."""

from __future__ import annotations

import argparse
import os
import pathlib
import shutil
import struct
import subprocess
import sys
import tempfile


def run(command: list[str], expected: int) -> None:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(command, capture_output=True, check=False, env=environment)
    if result.returncode != expected:
        raise RuntimeError(
            f"unexpected status {result.returncode}, expected {expected}: {command}\n"
            f"stdout={result.stdout.decode(errors='replace')}\n"
            f"stderr={result.stderr.decode(errors='replace')}"
        )


def flip(data: bytes, offset: int) -> bytes:
    result = bytearray(data)
    result[offset] ^= 0x01
    return bytes(result)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=pathlib.Path, required=True)
    parser.add_argument("--baseline", type=pathlib.Path, required=True)
    parser.add_argument("--defkeymap", type=pathlib.Path, required=True)
    args = parser.parse_args()
    script_dir = pathlib.Path(__file__).resolve().parent
    experiment_dir = script_dir.parent
    python = sys.executable

    final_validator = script_dir / "validate-final-artifact.py"
    baseline_validator = script_dir / "validate-z-baseline.py"
    boot_validator = script_dir / "validate-boot.py"
    initramfs_validator = script_dir / "validate-initramfs.py"
    keymap_validator = script_dir / "validate-console-keymap.py"
    z_boot = args.baseline / "gemini-keyboard-reboot-dispatch.boot.img"
    z_initramfs = args.baseline / "gemini-keyboard-reboot-dispatch-initramfs.img"
    aa_boot = args.artifact / "gemini-keyboard-console-map.boot.img"
    aa_initramfs = args.artifact / "gemini-keyboard-console-map-initramfs.img"
    dtb = args.artifact / "mt6797-gemini-pda-keyboard-console-map.dtb"
    keymap = args.artifact / "gemini-us.bkeymap"
    helper = args.artifact / "console-unicode-mode"
    verifier = args.artifact / "console-keymap-verify"

    try:
        run(
            [
                python,
                os.fspath(final_validator),
                "--artifact",
                os.fspath(args.artifact),
                "--baseline",
                os.fspath(args.baseline),
                "--defkeymap",
                os.fspath(args.defkeymap),
            ],
            0,
        )
        with tempfile.TemporaryDirectory(prefix="candidate-aa-mutations-") as temp_name:
            temp = pathlib.Path(temp_name)

            extra = temp / args.artifact.name
            shutil.copytree(args.artifact, extra, copy_function=shutil.copy2)
            os.chmod(extra, 0o700)
            (extra / "unexpected").write_bytes(b"unexpected\n")
            run(
                [python, os.fspath(final_validator), "--artifact", os.fspath(extra),
                 "--baseline", os.fspath(args.baseline), "--defkeymap", os.fspath(args.defkeymap)],
                2,
            )

            manifest = temp / "manifest" / args.artifact.name
            shutil.copytree(args.artifact, manifest, copy_function=shutil.copy2)
            os.chmod(manifest, 0o700)
            provenance = manifest / "provenance.txt"
            provenance.write_bytes(provenance.read_bytes() + b"mutation=yes\n")
            os.chmod(provenance, 0o600)
            run(
                [python, os.fspath(final_validator), "--artifact", os.fspath(manifest),
                 "--baseline", os.fspath(args.baseline), "--defkeymap", os.fspath(args.defkeymap)],
                2,
            )

            bad_baseline = temp / args.baseline.name
            shutil.copytree(args.baseline, bad_baseline, copy_function=shutil.copy2)
            os.chmod(bad_baseline, 0o700)
            baseline_manifest = bad_baseline / "SHA256SUMS"
            baseline_manifest.write_bytes(flip(baseline_manifest.read_bytes(), 0))
            os.chmod(baseline_manifest, 0o600)
            run(
                [python, os.fspath(baseline_validator), "--baseline", os.fspath(bad_baseline)],
                2,
            )

            bad_boot = temp / "bad.boot.img"
            bad_boot.write_bytes(flip(aa_boot.read_bytes(), 4096))
            run(
                [python, os.fspath(boot_validator), "--z-boot", os.fspath(z_boot),
                 "--z-initramfs", os.fspath(z_initramfs), "--aa-boot", os.fspath(bad_boot),
                 "--aa-initramfs", os.fspath(aa_initramfs), "--dtb", os.fspath(dtb)],
                2,
            )

            bad_initramfs = temp / "bad-initramfs.img"
            bad_initramfs.write_bytes(flip(aa_initramfs.read_bytes(), 32))
            run(
                [python, os.fspath(initramfs_validator), "--baseline", os.fspath(z_initramfs),
                 "--candidate", os.fspath(bad_initramfs), "--source-dir",
                 os.fspath(experiment_dir / "initramfs"), "--keymap", os.fspath(keymap),
                 "--unicode-helper", os.fspath(helper),
                 "--keymap-verifier", os.fspath(verifier)],
                2,
            )

            bad_helper = temp / "bad-helper"
            helper_data = bytearray(helper.read_bytes())
            struct.pack_into("<H", helper_data, 18, 62)  # EM_X86_64, not AArch64
            bad_helper.write_bytes(helper_data)
            run(
                [python, os.fspath(initramfs_validator), "--baseline", os.fspath(z_initramfs),
                 "--candidate", os.fspath(aa_initramfs), "--source-dir",
                 os.fspath(experiment_dir / "initramfs"), "--keymap", os.fspath(keymap),
                 "--unicode-helper", os.fspath(bad_helper),
                 "--keymap-verifier", os.fspath(verifier)],
                2,
            )

            bad_verifier = temp / "bad-verifier"
            verifier_data = bytearray(verifier.read_bytes())
            struct.pack_into("<H", verifier_data, 18, 62)  # EM_X86_64, not AArch64
            bad_verifier.write_bytes(verifier_data)
            run(
                [python, os.fspath(initramfs_validator), "--baseline", os.fspath(z_initramfs),
                 "--candidate", os.fspath(aa_initramfs), "--source-dir",
                 os.fspath(experiment_dir / "initramfs"), "--keymap", os.fspath(keymap),
                 "--unicode-helper", os.fspath(helper),
                 "--keymap-verifier", os.fspath(bad_verifier)],
                2,
            )

            bad_keymap = temp / "bad-keymap"
            keymap_data = bytearray(keymap.read_bytes())
            keymap_data[7 + 6] = 1  # Add a forbidden table without its payload.
            bad_keymap.write_bytes(keymap_data)
            run(
                [python, os.fspath(keymap_validator), "--source", os.fspath(args.defkeymap),
                 "--keymap", os.fspath(bad_keymap)],
                2,
            )
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print("clean_final_validation=PASS")
    print("final_inventory_mutation=REJECTED")
    print("final_manifest_mutation=REJECTED")
    print("baseline_manifest_mutation=REJECTED")
    print("boot_kernel_mutation=REJECTED")
    print("initramfs_stream_mutation=REJECTED")
    print("unicode_helper_arch_mutation=REJECTED")
    print("keymap_verifier_arch_mutation=REJECTED")
    print("keymap_table_mutation=REJECTED")
    print("mutations=8/8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
