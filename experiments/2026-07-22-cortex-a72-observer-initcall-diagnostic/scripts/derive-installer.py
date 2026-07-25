#!/usr/bin/env python3
"""Derive Candidate AF's guarded boot2 installer from exact Candidate AE."""

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
AE_INSTALLER_SHA256 = (
    "df0a57334d8fb15251ee49d6a6fac029488714fe9823f9e8c569182ef57e8df7"
)
AE_RAW_SHA256 = "d9895f619ea9b4bd8fcd5ba8e8bb546d50afd65bccc1a4209d950f56408c1e0d"
AE_RAW_SIZE = "7385088"
AE_PADDED_SHA256 = (
    "0e7cc17ce214f3904bae7172c81e50327ffda19fa46601c76bac36232b1079a9"
)
AD_PADDED_SHA256 = (
    "371fda65cf9c21406d6b08e52ffb46690426a7d356ba67aa9ffe1410e7d1e495"
)

# These are the only production calibration edits permitted after two final
# Candidate AF artifact trees reproduce byte-for-byte. The executable exposes
# no hash, size, predecessor, partition, credential, or power-policy override.
# Tests inject a fixture Calibration only into the imported pure transform.
AF_RAW_SHA256 = "fe43efa8c9d18174fec97ab7ad6cbe59bbc490df92366bcd254c55daa932d0a3"
AF_RAW_SIZE = "7385088"
AF_PADDED_SHA256 = "832965fbf6c9c056d7bcace238e3895dd206fa7e21e0d3bb2636466a6d073588"

HEX256 = re.compile(r"^[0-9a-f]{64}$")

# These patterns inspect logical shell lines, after backslash continuations
# have been joined. They intentionally cover absolute applet paths,
# BusyBox/Toybox multicall forms, and common service-manager reset requests.
_ABSOLUTE_DIR = r"(?:/[A-Za-z0-9._+:-]+)+/"
_COMMAND_EDGE = r"(?:^|[;&|][ \t]*)"
_CONTROL_PREFIX = r"(?:(?:if|elif|while|until|then|do|else)[ \t]+|![ \t]+)?"
_PRIVILEGE_PREFIX = (
    r"(?:(?:sudo|doas)(?:[ \t]+-[^ \t;&|]+)*[ \t]+)?"
    r"(?:(?:command|exec)[ \t]+)?"
)
_APPLET_PREFIX = (
    rf"(?:(?:{_ABSOLUTE_DIR})?(?:busybox|toybox)[ \t]+)?"
    rf"(?:{_ABSOLUTE_DIR})?"
)
_EXECUTABLE_PREFIX = _COMMAND_EDGE + _CONTROL_PREFIX + _PRIVILEGE_PREFIX
REBOOT_ACTIONS = (
    re.compile(
        _EXECUTABLE_PREFIX
        + _APPLET_PREFIX
        + r"(?:reboot|shutdown|poweroff|halt|kexec)(?=[ \t;&|()]|$)",
        re.MULTILINE,
    ),
    re.compile(
        _EXECUTABLE_PREFIX
        + rf"(?:{_ABSOLUTE_DIR})?(?:systemctl|loginctl)\b"
        + r"[^\n;&|]*\b(?:reboot|poweroff|halt|kexec)"
        + r"(?:\.target)?(?=[ \t;&|()]|$)",
        re.MULTILINE,
    ),
    re.compile(
        _EXECUTABLE_PREFIX
        + rf"(?:{_ABSOLUTE_DIR})?(?:init|telinit)[ \t]+(?:0|6)"
        + r"(?=[ \t;&|()]|$)",
        re.MULTILINE,
    ),
)

_TARGET_TOKEN = (
    r"(?:[\"']?\$target[\"']?|[\"']?\$\{target(?:[^}]*)\}[\"']?)"
)
DD_TARGET_WRITE = re.compile(
    _APPLET_PREFIX + r"dd\b[^\n]*\bof[ \t]*=[^\n]*" + _TARGET_TOKEN
)
OTHER_TARGET_WRITE = re.compile(
    _APPLET_PREFIX
    + r"(?:cp|install|mv|tee|sponge|truncate|fallocate|blkdiscard|flashcp|"
    + r"nandwrite|bmaptool|shred|wipefs|mkfs(?:\.[A-Za-z0-9._+-]+)?|mkswap|mount)\b"
    + r"[^\n]*"
    + _TARGET_TOKEN
)
TARGET_REDIRECTION = re.compile(r"(?:>>?|<>)[ \t]*" + _TARGET_TOKEN)
BLOCKDEV_TARGET = re.compile(r"\bblockdev\b[^\n]*" + _TARGET_TOKEN)


@dataclass(frozen=True)
class Calibration:
    raw_sha256: str
    raw_size: str
    padded_sha256: str


PRODUCTION_CALIBRATION = Calibration(
    AF_RAW_SHA256,
    AF_RAW_SIZE,
    AF_PADDED_SHA256,
)

# Each replacement is a candidate identity, evidence label, or checksum
# namespace change. Counts pin the exact validated AE installer's shape.
IDENTITY_REPLACEMENTS = (
    (
        "candidate-AE-a72-observer",
        "candidate-AF-a72-observer-initcall",
        1,
    ),
    (
        "gemini-a72-observer",
        "gemini-a72-observer-initcall-diagnostic",
        1,
    ),
    (
        "2026-07-21-cortex-a72-power-observer",
        "2026-07-22-cortex-a72-observer-initcall-diagnostic",
        2,
    ),
    ("Candidate AE", "Candidate AF", 7),
    ("candidate-ae", "candidate-af", 14),
    ("AE_RAW", "AF_RAW", 17),
    ("AE_PADDED", "AF_PADDED", 11),
    (
        "EXPECTED_CURRENT_AD_PADDED_SHA256",
        "EXPECTED_CURRENT_AE_PADDED_SHA256",
        8,
    ),
    ("candidate_label=AE", "candidate_label=AF", 2),
    (
        "AD-hardware-passed",
        "AE-installed-readback-verified",
        4,
    ),
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


def normalize_shell(text: str) -> str:
    """Join continuations and normalize insignificant horizontal whitespace."""

    joined = re.sub(r"\\\r?\n[ \t]*", " ", text)
    lines = []
    for line in joined.splitlines():
        lines.append(re.sub(r"[ \t]+", " ", line.strip()))
    return "\n".join(lines)


def contains_reboot_action(text: str) -> bool:
    normalized = normalize_shell(text)
    return any(pattern.search(normalized) for pattern in REBOOT_ACTIONS)


def require_semantic_fragment(
    normalized: str, label: str, fragment: str, expected: int = 1
) -> None:
    needle = normalize_shell(fragment).strip()
    actual = normalized.count(needle)
    if actual != expected:
        raise ValueError(
            f"derived installer executable guard changed: {label}: "
            f"expected {expected}, found {actual}"
        )


def validate_calibration(calibration: Calibration) -> None:
    values = (
        ("AF_RAW_SHA256", calibration.raw_sha256),
        ("AF_RAW_SIZE", calibration.raw_size),
        ("AF_PADDED_SHA256", calibration.padded_sha256),
    )
    for name, value in values:
        if value.startswith("TO_PIN_"):
            raise ValueError(f"Candidate AF calibration remains unpinned: {name}")
    if HEX256.fullmatch(calibration.raw_sha256) is None:
        raise ValueError("Candidate AF raw SHA-256 is malformed")
    if HEX256.fullmatch(calibration.padded_sha256) is None:
        raise ValueError("Candidate AF padded SHA-256 is malformed")
    if not calibration.raw_size.isdecimal():
        raise ValueError("Candidate AF raw size is malformed")
    raw_size = int(calibration.raw_size)
    if not 0 < raw_size <= BOOT2_SIZE:
        raise ValueError("Candidate AF raw size is invalid or exceeds boot2")
    if calibration.raw_sha256 == AE_RAW_SHA256:
        raise ValueError("Candidate AF raw identity equals Candidate AE")
    if calibration.padded_sha256 == AE_PADDED_SHA256:
        raise ValueError(
            "Candidate AF padded identity equals installed Candidate AE"
        )


def expected_transform(source_text: str, calibration: Calibration) -> str:
    validate_calibration(calibration)
    text = source_text
    for old, new, count in IDENTITY_REPLACEMENTS:
        text = replace_exact(text, old, new, count)

    pins = (
        (
            f"readonly AF_RAW_SHA256={AE_RAW_SHA256}",
            f"readonly AF_RAW_SHA256={calibration.raw_sha256}",
        ),
        (
            f"readonly AF_RAW_SIZE={AE_RAW_SIZE}",
            f"readonly AF_RAW_SIZE={calibration.raw_size}",
        ),
        (
            f"readonly AF_PADDED_SHA256={AE_PADDED_SHA256}",
            f"readonly AF_PADDED_SHA256={calibration.padded_sha256}",
        ),
        (
            f"readonly EXPECTED_CURRENT_AE_PADDED_SHA256={AD_PADDED_SHA256}",
            f"readonly EXPECTED_CURRENT_AE_PADDED_SHA256={AE_PADDED_SHA256}",
        ),
    )
    for old, new in pins:
        text = replace_exact(text, old, new, 1)
    return text


def validate_safety(text: str, calibration: Calibration) -> None:
    """Reject loss of an inherited AE storage or device safety invariant."""

    required_counts = {
        "readonly BOOT2_SIZE=16777216": 1,
        f"readonly AF_RAW_SHA256={calibration.raw_sha256}": 1,
        f"readonly AF_RAW_SIZE={calibration.raw_size}": 1,
        f"readonly AF_PADDED_SHA256={calibration.padded_sha256}": 1,
        f"readonly EXPECTED_CURRENT_AE_PADDED_SHA256={AE_PADDED_SHA256}": 1,
        "usage: install-candidate-af-boot2.sh": 1,
        "gemini-a72-observer-initcall-diagnostic.boot.img": 1,
        'candidate-AF-a72-observer-initcall-${AF_RAW_SHA256:0:8}': 1,
        "candidate-af-padded-boot2.img": 1,
        "expected_previous_label=AE-installed-readback-verified": 1,
        "candidate_label=AF": 2,
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
        "zero-padded Candidate AF checksum is not calibrated": 1,
        'chmod 0600 "$backup_partial"': 1,
        "boot2-before-candidate-af.img.sha256": 1,
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

    normalized = normalize_shell(text)
    semantic_fragments = (
        (
            "private-key mode gate",
            r'''[[ "$(file_mode "$identity")" == 600 ]] || die 'Gemini identity mode is not 0600' ''',
        ),
        (
            "zero-padded candidate construction",
            r'''padded="$backup_dir/candidate-af-padded-boot2.img"
cp "$candidate" "$padded"
if ((AF_RAW_SIZE < BOOT2_SIZE)); then
dd if=/dev/zero of="$padded" bs=1 count=1 seek=$((BOOT2_SIZE - 1)) conv=notrunc 2>/dev/null
fi
chmod 0600 "$padded"
[[ "$(file_size "$padded")" == "$BOOT2_SIZE" ]] || die 'padded candidate size mismatch'
head -c "$AF_RAW_SIZE" "$padded" | cmp -s "$candidate" - || die 'padded candidate prefix differs from raw candidate'
[[ "$(checked_sha256_file "$candidate")" == "$AF_RAW_SHA256" ]] || die 'raw candidate changed while its padded image was created'
tail_size=$((BOOT2_SIZE - AF_RAW_SIZE))
if ((tail_size > 0)); then
tail -c "$tail_size" "$padded" | od -An -v -tu1 | awk '{ for (field = 1; field <= NF; field++) if ($field != 0) exit 1 }' || die 'padded candidate tail is not all zero'
fi
padded_sha256="$(checked_sha256_file "$padded")"
[[ "$padded_sha256" == "$AF_PADDED_SHA256" ]] || die 'zero-padded Candidate AF checksum is not calibrated'
sync
[[ "$(checked_sha256_file "$padded")" == "$AF_PADDED_SHA256" ]] || die 'padded Candidate AF changed across initial sync' ''',
        ),
        (
            "live GPT boot2 resolver",
            r'''resolve_boot2() {
local rows row_count
rows="$(lsblk -brnpo NAME,PARTLABEL,TYPE,SIZE,RO,MOUNTPOINT | awk '$2 == "boot2" { print }')"
row_count="$(printf '%s\n' "$rows" | awk 'NF { count++ } END { print count + 0 }')"
[[ "$row_count" == 1 ]] || fail "live GPT has $row_count exact boot2 rows"
read -r target label type size ro mountpoint extra <<<"$rows"
[[ "$target" =~ ^/dev/mmcblk[0-9]+p[0-9]+$ ]] || fail "unsafe boot2 target: $target"
[[ "$label" == boot2 && "$type" == part && "$size" == "$EXPECTED_SIZE" && "$ro" == 0 ]] || fail "boot2 identity mismatch: label=$label type=$type size=$size ro=$ro"
[[ -z "${mountpoint:-}" && -z "${extra:-}" ]] || fail 'boot2 has a mountpoint'
[[ "$(readlink -f /dev/disk/by-partlabel/boot2)" == "$target" ]] || fail 'boot2 by-partlabel disagrees with the live GPT row'
[[ "$(lsblk -dnro PKNAME "$target")" == mmcblk0 ]] || fail 'boot2 parent is not mmcblk0'
[[ -b "$target" ]] || fail 'boot2 is not a block device'
[[ -r "$target" && -w "$target" ]] || fail 'boot2 is not root-readable and writable'
[[ "$(blockdev --getsize64 "$target")" == "$EXPECTED_SIZE" ]] || fail 'blockdev size mismatch'
[[ "$(blockdev --getro "$target")" == 0 ]] || fail 'blockdev reports read-only'
[[ "$(cat "/sys/class/block/${target##*/}/ro")" == 0 ]] || fail 'sysfs reports read-only'
partition_number="$(cat "/sys/class/block/${target##*/}/partition")"
[[ "$partition_number" =~ ^[0-9]+$ ]] || fail 'sysfs partition number is invalid'
}''',
        ),
        (
            "active-root exclusion",
            r'''check_active_root() {
active_root_source="$(findmnt -n -o SOURCE /)"
active_root="$(readlink -f "$active_root_source")"
[[ "$active_root" =~ ^/dev/mmcblk[0-9]+p[0-9]+$ && -b "$active_root" ]] || fail "active root is not one canonical MMC partition: $active_root"
[[ "$active_root" == "$EXPECTED_ROOT" ]] || fail "active root changed: expected=$EXPECTED_ROOT actual=$active_root"
[[ "$active_root" != "$target" ]] || fail 'boot2 is the active root'
}''',
        ),
        (
            "mount-swap-holder exclusion",
            r'''check_target_not_in_use() {
local holder_entries mount_matches swap_canonical swap_device swap_devices target_majmin
target_majmin="$(lsblk -dnro MAJ:MIN "$target")"
[[ "$target_majmin" =~ ^[0-9]+:[0-9]+$ ]] || fail 'boot2 major:minor identity is invalid'
if ! mount_matches="$(awk -v target_majmin="$target_majmin" '$3 == target_majmin { print }' /proc/self/mountinfo)"; then
fail 'boot2 mount enumeration failed'
fi
[[ -z "$mount_matches" ]] || fail 'boot2 is mounted'
if ! swap_devices="$(swapon --noheadings --raw --show=NAME)"; then
fail 'swap enumeration failed'
fi
while IFS= read -r swap_device; do
[[ -n "$swap_device" ]] || continue
if ! swap_canonical="$(readlink -f "$swap_device")"; then
fail "cannot canonicalize active swap device: $swap_device"
fi
[[ "$swap_canonical" != "$target" ]] || fail 'boot2 is active swap'
done <<<"$swap_devices"
if ! holder_entries="$(find "/sys/class/block/${target##*/}/holders" -mindepth 1 -maxdepth 1 -print -quit)"; then
fail 'boot2 holder enumeration failed'
fi
[[ -z "$holder_entries" ]] || fail 'boot2 has holders'
}''',
        ),
        (
            "power sampler",
            r'''power_sample() {
for path in /sys/class/power_supply/ac/online /sys/class/power_supply/usb/online /sys/class/power_supply/battery/present /sys/class/power_supply/battery/status /sys/class/power_supply/battery/capacity /sys/class/power_supply/battery/health; do
[[ -r "$path" ]] || fail "power attribute unavailable: $path"
done
printf '%s|%s|%s|%s|%s|%s' "$(cat /sys/class/power_supply/ac/online)" "$(cat /sys/class/power_supply/usb/online)" "$(cat /sys/class/power_supply/battery/present)" "$(cat /sys/class/power_supply/battery/status)" "$(cat /sys/class/power_supply/battery/capacity)" "$(cat /sys/class/power_supply/battery/health)"
}''',
        ),
        (
            "stable external power and boot ID",
            r'''check_power_and_boot_id() {
local ac_online battery_capacity battery_health battery_present battery_status
local power_first usb_online
power_first="$(power_sample)"
sleep 2
power_second="$(power_sample)"
[[ "$power_second" == "$power_first" ]] || fail "power changed during stability sample: first=$power_first second=$power_second"
IFS='|' read -r ac_online usb_online battery_present battery_status battery_capacity battery_health <<<"$power_first"
[[ "$ac_online" =~ ^[01]$ && "$usb_online" =~ ^[01]$ ]] || fail "external power state is malformed: $power_first"
[[ "$ac_online" == 1 || "$usb_online" == 1 ]] || fail "neither AC nor USB external power is online: $power_first"
[[ "$battery_present" == 1 && "$battery_status" == Full && "$battery_capacity" == 100 && "$battery_health" == Good ]] || fail "battery is not present, full, and healthy: $power_first"
[[ "$(cat /proc/sys/kernel/random/boot_id)" == "$EXPECTED_BOOT_ID" ]] || fail 'boot ID changed during the power check'
}''',
        ),
        (
            "remote predecessor environment",
            r'''"sudo -n -- env GATE_MODE=$mode EXPECTED_BOOT_ID=$initial_boot_id EXPECTED_TARGET=$expected_target EXPECTED_STAGE=$expected_stage EXPECTED_OWNER=$target_user EXPECTED_ROOT=$initial_root EXPECTED_SIZE=$BOOT2_SIZE EXPECTED_CURRENT_SHA256=$EXPECTED_CURRENT_AE_PADDED_SHA256 EXPECTED_CANDIDATE_SHA256=$AF_PADDED_SHA256 /bin/bash -s" <<'REMOTE_GATE' ''',
        ),
        (
            "initial live safety gate",
            r'''resolve_boot2
check_active_root
check_target_not_in_use
boot_id_before="$(cat /proc/sys/kernel/random/boot_id)"
[[ "$boot_id_before" == "$EXPECTED_BOOT_ID" ]] || fail "boot ID changed: $boot_id_before"
check_power_and_boot_id
target_sha256="$(sha256sum "$target" | awk '{ print $1 }')"''',
        ),
        (
            "already-matching remote probe branch",
            r'''probe)
case "$target_sha256" in
"$EXPECTED_CANDIDATE_SHA256") already_current=yes ;;
"$EXPECTED_CURRENT_SHA256") already_current=no ;;
*) fail "boot2 has unexpected full checksum: $target_sha256" ;;
esac
;;''',
        ),
        (
            "bounded write and prewrite gates",
            r'''write)
[[ "$EXPECTED_TARGET" != none && "$target" == "$EXPECTED_TARGET" ]] || fail "live boot2 target changed before write: $target"
[[ "$target_sha256" == "$EXPECTED_CURRENT_SHA256" ]] || fail "boot2 changed before write: $target_sha256"
validate_stage
create_root_stage
resolve_boot2
[[ "$target" == "$EXPECTED_TARGET" ]] || fail "live boot2 target changed after staging: $target"
check_active_root
check_power_and_boot_id
resolve_boot2
[[ "$target" == "$EXPECTED_TARGET" ]] || fail "live boot2 target changed at the final pre-write gate: $target"
check_active_root
check_target_not_in_use
[[ "$(cat /proc/sys/kernel/random/boot_id)" == "$EXPECTED_BOOT_ID" ]] || fail 'boot ID changed immediately before write'
prewrite_target_sha256="$(sha256sum "$target" | awk '{ print $1 }')"
[[ "$prewrite_target_sha256" == "$EXPECTED_CURRENT_SHA256" ]] || fail "boot2 changed at the final pre-write checksum: $prewrite_target_sha256"
dd if="$root_stage_file" of="$target" bs=4M iflag=fullblock count=4 conv=fsync,notrunc status=none
sync
blockdev --flushbufs "$target"
sync
target_sha256="$(sha256sum "$target" | awk '{ print $1 }')"
[[ "$target_sha256" == "$EXPECTED_CANDIDATE_SHA256" ]] || fail "post-flush checksum mismatch: $target_sha256"
[[ "$(cat /proc/sys/kernel/random/boot_id)" == "$EXPECTED_BOOT_ID" ]] || fail 'boot ID changed during write/flush'
cleanup_root_stage || fail 'exact root-owned staging cleanup failed after write'
root_stage_file=
root_stage_dir=
already_current=no
;;''',
        ),
        (
            "post-write live gate",
            r'''post)
[[ "$EXPECTED_TARGET" != none && "$target" == "$EXPECTED_TARGET" ]] || fail "live boot2 target changed after write: $target"
[[ "$target_sha256" == "$EXPECTED_CANDIDATE_SHA256" ]] || fail "post-write boot2 checksum mismatch: $target_sha256"
already_current=yes
;;''',
        ),
        (
            "already-matching host skip branch",
            r'''if [[ "$already_current" == yes ]]; then
{
printf 'experiment=2026-07-22-cortex-a72-observer-initcall-diagnostic\n'
printf 'candidate_label=AF\noperation=boot2-install\nresult=skipped-already-matching\n'
printf 'target=%s\nroot=%s\n' "$live_target" "$initial_root"
printf 'candidate_raw_sha256=%s\n' "$candidate_sha256"
printf 'candidate_padded_sha256=%s\n' "$padded_sha256"
printf 'target_sha256=%s\n' "$probe_sha256"
printf 'boot_id=%s\nreboot_or_shutdown_performed=no\nruntime_result=not-tested\n' "$initial_boot_id"
} >"$summary"
chmod 0600 "$summary"
{
manifest_line "$padded"
manifest_line "$summary"
} >"$manifest"
chmod 0600 "$manifest"
skip_manifest_sha256="$(checked_sha256_file "$manifest")"
sync
[[ "$(checked_sha256_file "$manifest")" == "$skip_manifest_sha256" ]] || die 'skipped-write evidence manifest changed across sync'
printf 'result=skipped-already-matching\n'
printf 'backup_dir=%s\nreboot=none\nruntime_result=not-tested\n' "$backup_dir"
exit 0
fi''',
        ),
        (
            "host predecessor decision",
            r'''[[ "$already_current" == no && "$probe_sha256" == "$EXPECTED_CURRENT_AE_PADDED_SHA256" ]] || die 'initial gate returned an inconsistent AE-installed-readback-verified predecessor checksum' ''',
        ),
        (
            "full predecessor backup checksum",
            r'''backup_sha256="$(checked_sha256_file "$backup_partial")"
[[ "$backup_sha256" == "$EXPECTED_CURRENT_AE_PADDED_SHA256" ]] || die "boot2 backup checksum mismatch; inspect $backup_partial"''',
        ),
        (
            "private full predecessor backup",
            r'''chmod 0600 "$backup_partial"
[[ "$(file_size "$backup_partial")" == "$BOOT2_SIZE" ]] || die "boot2 backup is short; inspect $backup_partial"
backup_sha256="$(checked_sha256_file "$backup_partial")"
[[ "$backup_sha256" == "$EXPECTED_CURRENT_AE_PADDED_SHA256" ]] || die "boot2 backup checksum mismatch; inspect $backup_partial"
mv "$backup_partial" "$backup"
backup_checksum_file="$backup_dir/boot2-before-candidate-af.img.sha256"
printf '%s  %s\n' "$backup_sha256" "$(basename -- "$backup")" >"$backup_checksum_file"
chmod 0600 "$backup_checksum_file"
sync
[[ "$(checked_sha256_file "$backup")" == "$backup_sha256" ]] || die 'durably flushed pre-write backup failed checksum revalidation'
[[ "$(cat "$backup_checksum_file")" == "$backup_sha256  $(basename -- "$backup")" ]] || die 'durably flushed pre-write backup checksum sidecar changed' ''',
        ),
        (
            "full local readback size",
            r'''[[ "$readback_stream_bytes" == "$BOOT2_SIZE" ]] || die "full boot2 readback stream length mismatch; inspect $readback_stats"
chmod 0600 "$readback_partial"
[[ "$(file_size "$readback_partial")" == "$BOOT2_SIZE" ]] || die "full boot2 readback is short; inspect $readback_partial"''',
        ),
        (
            "full local readback checksum and bytes",
            r'''readback_sha256="$(checked_sha256_file "$readback_partial")"
[[ "$readback_sha256" == "$AF_PADDED_SHA256" ]] || die "full boot2 readback checksum mismatch; inspect $readback_partial"
cmp -s "$padded" "$readback_partial" || die "full boot2 readback differs byte-for-byte; inspect $readback_partial"''',
        ),
        (
            "durable local readback",
            r'''sync
[[ "$(checked_sha256_file "$readback")" == "$readback_sha256" ]] || die 'durably flushed full local readback failed checksum revalidation'
[[ "$(cat "$readback_checksum_file")" == "$readback_sha256  $(basename -- "$readback")" ]] || die 'durably flushed readback checksum sidecar changed' ''',
        ),
        (
            "final target checksum",
            r'''post_sha256="$(result_field target_sha256 "$post_output")" || die 'post gate omitted checksum'
[[ "$post_sha256" == "$AF_PADDED_SHA256" ]] || die 'final target checksum mismatch' ''',
        ),
    )
    for label, fragment in semantic_fragments:
        require_semantic_fragment(normalized, label, fragment)

    expected_symbol_counts = {
        "resolve_boot2": 4,
        "check_active_root": 4,
        "check_target_not_in_use": 3,
        "power_sample": 3,
        "check_power_and_boot_id": 3,
    }
    for symbol, expected in expected_symbol_counts.items():
        actual = normalized.count(symbol)
        if actual != expected:
            raise ValueError(
                f"derived installer executable guard call count changed: {symbol}: "
                f"expected {expected}, found {actual}"
            )

    expected_target_write = (
        'dd if="$root_stage_file" of="$target" bs=4M iflag=fullblock count=4 '
        "conv=fsync,notrunc status=none"
    )
    logical_lines = normalized.splitlines()
    if logical_lines.count(expected_target_write) != 1:
        raise ValueError("derived installer lost its sole exact target write")
    target_dd_lines = [line for line in logical_lines if DD_TARGET_WRITE.search(line)]
    if target_dd_lines != [expected_target_write]:
        raise ValueError("derived installer gained an additional target dd write")
    if any(OTHER_TARGET_WRITE.search(line) for line in logical_lines):
        raise ValueError("derived installer gained another target-writing command")
    if any(TARGET_REDIRECTION.search(line) for line in logical_lines):
        raise ValueError("derived installer gained a shell redirection to boot2")

    expected_blockdev_lines = sorted(
        (
            '[[ "$(blockdev --getsize64 "$target")" == "$EXPECTED_SIZE" ]] || '
            "fail 'blockdev size mismatch'",
            '[[ "$(blockdev --getro "$target")" == 0 ]] || '
            "fail 'blockdev reports read-only'",
            'blockdev --flushbufs "$target"',
        )
    )
    blockdev_lines = sorted(
        line for line in logical_lines if BLOCKDEV_TARGET.search(line)
    )
    if blockdev_lines != expected_blockdev_lines:
        raise ValueError("derived installer block-device command surface changed")

    forbidden = (
        "Candidate AD",
        "candidate-ad",
        "Candidate AE",
        "candidate-ae",
        "gemini-a72-observer.boot.img",
        "candidate_label=AE",
        "expected_previous_label=AD-hardware-passed",
        "2026-07-21-cortex-a72-power-observer",
        "/dev/mmcblk0p30",
        "/dev/disk/by-partlabel/boot3",
        "sysrq-trigger",
        "sudo -S",
        "sshpass",
        "BEGIN OPENSSH PRIVATE KEY",
    )
    for token in forbidden:
        if token in text:
            raise ValueError(
                f"derived installer gained forbidden behavior: {token!r}"
            )
    if contains_reboot_action(text):
        raise ValueError("derived installer gained reboot or slot-selection behavior")


def validate_exact_delta(
    source_text: str, text: str, calibration: Calibration
) -> None:
    if text != expected_transform(source_text, calibration):
        raise ValueError("Candidate AF installer is not the exact narrow AE transform")


def derive_text(source_data: bytes, calibration: Calibration) -> str:
    if digest(source_data) != AE_INSTALLER_SHA256:
        raise ValueError("exact validated Candidate AE installer foundation changed")
    try:
        source_text = source_data.decode("utf-8")
    except UnicodeError as exc:
        raise ValueError("Candidate AE installer is not UTF-8") from exc
    text = expected_transform(source_text, calibration)
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
            f"Candidate AE installer lineage command failed ({result.returncode}): "
            f"{error}"
        )


def verify_lineage_output(path: pathlib.Path, expected_sha256: str) -> None:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode):
        raise ValueError("Candidate AE installer lineage emitted an unsafe file")
    if stat.S_IMODE(info.st_mode) != 0o700:
        raise ValueError("Candidate AE installer lineage mode changed")
    if digest_path(path) != expected_sha256:
        raise ValueError("Candidate AE installer lineage identity changed")


def reconstruct_ae_installer(
    repo_root: pathlib.Path, work: pathlib.Path
) -> pathlib.Path:
    """Reproduce the exact accepted AE installer from tracked lineage inputs."""

    ae_deriver = (
        repo_root
        / "experiments/2026-07-21-cortex-a72-power-observer/scripts/derive-installer.py"
    )
    ae = work / "install-candidate-ae-boot2.sh"
    run_lineage(
        [sys.executable, os.fspath(ae_deriver), "--output", os.fspath(ae)],
        repo_root,
    )
    verify_lineage_output(ae, AE_INSTALLER_SHA256)
    return ae


def read_exact_source(path: pathlib.Path) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode):
        raise ValueError("Candidate AE installer foundation is unsafe")
    data = path.read_bytes()
    if digest(data) != AE_INSTALLER_SHA256:
        raise ValueError("exact validated Candidate AE installer foundation changed")
    return data


def validate_output_path(path: pathlib.Path) -> pathlib.Path:
    if not path.name or path.name in {".", ".."}:
        raise ValueError("Candidate AF installer output name is invalid")
    if path.exists() or path.is_symlink():
        raise ValueError("refusing to overwrite Candidate AF installer")
    parent_info = path.parent.lstat()
    if path.parent.is_symlink() or not stat.S_ISDIR(parent_info.st_mode):
        raise ValueError("Candidate AF installer output parent is unsafe")
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
        help="exact validated AE installer; omit to reconstruct tracked lineage",
    )
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    previous_umask = os.umask(0o077)
    try:
        # Refuse before source inspection, lineage reconstruction, publication,
        # SSH, or any reachable installer/device behavior.
        validate_calibration(PRODUCTION_CALIBRATION)
        output = validate_output_path(args.output)
        script_dir = pathlib.Path(__file__).resolve().parent
        repo_root = script_dir.parents[2]
        if args.source is not None:
            source_data = read_exact_source(args.source)
        else:
            with tempfile.TemporaryDirectory(
                prefix=".candidate-af-ae-foundation.", dir=output.parent
            ) as raw_temp:
                source = reconstruct_ae_installer(
                    repo_root, pathlib.Path(raw_temp)
                )
                source_data = read_exact_source(source)
        text = derive_text(source_data, PRODUCTION_CALIBRATION)
        publish(output, text)
        print("validation=candidate-af-installer-derivation")
        print(f"installer_sha256={digest(text.encode('utf-8'))}")
        print(f"candidate_raw_sha256={AF_RAW_SHA256}")
        print(f"candidate_raw_size={AF_RAW_SIZE}")
        print(f"candidate_padded_sha256={AF_PADDED_SHA256}")
        print(f"expected_predecessor_sha256={AE_PADDED_SHA256}")
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
