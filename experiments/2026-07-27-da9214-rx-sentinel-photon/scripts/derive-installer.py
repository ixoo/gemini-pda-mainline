#!/usr/bin/env python3
"""Derive Photon's guarded boot2 installer from exact Candidate Cassini."""

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
import candidate_photon as cp


CASSINI_INSTALLER_SHA256 = (
    "3cd396d88b9ff70a0ffbeff0782d3eb1abdbdebba478c36d0d5c78aabbf9b7eb"
)
TARGET = "gemini@192.168.1.50"


def replace_exact(text: str, old: str, new: str, count: int) -> str:
    actual = text.count(old)
    if actual != count:
        raise ValueError(
            f"installer token count changed for {old!r}: "
            f"expected {count}, found {actual}"
        )
    return text.replace(old, new)


def reconstruct_cassini(work: pathlib.Path) -> str:
    root = pathlib.Path(__file__).resolve().parents[3]
    deriver = (
        root
        / "experiments/2026-07-27-da9214-direct-address-cassini/"
        "scripts/derive-installer.py"
    )
    cp.read_regular(deriver, "Candidate Cassini installer deriver")
    if cp.digest_path(deriver) != cp.CASSINI_DERIVER_SHA256:
        raise ValueError("source-pinned Cassini installer deriver changed")
    output = work / "install-candidate-cassini-boot2.sh"
    result = subprocess.run(
        [sys.executable, os.fspath(deriver), "--output", os.fspath(output)],
        cwd=root,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or "no diagnostic"
        raise ValueError(f"Cassini installer reconstruction failed: {detail}")
    info = output.lstat()
    if (
        output.is_symlink()
        or not stat.S_ISREG(info.st_mode)
        or stat.S_IMODE(info.st_mode) != 0o700
        or cp.digest_path(output) != CASSINI_INSTALLER_SHA256
    ):
        raise ValueError("exact Candidate Cassini installer changed")
    return output.read_text(encoding="utf-8", errors="strict")


def generic_identity_replacements() -> tuple[tuple[str, str, int], ...]:
    return (
        ("CASSINI", "PHOTON", 31),
        ("Cassini", "Photon", 11),
        ("cassini", "photon", 23),
        ("PIONEER", "CASSINI", 8),
        ("Pioneer", "Cassini", 4),
    )


def calibrated_replacements() -> tuple[tuple[str, str, int], ...]:
    return (
        (
            f"readonly PHOTON_RAW_SHA256={cp.CASSINI_BOOT_SHA256}",
            f"readonly PHOTON_RAW_SHA256={cp.RAW_SHA256}",
            1,
        ),
        (
            f"readonly PHOTON_RAW_SIZE={cp.CASSINI_BOOT_SIZE}",
            f"readonly PHOTON_RAW_SIZE={cp.RAW_SIZE}",
            1,
        ),
        (
            f"readonly PHOTON_PADDED_SHA256={cp.CASSINI_PADDED_SHA256}",
            f"readonly PHOTON_PADDED_SHA256={cp.PADDED_SHA256}",
            1,
        ),
        (
            f"readonly PHOTON_ARTIFACT_MANIFEST_SHA256={cp.CASSINI_MANIFEST_SHA256}",
            "readonly PHOTON_ARTIFACT_MANIFEST_SHA256="
            f"{cp.ARTIFACT_MANIFEST_SHA256}",
            1,
        ),
        (
            "EXPECTED_CURRENT_CASSINI_PADDED_SHA256",
            "EXPECTED_CURRENT_PHOTON_R0_PADDED_SHA256",
            8,
        ),
        (
            "Cassini-installed-readback-verified",
            "Photon-r0-installed-readback-verified",
            4,
        ),
        (
            "readonly EXPECTED_CURRENT_PHOTON_R0_PADDED_SHA256="
            "c02244700fcd41a9b6a2d70e90ae2b83276f9dcdd843329643a3d9ced454779d",
            "readonly EXPECTED_CURRENT_PHOTON_R0_PADDED_SHA256="
            f"{cp.PHOTON_R0_PADDED_SHA256}",
            1,
        ),
        (
            'expected_artifact_name="candidate-Photon-da9214-direct-address-e02e2673"',
            f'expected_artifact_name="{cp.ARTIFACT_PREFIX}{cp.RAW_SHA256[:8]}"',
            1,
        ),
        (
            "2026-07-27-da9214-direct-address-photon",
            cp.EXPERIMENT,
            2,
        ),
    )


def derive_text(source: str) -> str:
    cp.require_artifact_pins()
    text = source
    for old, new, count in generic_identity_replacements():
        text = replace_exact(text, old, new, count)
    for old, new, count in calibrated_replacements():
        text = replace_exact(text, old, new, count)

    restored = text
    for old, new, count in reversed(calibrated_replacements()):
        restored = replace_exact(restored, new, old, count)
    for old, new, count in reversed(generic_identity_replacements()):
        restored = replace_exact(restored, new, old, count)
    if restored != source:
        raise ValueError("Photon installer cannot restore exact Cassini foundation")

    required = (
        f"readonly PHOTON_RAW_SHA256={cp.RAW_SHA256}",
        f"readonly PHOTON_RAW_SIZE={cp.RAW_SIZE}",
        f"readonly PHOTON_PADDED_SHA256={cp.PADDED_SHA256}",
        "readonly EXPECTED_CURRENT_PHOTON_R0_PADDED_SHA256="
        f"{cp.PHOTON_R0_PADDED_SHA256}",
        f'expected_artifact_name="{cp.ARTIFACT_PREFIX}{cp.RAW_SHA256[:8]}"',
        f'[[ "$candidate_name" == {cp.BOOT_MEMBER} ]]',
        f"experiment={cp.EXPERIMENT}",
        "candidate_label=Photon",
        f"target must be exact {TARGET}",
        'dd if="$root_stage_file" of="$target" bs=4M iflag=fullblock count=4',
        "check_photon_battery_immediately_before_write",
        "battery_policy=present-health-Good-capacity-81..100",
        "external_power_required=no",
        "reboot_or_shutdown_performed=no",
    )
    for token in required:
        if token not in text:
            raise ValueError(f"derived Photon installer lost token: {token}")
    for stale in (
        "Candidate Pioneer",
        "EXPECTED_CURRENT_PIONEER",
        "EXPECTED_CURRENT_CASSINI",
        "Cassini-installed-readback-verified",
        "candidate-cassini-padded",
        "candidate-Cassini-da9214-direct-address",
        "2026-07-27-da9214-direct-address-cassini",
    ):
        if stale in text:
            raise ValueError(f"derived Photon installer retains stale token: {stale}")
    if text.count('dd if="$root_stage_file" of="$target"') != 1:
        raise ValueError("Photon installer lost its sole bounded target write")
    if any(
        token in text
        for token in ("reboot ", "shutdown ", "poweroff ", "kexec ", "sysrq")
    ):
        raise ValueError("Photon installer gained reboot or shutdown behavior")
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()
    previous_umask = os.umask(0o077)
    try:
        output = validate_output(args.output)
        with tempfile.TemporaryDirectory(
            prefix=".photon-cassini-installer.", dir=output.parent
        ) as raw:
            source = reconstruct_cassini(pathlib.Path(raw))
        text = derive_text(source)
        digest = hashlib.sha256(text.encode()).hexdigest()
        if cp.INSTALLER_SHA256 != "UNRESOLVED" and digest != cp.INSTALLER_SHA256:
            raise ValueError("derived Photon installer identity changed")
        publish(output, text)
        print("validation=photon-installer-derived")
        print(f"installer_sha256={digest}")
        print(f"candidate_raw_sha256={cp.RAW_SHA256}")
        print(f"candidate_padded_sha256={cp.PADDED_SHA256}")
        print(f"expected_predecessor_sha256={cp.PHOTON_R0_PADDED_SHA256}")
        print(f"accepted_target={TARGET}")
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
