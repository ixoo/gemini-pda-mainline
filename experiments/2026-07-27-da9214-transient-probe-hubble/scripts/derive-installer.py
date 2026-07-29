#!/usr/bin/env python3
"""Derive Hubble's guarded boot2 installer from exact Photon r2 machinery."""

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
import candidate_hubble as ch


TARGET = "gemini@192.168.1.50"


def replace_exact(text: str, old: str, new: str, count: int) -> str:
    actual = text.count(old)
    if actual != count:
        raise ValueError(
            f"installer token count changed for {old!r}: "
            f"expected {count}, found {actual}"
        )
    return text.replace(old, new)


def reconstruct_photon(work: pathlib.Path) -> str:
    root = pathlib.Path(__file__).resolve().parents[3]
    deriver = (
        root
        / "experiments/2026-07-27-da9214-rx-sentinel-photon/"
        "scripts/derive-installer.py"
    )
    ch.read_regular(deriver, "Candidate Photon installer deriver")
    if ch.digest_path(deriver) != ch.PHOTON_DERIVER_SHA256:
        raise ValueError("source-pinned Candidate Photon installer deriver changed")
    output = work / "install-candidate-photon-boot2.sh"
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
        raise ValueError(f"Photon installer reconstruction failed: {detail}")
    info = output.lstat()
    if (
        output.is_symlink()
        or not stat.S_ISREG(info.st_mode)
        or stat.S_IMODE(info.st_mode) != 0o700
        or ch.digest_path(output) != ch.PHOTON_INSTALLER_SHA256
    ):
        raise ValueError("exact Candidate Photon installer changed")
    return output.read_text(encoding="utf-8", errors="strict")


def generic_replacements() -> tuple[tuple[str, str, int], ...]:
    return (
        ("PHOTON", "HUBBLE", 39),
        ("Photon", "Hubble", 15),
        ("photon", "hubble", 23),
    )


def calibrated_replacements() -> tuple[tuple[str, str, int], ...]:
    return (
        (
            f"readonly HUBBLE_RAW_SHA256={ch.PHOTON_R2_RAW_SHA256}",
            f"readonly HUBBLE_RAW_SHA256={ch.CASSINI_RAW_SHA256}",
            1,
        ),
        (
            "readonly HUBBLE_RAW_SIZE=7647232",
            f"readonly HUBBLE_RAW_SIZE={ch.CASSINI_RAW_SIZE}",
            1,
        ),
        (
            f"readonly HUBBLE_PADDED_SHA256={ch.PHOTON_R2_PADDED_SHA256}",
            f"readonly HUBBLE_PADDED_SHA256={ch.CASSINI_PADDED_SHA256}",
            1,
        ),
        (
            "readonly HUBBLE_ARTIFACT_MANIFEST_SHA256="
            "5b036d5234ab8d27eddcf152f44d5627de2ba669cb0571491f186cd977f2a551",
            "readonly HUBBLE_ARTIFACT_MANIFEST_SHA256="
            f"{ch.CASSINI_MANIFEST_SHA256}",
            1,
        ),
        (
            "EXPECTED_CURRENT_HUBBLE_R0_PADDED_SHA256",
            "EXPECTED_CURRENT_PHOTON_R2_PADDED_SHA256",
            8,
        ),
        (
            "Hubble-r0-installed-readback-verified",
            "Photon-r2-installed-readback-verified",
            4,
        ),
        (
            "readonly EXPECTED_CURRENT_PHOTON_R2_PADDED_SHA256="
            "5c044fc3d2ccecf399d6ccb058f354b43e9d14b3fb98f9eb448016ab7f9e8e04",
            "readonly EXPECTED_CURRENT_PHOTON_R2_PADDED_SHA256="
            f"{ch.PHOTON_R2_PADDED_SHA256}",
            1,
        ),
        (
            "gemini-mt6797-da9214-hubble.boot.img",
            ch.BOOT_MEMBER,
            1,
        ),
        (
            'expected_artifact_name="candidate-Hubble-r2-da9214-rx-sentinel-75b9081c"',
            f'expected_artifact_name="{ch.ARTIFACT_DIR}"',
            1,
        ),
        (
            "2026-07-27-da9214-rx-sentinel-hubble",
            ch.EXPERIMENT,
            2,
        ),
    )


def derive_text(source: str) -> str:
    ch.require_pins()
    text = source
    for old, new, count in generic_replacements():
        text = replace_exact(text, old, new, count)
    for old, new, count in calibrated_replacements():
        text = replace_exact(text, old, new, count)

    restored = text
    for old, new, count in reversed(calibrated_replacements()):
        restored = replace_exact(restored, new, old, count)
    for old, new, count in reversed(generic_replacements()):
        restored = replace_exact(restored, new, old, count)
    if restored != source:
        raise ValueError("Hubble installer cannot restore exact Photon foundation")

    required = (
        f"readonly HUBBLE_RAW_SHA256={ch.CASSINI_RAW_SHA256}",
        f"readonly HUBBLE_RAW_SIZE={ch.CASSINI_RAW_SIZE}",
        f"readonly HUBBLE_PADDED_SHA256={ch.CASSINI_PADDED_SHA256}",
        "readonly EXPECTED_CURRENT_PHOTON_R2_PADDED_SHA256="
        f"{ch.PHOTON_R2_PADDED_SHA256}",
        f'expected_artifact_name="{ch.ARTIFACT_DIR}"',
        f'[[ "$candidate_name" == {ch.BOOT_MEMBER} ]]',
        f"experiment={ch.EXPERIMENT}",
        "candidate_label=Hubble",
        f"target must be exact {TARGET}",
        'dd if="$root_stage_file" of="$target" bs=4M iflag=fullblock count=4',
        "check_hubble_battery_immediately_before_write",
        "battery_policy=present-health-Good-capacity-81..100",
        "external_power_required=no",
        "reboot_or_shutdown_performed=no",
    )
    for token in required:
        if token not in text:
            raise ValueError(f"derived Hubble installer lost token: {token}")
    for stale in (
        "EXPECTED_CURRENT_HUBBLE_R0",
        "Hubble-r0-installed-readback-verified",
        "candidate-Hubble-r2-da9214-rx-sentinel",
        "2026-07-27-da9214-rx-sentinel-hubble",
    ):
        if stale in text:
            raise ValueError(f"derived Hubble installer retains stale token: {stale}")
    if text.count('dd if="$root_stage_file" of="$target"') != 1:
        raise ValueError("Hubble installer lost its sole bounded target write")
    if any(
        token in text
        for token in ("reboot ", "shutdown ", "poweroff ", "kexec ", "sysrq")
    ):
        raise ValueError("Hubble installer gained reboot or shutdown behavior")
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
            prefix=".hubble-photon-installer.", dir=output.parent
        ) as raw:
            source = reconstruct_photon(pathlib.Path(raw))
        text = derive_text(source)
        digest = hashlib.sha256(text.encode()).hexdigest()
        if ch.INSTALLER_SHA256 != "UNRESOLVED" and digest != ch.INSTALLER_SHA256:
            raise ValueError("derived Hubble installer identity changed")
        publish(output, text)
        print("validation=hubble-installer-derived")
        print(f"installer_sha256={digest}")
        print(f"candidate_raw_sha256={ch.CASSINI_RAW_SHA256}")
        print(f"candidate_padded_sha256={ch.CASSINI_PADDED_SHA256}")
        print(f"expected_predecessor_sha256={ch.PHOTON_R2_PADDED_SHA256}")
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
