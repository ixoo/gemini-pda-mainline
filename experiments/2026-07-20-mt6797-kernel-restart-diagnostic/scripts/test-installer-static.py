#!/usr/bin/env python3
"""Exercise Candidate AB's installer derivation without contacting hardware."""

from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import re
import stat
import subprocess
import sys
import tempfile

from ab_contract import (
    AA_BOOT_SHA256,
    AA_R1_INSTALLER_SHA256,
    AA_R1_PADDED_SHA256,
    BOOT2_CAPACITY,
    digest_path,
)


RAW_FIXTURE = hashlib.sha256(b"Candidate AB installer raw fixture").hexdigest()
PADDED_FIXTURE = hashlib.sha256(b"Candidate AB installer padded fixture").hexdigest()
RAW_SIZE_FIXTURE = 8_765_432
OLD_AA_R0_PADDED_SHA256 = (
    "157c7cd5d814d7b2704d679faacd3215c5e889642b4261441f99653957585eaa"
)


def run(command: list[str], expected: int) -> subprocess.CompletedProcess[bytes]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(command, capture_output=True, check=False, env=environment)
    if result.returncode != expected:
        raise RuntimeError(
            f"unexpected status {result.returncode}, expected {expected}: {command}\n"
            f"stdout={result.stdout.decode(errors='replace')}\n"
            f"stderr={result.stderr.decode(errors='replace')}"
        )
    return result


def derive_command(
    deriver: pathlib.Path,
    source: pathlib.Path,
    output: pathlib.Path,
    *,
    raw_hash: str = RAW_FIXTURE,
    raw_size: str = str(RAW_SIZE_FIXTURE),
    padded_hash: str = PADDED_FIXTURE,
) -> list[str]:
    return [
        sys.executable,
        os.fspath(deriver),
        "--source",
        os.fspath(source),
        "--output",
        os.fspath(output),
        "--raw-sha256",
        raw_hash,
        "--raw-size",
        raw_size,
        "--padded-sha256",
        padded_hash,
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aa-installer", type=pathlib.Path, required=True)
    args = parser.parse_args()
    script_dir = pathlib.Path(__file__).resolve().parent
    repo_root = script_dir.parents[2]
    deriver = script_dir / "derive-installer.py"
    materializer = script_dir / "materialize-aa-r1-installer.py"
    wrapper_deriver = script_dir / "derive-installer-wrapper.py"
    try:
        if digest_path(args.aa_installer) != AA_R1_INSTALLER_SHA256:
            raise ValueError("exact Candidate AA r1 installer fixture changed")
        with tempfile.TemporaryDirectory(prefix="candidate-ab-installer-static.") as raw:
            temp = pathlib.Path(raw)
            first = temp / "install-candidate-ab-boot2.first.sh"
            second = temp / "install-candidate-ab-boot2.second.sh"
            run(derive_command(deriver, args.aa_installer, first), 0)
            run(derive_command(deriver, args.aa_installer, second), 0)
            run(["bash", "-n", os.fspath(first)], 0)
            if first.read_bytes() != second.read_bytes():
                raise ValueError("two installer derivations were not byte-identical")
            if stat.S_IMODE(first.stat().st_mode) != 0o700:
                raise ValueError("derived installer mode is not exactly 0700")

            text = first.read_text(encoding="utf-8")
            exact_counts = {
                f"readonly AB_RAW_SHA256={RAW_FIXTURE}": 1,
                f"readonly AB_RAW_SIZE={RAW_SIZE_FIXTURE}": 1,
                f"readonly AB_PADDED_SHA256={PADDED_FIXTURE}": 1,
                "readonly EXPECTED_CURRENT_AA_R1_PADDED_SHA256="
                + AA_R1_PADDED_SHA256: 1,
                "gemini-mt6797-kernel-restart.boot.img": 1,
                "candidate-AB-mt6797-kernel-restart-final-${AB_RAW_SHA256:0:8}": 1,
                'dd if="$root_stage_file" of="$target" bs=4M iflag=fullblock count=4': 1,
                "expected_previous_label=AA-r1-hardware-passed": 1,
                "candidate_label=AB": 2,
                "reboot_or_shutdown_performed=no": 2,
            }
            for token, count in exact_counts.items():
                if text.count(token) != count:
                    raise ValueError(f"derived installer token count changed: {token!r}")
            if text.count('of="$target"') != 1:
                raise ValueError("derived installer gained another target write")
            forbidden = (
                AA_BOOT_SHA256,
                OLD_AA_R0_PADDED_SHA256,
                "Candidate AA r1",
                "candidate-aa-r1",
                "AA_R1_RAW",
                "EXPECTED_CURRENT_AA_R0",
                "gemini-keyboard-console-map.boot.img",
            )
            if any(token in text for token in forbidden):
                raise ValueError("derived installer retained superseded target identity")
            if "sysrq-trigger" in text or re.search(
                r"(?m)^[ \t]*(?:sudo[ \t]+)?"
                r"(?:reboot|shutdown|poweroff|halt|kexec)(?:[ \t]|$)",
                text,
            ):
                raise ValueError("derived installer can reboot or power off the device")

            wrapper = temp / "install-candidate-ab-boot2.sh"
            wrapper_replica = temp / "install-candidate-ab-boot2.replica.sh"
            wrapper_command = [
                sys.executable,
                os.fspath(wrapper_deriver),
                "--output",
                os.fspath(wrapper),
                "--raw-sha256",
                RAW_FIXTURE,
                "--raw-size",
                str(RAW_SIZE_FIXTURE),
                "--padded-sha256",
                PADDED_FIXTURE,
                "--inner-sha256",
                digest_path(first),
                "--materializer-sha256",
                digest_path(materializer),
                "--deriver-sha256",
                digest_path(deriver),
            ]
            run(wrapper_command, 0)
            replica_command = list(wrapper_command)
            replica_command[replica_command.index(os.fspath(wrapper))] = os.fspath(
                wrapper_replica
            )
            run(replica_command, 0)
            if wrapper.read_bytes() != wrapper_replica.read_bytes():
                raise ValueError("two outer-wrapper derivations were not byte-identical")
            if stat.S_IMODE(wrapper.stat().st_mode) != 0o700:
                raise ValueError("derived outer-wrapper mode is not exactly 0700")
            wrapper_text = wrapper.read_text(encoding="utf-8")
            for token in (
                'export GEMINI_REPO_ROOT="$repo_root"',
                '"$ab_inner" "${installer_args[@]}"',
                f"readonly AB_INNER_INSTALLER_SHA256={digest_path(first)}",
                f"readonly MATERIALIZER_SHA256={digest_path(materializer)}",
                f"readonly DERIVER_SHA256={digest_path(deriver)}",
            ):
                if wrapper_text.count(token) != 1:
                    raise ValueError(f"outer-wrapper token count changed: {token!r}")
            if 'of="$target"' in wrapper_text or "sysrq-trigger" in wrapper_text:
                raise ValueError("outer wrapper gained a direct hardware side effect")
            run(
                [
                    os.fspath(wrapper),
                    "--repo-root",
                    os.fspath(repo_root),
                    "--help",
                ],
                0,
            )
            run([os.fspath(wrapper), "--help"], 2)
            wrong_wrapper = temp / "install-candidate-ab-boot2.wrong-input.sh"
            wrong_command = list(wrapper_command)
            wrong_command[wrong_command.index(os.fspath(wrapper))] = os.fspath(
                wrong_wrapper
            )
            materializer_index = wrong_command.index("--materializer-sha256") + 1
            wrong_command[materializer_index] = "0" * 64
            run(wrong_command, 0)
            run(
                [
                    os.fspath(wrong_wrapper),
                    "--repo-root",
                    os.fspath(repo_root),
                    "--help",
                ],
                2,
            )

            run(derive_command(deriver, args.aa_installer, first), 2)
            tampered = temp / "tampered-aa-installer.sh"
            tampered.write_bytes(args.aa_installer.read_bytes() + b"# mutation\n")
            run(derive_command(deriver, tampered, temp / "tampered.out"), 2)
            symlink = temp / "symlink-aa-installer.sh"
            symlink.symlink_to(args.aa_installer)
            run(derive_command(deriver, symlink, temp / "symlink.out"), 2)
            run(
                derive_command(
                    deriver,
                    args.aa_installer,
                    temp / "old-raw.out",
                    raw_hash=AA_BOOT_SHA256,
                ),
                2,
            )
            run(
                derive_command(
                    deriver,
                    args.aa_installer,
                    temp / "old-padded.out",
                    padded_hash=AA_R1_PADDED_SHA256,
                ),
                2,
            )
            run(
                derive_command(
                    deriver,
                    args.aa_installer,
                    temp / "malformed-hash.out",
                    raw_hash="not-a-sha256",
                ),
                2,
            )
            run(
                derive_command(
                    deriver, args.aa_installer, temp / "zero-size.out", raw_size="0"
                ),
                2,
            )
            run(
                derive_command(
                    deriver,
                    args.aa_installer,
                    temp / "oversize.out",
                    raw_size=str(BOOT2_CAPACITY + 1),
                ),
                2,
            )
    except (OSError, RuntimeError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print("foundation_identity=PASS")
    print("deterministic_derivation=PASS")
    print("derived_mode_and_syntax=PASS")
    print("candidate_identity_rewrite=PASS")
    print("sole_bounded_target_write=PASS")
    print("no_automatic_reboot=PASS")
    print("deterministic_outer_wrapper=PASS")
    print("outer_wrapper_reconstructs_inner=PASS")
    print("outer_wrapper_exports_repo_root=PASS")
    print("outer_wrapper_input_hash_rejection=PASS")
    print("existing_output_rejection=PASS")
    print("foundation_mutation_rejection=PASS")
    print("foundation_symlink_rejection=PASS")
    print("predecessor_identity_rejection=PASS")
    print("malformed_calibration_rejection=PASS")
    print("size_boundary_rejection=PASS")
    print("device_contact=none")
    print("hardware_write=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
