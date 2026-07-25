#!/usr/bin/env python3
"""Derive AP's guarded boot2 installer from exact Candidate AO."""

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

import candidate_ap as ap


AO_DERIVER_SHA256 = (
    "64edec00e1867784599b59f5d950dea5e9332a4ac70bdba7bae9613390130691"
)
AO_INSTALLER_SHA256 = ap.AO_INSTALLER_SHA256
AO_INSTALLER_PREDECESSOR_SHA256 = (
    "1ef53a25c274ed6f0df265fbc4f4e3a64150d5b7fd4cd1e0cde1db53ffb18ccb"
)
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
            f"AO installer token count changed for {old!r}: "
            f"expected {count}, found {actual}"
        )
    return text.replace(old, new)


def production_calibration() -> Calibration:
    ap.require_artifact_pins()
    calibration = Calibration(
        ap.RAW_SHA256,
        ap.RAW_SIZE,
        ap.ARTIFACT_MANIFEST_SHA256,
        ap.PADDED_SHA256,
    )
    validate_calibration(calibration)
    return calibration


def validate_calibration(calibration: Calibration) -> None:
    for label, value in (
        ("raw", calibration.raw_sha256),
        ("artifact manifest", calibration.manifest_sha256),
        ("padded", calibration.padded_sha256),
    ):
        if ap.HEX256.fullmatch(value) is None:
            raise ValueError(f"Candidate AP {label} SHA-256 is unresolved or malformed")
    if (
        not calibration.raw_size.isdecimal()
        or not 0 < int(calibration.raw_size) <= ap.BOOT2_SIZE
    ):
        raise ValueError("Candidate AP raw size is unresolved, malformed, or oversized")
    if calibration.raw_sha256 == ap.AO_RAW_SHA256:
        raise ValueError("Candidate AP raw identity equals Candidate AO")
    if calibration.manifest_sha256 == ap.AO_MANIFEST_SHA256:
        raise ValueError("Candidate AP artifact manifest equals Candidate AO")
    if calibration.padded_sha256 == ap.AO_PADDED_SHA256:
        raise ValueError("Candidate AP padded identity equals Candidate AO")


def artifact_directory(calibration: Calibration) -> str:
    return ap.ARTIFACT_PREFIX + calibration.raw_sha256[:8]


def identity_replacements(
    calibration: Calibration,
) -> tuple[tuple[str, str, int], ...]:
    return (
        (
            f'expected_artifact_name="{ap.AO_ARTIFACT_DIR}"',
            f'expected_artifact_name="{artifact_directory(calibration)}"',
            1,
        ),
        (ap.AO_BOOT_MEMBER, ap.BOOT_MEMBER, 1),
        ("2026-07-24-mt6797-dvfsp-one-way-handoff", ap.EXPERIMENT, 2),
        ("Candidate AO", "Candidate AP", 8),
        ("candidate-ao", "candidate-ap", 14),
        ("AO_RAW", "AP_RAW", 16),
        ("AO_PADDED", "AP_PADDED", 11),
        ("AO_ARTIFACT", "AP_ARTIFACT", 4),
        (
            "EXPECTED_CURRENT_AN_PADDED_SHA256",
            "EXPECTED_CURRENT_AO_PADDED_SHA256",
            8,
        ),
        ("candidate_label=AO", "candidate_label=AP", 2),
        ("AN-installed-readback-verified", "AO-installed-readback-verified", 4),
    )


def pin_replacements(
    calibration: Calibration,
) -> tuple[tuple[str, str], ...]:
    return (
        (
            f"readonly AP_RAW_SHA256={ap.AO_RAW_SHA256}",
            f"readonly AP_RAW_SHA256={calibration.raw_sha256}",
        ),
        (
            f"readonly AP_RAW_SIZE={ap.AO_RAW_SIZE}",
            f"readonly AP_RAW_SIZE={calibration.raw_size}",
        ),
        (
            f"readonly AP_PADDED_SHA256={ap.AO_PADDED_SHA256}",
            f"readonly AP_PADDED_SHA256={calibration.padded_sha256}",
        ),
        (
            f"readonly AP_ARTIFACT_MANIFEST_SHA256={ap.AO_MANIFEST_SHA256}",
            f"readonly AP_ARTIFACT_MANIFEST_SHA256={calibration.manifest_sha256}",
        ),
        (
            "readonly EXPECTED_CURRENT_AO_PADDED_SHA256="
            f"{AO_INSTALLER_PREDECESSOR_SHA256}",
            f"readonly EXPECTED_CURRENT_AO_PADDED_SHA256={ap.AO_PADDED_SHA256}",
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
        raise ValueError("Candidate AP installer cannot restore exact AO foundation")

    required = (
        f"readonly EXPECTED_CURRENT_AO_PADDED_SHA256={ap.AO_PADDED_SHA256}",
        f"readonly AP_PADDED_SHA256={calibration.padded_sha256}",
        f'expected_artifact_name="{artifact_directory(calibration)}"',
        f'[[ "$candidate_name" == {ap.BOOT_MEMBER} ]]',
        f"--target {TARGET}",
        TARGET_CHECK,
        'dd if="$root_stage_file" of="$target" bs=4M iflag=fullblock count=4',
        "reboot_or_shutdown_performed=no",
    )
    for token in required:
        if token not in text:
            raise ValueError(
                f"derived Candidate AP installer lost safety token: {token}"
            )
    for token in (
        "Candidate AN",
        "candidate-an",
        "Candidate AO image",
        "candidate-ao-padded",
        "EXPECTED_CURRENT_AN_PADDED_SHA256",
    ):
        if token in text:
            raise ValueError(f"derived Candidate AP installer retains stale token: {token}")
    if text.count(TARGET_CHECK) != 1:
        raise ValueError("derived Candidate AP installer target is not source-pinned")
    return text


def repository_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[3]


def reconstruct_ao(work: pathlib.Path) -> pathlib.Path:
    root = repository_root()
    deriver = (
        root
        / "experiments/2026-07-24-mt6797-dvfsp-one-way-handoff/scripts/"
        "derive-installer.py"
    )
    ap.read_regular(deriver, "Candidate AO installer deriver")
    if ap.digest_path(deriver) != AO_DERIVER_SHA256:
        raise ValueError("source-pinned Candidate AO installer deriver changed")
    output = work / "install-candidate-ao-boot2.sh"
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
        raise ValueError(f"Candidate AO installer reconstruction failed: {detail}")
    info = output.lstat()
    if (
        output.is_symlink()
        or not stat.S_ISREG(info.st_mode)
        or stat.S_IMODE(info.st_mode) != 0o700
        or ap.digest_path(output) != AO_INSTALLER_SHA256
    ):
        raise ValueError("exact Candidate AO installer reconstruction changed")
    return output


def validate_output(path: pathlib.Path) -> pathlib.Path:
    if not path.name or path.name in {".", ".."} or path.exists() or path.is_symlink():
        raise ValueError("Candidate AP installer output is invalid or already exists")
    info = path.parent.lstat()
    if path.parent.is_symlink() or not stat.S_ISDIR(info.st_mode):
        raise ValueError("Candidate AP installer output parent is unsafe")
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
            prefix=".candidate-ap-ao-installer.", dir=output.parent
        ) as raw:
            source_path = reconstruct_ao(pathlib.Path(raw))
            source = source_path.read_text(encoding="utf-8", errors="strict")
        text = derive_text(source, calibration)
        publish(output, text)
        print("validation=candidate-ap-installer-derivation")
        print(f"foundation_installer_sha256={AO_INSTALLER_SHA256}")
        print(f"installer_sha256={hashlib.sha256(text.encode()).hexdigest()}")
        print(f"candidate_raw_sha256={calibration.raw_sha256}")
        print(f"candidate_raw_size={calibration.raw_size}")
        print(f"candidate_artifact_manifest_sha256={calibration.manifest_sha256}")
        print(f"candidate_padded_sha256={calibration.padded_sha256}")
        print(f"expected_predecessor_sha256={ap.AO_PADDED_SHA256}")
        print(f"accepted_target={TARGET}")
        print(f"artifact_directory={artifact_directory(calibration)}")
        print(f"boot_filename={ap.BOOT_MEMBER}")
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
