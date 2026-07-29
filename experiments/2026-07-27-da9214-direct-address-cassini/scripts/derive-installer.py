#!/usr/bin/env python3
"""Derive Cassini's guarded boot2 installer from exact Candidate AO."""

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
import candidate_cassini as cc

AO_DERIVER_SHA256 = (
    "64edec00e1867784599b59f5d950dea5e9332a4ac70bdba7bae9613390130691"
)
AO_INSTALLER_PREDECESSOR_SHA256 = (
    "1ef53a25c274ed6f0df265fbc4f4e3a64150d5b7fd4cd1e0cde1db53ffb18ccb"
)
TARGET = "gemini@192.168.1.50"
TARGET_CHECK = (
    f'[[ "$target" == {TARGET} ]] || \\\n'
    f"\tdie 'target must be exact {TARGET}'"
)
AO_POWER_BLOCK_SHA256 = (
    "3140c4fd8ebba97864fd12780ae4db3f44888d5d8477c7fb30379c2c426c14e2"
)
POWER_BLOCK_START = "power_sample() {\n"
POWER_BLOCK_END = "validate_stage() {\n"
CASSINI_POWER_BLOCK = r"""sample_power_value() {
	local path=$1
	local policy=$2
	local value
	if [[ -r "$path" ]] && value="$(cat "$path" 2>/dev/null)" &&
		[[ "$value" != *'|'* ]]; then
		printf '%s' "$value"
		return
	fi
	[[ "$policy" == observational ]] && {
		printf unavailable
		return
	}
	fail "required battery attribute unavailable or malformed: $path"
}

power_sample() {
	local ac_online battery_capacity battery_health battery_present battery_status
	local usb_online
	ac_online="$(sample_power_value /sys/class/power_supply/ac/online observational)"
	usb_online="$(sample_power_value /sys/class/power_supply/usb/online observational)"
	battery_present="$(sample_power_value /sys/class/power_supply/battery/present required)"
	battery_status="$(sample_power_value /sys/class/power_supply/battery/status observational)"
	battery_capacity="$(sample_power_value /sys/class/power_supply/battery/capacity required)"
	battery_health="$(sample_power_value /sys/class/power_supply/battery/health required)"
	printf '%s|%s|%s|%s|%s|%s' "$ac_online" "$usb_online" \
		"$battery_present" "$battery_status" "$battery_capacity" "$battery_health"
}

validate_cassini_battery_sample() {
	local ac_online battery_capacity battery_health battery_present battery_status
	local label=$1
	local sample=$2
	local usb_online
	IFS='|' read -r ac_online usb_online battery_present battery_status \
		battery_capacity battery_health <<<"$sample"
	[[ "$battery_present" == 1 ]] || \
		fail "battery is not present at $label gate: $sample"
	[[ "$battery_capacity" =~ ^(0|[1-9][0-9]{0,2})$ ]] || \
		fail "battery capacity is not an integer at $label gate: $sample"
	(( battery_capacity >= 81 && battery_capacity <= 100 )) || \
		fail "battery capacity is not strictly above 80 percent at $label gate: $sample"
	[[ "$battery_health" == Good ]] || \
		fail "battery health is not Good at $label gate: $sample"
}

record_external_power_observation() {
	local observed_capacity observed_health observed_present observed_status
	local sample=$1
	IFS='|' read -r ac_online_observed usb_online_observed observed_present \
		observed_status observed_capacity observed_health <<<"$sample"
}

ac_online_observed=
usb_online_observed=
power_second=

check_power_and_boot_id() {
	local power_first
	power_first="$(power_sample)"
	sleep 2
	power_second="$(power_sample)"
	validate_cassini_battery_sample first "$power_first"
	validate_cassini_battery_sample second "$power_second"
	record_external_power_observation "$power_second"
	[[ "$(cat /proc/sys/kernel/random/boot_id)" == "$EXPECTED_BOOT_ID" ]] || \
		fail 'boot ID changed during the battery check'
}

check_cassini_battery_immediately_before_write() {
	power_second="$(power_sample)"
	validate_cassini_battery_sample immediate-pre-write "$power_second"
	record_external_power_observation "$power_second"
	[[ "$(cat /proc/sys/kernel/random/boot_id)" == "$EXPECTED_BOOT_ID" ]] || \
		fail 'boot ID changed at the immediate pre-write battery gate'
}

"""
AO_PREWRITE_SEQUENCE = (
    '\tprewrite_target_sha256="$(sha256sum "$target" | awk \'{ print $1 }\')"\n'
    '\t[[ "$prewrite_target_sha256" == "$EXPECTED_CURRENT_SHA256" ]] || \\\n'
    '\t\tfail "boot2 changed at the final pre-write checksum: '
    '$prewrite_target_sha256"\n'
    '\tdd if="$root_stage_file" of="$target" bs=4M iflag=fullblock count=4'
)
CASSINI_PREWRITE_SEQUENCE = (
    "\tcheck_cassini_battery_immediately_before_write\n"
    '\tprewrite_target_sha256="$(sha256sum "$target" | awk \'{ print $1 }\')"\n'
    '\t[[ "$prewrite_target_sha256" == "$EXPECTED_CURRENT_SHA256" ]] || \\\n'
    '\t\tfail "boot2 changed at the final pre-write checksum: '
    '$prewrite_target_sha256"\n'
    '\tdd if="$root_stage_file" of="$target" bs=4M iflag=fullblock count=4'
)
AO_POWER_REPORT = 'printf \'power=%s\\n\' "$power_second"'
CASSINI_POWER_REPORT = """printf 'power=%s\\n' "$power_second"
printf 'ac_online_observed=%s\\n' "$ac_online_observed"
printf 'usb_online_observed=%s\\n' "$usb_online_observed"
printf 'external_power_required=no\\n'
printf 'battery_policy=present-health-Good-capacity-81..100\\n'"""


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
    cc.require_artifact_pins()
    return Calibration(
        cc.RAW_SHA256,
        cc.RAW_SIZE,
        cc.ARTIFACT_MANIFEST_SHA256,
        cc.PADDED_SHA256,
    )


def validate_calibration(value: Calibration) -> None:
    for label, digest in (
        ("raw", value.raw_sha256),
        ("manifest", value.manifest_sha256),
        ("padded", value.padded_sha256),
    ):
        if cc.HEX256.fullmatch(digest) is None:
            raise ValueError(f"Cassini {label} SHA-256 is unresolved")
    if not value.raw_size.isdecimal() or not 0 < int(value.raw_size) <= cc.BOOT2_SIZE:
        raise ValueError("Cassini raw size is invalid")
    if value.padded_sha256 == cc.PIONEER_PADDED_SHA256:
        raise ValueError("Cassini padded image equals Pioneer")


def artifact_directory(value: Calibration) -> str:
    return cc.ARTIFACT_PREFIX + value.raw_sha256[:8]


def identity_replacements(
    value: Calibration,
) -> tuple[tuple[str, str, int], ...]:
    return (
        (
            f'expected_artifact_name="{cc.AO_ARTIFACT_DIR}"',
            f'expected_artifact_name="{artifact_directory(value)}"',
            1,
        ),
        (cc.AO_BOOT_MEMBER, cc.BOOT_MEMBER, 1),
        ("2026-07-24-mt6797-dvfsp-one-way-handoff", cc.EXPERIMENT, 2),
        ("Candidate AO", "Candidate Cassini", 8),
        ("candidate-ao", "candidate-cassini", 14),
        ("AO_RAW", "CASSINI_RAW", 16),
        ("AO_PADDED", "CASSINI_PADDED", 11),
        ("AO_ARTIFACT", "CASSINI_ARTIFACT", 4),
        (
            "EXPECTED_CURRENT_AN_PADDED_SHA256",
            "EXPECTED_CURRENT_PIONEER_PADDED_SHA256",
            8,
        ),
        ("candidate_label=AO", "candidate_label=Cassini", 2),
        (
            "AN-installed-readback-verified",
            "Pioneer-installed-readback-verified",
            4,
        ),
    )


def pin_replacements(
    value: Calibration,
) -> tuple[tuple[str, str], ...]:
    return (
        (
            f"readonly CASSINI_RAW_SHA256={cc.AO_RAW_SHA256}",
            f"readonly CASSINI_RAW_SHA256={value.raw_sha256}",
        ),
        (
            f"readonly CASSINI_RAW_SIZE={cc.AO_RAW_SIZE}",
            f"readonly CASSINI_RAW_SIZE={value.raw_size}",
        ),
        (
            f"readonly CASSINI_PADDED_SHA256={cc.AO_PADDED_SHA256}",
            f"readonly CASSINI_PADDED_SHA256={value.padded_sha256}",
        ),
        (
            f"readonly CASSINI_ARTIFACT_MANIFEST_SHA256={cc.AO_MANIFEST_SHA256}",
            f"readonly CASSINI_ARTIFACT_MANIFEST_SHA256={value.manifest_sha256}",
        ),
        (
            "readonly EXPECTED_CURRENT_PIONEER_PADDED_SHA256="
            f"{AO_INSTALLER_PREDECESSOR_SHA256}",
            "readonly EXPECTED_CURRENT_PIONEER_PADDED_SHA256="
            f"{cc.PIONEER_PADDED_SHA256}",
        ),
    )


def replace_power_policy(text: str) -> tuple[str, str]:
    if text.count(POWER_BLOCK_START) != 1 or text.count(POWER_BLOCK_END) != 1:
        raise ValueError("exact AO installer power-policy boundaries changed")
    start = text.index(POWER_BLOCK_START)
    end = text.index(POWER_BLOCK_END, start)
    ao_block = text[start:end]
    if hashlib.sha256(ao_block.encode()).hexdigest() != AO_POWER_BLOCK_SHA256:
        raise ValueError("source-pinned AO installer power policy changed")
    return text[:start] + CASSINI_POWER_BLOCK + text[end:], ao_block


def audit_power_policy(text: str) -> None:
    if text.count(CASSINI_POWER_BLOCK) != 1:
        raise ValueError("Cassini installer battery policy is not exact")
    if text.count(CASSINI_PREWRITE_SEQUENCE) != 1:
        raise ValueError("Cassini immediate pre-write battery gate is not exact")
    if text.count(CASSINI_POWER_REPORT) != 1:
        raise ValueError("Cassini external-power observation report is not exact")
    for stale in (
        '[[ "$power_second" == "$power_first" ]]',
        '[[ "$ac_online" == 1 || "$usb_online" == 1 ]]',
        '"$battery_status" == Full',
        '"$battery_capacity" == 100',
        "neither AC nor USB external power is online",
    ):
        if stale in text:
            raise ValueError(f"Cassini installer retains stale power gate: {stale}")


def derive_text(source: str, value: Calibration) -> str:
    validate_calibration(value)
    text = source
    for old, new, count in identity_replacements(value):
        text = replace_exact(text, old, new, count)
    for old, new in pin_replacements(value):
        text = replace_exact(text, old, new, 1)
    text, ao_power_block = replace_power_policy(text)
    text = replace_exact(text, AO_PREWRITE_SEQUENCE, CASSINI_PREWRITE_SEQUENCE, 1)
    text = replace_exact(text, AO_POWER_REPORT, CASSINI_POWER_REPORT, 1)
    audit_power_policy(text)

    restored = replace_exact(
        text, CASSINI_POWER_REPORT, AO_POWER_REPORT, 1
    )
    restored = replace_exact(
        restored, CASSINI_PREWRITE_SEQUENCE, AO_PREWRITE_SEQUENCE, 1
    )
    restored = replace_exact(restored, CASSINI_POWER_BLOCK, ao_power_block, 1)
    for old, new in reversed(pin_replacements(value)):
        restored = replace_exact(restored, new, old, 1)
    for old, new, count in reversed(identity_replacements(value)):
        restored = replace_exact(restored, new, old, count)
    if restored != source:
        raise ValueError("Cassini installer cannot restore exact AO foundation")

    required = (
        "readonly EXPECTED_CURRENT_PIONEER_PADDED_SHA256="
        f"{cc.PIONEER_PADDED_SHA256}",
        f"readonly CASSINI_PADDED_SHA256={value.padded_sha256}",
        f'expected_artifact_name="{artifact_directory(value)}"',
        f'[[ "$candidate_name" == {cc.BOOT_MEMBER} ]]',
        TARGET_CHECK,
        'dd if="$root_stage_file" of="$target" bs=4M iflag=fullblock count=4',
        "check_cassini_battery_immediately_before_write",
        "battery_policy=present-health-Good-capacity-81..100",
        "external_power_required=no",
        "reboot_or_shutdown_performed=no",
    )
    for token in required:
        if token not in text:
            raise ValueError(f"derived Cassini installer lost token: {token}")
    for stale in (
        "Candidate AN",
        "candidate-an",
        "Candidate AO image",
        "EXPECTED_CURRENT_AN_PADDED_SHA256",
    ):
        if stale in text:
            raise ValueError(f"derived Cassini installer retains {stale}")
    if text.count(TARGET_CHECK) != 1:
        raise ValueError("Cassini installer target is not exact")
    return text


def reconstruct_ao(work: pathlib.Path) -> pathlib.Path:
    root = pathlib.Path(__file__).resolve().parents[3]
    deriver = (
        root
        / "experiments/2026-07-24-mt6797-dvfsp-one-way-handoff/"
        "scripts/derive-installer.py"
    )
    cc.read_regular(deriver, "Candidate AO installer deriver")
    if cc.digest_path(deriver) != AO_DERIVER_SHA256:
        raise ValueError("source-pinned Candidate AO installer deriver changed")
    output = work / "install-candidate-ao-boot2.sh"
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
        raise ValueError(f"AO installer reconstruction failed: {detail}")
    info = output.lstat()
    if (
        output.is_symlink()
        or not stat.S_ISREG(info.st_mode)
        or stat.S_IMODE(info.st_mode) != 0o700
        or cc.digest_path(output) != cc.AO_INSTALLER_SHA256
    ):
        raise ValueError("exact Candidate AO installer changed")
    return output


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
        value = production_calibration()
        validate_calibration(value)
        output = validate_output(args.output)
        with tempfile.TemporaryDirectory(
            prefix=".cassini-ao-installer.", dir=output.parent
        ) as raw:
            source = reconstruct_ao(pathlib.Path(raw)).read_text(
                encoding="utf-8", errors="strict"
            )
        text = derive_text(source, value)
        publish(output, text)
        print("validation=cassini-installer-derived")
        print(f"installer_sha256={hashlib.sha256(text.encode()).hexdigest()}")
        print(f"candidate_raw_sha256={value.raw_sha256}")
        print(f"candidate_padded_sha256={value.padded_sha256}")
        print(f"expected_predecessor_sha256={cc.PIONEER_PADDED_SHA256}")
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
