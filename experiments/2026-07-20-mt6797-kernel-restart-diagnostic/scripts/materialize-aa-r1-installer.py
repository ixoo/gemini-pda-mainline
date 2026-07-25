#!/usr/bin/env python3
"""Materialize the exact hardware-passed AA r1 installer foundation."""

from __future__ import annotations

import argparse
import os
import pathlib
import stat
import subprocess
import sys
import tempfile

from ab_contract import (
    AA_BOOT_SHA256,
    AA_BOOT_SIZE,
    AA_R1_INSTALLER_SHA256,
    AA_R1_PADDED_SHA256,
    digest_path,
)


AA_R0_RAW_SHA256 = "a2ad7a4107abd99cbd349b8f2deadd0185cbdd5bb0884ecbdae8ff2a7499ed4c"
AA_R0_RAW_SIZE = "7120896"
AA_R0_PADDED_SHA256 = "157c7cd5d814d7b2704d679faacd3215c5e889642b4261441f99653957585eaa"
FOUNDATIONS = {
    "experiments/2026-07-19-keyboard-manual-reboot-diagnostic/scripts/"
    "install-candidate-x-boot2.sh": (
        "2ae4e2a3ee4741bff80b87f8b32fef44bdfefdc1a870c876d0ea95feb247a79e"
    ),
    "experiments/2026-07-19-keyboard-typed-watchdog-reboot-diagnostic/scripts/"
    "derive-installer.py": (
        "ac343dc456f90098fbe28062148aa2f79d1b27b436ce7065a71e8a56c13f24e7"
    ),
    "experiments/2026-07-19-keyboard-reboot-dispatch-diagnostic/scripts/"
    "derive-installer.py": (
        "7bd871c8b068a3330996d145a1979c076d79db032e7b0efe97d868a00664f51a"
    ),
    "experiments/2026-07-20-keyboard-console-map-diagnostic/scripts/"
    "derive-installer.py": (
        "acbd27b3cf782ce7930059b4c91e00b113399a503fb84e9296a06b6199f65d1a"
    ),
    "experiments/2026-07-20-keyboard-console-map-diagnostic/scripts/"
    "derive-revision-installer.py": (
        "cd3676188f4d77fcff3321bdf046c46999e1859ba91903a08e6781928e983fb9"
    ),
}
Y_RAW_SHA256 = "94edd593924c52f0224f1ba2134120b54516e622aee3c52de2781a4ec8e889ee"
Y_PADDED_SHA256 = "dab4a5217ddffe32062819febc3160f0a12eb97ac8afbf0bc4f068ce3c72cb17"
Y_INSTALLER_SHA256 = "923bca5daab72afcf46fbd2de6abd1f81bf3412a990c938aff68ccec3f4a3e67"
Z_RAW_SHA256 = "985a6472b7fdbfd4c58da4773a8c2cae1e3aa40ea90240eb2b309390ed7674b9"
Z_PADDED_SHA256 = "ba21e6424f94c82f14fd51b5681eea68d6cf09e9177e4f9ca2061c9f129abb40"
Z_INSTALLER_SHA256 = "38b5956e3f5146bc2c8e8ddc3cec9cfb8be25bd3661949b5bd8fb5dbdba51b76"
AA_R0_INSTALLER_SHA256 = (
    "c920eca1207dfe1362f947a74935a50fd934574f7becae4d056b09f362d46196"
)


def run(command: list[str]) -> None:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(command, capture_output=True, check=False, env=environment)
    if result.returncode:
        raise ValueError(
            f"foundation command failed ({result.returncode}): {' '.join(command)}: "
            f"{result.stderr.decode('utf-8', errors='replace').strip()}"
        )


def derive(
    deriver: pathlib.Path,
    source: pathlib.Path,
    output: pathlib.Path,
    raw_sha256: str,
    raw_size: str,
    padded_sha256: str,
    expected_sha256: str,
) -> None:
    run(
        [
            sys.executable,
            os.fspath(deriver),
            "--source",
            os.fspath(source),
            "--output",
            os.fspath(output),
            "--raw-sha256",
            raw_sha256,
            "--raw-size",
            raw_size,
            "--padded-sha256",
            padded_sha256,
        ]
    )
    if output.is_symlink() or not output.is_file() or digest_path(output) != expected_sha256:
        raise ValueError("derived installer lineage identity changed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    script_dir = pathlib.Path(__file__).resolve().parent
    repo_root = script_dir.parents[2]
    previous_umask = os.umask(0o077)
    try:
        if not args.output.name or args.output.name in {".", ".."}:
            raise ValueError("installer output filename is invalid")
        output_parent = args.output.parent.resolve(strict=True)
        if args.output.parent.is_symlink() or not output_parent.is_dir():
            raise ValueError("installer output parent is missing or unsafe")
        output = output_parent / args.output.name
        if output.exists() or output.is_symlink():
            raise ValueError("refusing to overwrite AA r1 installer foundation")

        resolved: dict[str, pathlib.Path] = {}
        for relative, expected in FOUNDATIONS.items():
            foundation = repo_root / relative
            info = foundation.lstat()
            if foundation.is_symlink() or not stat.S_ISREG(info.st_mode):
                raise ValueError(f"installer lineage input is unsafe: {relative}")
            if digest_path(foundation) != expected:
                raise ValueError(f"installer lineage input changed: {relative}")
            resolved[relative] = foundation

        x_installer = resolved[
            "experiments/2026-07-19-keyboard-manual-reboot-diagnostic/scripts/"
            "install-candidate-x-boot2.sh"
        ]
        y_deriver = resolved[
            "experiments/2026-07-19-keyboard-typed-watchdog-reboot-diagnostic/scripts/"
            "derive-installer.py"
        ]
        z_deriver = resolved[
            "experiments/2026-07-19-keyboard-reboot-dispatch-diagnostic/scripts/"
            "derive-installer.py"
        ]
        aa_r0_deriver = resolved[
            "experiments/2026-07-20-keyboard-console-map-diagnostic/scripts/"
            "derive-installer.py"
        ]
        aa_r1_deriver = resolved[
            "experiments/2026-07-20-keyboard-console-map-diagnostic/scripts/"
            "derive-revision-installer.py"
        ]

        with tempfile.TemporaryDirectory(
            prefix=".candidate-aa-r1-foundation.", dir=output_parent
        ) as raw_temp:
            temp = pathlib.Path(raw_temp)
            y_installer = temp / "install-candidate-y-boot2.sh"
            derive(
                y_deriver,
                x_installer,
                y_installer,
                Y_RAW_SHA256,
                "6866944",
                Y_PADDED_SHA256,
                Y_INSTALLER_SHA256,
            )
            z_installer = temp / "install-candidate-z-boot2.sh"
            derive(
                z_deriver,
                y_installer,
                z_installer,
                Z_RAW_SHA256,
                "6866944",
                Z_PADDED_SHA256,
                Z_INSTALLER_SHA256,
            )
            aa_r0_installer = temp / "install-candidate-aa-r0-boot2.sh"
            derive(
                aa_r0_deriver,
                z_installer,
                aa_r0_installer,
                AA_R0_RAW_SHA256,
                AA_R0_RAW_SIZE,
                AA_R0_PADDED_SHA256,
                AA_R0_INSTALLER_SHA256,
            )
            aa_r1_installer = temp / "install-candidate-aa-r1-boot2.sh"
            derive(
                aa_r1_deriver,
                aa_r0_installer,
                aa_r1_installer,
                AA_BOOT_SHA256,
                str(AA_BOOT_SIZE),
                AA_R1_PADDED_SHA256,
                AA_R1_INSTALLER_SHA256,
            )
            run(["bash", "-n", os.fspath(aa_r1_installer)])
            aa_r1_installer.chmod(0o700)
            os.link(aa_r1_installer, output, follow_symlinks=False)

        if digest_path(output) != AA_R1_INSTALLER_SHA256:
            raise ValueError("published AA r1 installer foundation changed")
        if stat.S_IMODE(output.stat().st_mode) != 0o700:
            raise ValueError("published AA r1 installer mode is not 0700")
        print("validation=exact-aa-r1-installer-foundation")
        print(f"output={output}")
        print(f"installer_sha256={AA_R1_INSTALLER_SHA256}")
        print("lineage=X,Y,Z,AA-r0,AA-r1")
        print("device_contact=none")
        print("hardware_write=none")
        return 0
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    finally:
        os.umask(previous_umask)


if __name__ == "__main__":
    raise SystemExit(main())
