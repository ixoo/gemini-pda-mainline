#!/usr/bin/env python3
"""Validate AB as an exact AA r1 keymap/gate plus kernel-reboot wrapper."""

from __future__ import annotations

import argparse
import gzip
import pathlib
import re
import stat
import struct
import sys
import zlib
from dataclasses import dataclass, replace

from ab_contract import (
    AA_INITRAMFS_SHA256,
    AA_KEYMAP_SHA256,
    AA_KEYMAP_VERIFIER_SHA256,
    AA_UNICODE_HELPER_SHA256,
    BUSYBOX_SHA256,
    DISPATCH_ENV_SHA256,
    MARKER,
    digest_bytes,
    read_regular,
)


CHANGED_MEMBERS = frozenset({"init", "bin/local-shell", "bin/reboot", "bin/x-record"})
SOURCE_NAMES = {
    "init": "init",
    "bin/local-shell": "local-shell",
    "bin/reboot": "reboot",
    "bin/x-record": "x-record",
}
AA_REBOOT_SHA256 = "29ccd527fdf5fb6bb36fd09d41f76080df48ba608a239eb04c70de896b3349a2"
DISPATCH_BYTES = b"alias reboot='/bin/reboot'\n"
AB_REBOOT_BYTES = (
    b"#!/bin/busybox sh\n"
    b"# shellcheck shell=dash\n"
    b"\n"
    b"export PATH=/bin\n"
    b"/bin/x-record 'candidate=AB manual_reboot=requested trigger=bare-reboot "
    b"dispatch=absolute-wrapper method=busybox-reboot-no-sync-force "
    b"storage_access=none watchdog_userspace=none'\n"
    b"printf '%s\\n' 'Candidate AB: kernel restart requested now "
    b"(BusyBox reboot -n -f).'\n"
    b"\n"
    b"# Do not sync or inspect any filesystem: this is an explicit forced reboot\n"
    b"# request against the pinned BusyBox applet and ordinary reboot(2) path.\n"
    b"/bin/busybox reboot -n -f\n"
    b"status=$?\n"
    b"/bin/x-record \"candidate=AB manual_reboot=failed status=$status\"\n"
    b"printf 'Candidate AB: reboot failed (status %s).\\n' \"$status\" >&2\n"
    b"exit \"$status\"\n"
)

INIT_REPLACEMENTS = (
    (
        "readonly MARKER='GEMINI_KEYBOARD_CONSOLE_MAP_20260720_AA_R1'",
        f"readonly MARKER='{MARKER}'",
    ),
    (
        "/bin/x-record 'entry profile=keyboard-console-map cpu_policy=maxcpus-1'",
        "/bin/x-record 'entry profile=mt6797-kernel-restart cpu_policy=maxcpus-1'",
    ),
    (
        "# Retain Candidate Z's independent observation worker and typed-only watchdog\n"
        "# recovery.  The console map is loaded synchronously by the tty1 supervisor;\n"
        "# no automatic path opens watchdog0 or requests a reset.",
        "# Retain Candidate AA r1's independent observation worker. Candidate AB starts\n"
        "# no automatic reset worker and no userspace watchdog owner; only an\n"
        "# owner-typed bare reboot reaches the audited /bin/reboot wrapper.",
    ),
    (
        "/bin/x-record 'services=launched probe=independent tty1_shell=supervised "
        "clean_tty1_background=yes reboot_dispatch=env-alias watchdog_userspace=typed-only "
        "keyboard_map=tty1-synchronous'",
        "/bin/x-record 'services=launched probe=independent tty1_shell=supervised "
        "clean_tty1_background=yes reboot_dispatch=env-alias watchdog_userspace=none "
        "keyboard_map=tty1-synchronous manual_reboot=busybox-no-sync-force'",
    ),
)

SHELL_REPLACEMENTS = (
    (
        "Candidate AA: reboot dispatch self-check failed; shell withheld; STATIC HOLD.",
        "Candidate AB: reboot dispatch self-check failed; shell withheld; STATIC HOLD.",
    ),
    (
        "export PS1='GEMINI-AA-R1-KEYMAP-FAIL# '",
        "export PS1='GEMINI-AB-KEYMAP-FAIL# '",
    ),
    ("export PS1='GEMINI-AA-R1# '", "export PS1='GEMINI-AB# '"),
    (
        "Candidate AA: Gemini console map failed its load/readback gate.",
        "Candidate AB: Gemini console map failed its load/readback gate.",
    ),
    (
        "Recovery shell only; type reboot to use Candidate Z watchdog recovery.",
        "Recovery shell only; type reboot to request the kernel restart path.",
    ),
    ("prompt=GEMINI-AA-R1#", "prompt=GEMINI-AB#"),
    ("GEMINI_KEYBOARD_CONSOLE_MAP_20260720_AA_R1", MARKER),
    (
        "Type reboot to use the proven 31-second watchdog recovery.",
        "After at least 45 seconds idle, type reboot to test the kernel restart path.",
    ),
)

RECORDER_REPLACEMENTS = (
    (
        "readonly MARKER='GEMINI_KEYBOARD_CONSOLE_MAP_20260720_AA_R1'",
        f"readonly MARKER='{MARKER}'",
    ),
)


@dataclass(frozen=True)
class Member:
    mode: int
    uid: int
    gid: int
    nlink: int
    mtime: int
    devmajor: int
    devminor: int
    rdevmajor: int
    rdevminor: int
    data: bytes


AB_REBOOT_MEMBER = Member(
    mode=stat.S_IFREG | 0o755,
    uid=0,
    gid=0,
    nlink=1,
    mtime=0,
    devmajor=0,
    devminor=0,
    rdevmajor=0,
    rdevminor=0,
    data=AB_REBOOT_BYTES,
)


def align4(value: int) -> int:
    return (value + 3) & ~3


def parse_newc(compressed: bytes) -> dict[str, Member]:
    if len(compressed) < 10 or compressed[:10] != b"\x1f\x8b\x08\0\0\0\0\0\x02\x03":
        raise ValueError("archive is not a canonical gzip -n -9 stream")
    raw = gzip.decompress(compressed)
    offset = 0
    previous = ""
    members: dict[str, Member] = {}
    while True:
        if offset + 110 > len(raw):
            raise ValueError("truncated newc header")
        header = raw[offset : offset + 110]
        if header[:6] != b"070701":
            raise ValueError("archive is not crc-free newc")
        try:
            fields = [int(header[6 + index * 8 : 14 + index * 8], 16) for index in range(13)]
        except ValueError as exc:
            raise ValueError("invalid newc numeric field") from exc
        (
            _ino,
            mode,
            uid,
            gid,
            nlink,
            mtime,
            size,
            devmajor,
            devminor,
            rdevmajor,
            rdevminor,
            namesize,
            check,
        ) = fields
        if check or namesize < 2:
            raise ValueError("invalid newc checksum or name size")
        name_start = offset + 110
        name_end = name_start + namesize
        if name_end > len(raw) or raw[name_end - 1] != 0:
            raise ValueError("truncated or unterminated newc name")
        stored_name = raw[name_start : name_end - 1].decode("utf-8")
        data_start = align4(name_end)
        data_end = data_start + size
        if data_end > len(raw):
            raise ValueError("truncated newc data")
        if stored_name == "TRAILER!!!":
            if size or any(raw[align4(data_end) :]):
                raise ValueError("invalid newc trailer or trailing bytes")
            break
        name = stored_name.removeprefix("./") or "."
        parts = pathlib.PurePosixPath(name).parts
        if stored_name.startswith("/") or ".." in parts or name in members:
            raise ValueError("unsafe or duplicate newc member")
        if previous and name < previous:
            raise ValueError("newc members are not canonically sorted")
        previous = name
        members[name] = Member(
            mode,
            uid,
            gid,
            nlink,
            mtime,
            devmajor,
            devminor,
            rdevmajor,
            rdevminor,
            raw[data_start:data_end],
        )
        offset = align4(data_end)
    return members


def replace_exact(text: str, replacements: tuple[tuple[str, str], ...], label: str) -> str:
    for old, new in replacements:
        if text.count(old) != 1:
            raise ValueError(f"AA {label} transformation token count changed: {old!r}")
        text = text.replace(old, new)
    return text


def expected_script(member: Member, replacements: tuple[tuple[str, str], ...], label: str) -> Member:
    try:
        text = member.data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"AA {label} is not UTF-8") from exc
    return replace(member, data=replace_exact(text, replacements, label).encode("utf-8"))


def text_member(members: dict[str, Member], name: str) -> str:
    try:
        return members[name].data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"non-UTF-8 script: {name}") from exc


def require_once(text: str, token: str, label: str) -> None:
    if text.count(token) != 1:
        raise ValueError(f"required {label} is absent or duplicated")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=pathlib.Path, required=True)
    parser.add_argument("--candidate", type=pathlib.Path, required=True)
    parser.add_argument("--source-dir", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        baseline_data = read_regular(args.baseline, "AA initramfs")
        candidate_data = read_regular(args.candidate, "AB initramfs")
        if digest_bytes(baseline_data) != AA_INITRAMFS_SHA256:
            raise ValueError("baseline is not exact hardware-passed AA r1 initramfs")
        baseline = parse_newc(baseline_data)
        candidate = parse_newc(candidate_data)
        if set(candidate) != set(baseline):
            raise ValueError("AB archive inventory differs from exact AA r1")
        changed = {name for name in baseline if candidate[name] != baseline[name]}
        if changed != CHANGED_MEMBERS:
            raise ValueError(f"AB changed unexpected AA members: {sorted(changed)}")
        for name in set(baseline) - CHANGED_MEMBERS:
            if candidate[name] != baseline[name]:
                raise ValueError(f"inherited AA member changed: {name}")

        expected = {
            "init": expected_script(baseline["init"], INIT_REPLACEMENTS, "init"),
            "bin/local-shell": expected_script(
                baseline["bin/local-shell"], SHELL_REPLACEMENTS, "local-shell"
            ),
            "bin/reboot": AB_REBOOT_MEMBER,
            "bin/x-record": expected_script(
                baseline["bin/x-record"], RECORDER_REPLACEMENTS, "x-record"
            ),
        }
        for member_name, source_name in SOURCE_NAMES.items():
            source = read_regular(args.source_dir / source_name, f"AB source {source_name}")
            if candidate[member_name].data != source:
                raise ValueError(f"embedded AB member differs from source: {source_name}")
            if not stat.S_ISREG(candidate[member_name].mode) or stat.S_IMODE(
                candidate[member_name].mode
            ) != 0o755:
                raise ValueError(f"AB overlay type/mode changed: {member_name}")
            if (
                candidate[member_name].uid
                or candidate[member_name].gid
                or candidate[member_name].mtime
                or candidate[member_name].nlink != 1
            ):
                raise ValueError(f"AB overlay metadata changed: {member_name}")
        for name, transformed in expected.items():
            if candidate[name] != transformed:
                raise ValueError(f"AB {name} differs beyond the audited AA attribution transform")
        if digest_bytes(baseline["bin/reboot"].data) != AA_REBOOT_SHA256:
            raise ValueError("AA typed-watchdog reboot foundation changed")

        exact_preserved = (
            ("bin/busybox", BUSYBOX_SHA256),
            ("bin/console-unicode-mode", AA_UNICODE_HELPER_SHA256),
            ("bin/console-keymap-verify", AA_KEYMAP_VERIFIER_SHA256),
            ("etc/gemini-us.bkeymap", AA_KEYMAP_SHA256),
            ("bin/reboot-dispatch.env", DISPATCH_ENV_SHA256),
        )
        for name, checksum in exact_preserved:
            if digest_bytes(candidate[name].data) != checksum:
                raise ValueError(f"exact AA runtime member changed: {name}")
        if candidate["bin/reboot-dispatch.env"].data != DISPATCH_BYTES:
            raise ValueError("absolute reboot dispatch alias changed")
        if text_member(candidate, "etc/inittab") != (
            "tty1::respawn:/bin/local-shell\n::ctrlaltdel:/bin/busybox true\n"
        ):
            raise ValueError("inert ctrl-alt-delete/tty1 supervision changed")

        init = text_member(candidate, "init")
        shell = text_member(candidate, "bin/local-shell")
        reboot = text_member(candidate, "bin/reboot")
        recorder = text_member(candidate, "bin/x-record")
        probe = text_member(candidate, "bin/x-probe")
        inittab = text_member(candidate, "etc/inittab")

        # The exact transformed shell proves the complete AA Unicode, preflight,
        # load, 2,048-entry KDGKBENT readback, respawn, and dispatch gate is
        # unchanged.  Keep explicit checks for the security-critical endpoints.
        for token, count in (
            ('/bin/console-keymap-verify --verify "$KEYMAP"', 2),
            ('/bin/console-keymap-verify --preflight "$KEYMAP"', 1),
            ('/bin/busybox loadkmap <"$KEYMAP"', 1),
            ("readback=all-2048-kernel-entries-exact-high-halves-hole-and-all-others-absent", 1),
            ("first_entry=preflight-then-load-or-existing-exact-map", 1),
            ("exec /bin/busybox ash -i", 2),
            ("export PS1='GEMINI-AB# '", 1),
            (f"printf '%s\\n' '{MARKER}'", 1),
        ):
            if shell.count(token) != count:
                raise ValueError(f"AA keymap/dispatch gate count changed: {token}")

        require_once(
            reboot,
            "/bin/x-record 'candidate=AB manual_reboot=requested trigger=bare-reboot "
            "dispatch=absolute-wrapper method=busybox-reboot-no-sync-force "
            "storage_access=none watchdog_userspace=none'",
            "pre-syscall AB attribution",
        )
        require_once(reboot, "/bin/busybox reboot -n -f", "forced BusyBox reboot")
        attribution = reboot.index("candidate=AB manual_reboot=requested")
        invocation = reboot.index("/bin/busybox reboot -n -f")
        if attribution >= invocation:
            raise ValueError("AB attribution does not precede the reboot request")
        if re.search(
            r"(?m)^[ \t]*(?:exec[ \t]+)?(?:/bin/)?(?:busybox[ \t]+)?sync(?:[ \t]|$)",
            reboot,
        ):
            raise ValueError("AB reboot wrapper gained a sync command")

        all_control = "\n".join((init, shell, reboot, recorder, probe, inittab))
        forbidden_watchdog = (
            "/dev/watchdog",
            "/sys/class/watchdog",
            "10007000.watchdog",
            "watchdog@10007000",
            "WATCHDOG_TIMEOUT",
            "handoff_ping",
            "further_pings",
            "watchdog0=opening",
            "reset expected in",
            "countdown",
            "fd3=retained",
        )
        for token in forbidden_watchdog:
            if token in all_control:
                raise ValueError(f"AB retained a userspace watchdog path: {token}")
        for token in (
            "/dev/mmc",
            "/dev/block",
            "/sys/block",
            "/proc/partitions",
            "/bin/dd",
            "/bin/mountpoint",
            "/bin/swapon",
            "/bin/fsck",
            "/bin/mkfs",
            "sysrq-trigger",
            "/bin/poweroff",
            "/bin/halt",
            "/bin/kexec",
            "/bin/busybox poweroff",
            "/bin/busybox halt",
            "/bin/busybox kexec",
        ):
            if token in all_control:
                raise ValueError(f"AB gained a storage/reset side path: {token}")

        automatic = "\n".join((init, shell, recorder, probe, inittab))
        if re.search(
            r"(?m)^[ \t]*(?:exec[ \t]+)?(?:/bin/reboot|"
            r"/bin/busybox[ \t]+reboot|reboot)(?:[ \t]|$)",
            automatic,
        ):
            raise ValueError("an automatic AB path gained a reboot invocation")
        if automatic.count("/bin/x-probe &") != 1:
            raise ValueError("independent probe start changed")
        background = "\n".join((init, recorder, probe, inittab))
        for token in ("/dev/tty0", "/dev/tty1", "/dev/tty2", "/dev/console"):
            if token in background:
                raise ValueError(f"AB background path gained visible-console sink: {token}")
        require_once(recorder, "output=/dev/ttyS0", "serial-only recorder")

        print("validation=candidate-ab-initramfs")
        print(f"candidate_initramfs_sha256={digest_bytes(candidate_data)}")
        print(f"baseline_initramfs_sha256={AA_INITRAMFS_SHA256}")
        print("changed_members=init,bin/local-shell,bin/reboot,bin/x-record")
        print("keymap_and_gate=exact-aa-r1-with-attribution-only-shell-transform")
        print(f"keymap_sha256={AA_KEYMAP_SHA256}")
        print(f"keymap_verifier_sha256={AA_KEYMAP_VERIFIER_SHA256}")
        print("reboot_dispatch=ENV-alias-absolute-wrapper")
        print("manual_reboot=busybox-reboot-no-sync-force")
        print("watchdog_userspace=start-none,open-none,ping-none,countdown-none,fallback-none")
        print("automatic_reboot=none")
        print("storage_access=none")
        print("runtime_networking=none")
        print("hardware_write=none")
        return 0
    except (
        OSError,
        UnicodeError,
        ValueError,
        gzip.BadGzipFile,
        struct.error,
        zlib.error,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
