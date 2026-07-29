#!/usr/bin/env python3
"""Derive Quasar's guarded boot2 installer from exact Vega machinery."""

from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import stat
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
import installer_quasar as io


def replace_exact(text: str, old: str, new: str, count: int) -> str:
    actual = text.count(old)
    if actual != count:
        raise ValueError(
            f"installer token count changed for {old!r}: "
            f"expected {count}, found {actual}"
        )
    return text.replace(old, new)


def reconstruct_vega(work: pathlib.Path) -> str:
    repository = pathlib.Path(__file__).resolve().parents[3]
    deriver = repository / io.VEGA_DERIVER
    pins = repository / io.VEGA_PINS
    io.read_regular(deriver, "Candidate Vega installer deriver")
    io.read_regular(pins, "Candidate Vega installer pins")
    if io.digest_path(deriver) != io.VEGA_DERIVER_SHA256:
        raise ValueError("source-pinned Candidate Vega installer deriver changed")
    if io.digest_path(pins) != io.VEGA_PINS_SHA256:
        raise ValueError("source-pinned Candidate Vega installer pins changed")

    output = work / "install-candidate-vega-boot2.sh"
    result = subprocess.run(
        [sys.executable, os.fspath(deriver), "--output", os.fspath(output)],
        cwd=repository,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or "no diagnostic"
        raise ValueError(f"Vega installer reconstruction failed: {detail}")
    info = output.lstat()
    if (
        output.is_symlink()
        or not stat.S_ISREG(info.st_mode)
        or stat.S_IMODE(info.st_mode) != 0o700
        or io.digest_path(output) != io.VEGA_INSTALLER_SHA256
    ):
        raise ValueError("exact Candidate Vega installer changed")
    return output.read_text(encoding="utf-8", errors="strict")


def generic_replacements() -> tuple[tuple[str, str, int], ...]:
    return (
        ("VEGA", "QUASAR", 31),
        ("Vega", "Quasar", 11),
        ("vega", "quasar", 23),
    )


def calibrated_replacements(
    pins: io.ArtifactPins,
) -> tuple[tuple[str, str, int], ...]:
    return (
        (
            "readonly QUASAR_RAW_SHA256="
            "08cf45530de0b15441680fafecad1d56557f2285b1d06307fee6ac55ae9b8975",
            f"readonly QUASAR_RAW_SHA256={pins.raw_sha256}",
            1,
        ),
        (
            "readonly QUASAR_RAW_SIZE=7747584",
            f"readonly QUASAR_RAW_SIZE={pins.raw_size}",
            1,
        ),
        (
            "readonly QUASAR_PADDED_SHA256="
            "4fc71c508c40081c91a48e13af1c8a0ac5fb79871e04d63f98efa4ddbea3e6a7",
            f"readonly QUASAR_PADDED_SHA256={pins.padded_sha256}",
            1,
        ),
        (
            "readonly QUASAR_ARTIFACT_MANIFEST_SHA256="
            "0abe52ebbda743bfd031fe856aa82dd8d9e9625620aa810ab1a71b9356f4ae07",
            "readonly QUASAR_ARTIFACT_MANIFEST_SHA256="
            f"{pins.manifest_sha256}",
            1,
        ),
        (
            "EXPECTED_CURRENT_ORION_PADDED_SHA256",
            "EXPECTED_CURRENT_VEGA_PADDED_SHA256",
            8,
        ),
        (
            "Orion-installed-readback-verified",
            "Vega-installed-readback-verified",
            4,
        ),
        (
            "readonly EXPECTED_CURRENT_VEGA_PADDED_SHA256="
            "74f9d9c8cae1213665db2100dda72e0531e0b221cd74a660fc183edcd7bb50d4",
            "readonly EXPECTED_CURRENT_VEGA_PADDED_SHA256="
            f"{io.VEGA_PADDED_SHA256}",
            1,
        ),
        (
            'expected_artifact_name="candidate-Quasar-mt6797-i2c6-08cf4553"',
            f'expected_artifact_name="{pins.artifact_dir}"',
            1,
        ),
    )


CRITICAL_TOKEN_COUNTS = {
    "lsblk -brnpo NAME,PARTLABEL,TYPE,SIZE,RO,MOUNTPOINT": 1,
    '$2 == "boot2" { print }': 1,
    "readlink -f /dev/disk/by-partlabel/boot2": 1,
    '[[ -r "$target" && -w "$target" ]]': 1,
    'blockdev --getsize64 "$target"': 1,
    'blockdev --getro "$target"': 1,
    'cat "/sys/class/block/${target##*/}/ro"': 1,
    '[[ "$active_root" != "$target" ]]': 1,
    "/proc/self/mountinfo": 1,
    "swapon --noheadings --raw --show=NAME": 1,
    'find "/sys/class/block/${target##*/}/holders"': 1,
    '[[ "$battery_present" == 1 ]]': 1,
    "battery_capacity >= 81 && battery_capacity <= 100": 1,
    '[[ "$battery_health" == Good ]]': 1,
    "check_quasar_battery_immediately_before_write": 2,
    '[[ "$prewrite_target_sha256" == "$EXPECTED_CURRENT_SHA256" ]]': 1,
    '"sudo -n -- dd if=\'$live_target\' bs=4M iflag=fullblock count=4 status=none"': 1,
    '[[ "$backup_sha256" == "$EXPECTED_CURRENT_VEGA_PADDED_SHA256" ]]': 1,
    'dd if="$root_stage_file" of="$target" bs=4M iflag=fullblock count=4': 1,
    'blockdev --flushbufs "$target"': 1,
    '[[ "$target_sha256" == "$EXPECTED_CANDIDATE_SHA256" ]]': 2,
    'dd of="$readback_partial" bs=1048576 conv=notrunc': 1,
    '[[ "$readback_stream_bytes" == "$BOOT2_SIZE" ]]': 1,
    'cmp -s "$padded" "$readback_partial"': 1,
    "remote_gate post": 1,
    '[[ "$(dirname -- "$backup_dir")" == "$private_root" ]]': 2,
    '[[ "$(file_mode "$identity")" == 600 ]]': 1,
}


def validate_contract(text: str, pins: io.ArtifactPins) -> None:
    io.require_artifact_pins(pins)
    exact_counts = {
        f"readonly QUASAR_RAW_SHA256={pins.raw_sha256}": 1,
        f"readonly QUASAR_RAW_SIZE={pins.raw_size}": 1,
        f"readonly QUASAR_PADDED_SHA256={pins.padded_sha256}": 1,
        "readonly QUASAR_ARTIFACT_MANIFEST_SHA256="
        f"{pins.manifest_sha256}": 1,
        "readonly EXPECTED_CURRENT_VEGA_PADDED_SHA256="
        f"{io.VEGA_PADDED_SHA256}": 1,
        f'expected_artifact_name="{pins.artifact_dir}"': 1,
        f'[[ "$candidate_name" == {io.BOOT_MEMBER} ]]': 1,
        f"experiment={io.EXPERIMENT}": 2,
        "candidate_label=Quasar": 2,
        "EXPECTED_CURRENT_VEGA_PADDED_SHA256": 8,
        "Vega-installed-readback-verified": 4,
        'dd if="$root_stage_file" of="$target"': 1,
        'of="$target"': 1,
        "reboot_or_shutdown_performed=no": 2,
    }
    for token, expected in exact_counts.items():
        actual = text.count(token)
        if actual != expected:
            raise ValueError(
                f"derived Quasar installer count changed for {token!r}: "
                f"expected {expected}, found {actual}"
            )
    for token, expected in CRITICAL_TOKEN_COUNTS.items():
        actual = text.count(token)
        if actual != expected:
            raise ValueError(
                f"derived Quasar safety gate changed for {token!r}: "
                f"expected {expected}, found {actual}"
            )

    required = (
        f"target must be exact {io.TARGET}",
        "candidate raw size/hash, exact artifact-manifest hash, padded hash",
        "private full",
        "backup, pads the candidate to exactly 16 MiB, writes only boot2",
        "syncs and",
        "flushes, and requires matching full remote and local readbacks",
        "battery_policy=present-health-Good-capacity-81..100",
        "external_power_required=no",
        "sudo -n -- true",
        "live GPT has $row_count exact boot2 rows",
        "boot2 is mounted",
        "boot2 is active swap",
        "boot2 has holders",
        "boot2 is the active root",
        "boot2 is not root-readable and writable",
        "boot2 backup checksum mismatch",
        "post-flush checksum mismatch",
        "full boot2 readback checksum mismatch",
        "full boot2 readback differs byte-for-byte",
        "remote_staging_removed=yes",
        "runtime_result=not-tested",
    )
    for token in required:
        if token not in text:
            raise ValueError(f"derived Quasar installer lost contract token: {token}")
    stale = (
        "EXPECTED_CURRENT_ORION",
        "Orion-installed-readback-verified",
        "candidate-Vega-mt6797-i2c6-08cf4553",
        "gemini-mt6797-i2c6-vega.boot.img",
        "2026-07-27-mt6797-i2c6-vega",
        "boot2-before-candidate-vega",
        "boot2-after-candidate-vega",
        ".gemini-candidate-vega",
    )
    for token in stale:
        if token in text:
            raise ValueError(f"derived Quasar installer retains stale token: {token}")
    forbidden = (
        "reboot ",
        "shutdown ",
        "poweroff ",
        "kexec ",
        "sysrq",
        "sudo -S",
        "SSH_ASKPASS",
        "of=/dev/mmc",
    )
    for token in forbidden:
        if token in text:
            raise ValueError(f"derived Quasar installer gained forbidden token: {token}")


def derive_text(source: str, pins: io.ArtifactPins) -> str:
    io.require_artifact_pins(pins)
    text = source
    for old, new, count in generic_replacements():
        text = replace_exact(text, old, new, count)
    replacements = calibrated_replacements(pins)
    for old, new, count in replacements:
        text = replace_exact(text, old, new, count)
    restored = text
    for old, new, count in reversed(replacements):
        restored = replace_exact(restored, new, old, count)
    for old, new, count in reversed(generic_replacements()):
        restored = replace_exact(restored, new, old, count)
    if restored != source:
        raise ValueError("Quasar installer cannot restore exact Vega foundation")
    validate_contract(text, pins)
    return text


def validate_output(path: pathlib.Path) -> pathlib.Path:
    if not path.name or path.name in {".", ".."} or path.exists() or path.is_symlink():
        raise ValueError("installer output is invalid or exists")
    info = path.parent.lstat()
    if path.parent.is_symlink() or not stat.S_ISDIR(info.st_mode):
        raise ValueError("installer output parent is unsafe")
    return path.parent.resolve(strict=True) / path.name


def publish(path: pathlib.Path, text: str) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o700)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        os.fchmod(stream.fileno(), 0o700)
        stream.write(text)
        stream.flush()
        os.fsync(stream.fileno())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()
    previous_umask = os.umask(0o077)
    try:
        repository = pathlib.Path(__file__).resolve().parents[3]
        pins = io.production_pins()
        io.require_artifact_pins(pins)
        predecessor_record = io.require_predecessor_evidence(repository)
        reproducibility_record = io.require_reproducibility_record(repository, pins)
        io.require_installer_pin()
        output = validate_output(args.output)
        with tempfile.TemporaryDirectory(
            prefix=".quasar-vega-installer.", dir=output.parent
        ) as raw:
            source = reconstruct_vega(pathlib.Path(raw))
        text = derive_text(source, pins)
        digest = hashlib.sha256(text.encode()).hexdigest()
        if io.INSTALLER_SHA256 != "UNRESOLVED" and digest != io.INSTALLER_SHA256:
            raise ValueError("derived Quasar installer identity changed")
        publish(output, text)
        print("validation=quasar-installer-derived")
        print(f"installer_sha256={digest}")
        print(f"artifact={pins.artifact_dir}")
        print(f"candidate_raw_sha256={pins.raw_sha256}")
        print(f"candidate_raw_size={pins.raw_size}")
        print(f"candidate_manifest_sha256={pins.manifest_sha256}")
        print(f"candidate_padded_sha256={pins.padded_sha256}")
        print(f"reproducibility_record_sha256={reproducibility_record}")
        print(f"predecessor_record_sha256={predecessor_record}")
        print(f"expected_predecessor_sha256={io.VEGA_PADDED_SHA256}")
        print(f"accepted_target={io.TARGET}")
        print("sole_target_write=one-bounded-16MiB-boot2-write")
        print("stable_power=battery-present-health-Good-capacity-81..100")
        print("ac_usb_online=observational-only")
        print("reboot_or_slot_selection=none")
        print(f"output={output}")
        return 0
    except (OSError, RuntimeError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    finally:
        os.umask(previous_umask)


if __name__ == "__main__":
    raise SystemExit(main())
