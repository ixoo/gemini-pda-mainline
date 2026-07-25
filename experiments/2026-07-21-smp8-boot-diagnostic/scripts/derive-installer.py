#!/usr/bin/env python3
"""Derive Candidate AD's guarded boot2 installer from exact Candidate AC."""

from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import re
import stat
import sys


BOOT2_SIZE = 16 * 1024 * 1024
AC_INNER_SHA256 = "b1a71fc2bb6d2e3b374b16dcfdeec4ec334acf7596556c7d9631930997664dd7"
AC_RAW_SHA256 = "3491c119d19b7b0af2ac2342659648227182ead0e32bb4c39a66fa22cadfb39d"
AC_RAW_SIZE = 7_378_944
AC_PADDED_SHA256 = "318f418a5e67042ecdd1c98a8767c104c8cfc68c3d56cd7c0d13cb3c5fad8a84"
AB_PADDED_SHA256 = "b58c0347d34a3fd9031c74cb03447dd7a6fc630d5b8ea2b7eabc36827e754350"
HEX256 = re.compile(r"^[0-9a-f]{64}$")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError(f"installer foundation token count changed: {old!r}")
    return text.replace(old, new)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--raw-sha256", required=True)
    parser.add_argument("--raw-size", required=True)
    parser.add_argument("--padded-sha256", required=True)
    args = parser.parse_args()
    try:
        source_info = args.source.lstat()
        if args.source.is_symlink() or not stat.S_ISREG(source_info.st_mode):
            raise ValueError("Candidate AC installer foundation is unsafe")
        if args.output.exists() or args.output.is_symlink():
            raise ValueError("refusing to overwrite derived Candidate AD installer")
        if not args.output.parent.is_dir() or args.output.parent.is_symlink():
            raise ValueError("Candidate AD installer output parent is unsafe")
        if HEX256.fullmatch(args.raw_sha256) is None or HEX256.fullmatch(args.padded_sha256) is None:
            raise ValueError("Candidate AD hashes are malformed")
        if not args.raw_size.isdecimal() or not 0 < int(args.raw_size) <= BOOT2_SIZE:
            raise ValueError("Candidate AD size is invalid or oversized")
        if args.raw_sha256 == AC_RAW_SHA256 or args.padded_sha256 == AC_PADDED_SHA256:
            raise ValueError("Candidate AD identity equals installed Candidate AC")

        source_data = args.source.read_bytes()
        if digest(source_data) != AC_INNER_SHA256:
            raise ValueError("exact Candidate AC installer foundation changed")
        text = source_data.decode("utf-8")
        replacements = (
            ("candidate-AC-usb-gadget-ethernet", "candidate-AD-smp8"),
            ("gemini-usb-gadget-ethernet", "gemini-smp8"),
            ("2026-07-21-usb-gadget-ethernet", "2026-07-21-smp8-boot-diagnostic"),
            ("Candidate AC", "Candidate AD"),
            ("candidate-ac", "candidate-ad"),
            ("AC_RAW", "AD_RAW"),
            ("AC_PADDED", "AD_PADDED"),
            ("EXPECTED_CURRENT_AB_PADDED_SHA256", "EXPECTED_CURRENT_AC_PADDED_SHA256"),
            ("candidate_label=AC", "candidate_label=AD"),
            ("AB-hardware-passed", "AC-hardware-passed"),
        )
        for old, new in replacements:
            if old not in text:
                raise ValueError(f"installer foundation lacks transform token: {old!r}")
            text = text.replace(old, new)

        old_power_gate = """power_sample() {
\tfor path in \\
\t\t/sys/class/power_supply/ac/online \\
\t\t/sys/class/power_supply/battery/present \\
\t\t/sys/class/power_supply/battery/status \\
\t\t/sys/class/power_supply/battery/capacity \\
\t\t/sys/class/power_supply/battery/health; do
\t\t[[ -r "$path" ]] || fail "power attribute unavailable: $path"
\tdone
\tprintf '%s|%s|%s|%s|%s' \\
\t\t"$(cat /sys/class/power_supply/ac/online)" \\
\t\t"$(cat /sys/class/power_supply/battery/present)" \\
\t\t"$(cat /sys/class/power_supply/battery/status)" \\
\t\t"$(cat /sys/class/power_supply/battery/capacity)" \\
\t\t"$(cat /sys/class/power_supply/battery/health)"
}

check_power_and_boot_id() {
\tlocal power_first
\tpower_first="$(power_sample)"
\tsleep 2
\tpower_second="$(power_sample)"
\t[[ "$power_first" == '1|1|Full|100|Good' && "$power_second" == "$power_first" ]] || \\
\t\tfail "power is not stable and exact: first=$power_first second=$power_second"
\t[[ "$(cat /proc/sys/kernel/random/boot_id)" == "$EXPECTED_BOOT_ID" ]] || \\
\t\tfail 'boot ID changed during the power check'
}
"""
        new_power_gate = """power_sample() {
\tfor path in \\
\t\t/sys/class/power_supply/ac/online \\
\t\t/sys/class/power_supply/usb/online \\
\t\t/sys/class/power_supply/battery/present \\
\t\t/sys/class/power_supply/battery/status \\
\t\t/sys/class/power_supply/battery/capacity \\
\t\t/sys/class/power_supply/battery/health; do
\t\t[[ -r "$path" ]] || fail "power attribute unavailable: $path"
\tdone
\tprintf '%s|%s|%s|%s|%s|%s' \\
\t\t"$(cat /sys/class/power_supply/ac/online)" \\
\t\t"$(cat /sys/class/power_supply/usb/online)" \\
\t\t"$(cat /sys/class/power_supply/battery/present)" \\
\t\t"$(cat /sys/class/power_supply/battery/status)" \\
\t\t"$(cat /sys/class/power_supply/battery/capacity)" \\
\t\t"$(cat /sys/class/power_supply/battery/health)"
}

check_power_and_boot_id() {
\tlocal ac_online battery_capacity battery_health battery_present battery_status
\tlocal power_first usb_online
\tpower_first="$(power_sample)"
\tsleep 2
\tpower_second="$(power_sample)"
\t[[ "$power_second" == "$power_first" ]] || \\
\t\tfail "power changed during stability sample: first=$power_first second=$power_second"
\tIFS='|' read -r ac_online usb_online battery_present battery_status \\
\t\tbattery_capacity battery_health <<<"$power_first"
\t[[ "$ac_online" =~ ^[01]$ && "$usb_online" =~ ^[01]$ ]] || \\
\t\tfail "external power state is malformed: $power_first"
\t[[ "$ac_online" == 1 || "$usb_online" == 1 ]] || \\
\t\tfail "neither AC nor USB external power is online: $power_first"
\t[[ "$battery_present" == 1 && "$battery_status" == Full && \\
\t\t"$battery_capacity" == 100 && "$battery_health" == Good ]] || \\
\t\tfail "battery is not present, full, and healthy: $power_first"
\t[[ "$(cat /proc/sys/kernel/random/boot_id)" == "$EXPECTED_BOOT_ID" ]] || \\
\t\tfail 'boot ID changed during the power check'
}
"""
        text = replace_once(text, old_power_gate, new_power_gate)

        text = replace_once(
            text,
            f"readonly AD_RAW_SHA256={AC_RAW_SHA256}",
            f"readonly AD_RAW_SHA256={args.raw_sha256}",
        )
        text = replace_once(
            text,
            f"readonly AD_RAW_SIZE={AC_RAW_SIZE}",
            f"readonly AD_RAW_SIZE={args.raw_size}",
        )
        text = replace_once(
            text,
            f"readonly AD_PADDED_SHA256={AC_PADDED_SHA256}",
            f"readonly AD_PADDED_SHA256={args.padded_sha256}",
        )
        text = replace_once(
            text,
            f"readonly EXPECTED_CURRENT_AC_PADDED_SHA256={AB_PADDED_SHA256}",
            f"readonly EXPECTED_CURRENT_AC_PADDED_SHA256={AC_PADDED_SHA256}",
        )
        text = replace_once(
            text,
            "already_current=\"$(result_field already_current \"$probe_output\")\" || die 'probe omitted skip state'",
            "already_current=\"$(result_field already_current \"$probe_output\")\" || die 'probe omitted skip state'\n"
            "initial_power=\"$(result_field power \"$probe_output\")\" || die 'probe omitted power state'",
        )
        text = replace_once(
            text,
            "printf 'boot_id=%s\\npower=1|1|Full|100|Good\\n' \"$initial_boot_id\"",
            "printf 'boot_id=%s\\npower=%s\\n' \"$initial_boot_id\" \"$initial_power\"",
        )

        sole_write = 'dd if="$root_stage_file" of="$target" bs=4M iflag=fullblock count=4'
        if text.count(sole_write) != 1:
            raise ValueError("derived installer lost its sole bounded target write")
        required = (
            "gemini-smp8.boot.img",
            "candidate-AD-smp8-final-${AD_RAW_SHA256:0:8}",
            "candidate-ad-padded-boot2.img",
            ".gemini-candidate-ad.",
            ".gemini-candidate-ad-root.",
            "boot2-before-candidate-ad.img",
            "boot2-after-candidate-ad.img",
            "expected_previous_label=AC-hardware-passed",
            "candidate_label=AD",
            f"readonly EXPECTED_CURRENT_AC_PADDED_SHA256={AC_PADDED_SHA256}",
            "/sys/class/power_supply/usb/online",
            "neither AC nor USB external power is online",
            "initial_power=\"$(result_field power \"$probe_output\")\"",
            "reboot_or_shutdown_performed=no",
        )
        if any(token not in text for token in required):
            raise ValueError("derived installer lost Candidate AD safety identity")
        forbidden = (
            "Candidate AC",
            "candidate-ac",
            "readonly AC_RAW",
            "readonly AC_PADDED",
            "EXPECTED_CURRENT_AB_PADDED_SHA256",
            "gemini-usb-gadget-ethernet.boot.img",
            "candidate_label=AC",
            "expected_previous_label=AB-hardware-passed",
            "power=1|1|Full|100|Good",
        )
        if any(token in text for token in forbidden):
            raise ValueError("derived installer retained Candidate AC target identity")
        if "sysrq-trigger" in text or re.search(
            r"(?m)^[ \t]*(?:sudo[ \t]+)?(?:reboot|shutdown|poweroff|halt|kexec)(?:[ \t]|$)",
            text,
        ):
            raise ValueError("derived installer gained a reboot action")

        descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o700)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            os.fchmod(stream.fileno(), 0o700)
            stream.write(text)
        print("validation=candidate-ad-installer-derivation")
        print(f"installer_sha256={digest(text.encode())}")
        print(f"candidate_raw_sha256={args.raw_sha256}")
        print(f"candidate_raw_size={args.raw_size}")
        print(f"candidate_padded_sha256={args.padded_sha256}")
        print(f"expected_predecessor_sha256={AC_PADDED_SHA256}")
        print("sole_target_write=one-bounded-16MiB-write")
        print("reboot_or_slot_selection=none")
        return 0
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
