#!/usr/bin/env python3
"""Derive AL's guarded boot2 installer from exact Candidate AK."""

from __future__ import annotations

import argparse
import os
import pathlib
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass

sys.dont_write_bytecode = True

import candidate_al as al


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
            f"AK installer token count changed for {old!r}: "
            f"expected {count}, found {actual}"
        )
    return text.replace(old, new)


def production_calibration() -> Calibration:
    al.require_artifact_pins()
    return Calibration(
        al.RAW_SHA256,
        al.RAW_SIZE,
        al.ARTIFACT_MANIFEST_SHA256,
        al.PADDED_SHA256,
    )


def artifact_directory(calibration: Calibration) -> str:
    return al.ARTIFACT_PREFIX + calibration.raw_sha256[:8]


def identity_replacements(
    calibration: Calibration,
) -> tuple[tuple[str, str, int], ...]:
    return (
        (
            f'expected_artifact_name="{al.AK_ARTIFACT_DIR}"',
            f'expected_artifact_name="{artifact_directory(calibration)}"',
            1,
        ),
        (al.AK_BOOT_MEMBER, al.BOOT_MEMBER, 1),
        (
            "2026-07-22-a72-reject-cpu9-request",
            al.EXPERIMENT,
            2,
        ),
        ("Candidate AK", "Candidate AL", 8),
        ("candidate-ak", "candidate-al", 14),
        ("AK_RAW", "AL_RAW", 16),
        ("AK_PADDED", "AL_PADDED", 11),
        ("AK_ARTIFACT", "AL_ARTIFACT", 4),
        (
            "EXPECTED_CURRENT_AJ_PADDED_SHA256",
            "EXPECTED_CURRENT_AK_PADDED_SHA256",
            8,
        ),
        ("candidate_label=AK", "candidate_label=AL", 2),
        ("AJ-installed-readback-verified", "AK-installed-readback-verified", 4),
    )


def pin_replacements(
    calibration: Calibration,
) -> tuple[tuple[str, str], ...]:
    return (
        (
            f"readonly AL_RAW_SHA256={al.AK_RAW_SHA256}",
            f"readonly AL_RAW_SHA256={calibration.raw_sha256}",
        ),
        (
            f"readonly AL_RAW_SIZE={al.AK_RAW_SIZE}",
            f"readonly AL_RAW_SIZE={calibration.raw_size}",
        ),
        (
            f"readonly AL_PADDED_SHA256={al.AK_PADDED_SHA256}",
            f"readonly AL_PADDED_SHA256={calibration.padded_sha256}",
        ),
        (
            f"readonly AL_ARTIFACT_MANIFEST_SHA256={al.AK_MANIFEST_SHA256}",
            f"readonly AL_ARTIFACT_MANIFEST_SHA256={calibration.manifest_sha256}",
        ),
        (
            "readonly EXPECTED_CURRENT_AK_PADDED_SHA256="
            "8e322ed2a8fc82a4746ec118c2b0adad6003d03f0670284b9ab281c92120b257",
            f"readonly EXPECTED_CURRENT_AK_PADDED_SHA256={al.AK_PADDED_SHA256}",
        ),
    )


def derive_text(source: str, calibration: Calibration) -> str:
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
        raise ValueError("Candidate AL installer cannot restore exact AK foundation")
    required = (
        f"readonly EXPECTED_CURRENT_AK_PADDED_SHA256={al.AK_PADDED_SHA256}",
        f"readonly AL_PADDED_SHA256={calibration.padded_sha256}",
        f'expected_artifact_name="{artifact_directory(calibration)}"',
        f"[[ \"$candidate_name\" == {al.BOOT_MEMBER} ]]",
        'dd if="$root_stage_file" of="$target" bs=4M iflag=fullblock count=4',
        "reboot_or_shutdown_performed=no",
    )
    for token in required:
        if token not in text:
            raise ValueError(f"derived Candidate AL installer lost safety token: {token}")
    if "Candidate AJ" in text or "EXPECTED_CURRENT_AJ_PADDED_SHA256" in text:
        raise ValueError("derived Candidate AL installer retains stale AJ predecessor")
    return text


def repository_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[3]


def reconstruct_ak(work: pathlib.Path) -> pathlib.Path:
    root = repository_root()
    deriver = (
        root
        / "experiments/2026-07-22-a72-reject-cpu9-request/scripts/derive-installer.py"
    )
    al.read_regular(deriver, "Candidate AK installer deriver")
    if al.digest_path(deriver) != al.AK_DERIVER_SHA256:
        raise ValueError("source-pinned Candidate AK installer deriver changed")
    output = work / "install-candidate-ak-boot2.sh"
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [sys.executable, os.fspath(deriver), "--output", os.fspath(output)],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or "no diagnostic"
        raise ValueError(f"Candidate AK installer reconstruction failed: {detail}")
    info = output.lstat()
    if (
        output.is_symlink()
        or not stat.S_ISREG(info.st_mode)
        or stat.S_IMODE(info.st_mode) != 0o700
        or al.digest_path(output) != al.AK_INSTALLER_SHA256
    ):
        raise ValueError("exact Candidate AK installer reconstruction changed")
    return output


def validate_output(path: pathlib.Path) -> pathlib.Path:
    if not path.name or path.name in {".", ".."} or path.exists() or path.is_symlink():
        raise ValueError("Candidate AL installer output is invalid or already exists")
    info = path.parent.lstat()
    if path.parent.is_symlink() or not stat.S_ISDIR(info.st_mode):
        raise ValueError("Candidate AL installer output parent is unsafe")
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
        # Refuse before reconstructing a runnable installer when any AL
        # calibration field is unresolved.
        calibration = production_calibration()
        output = validate_output(args.output)
        with tempfile.TemporaryDirectory(
            prefix=".candidate-al-ak-installer.", dir=output.parent
        ) as raw:
            source_path = reconstruct_ak(pathlib.Path(raw))
            source = source_path.read_text(encoding="utf-8", errors="strict")
        text = derive_text(source, calibration)
        publish(output, text)
        print("validation=candidate-al-installer-derivation")
        print(f"foundation_installer_sha256={al.AK_INSTALLER_SHA256}")
        print(f"installer_sha256={__import__('hashlib').sha256(text.encode()).hexdigest()}")
        print(f"candidate_raw_sha256={calibration.raw_sha256}")
        print(f"candidate_raw_size={calibration.raw_size}")
        print(f"candidate_artifact_manifest_sha256={calibration.manifest_sha256}")
        print(f"candidate_padded_sha256={calibration.padded_sha256}")
        print(f"expected_predecessor_sha256={al.AK_PADDED_SHA256}")
        print(f"artifact_directory={artifact_directory(calibration)}")
        print(f"boot_filename={al.BOOT_MEMBER}")
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
