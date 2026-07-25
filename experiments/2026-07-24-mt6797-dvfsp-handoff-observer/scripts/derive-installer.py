#!/usr/bin/env python3
"""Derive AN's guarded boot2 installer from exact Candidate AL."""

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

import candidate_an as an


AL_DERIVER_SHA256 = (
    "af9bddda3e98621e2396912a1da0db8d05d1cf14af6179fef2f607a0a27c6034"
)
AL_INSTALLER_SHA256 = (
    "a1ee9a53fd52b4f0a59c8d3946666d3578ce256bd627fb3e1d98a51a2aa26104"
)
TARGET = "gemini@192.168.1.50"
AL_TARGET_CHECK = (
    '[[ "$target" =~ ^[A-Za-z_][A-Za-z0-9._-]*@'
    '[A-Za-z0-9][A-Za-z0-9.-]*$ ]] || \\\n'
    "\tdie 'target must be a simple USER@HOST value'"
)
AN_TARGET_CHECK = (
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
            f"AL installer token count changed for {old!r}: "
            f"expected {count}, found {actual}"
        )
    return text.replace(old, new)


def production_calibration() -> Calibration:
    an.require_artifact_pins()
    calibration = Calibration(
        an.RAW_SHA256,
        an.RAW_SIZE,
        an.ARTIFACT_MANIFEST_SHA256,
        an.PADDED_SHA256,
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
        if an.HEX256.fullmatch(value) is None:
            raise ValueError(f"Candidate AN {label} SHA-256 is unresolved or malformed")
    if (
        not calibration.raw_size.isdecimal()
        or not 0 < int(calibration.raw_size) <= an.BOOT2_SIZE
    ):
        raise ValueError("Candidate AN raw size is unresolved, malformed, or oversized")
    if calibration.raw_sha256 in {an.AH_RAW_SHA256, an.AL_RAW_SHA256}:
        raise ValueError("Candidate AN raw identity equals a predecessor")
    if calibration.manifest_sha256 == an.AL_ARTIFACT_MANIFEST_SHA256:
        raise ValueError("Candidate AN artifact manifest equals Candidate AL")
    if calibration.padded_sha256 == an.AL_PADDED_SHA256:
        raise ValueError("Candidate AN padded identity equals Candidate AL")


def artifact_directory(calibration: Calibration) -> str:
    return an.ARTIFACT_PREFIX + calibration.raw_sha256[:8]


def identity_replacements(
    calibration: Calibration,
) -> tuple[tuple[str, str, int], ...]:
    return (
        (
            f'expected_artifact_name="{an.AL_ARTIFACT_DIR}"',
            f'expected_artifact_name="{artifact_directory(calibration)}"',
            1,
        ),
        ("gemini-da9214-resource-only.boot.img", an.BOOT_MEMBER, 1),
        ("2026-07-23-da9214-resource-only", an.EXPERIMENT, 2),
        ("Candidate AL", "Candidate AN", 8),
        ("candidate-al", "candidate-an", 14),
        ("AL_RAW", "AN_RAW", 16),
        ("AL_PADDED", "AN_PADDED", 11),
        ("AL_ARTIFACT", "AN_ARTIFACT", 4),
        (
            "EXPECTED_CURRENT_AK_PADDED_SHA256",
            "EXPECTED_CURRENT_AL_PADDED_SHA256",
            8,
        ),
        ("candidate_label=AL", "candidate_label=AN", 2),
        ("AK-installed-readback-verified", "AL-installed-readback-verified", 4),
        ("--target USER@HOST", f"--target {TARGET}", 1),
        (AL_TARGET_CHECK, AN_TARGET_CHECK, 1),
    )


def pin_replacements(
    calibration: Calibration,
) -> tuple[tuple[str, str], ...]:
    return (
        (
            f"readonly AN_RAW_SHA256={an.AL_RAW_SHA256}",
            f"readonly AN_RAW_SHA256={calibration.raw_sha256}",
        ),
        (
            f"readonly AN_RAW_SIZE={an.AL_RAW_SIZE}",
            f"readonly AN_RAW_SIZE={calibration.raw_size}",
        ),
        (
            f"readonly AN_PADDED_SHA256={an.AL_PADDED_SHA256}",
            f"readonly AN_PADDED_SHA256={calibration.padded_sha256}",
        ),
        (
            "readonly AN_ARTIFACT_MANIFEST_SHA256="
            f"{an.AL_ARTIFACT_MANIFEST_SHA256}",
            f"readonly AN_ARTIFACT_MANIFEST_SHA256={calibration.manifest_sha256}",
        ),
        (
            "readonly EXPECTED_CURRENT_AL_PADDED_SHA256="
            "66902cb2f2faa5c4c6457ce89ff67aa25e5345ac43ee0ca8062a55e0fbac870e",
            f"readonly EXPECTED_CURRENT_AL_PADDED_SHA256={an.AL_PADDED_SHA256}",
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
        raise ValueError("Candidate AN installer cannot restore exact AL foundation")

    required = (
        f"readonly EXPECTED_CURRENT_AL_PADDED_SHA256={an.AL_PADDED_SHA256}",
        f"readonly AN_PADDED_SHA256={calibration.padded_sha256}",
        f'expected_artifact_name="{artifact_directory(calibration)}"',
        f'[[ "$candidate_name" == {an.BOOT_MEMBER} ]]',
        f"--target {TARGET}",
        AN_TARGET_CHECK,
        'dd if="$root_stage_file" of="$target" bs=4M iflag=fullblock count=4',
        "reboot_or_shutdown_performed=no",
    )
    for token in required:
        if token not in text:
            raise ValueError(
                f"derived Candidate AN installer lost safety token: {token}"
            )
    if "Candidate AK" in text or "EXPECTED_CURRENT_AK_PADDED_SHA256" in text:
        raise ValueError("derived Candidate AN installer retains stale AK predecessor")
    if AL_TARGET_CHECK in text or text.count(AN_TARGET_CHECK) != 1:
        raise ValueError("derived Candidate AN installer target is not source-pinned")
    return text


def repository_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[3]


def reconstruct_al(work: pathlib.Path) -> pathlib.Path:
    root = repository_root()
    deriver = (
        root
        / "experiments/2026-07-23-da9214-resource-only/scripts/"
        "derive-installer.py"
    )
    an.read_regular(deriver, "Candidate AL installer deriver")
    if an.digest_path(deriver) != AL_DERIVER_SHA256:
        raise ValueError("source-pinned Candidate AL installer deriver changed")
    output = work / "install-candidate-al-boot2.sh"
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
        raise ValueError(f"Candidate AL installer reconstruction failed: {detail}")
    info = output.lstat()
    if (
        output.is_symlink()
        or not stat.S_ISREG(info.st_mode)
        or stat.S_IMODE(info.st_mode) != 0o700
        or an.digest_path(output) != AL_INSTALLER_SHA256
    ):
        raise ValueError("exact Candidate AL installer reconstruction changed")
    return output


def validate_output(path: pathlib.Path) -> pathlib.Path:
    if not path.name or path.name in {".", ".."} or path.exists() or path.is_symlink():
        raise ValueError("Candidate AN installer output is invalid or already exists")
    info = path.parent.lstat()
    if path.parent.is_symlink() or not stat.S_ISDIR(info.st_mode):
        raise ValueError("Candidate AN installer output parent is unsafe")
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
            prefix=".candidate-an-al-installer.", dir=output.parent
        ) as raw:
            source_path = reconstruct_al(pathlib.Path(raw))
            source = source_path.read_text(encoding="utf-8", errors="strict")
        text = derive_text(source, calibration)
        publish(output, text)
        print("validation=candidate-an-installer-derivation")
        print(f"foundation_installer_sha256={AL_INSTALLER_SHA256}")
        print(
            "installer_sha256="
            f"{__import__('hashlib').sha256(text.encode()).hexdigest()}"
        )
        print(f"candidate_raw_sha256={calibration.raw_sha256}")
        print(f"candidate_raw_size={calibration.raw_size}")
        print(f"candidate_artifact_manifest_sha256={calibration.manifest_sha256}")
        print(f"candidate_padded_sha256={calibration.padded_sha256}")
        print(f"expected_predecessor_sha256={an.AL_PADDED_SHA256}")
        print(f"accepted_target={TARGET}")
        print(f"artifact_directory={artifact_directory(calibration)}")
        print(f"boot_filename={an.BOOT_MEMBER}")
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
