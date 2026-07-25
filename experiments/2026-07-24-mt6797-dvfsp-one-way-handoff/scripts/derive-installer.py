#!/usr/bin/env python3
"""Derive AO's guarded boot2 installer from exact Candidate AN."""

from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass

sys.dont_write_bytecode = True

import candidate_ao as ao


AN_DERIVER_SHA256 = (
    "16e915f561c0edfdf58d1595d3f1c950b2b5cda3a6c915857aad36c129f6befb"
)
AN_INSTALLER_SHA256 = ao.AN_INSTALLER_SHA256
TARGET = "gemini@192.168.1.50"
TARGET_CHECK = (
    f'[[ "$target" == {TARGET} ]] || \\\n'
    f"\tdie 'target must be exact {TARGET}'"
)


@dataclass(frozen=True)
class Calibration:
    raw_sha256: str
    raw_size: str
    manifest_sha256: str
    padded_sha256: str


def replace_exact(text: str, old: str, new: str, count: int) -> str:
    actual = text.count(old)
    if actual != count:
        raise ValueError(
            f"AN installer token count changed for {old!r}: "
            f"expected {count}, found {actual}"
        )
    return text.replace(old, new)


def production_calibration() -> Calibration:
    ao.require_artifact_pins()
    calibration = Calibration(
        ao.RAW_SHA256,
        ao.RAW_SIZE,
        ao.ARTIFACT_MANIFEST_SHA256,
        ao.PADDED_SHA256,
    )
    validate_calibration(calibration)
    return calibration


def validate_calibration(calibration: Calibration) -> None:
    hashes = {
        "raw": calibration.raw_sha256,
        "artifact manifest": calibration.manifest_sha256,
        "padded": calibration.padded_sha256,
    }
    for label, value in hashes.items():
        if ao.HEX256.fullmatch(value) is None:
            raise ValueError(f"Candidate AO {label} SHA-256 is unresolved or malformed")
    if (
        not calibration.raw_size.isdecimal()
        or not 0 < int(calibration.raw_size) <= ao.BOOT2_SIZE
    ):
        raise ValueError("Candidate AO raw size is unresolved, malformed, or oversized")
    if calibration.raw_sha256 in {ao.AH_RAW_SHA256, ao.AN_RAW_SHA256}:
        raise ValueError("Candidate AO raw identity equals a predecessor")
    if calibration.manifest_sha256 == ao.AN_ARTIFACT_MANIFEST_SHA256:
        raise ValueError("Candidate AO artifact manifest equals Candidate AN")
    if calibration.padded_sha256 == ao.AN_PADDED_SHA256:
        raise ValueError("Candidate AO padded identity equals Candidate AN")


def artifact_directory(calibration: Calibration) -> str:
    return ao.ARTIFACT_PREFIX + calibration.raw_sha256[:8]


def identity_replacements(
    calibration: Calibration,
) -> tuple[tuple[str, str, int], ...]:
    return (
        (
            f'expected_artifact_name="{ao.AN_ARTIFACT_DIR}"',
            f'expected_artifact_name="{artifact_directory(calibration)}"',
            1,
        ),
        (
            "gemini-mt6797-dvfsp-handoff-observer.boot.img",
            ao.BOOT_MEMBER,
            1,
        ),
        (
            "2026-07-24-mt6797-dvfsp-handoff-observer",
            ao.EXPERIMENT,
            2,
        ),
        ("Candidate AN", "Candidate AO", 8),
        ("candidate-an", "candidate-ao", 14),
        ("AN_RAW", "AO_RAW", 16),
        ("AN_PADDED", "AO_PADDED", 11),
        ("AN_ARTIFACT", "AO_ARTIFACT", 4),
        (
            "EXPECTED_CURRENT_AL_PADDED_SHA256",
            "EXPECTED_CURRENT_AN_PADDED_SHA256",
            8,
        ),
        ("candidate_label=AN", "candidate_label=AO", 2),
        ("AL-installed-readback-verified", "AN-installed-readback-verified", 4),
    )


def pin_replacements(
    calibration: Calibration,
) -> tuple[tuple[str, str], ...]:
    return (
        (
            f"readonly AO_RAW_SHA256={ao.AN_RAW_SHA256}",
            f"readonly AO_RAW_SHA256={calibration.raw_sha256}",
        ),
        (
            f"readonly AO_RAW_SIZE={ao.AN_RAW_SIZE}",
            f"readonly AO_RAW_SIZE={calibration.raw_size}",
        ),
        (
            f"readonly AO_PADDED_SHA256={ao.AN_PADDED_SHA256}",
            f"readonly AO_PADDED_SHA256={calibration.padded_sha256}",
        ),
        (
            "readonly AO_ARTIFACT_MANIFEST_SHA256="
            f"{ao.AN_ARTIFACT_MANIFEST_SHA256}",
            f"readonly AO_ARTIFACT_MANIFEST_SHA256={calibration.manifest_sha256}",
        ),
        (
            "readonly EXPECTED_CURRENT_AN_PADDED_SHA256="
            "5f022a8b4d6ed19a248d21b8cebdbfa2190e86675714eab49adfc57de9a7f794",
            f"readonly EXPECTED_CURRENT_AN_PADDED_SHA256={ao.AN_PADDED_SHA256}",
        ),
    )


def derive_text(source: str, calibration: Calibration) -> str:
    validate_calibration(calibration)
    text = source
    for old, new, count in identity_replacements(calibration):
        text = replace_exact(text, old, new, count)
    for old, new in pin_replacements(calibration):
        text = replace_exact(text, old, new, 1)

    restored = text
    for old, new in reversed(pin_replacements(calibration)):
        restored = replace_exact(restored, new, old, 1)
    for old, new, count in reversed(identity_replacements(calibration)):
        restored = replace_exact(restored, new, old, count)
    if restored != source:
        raise ValueError("Candidate AO installer cannot restore exact AN foundation")

    required = (
        f"readonly EXPECTED_CURRENT_AN_PADDED_SHA256={ao.AN_PADDED_SHA256}",
        f"readonly AO_PADDED_SHA256={calibration.padded_sha256}",
        f'expected_artifact_name="{artifact_directory(calibration)}"',
        f'[[ "$candidate_name" == {ao.BOOT_MEMBER} ]]',
        f"--target {TARGET}",
        TARGET_CHECK,
        'dd if="$root_stage_file" of="$target" bs=4M iflag=fullblock count=4',
        "reboot_or_shutdown_performed=no",
    )
    for token in required:
        if token not in text:
            raise ValueError(
                f"derived Candidate AO installer lost safety token: {token}"
            )
    stale = (
        "Candidate AL",
        "Candidate AN",
        "candidate-al",
        "candidate-an",
        "EXPECTED_CURRENT_AL_PADDED_SHA256",
    )
    for token in stale:
        if token in text:
            raise ValueError(f"derived Candidate AO installer retains stale token: {token}")
    if text.count(TARGET_CHECK) != 1:
        raise ValueError("derived Candidate AO installer target is not source-pinned")
    return text


def repository_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[3]


def reconstruct_an(work: pathlib.Path) -> pathlib.Path:
    root = repository_root()
    deriver = (
        root
        / "experiments/2026-07-24-mt6797-dvfsp-handoff-observer/scripts/"
        "derive-installer.py"
    )
    ao.read_regular(deriver, "Candidate AN installer deriver")
    if ao.digest_path(deriver) != AN_DERIVER_SHA256:
        raise ValueError("source-pinned Candidate AN installer deriver changed")
    output = work / "install-candidate-an-boot2.sh"
    result = subprocess.run(
        [sys.executable, os.fspath(deriver), "--output", os.fspath(output)],
        cwd=root,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or "no diagnostic"
        raise ValueError(f"Candidate AN installer reconstruction failed: {detail}")
    info = output.lstat()
    if (
        output.is_symlink()
        or not stat.S_ISREG(info.st_mode)
        or stat.S_IMODE(info.st_mode) != 0o700
        or ao.digest_path(output) != AN_INSTALLER_SHA256
    ):
        raise ValueError("exact Candidate AN installer reconstruction changed")
    return output


def validate_output(path: pathlib.Path) -> pathlib.Path:
    if not path.name or path.name in {".", ".."} or path.exists() or path.is_symlink():
        raise ValueError("Candidate AO installer output is invalid or already exists")
    info = path.parent.lstat()
    if path.parent.is_symlink() or not stat.S_ISDIR(info.st_mode):
        raise ValueError("Candidate AO installer output parent is unsafe")
    return path.parent.resolve(strict=True) / path.name


def publish(path: pathlib.Path, text: str) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o700)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        os.fchmod(stream.fileno(), 0o700)
        stream.write(text)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()
    previous_umask = os.umask(0o077)
    try:
        calibration = production_calibration()
        output = validate_output(args.output)
        with tempfile.TemporaryDirectory(
            prefix=".candidate-ao-an-installer.", dir=output.parent
        ) as raw:
            source_path = reconstruct_an(pathlib.Path(raw))
            source = source_path.read_text(encoding="utf-8", errors="strict")
        text = derive_text(source, calibration)
        publish(output, text)
        print("validation=candidate-ao-installer-derivation")
        print(f"foundation_installer_sha256={AN_INSTALLER_SHA256}")
        print(f"installer_sha256={hashlib.sha256(text.encode()).hexdigest()}")
        print(f"candidate_raw_sha256={calibration.raw_sha256}")
        print(f"candidate_raw_size={calibration.raw_size}")
        print(f"candidate_artifact_manifest_sha256={calibration.manifest_sha256}")
        print(f"candidate_padded_sha256={calibration.padded_sha256}")
        print(f"expected_predecessor_sha256={ao.AN_PADDED_SHA256}")
        print(f"accepted_target={TARGET}")
        print(f"artifact_directory={artifact_directory(calibration)}")
        print(f"boot_filename={ao.BOOT_MEMBER}")
        print(f"output={output}")
        print("sole_target_write=one-bounded-16MiB-write")
        print("reboot_or_slot_selection=none")
        return 0
    except (OSError, RuntimeError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    finally:
        os.umask(previous_umask)


if __name__ == "__main__":
    raise SystemExit(main())
