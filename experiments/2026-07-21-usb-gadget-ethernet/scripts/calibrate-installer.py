#!/usr/bin/env python3
"""Validate Candidate AC and publish its calibrated boot2 wrapper outside Git."""

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

sys.dont_write_bytecode = True

from ac_contract import (  # noqa: E402
    AB_BOOT_SHA256,
    AB_BOOT_SIZE,
    AC_BOOT_FILE,
    BOOT2_CAPACITY,
    digest_path,
    read_regular,
)


# These two repository inputs reconstruct exact AA r1 and exact AB. They are
# historical foundations, not calibration-dependent AC inputs.
MATERIALIZER_SHA256 = "4199517680e63b1d793b7ed7e5c61ca82326a06159d5e057cc708761cc0e540c"
AB_DERIVER_SHA256 = "0ca386dca403da51ea700dc3a697e13ddcfccafc257167afa4d37d940f50d7d7"
AA_R1_INSTALLER_SHA256 = "f081ef03b2dce68d28458eacdcc184a5550c88eeb75579fab61359e936a40f9f"
AB_INNER_INSTALLER_SHA256 = "260c7d907cdd7656b664d71a6564109a6ed03fcb95bf3e5c6da8bcc3bff4050c"
AB_PADDED_SHA256 = "b58c0347d34a3fd9031c74cb03447dd7a6fc630d5b8ea2b7eabc36827e754350"

PLACEHOLDER_PREFIX = "REPLACE_AFTER_CALIBRATION_"
PLACEHOLDER_NAMES = (
    "AC_RAW_SHA256",
    "AC_RAW_SIZE",
    "AC_PADDED_SHA256",
    "AC_INNER_INSTALLER_SHA256",
    "MATERIALIZER_SHA256",
    "AB_DERIVER_SHA256",
    "AC_DERIVER_SHA256",
)
HEX256 = re.compile(r"^[0-9a-f]{64}$")


def run(command: list[str], expected: int = 0) -> subprocess.CompletedProcess[bytes]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(command, check=False, capture_output=True, env=environment)
    if result.returncode != expected:
        raise ValueError(
            f"command failed ({result.returncode}, expected {expected}): "
            f"{' '.join(command)}: "
            f"{result.stderr.decode('utf-8', errors='replace').strip()}"
        )
    return result


def padded_digest(raw: bytes) -> str:
    if not 0 < len(raw) <= BOOT2_CAPACITY:
        raise ValueError("Candidate AC raw size is invalid or exceeds boot2")
    hasher = hashlib.sha256()
    hasher.update(raw)
    remaining = BOOT2_CAPACITY - len(raw)
    zeros = b"\0" * (1024 * 1024)
    while remaining:
        count = min(remaining, len(zeros))
        hasher.update(zeros[:count])
        remaining -= count
    return hasher.hexdigest()


def render_wrapper(template: bytes, values: dict[str, str]) -> bytes:
    if set(values) != set(PLACEHOLDER_NAMES):
        raise ValueError("calibrated wrapper value inventory changed")
    for name in PLACEHOLDER_NAMES:
        value = values[name]
        if name == "AC_RAW_SIZE":
            if not value.isdecimal() or not 0 < int(value) <= BOOT2_CAPACITY:
                raise ValueError("calibrated AC raw size is invalid")
        elif HEX256.fullmatch(value) is None:
            raise ValueError(f"calibrated wrapper value is not SHA-256: {name}")

    text = template.decode("utf-8")
    prefix_line = f"readonly PLACEHOLDER_PREFIX={PLACEHOLDER_PREFIX}"
    if text.count(prefix_line) != 1:
        raise ValueError("calibration prefix declaration changed")
    for name in PLACEHOLDER_NAMES:
        token = PLACEHOLDER_PREFIX + name
        if text.count(token) != 1:
            raise ValueError(f"calibration placeholder count changed: {name}")
        text = text.replace(token, values[name])
    if text.count(PLACEHOLDER_PREFIX) != 1:
        raise ValueError("calibrated wrapper retains an unexpected placeholder")

    required = (
        f"readonly AC_RAW_SHA256={values['AC_RAW_SHA256']}",
        f"readonly AC_RAW_SIZE={values['AC_RAW_SIZE']}",
        f"readonly AC_PADDED_SHA256={values['AC_PADDED_SHA256']}",
        f"readonly AC_INNER_INSTALLER_SHA256={values['AC_INNER_INSTALLER_SHA256']}",
        f"readonly MATERIALIZER_SHA256={values['MATERIALIZER_SHA256']}",
        f"readonly AB_DERIVER_SHA256={values['AB_DERIVER_SHA256']}",
        f"readonly AC_DERIVER_SHA256={values['AC_DERIVER_SHA256']}",
        'export GEMINI_REPO_ROOT="$repo_root"',
        '"$ac_inner" "${installer_args[@]}"',
    )
    if any(text.count(token) != 1 for token in required):
        raise ValueError("calibrated wrapper lost its exact reconstruction contract")
    if 'of="$target"' in text or "sysrq-trigger" in text:
        raise ValueError("outer wrapper gained a direct hardware side effect")
    if re.search(
        r"(?m)^[ \t]*(?:sudo[ \t]+)?"
        r"(?:reboot|shutdown|poweroff|halt|kexec)(?:[ \t]|$)",
        text,
    ):
        raise ValueError("outer wrapper gained a reboot or shutdown command")
    return text.encode("utf-8")


def publish(path: pathlib.Path, data: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o700)
    with os.fdopen(descriptor, "wb") as stream:
        os.fchmod(stream.fileno(), 0o700)
        stream.write(data)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=pathlib.Path, required=True)
    parser.add_argument("--baseline", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    script_dir = pathlib.Path(__file__).resolve().parent
    repo_root = script_dir.parents[2]
    previous_umask = os.umask(0o077)
    try:
        if not args.output.name or args.output.name in {".", ".."}:
            raise ValueError("installer wrapper output filename is invalid")
        if args.output.parent.is_symlink():
            raise ValueError("installer wrapper output parent is unsafe")
        output_parent = args.output.parent.resolve(strict=True)
        if not output_parent.is_dir():
            raise ValueError("installer wrapper output parent is missing")
        try:
            output_parent.relative_to(repo_root)
        except ValueError:
            pass
        else:
            raise ValueError("calibrated installer output must remain outside the repository")
        output = output_parent / args.output.name
        if output.exists() or output.is_symlink():
            raise ValueError("refusing to overwrite Candidate AC installer wrapper")

        template = script_dir / "install-candidate-ac-boot2.sh.in"
        baseline_validator = script_dir / "validate-ab-baseline.py"
        final_validator = script_dir / "validate-final-artifact.py"
        materializer = (
            repo_root
            / "experiments/2026-07-20-mt6797-kernel-restart-diagnostic/scripts/"
            "materialize-aa-r1-installer.py"
        )
        ab_deriver = (
            repo_root
            / "experiments/2026-07-20-mt6797-kernel-restart-diagnostic/scripts/"
            "derive-installer.py"
        )
        ac_deriver = script_dir / "derive-installer.py"
        dependencies = (
            template,
            baseline_validator,
            final_validator,
            materializer,
            ab_deriver,
            ac_deriver,
        )
        for dependency in dependencies:
            info = dependency.lstat()
            if dependency.is_symlink() or not stat.S_ISREG(info.st_mode):
                raise ValueError(f"installer calibration input is unsafe: {dependency}")
        if digest_path(materializer) != MATERIALIZER_SHA256:
            raise ValueError("exact AA r1 installer materializer changed")
        if digest_path(ab_deriver) != AB_DERIVER_SHA256:
            raise ValueError("exact Candidate AB installer deriver changed")

        run(
            [
                sys.executable,
                os.fspath(baseline_validator),
                "--artifact",
                os.fspath(args.baseline),
            ]
        )
        run(
            [
                sys.executable,
                os.fspath(final_validator),
                "--artifact",
                os.fspath(args.artifact),
                "--baseline",
                os.fspath(args.baseline),
            ]
        )

        boot = args.artifact / AC_BOOT_FILE
        raw = read_regular(boot, "validated Candidate AC boot", mode=0o600)
        raw_sha256 = hashlib.sha256(raw).hexdigest()
        padded_sha256 = padded_digest(raw)
        if raw_sha256 == AB_BOOT_SHA256:
            raise ValueError("Candidate AC raw identity equals hardware-passed AB")
        if padded_sha256 == AB_PADDED_SHA256:
            raise ValueError("Candidate AC padded identity equals installed AB predecessor")

        template_data = read_regular(template, "Candidate AC installer template", mode=0o644)
        with tempfile.TemporaryDirectory(
            prefix=".candidate-ac-installer-calibration.", dir=output_parent
        ) as raw_temp:
            temp = pathlib.Path(raw_temp)
            aa_installer = temp / "install-candidate-aa-r1-boot2.sh"
            ab_inner = temp / "install-candidate-ab-inner-boot2.sh"
            ac_inner = temp / "install-candidate-ac-inner-boot2.sh"
            wrapper = temp / "install-candidate-ac-boot2.sh"

            run(
                [
                    sys.executable,
                    os.fspath(materializer),
                    "--output",
                    os.fspath(aa_installer),
                ]
            )
            if digest_path(aa_installer) != AA_R1_INSTALLER_SHA256:
                raise ValueError("reconstructed AA r1 installer identity changed")
            run(
                [
                    sys.executable,
                    os.fspath(ab_deriver),
                    "--source",
                    os.fspath(aa_installer),
                    "--output",
                    os.fspath(ab_inner),
                    "--raw-sha256",
                    AB_BOOT_SHA256,
                    "--raw-size",
                    str(AB_BOOT_SIZE),
                    "--padded-sha256",
                    AB_PADDED_SHA256,
                ]
            )
            run(["bash", "-n", os.fspath(ab_inner)])
            if digest_path(ab_inner) != AB_INNER_INSTALLER_SHA256:
                raise ValueError("derived exact Candidate AB installer identity changed")
            run(
                [
                    sys.executable,
                    os.fspath(ac_deriver),
                    "--source",
                    os.fspath(ab_inner),
                    "--output",
                    os.fspath(ac_inner),
                    "--raw-sha256",
                    raw_sha256,
                    "--raw-size",
                    str(len(raw)),
                    "--padded-sha256",
                    padded_sha256,
                ]
            )
            run(["bash", "-n", os.fspath(ac_inner)])
            inner_sha256 = digest_path(ac_inner)
            values = {
                "AC_RAW_SHA256": raw_sha256,
                "AC_RAW_SIZE": str(len(raw)),
                "AC_PADDED_SHA256": padded_sha256,
                "AC_INNER_INSTALLER_SHA256": inner_sha256,
                "MATERIALIZER_SHA256": digest_path(materializer),
                "AB_DERIVER_SHA256": digest_path(ab_deriver),
                "AC_DERIVER_SHA256": digest_path(ac_deriver),
            }
            wrapper_data = render_wrapper(template_data, values)
            if render_wrapper(template_data, values) != wrapper_data:
                raise ValueError("installer wrapper rendering is not deterministic")
            publish(wrapper, wrapper_data)
            run(["bash", "-n", os.fspath(wrapper)])
            run(
                [
                    os.fspath(wrapper),
                    "--repo-root",
                    os.fspath(repo_root),
                    "--help",
                ]
            )
            wrapper_sha256 = digest_path(wrapper)
            os.link(wrapper, output, follow_symlinks=False)

        if stat.S_IMODE(output.stat().st_mode) != 0o700:
            raise ValueError("calibrated Candidate AC wrapper mode is not 0700")
        if digest_path(output) != wrapper_sha256:
            raise ValueError("published Candidate AC wrapper identity changed")
        print("validation=candidate-ac-installer-calibration")
        print(f"candidate_raw_sha256={raw_sha256}")
        print(f"candidate_raw_size={len(raw)}")
        print(f"candidate_padded_sha256={padded_sha256}")
        print(f"expected_predecessor_padded_sha256={AB_PADDED_SHA256}")
        print(f"derived_ab_installer_sha256={AB_INNER_INSTALLER_SHA256}")
        print(f"derived_ac_installer_sha256={inner_sha256}")
        print(f"calibrated_wrapper_sha256={wrapper_sha256}")
        print("wrapper_runtime_reconstruction=passed")
        print("installer_predecessor=exact-hardware-passed-ab")
        print("installer_target=live-GPT-logical-boot2-only")
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
