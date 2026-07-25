#!/usr/bin/env python3
"""Validate Candidate AB, compute its padded identity, and derive its installer."""

from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import stat
import subprocess
import sys
import tempfile

from ab_contract import (
    AA_R1_PADDED_SHA256,
    BOOT2_CAPACITY,
    digest_path,
    read_regular,
)


def run(command: list[str]) -> None:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(command, check=False, capture_output=True, env=environment)
    if result.returncode:
        raise ValueError(
            f"command failed ({result.returncode}): {' '.join(command)}: "
            f"{result.stderr.decode('utf-8', errors='replace').strip()}"
        )


def padded_digest(raw: bytes) -> str:
    if not 0 < len(raw) <= BOOT2_CAPACITY:
        raise ValueError("Candidate AB raw size is invalid or exceeds boot2")
    hasher = hashlib.sha256()
    hasher.update(raw)
    remaining = BOOT2_CAPACITY - len(raw)
    zeros = b"\0" * (1024 * 1024)
    while remaining:
        count = min(remaining, len(zeros))
        hasher.update(zeros[:count])
        remaining -= count
    return hasher.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=pathlib.Path, required=True)
    parser.add_argument("--baseline", type=pathlib.Path, required=True)
    parser.add_argument("--package", type=pathlib.Path, required=True)
    parser.add_argument("--manifest", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    script_dir = pathlib.Path(__file__).resolve().parent
    try:
        if not args.output.name or args.output.name in {".", ".."}:
            raise ValueError("installer wrapper output filename is invalid")
        output_parent = args.output.parent.resolve(strict=True)
        output = output_parent / args.output.name
        if output.exists() or output.is_symlink():
            raise ValueError("refusing to overwrite Candidate AB installer")
        if not output_parent.is_dir() or args.output.parent.is_symlink():
            raise ValueError("installer output parent is missing or unsafe")
        run(
            [
                sys.executable,
                os.fspath(script_dir / "validate-final-artifact.py"),
                "--artifact",
                os.fspath(args.artifact),
                "--baseline",
                os.fspath(args.baseline),
                "--package",
                os.fspath(args.package),
                "--manifest",
                os.fspath(args.manifest),
            ]
        )
        boot = args.artifact / "gemini-mt6797-kernel-restart.boot.img"
        raw = read_regular(boot, "validated Candidate AB boot")
        raw_sha256 = hashlib.sha256(raw).hexdigest()
        padded_sha256 = padded_digest(raw)
        if padded_sha256 == AA_R1_PADDED_SHA256:
            raise ValueError("Candidate AB padded identity equals installed AA r1")
        materializer = script_dir / "materialize-aa-r1-installer.py"
        deriver = script_dir / "derive-installer.py"
        wrapper_deriver = script_dir / "derive-installer-wrapper.py"
        with tempfile.TemporaryDirectory(
            prefix=".candidate-ab-installer-calibration.", dir=output_parent
        ) as raw_temp:
            temp = pathlib.Path(raw_temp)
            aa_installer = temp / "install-candidate-aa-r1-boot2.sh"
            inner = temp / "install-candidate-ab-inner-boot2.sh"
            wrapper = temp / "install-candidate-ab-boot2.sh"
            run(
                [
                    sys.executable,
                    os.fspath(materializer),
                    "--output",
                    os.fspath(aa_installer),
                ]
            )
            run(
                [
                    sys.executable,
                    os.fspath(deriver),
                    "--source",
                    os.fspath(aa_installer),
                    "--output",
                    os.fspath(inner),
                    "--raw-sha256",
                    raw_sha256,
                    "--raw-size",
                    str(len(raw)),
                    "--padded-sha256",
                    padded_sha256,
                ]
            )
            run(["bash", "-n", os.fspath(inner)])
            inner_sha256 = digest_path(inner)
            run(
                [
                    sys.executable,
                    os.fspath(wrapper_deriver),
                    "--output",
                    os.fspath(wrapper),
                    "--raw-sha256",
                    raw_sha256,
                    "--raw-size",
                    str(len(raw)),
                    "--padded-sha256",
                    padded_sha256,
                    "--inner-sha256",
                    inner_sha256,
                    "--materializer-sha256",
                    digest_path(materializer),
                    "--deriver-sha256",
                    digest_path(deriver),
                ]
            )
            run(["bash", "-n", os.fspath(wrapper)])
            run(
                [
                    os.fspath(wrapper),
                    "--repo-root",
                    os.fspath(script_dir.parents[2]),
                    "--help",
                ]
            )
            wrapper_sha256 = digest_path(wrapper)
            os.link(wrapper, output, follow_symlinks=False)
        if stat.S_IMODE(output.stat().st_mode) != 0o700:
            raise ValueError("calibrated Candidate AB wrapper mode is not 0700")
        if digest_path(output) != wrapper_sha256:
            raise ValueError("published Candidate AB wrapper identity changed")
        print("validation=candidate-ab-installer-calibration")
        print(f"candidate_raw_sha256={raw_sha256}")
        print(f"candidate_raw_size={len(raw)}")
        print(f"candidate_padded_sha256={padded_sha256}")
        print(f"expected_predecessor_padded_sha256={AA_R1_PADDED_SHA256}")
        print(f"derived_inner_installer_sha256={inner_sha256}")
        print(f"calibrated_wrapper_sha256={wrapper_sha256}")
        print("wrapper_runtime_reconstruction=passed")
        print("wrapper_exports_repo_root=yes")
        print("installer_predecessor=exact-hardware-passed-aa-r1")
        print("installer_target=live-GPT-logical-boot2-only")
        print("device_contact=none")
        print("hardware_write=none")
        return 0
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
