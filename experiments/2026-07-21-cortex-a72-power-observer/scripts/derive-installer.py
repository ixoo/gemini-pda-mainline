#!/usr/bin/env python3
"""Derive Candidate AE's guarded boot2 installer from exact Candidate AD."""

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
from dataclasses import dataclass


BOOT2_SIZE = 16 * 1024 * 1024
AD_INSTALLER_SHA256 = (
    "41f8a20b04f0bed34ce7b3a77662ee31ecae778b2372afb5275c436914d944c3"
)
AD_RAW_SHA256 = "a1b61d8c34b5a447f1f672663f4e74fed6eb465b90154392a3c42f4db030826b"
AD_RAW_SIZE = "7378944"
AD_PADDED_SHA256 = (
    "371fda65cf9c21406d6b08e52ffb46690426a7d356ba67aa9ffe1410e7d1e495"
)
AC_PADDED_SHA256 = (
    "318f418a5e67042ecdd1c98a8767c104c8cfc68c3d56cd7c0d13cb3c5fad8a84"
)

# These three values are the only production calibration edits permitted after
# the two final Candidate AE artifacts agree byte-for-byte.  The command-line
# interface deliberately has no calibration override flags or environment
# variables.  Unit tests pass a fixture Calibration directly to the pure
# transform and therefore cannot weaken the executable path.
AE_RAW_SHA256 = "d9895f619ea9b4bd8fcd5ba8e8bb546d50afd65bccc1a4209d950f56408c1e0d"
AE_RAW_SIZE = "7385088"
AE_PADDED_SHA256 = "0e7cc17ce214f3904bae7172c81e50327ffda19fa46601c76bac36232b1079a9"

HEX256 = re.compile(r"^[0-9a-f]{64}$")
REBOOT_ACTION = re.compile(
    r"(?m)^[ \t]*(?:sudo[ \t]+)?"
    r"(?:reboot|shutdown|poweroff|halt|kexec)(?:[ \t]|$)"
)


@dataclass(frozen=True)
class Calibration:
    raw_sha256: str
    raw_size: str
    padded_sha256: str


PRODUCTION_CALIBRATION = Calibration(
    AE_RAW_SHA256,
    AE_RAW_SIZE,
    AE_PADDED_SHA256,
)

# Each replacement is a board-candidate identity, evidence label, or checksum
# namespace change.  Counts pin the exact validated AD foundation's shape.
IDENTITY_REPLACEMENTS = (
    ("candidate-AD-smp8-final", "candidate-AE-a72-observer", 1),
    ("gemini-smp8", "gemini-a72-observer", 1),
    (
        "2026-07-21-smp8-boot-diagnostic",
        "2026-07-21-cortex-a72-power-observer",
        2,
    ),
    ("Candidate AD", "Candidate AE", 7),
    ("candidate-ad", "candidate-ae", 14),
    ("AD_RAW", "AE_RAW", 17),
    ("AD_PADDED", "AE_PADDED", 11),
    (
        "EXPECTED_CURRENT_AC_PADDED_SHA256",
        "EXPECTED_CURRENT_AD_PADDED_SHA256",
        8,
    ),
    ("candidate_label=AD", "candidate_label=AE", 2),
    ("AC-hardware-passed", "AD-hardware-passed", 4),
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_path(path: pathlib.Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def replace_exact(text: str, old: str, new: str, count: int) -> str:
    actual = text.count(old)
    if actual != count:
        raise ValueError(
            f"installer foundation token count changed: {old!r}: "
            f"expected {count}, found {actual}"
        )
    return text.replace(old, new)


def validate_calibration(calibration: Calibration) -> None:
    values = (
        ("AE_RAW_SHA256", calibration.raw_sha256),
        ("AE_RAW_SIZE", calibration.raw_size),
        ("AE_PADDED_SHA256", calibration.padded_sha256),
    )
    for name, value in values:
        if value.startswith("TO_PIN_"):
            raise ValueError(f"Candidate AE calibration remains unpinned: {name}")
    if HEX256.fullmatch(calibration.raw_sha256) is None:
        raise ValueError("Candidate AE raw SHA-256 is malformed")
    if HEX256.fullmatch(calibration.padded_sha256) is None:
        raise ValueError("Candidate AE padded SHA-256 is malformed")
    if not calibration.raw_size.isdecimal():
        raise ValueError("Candidate AE raw size is malformed")
    raw_size = int(calibration.raw_size)
    if not 0 < raw_size <= BOOT2_SIZE:
        raise ValueError("Candidate AE raw size is invalid or exceeds boot2")
    if calibration.raw_sha256 == AD_RAW_SHA256:
        raise ValueError("Candidate AE raw identity equals Candidate AD")
    if calibration.padded_sha256 == AD_PADDED_SHA256:
        raise ValueError("Candidate AE padded identity equals installed Candidate AD")


def expected_transform(source_text: str, calibration: Calibration) -> str:
    validate_calibration(calibration)
    text = source_text
    for old, new, count in IDENTITY_REPLACEMENTS:
        text = replace_exact(text, old, new, count)

    pins = (
        (
            f"readonly AE_RAW_SHA256={AD_RAW_SHA256}",
            f"readonly AE_RAW_SHA256={calibration.raw_sha256}",
        ),
        (
            f"readonly AE_RAW_SIZE={AD_RAW_SIZE}",
            f"readonly AE_RAW_SIZE={calibration.raw_size}",
        ),
        (
            f"readonly AE_PADDED_SHA256={AD_PADDED_SHA256}",
            f"readonly AE_PADDED_SHA256={calibration.padded_sha256}",
        ),
        (
            f"readonly EXPECTED_CURRENT_AD_PADDED_SHA256={AC_PADDED_SHA256}",
            f"readonly EXPECTED_CURRENT_AD_PADDED_SHA256={AD_PADDED_SHA256}",
        ),
    )
    for old, new in pins:
        text = replace_exact(text, old, new, 1)
    return text


def validate_safety(text: str, calibration: Calibration) -> None:
    """Reject loss of an inherited AD storage or device safety invariant."""

    required_counts = {
        "readonly BOOT2_SIZE=16777216": 1,
        f"readonly AE_RAW_SHA256={calibration.raw_sha256}": 1,
        f"readonly AE_RAW_SIZE={calibration.raw_size}": 1,
        f"readonly AE_PADDED_SHA256={calibration.padded_sha256}": 1,
        f"readonly EXPECTED_CURRENT_AD_PADDED_SHA256={AD_PADDED_SHA256}": 1,
        "usage: install-candidate-ae-boot2.sh": 1,
        "gemini-a72-observer.boot.img": 1,
        'candidate-AE-a72-observer-${AE_RAW_SHA256:0:8}': 1,
        "candidate-ae-padded-boot2.img": 1,
        "expected_previous_label=AD-hardware-passed": 1,
        "candidate_label=AE": 2,
        "resolve_boot2": 4,
        "lsblk -brnpo NAME,PARTLABEL,TYPE,SIZE,RO,MOUNTPOINT": 1,
        "readlink -f /dev/disk/by-partlabel/boot2": 1,
        '[[ "$label" == boot2 && "$type" == part && '
        '"$size" == "$EXPECTED_SIZE" && "$ro" == 0 ]]': 1,
        "boot2 is not root-readable and writable": 1,
        "boot2 is the active root": 1,
        "boot2 is mounted": 1,
        "boot2 is active swap": 1,
        "boot2 has holders": 1,
        "power changed during stability sample": 1,
        "neither AC nor USB external power is online": 1,
        "battery is not present, full, and healthy": 1,
        "IdentitiesOnly=yes": 1,
        "IdentityAgent=none": 1,
        "StrictHostKeyChecking=yes": 1,
        "artifacts/credentials/gemini_ed25519": 1,
        "Gemini identity mode is not 0600": 1,
        "target must be a simple USER@HOST value": 1,
        "result=skipped-already-matching": 2,
        "padded candidate prefix differs from raw candidate": 1,
        "padded candidate tail is not all zero": 1,
        "zero-padded Candidate AE checksum is not calibrated": 1,
        "chmod 0600 \"$backup_partial\"": 1,
        "boot2-before-candidate-ae.img.sha256": 1,
        "boot2 backup checksum mismatch": 1,
        "durably flushed pre-write backup failed checksum revalidation": 1,
        "durably flushed pre-write backup checksum sidecar changed": 1,
        "boot ID changed immediately before write": 1,
        "boot2 changed at the final pre-write checksum": 1,
        'dd if="$root_stage_file" of="$target" bs=4M '
        "iflag=fullblock count=4": 1,
        "conv=fsync,notrunc status=none": 1,
        'blockdev --flushbufs "$target"': 1,
        "full boot2 readback stream length mismatch": 1,
        "full boot2 readback checksum mismatch": 1,
        "full boot2 readback differs byte-for-byte": 1,
        "durably flushed full local readback failed checksum revalidation": 1,
        "durably flushed readback checksum sidecar changed": 1,
        "final target checksum mismatch": 1,
        "reboot_or_shutdown_performed=no": 2,
    }
    for token, expected in required_counts.items():
        actual = text.count(token)
        if actual != expected:
            raise ValueError(
                f"derived installer safety token changed: {token!r}: "
                f"expected {expected}, found {actual}"
            )

    forbidden = (
        "Candidate AC",
        "candidate-ac",
        "Candidate AD",
        "candidate-ad",
        "gemini-smp8.boot.img",
        "candidate_label=AD",
        "expected_previous_label=AC-hardware-passed",
        "/dev/mmcblk0p30",
        "/dev/disk/by-partlabel/boot3",
        "sysrq-trigger",
        "sudo -S",
        "sshpass",
        "BEGIN OPENSSH PRIVATE KEY",
    )
    for token in forbidden:
        if token in text:
            raise ValueError(f"derived installer gained forbidden behavior: {token!r}")
    if REBOOT_ACTION.search(text):
        raise ValueError("derived installer gained reboot or slot-selection behavior")


def validate_exact_delta(
    source_text: str, text: str, calibration: Calibration
) -> None:
    if text != expected_transform(source_text, calibration):
        raise ValueError("Candidate AE installer is not the exact narrow AD transform")


def derive_text(source_data: bytes, calibration: Calibration) -> str:
    if digest(source_data) != AD_INSTALLER_SHA256:
        raise ValueError("exact validated Candidate AD installer foundation changed")
    try:
        source_text = source_data.decode("utf-8")
    except UnicodeError as exc:
        raise ValueError("Candidate AD installer is not UTF-8") from exc
    text = expected_transform(source_text, calibration)
    # This equality is intentionally redundant with the construction. It gives
    # mutation tests and future refactors one exact, narrow-delta gate.
    validate_exact_delta(source_text, text, calibration)
    validate_safety(text, calibration)
    return text


def run_lineage(command: list[str], cwd: pathlib.Path) -> None:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        error = result.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(
            f"Candidate AD installer lineage command failed ({result.returncode}): "
            f"{error}"
        )


def verify_lineage_output(path: pathlib.Path, expected_sha256: str) -> None:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode):
        raise ValueError("Candidate AD installer lineage emitted an unsafe file")
    if stat.S_IMODE(info.st_mode) != 0o700:
        raise ValueError("Candidate AD installer lineage mode changed")
    if digest_path(path) != expected_sha256:
        raise ValueError("Candidate AD installer lineage identity changed")


def reconstruct_ad_installer(repo_root: pathlib.Path, work: pathlib.Path) -> pathlib.Path:
    """Reproduce the exact accepted AD installer from tracked lineage inputs."""

    python = sys.executable
    ab_scripts = (
        repo_root
        / "experiments/2026-07-20-mt6797-kernel-restart-diagnostic/scripts"
    )
    aa = work / "install-candidate-aa-r1-boot2.sh"
    run_lineage(
        [python, os.fspath(ab_scripts / "materialize-aa-r1-installer.py"),
         "--output", os.fspath(aa)],
        repo_root,
    )
    verify_lineage_output(
        aa, "f081ef03b2dce68d28458eacdcc184a5550c88eeb75579fab61359e936a40f9f"
    )

    ab = work / "install-candidate-ab-boot2.sh"
    run_lineage(
        [
            python,
            os.fspath(ab_scripts / "derive-installer.py"),
            "--source", os.fspath(aa),
            "--output", os.fspath(ab),
            "--raw-sha256",
            "61c74592267466735164c19f8b831ea18db2892de95e32109f2aacd7ec5c5446",
            "--raw-size", "7378944",
            "--padded-sha256",
            "b58c0347d34a3fd9031c74cb03447dd7a6fc630d5b8ea2b7eabc36827e754350",
        ],
        repo_root,
    )
    verify_lineage_output(
        ab, "260c7d907cdd7656b664d71a6564109a6ed03fcb95bf3e5c6da8bcc3bff4050c"
    )

    ac = work / "install-candidate-ac-boot2.sh"
    run_lineage(
        [
            python,
            os.fspath(
                repo_root
                / "experiments/2026-07-21-usb-gadget-ethernet/scripts/derive-installer.py"
            ),
            "--source", os.fspath(ab),
            "--output", os.fspath(ac),
            "--raw-sha256",
            "3491c119d19b7b0af2ac2342659648227182ead0e32bb4c39a66fa22cadfb39d",
            "--raw-size", "7378944",
            "--padded-sha256", AC_PADDED_SHA256,
        ],
        repo_root,
    )
    verify_lineage_output(
        ac, "b1a71fc2bb6d2e3b374b16dcfdeec4ec334acf7596556c7d9631930997664dd7"
    )

    ad = work / "install-candidate-ad-boot2.sh"
    run_lineage(
        [
            python,
            os.fspath(
                repo_root
                / "experiments/2026-07-21-smp8-boot-diagnostic/scripts/derive-installer.py"
            ),
            "--source", os.fspath(ac),
            "--output", os.fspath(ad),
            "--raw-sha256", AD_RAW_SHA256,
            "--raw-size", AD_RAW_SIZE,
            "--padded-sha256", AD_PADDED_SHA256,
        ],
        repo_root,
    )
    verify_lineage_output(ad, AD_INSTALLER_SHA256)
    return ad


def read_exact_source(path: pathlib.Path) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode):
        raise ValueError("Candidate AD installer foundation is unsafe")
    data = path.read_bytes()
    if digest(data) != AD_INSTALLER_SHA256:
        raise ValueError("exact validated Candidate AD installer foundation changed")
    return data


def validate_output_path(path: pathlib.Path) -> pathlib.Path:
    if not path.name or path.name in {".", ".."}:
        raise ValueError("Candidate AE installer output name is invalid")
    if path.exists() or path.is_symlink():
        raise ValueError("refusing to overwrite Candidate AE installer")
    parent_info = path.parent.lstat()
    if path.parent.is_symlink() or not stat.S_ISDIR(parent_info.st_mode):
        raise ValueError("Candidate AE installer output parent is unsafe")
    parent = path.parent.resolve(strict=True)
    return parent / path.name


def publish(path: pathlib.Path, text: str) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o700)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        os.fchmod(stream.fileno(), 0o700)
        stream.write(text)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=pathlib.Path,
        help="exact validated AD installer; omit to reconstruct the tracked lineage",
    )
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    previous_umask = os.umask(0o077)
    try:
        # Refuse before inspecting a source, reconstructing lineage, publishing
        # output, opening SSH, or reaching any installer/device behavior.
        validate_calibration(PRODUCTION_CALIBRATION)
        output = validate_output_path(args.output)
        script_dir = pathlib.Path(__file__).resolve().parent
        repo_root = script_dir.parents[2]
        if args.source is not None:
            source_data = read_exact_source(args.source)
        else:
            with tempfile.TemporaryDirectory(
                prefix=".candidate-ae-ad-foundation.", dir=output.parent
            ) as raw_temp:
                source = reconstruct_ad_installer(repo_root, pathlib.Path(raw_temp))
                source_data = read_exact_source(source)
        text = derive_text(source_data, PRODUCTION_CALIBRATION)
        publish(output, text)
        print("validation=candidate-ae-installer-derivation")
        print(f"installer_sha256={digest(text.encode('utf-8'))}")
        print(f"candidate_raw_sha256={AE_RAW_SHA256}")
        print(f"candidate_raw_size={AE_RAW_SIZE}")
        print(f"candidate_padded_sha256={AE_PADDED_SHA256}")
        print(f"expected_predecessor_sha256={AD_PADDED_SHA256}")
        print("sole_target_write=one-bounded-16MiB-write")
        print("reboot_or_slot_selection=none")
        return 0
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    finally:
        os.umask(previous_umask)


if __name__ == "__main__":
    raise SystemExit(main())
