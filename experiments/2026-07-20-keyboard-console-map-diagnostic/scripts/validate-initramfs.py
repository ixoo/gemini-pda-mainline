#!/usr/bin/env python3
"""Validate Candidate AA as an exact-Z console-map initramfs delta."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import pathlib
import re
import stat
import struct
import sys
import zlib
from dataclasses import dataclass


Z_INITRAMFS_SHA256 = "a21cc6bed9024bba9e01864aeb0c6c3339231d217f77ff5fa733ea33e6a0e7d2"
BUSYBOX_SHA256 = "52151e7f322f926b64049cdaa1410dc3ea6485525e0624b05813791c219ae933"
KEYMAP_SHA256 = "02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c"
UNICODE_SOURCE_SHA256 = "4a3f8064dddb5845886453bc0fdc5753e87b3f6ef8ce064c0c2a32fb7c7bf357"
UNICODE_HELPER_SHA256 = "5949ee28aedeb8f8ba7b5486abbec7714034f7b833265bace9a1438b8a1dd650"
VERIFIER_SOURCE_SHA256 = "70d70bcef6e403d850c32b85f4bab928b2eb1444fae68ec3f629d7ff7c22785d"
# CALIBRATION: replace from the pinned recovery VM after verifier source is final.
KEYMAP_VERIFIER_SHA256 = "29735d212e74d0b0040a3ead173a83223b89ce5d947b697a115707eb3d23b238"
MARKER = "GEMINI_KEYBOARD_CONSOLE_MAP_20260720_AA_R1"
CHANGED_MEMBERS = {"init", "bin/local-shell", "bin/x-record"}
ADDED_MEMBERS = {
    "bin/console-keymap-verify",
    "bin/console-unicode-mode",
    "etc/gemini-us.bkeymap",
}


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


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def align4(value: int) -> int:
    return (value + 3) & ~3


def parse_newc(compressed: bytes) -> dict[str, Member]:
    if len(compressed) < 10 or compressed[:3] != b"\x1f\x8b\x08" or compressed[4:8] != b"\0\0\0\0":
        raise ValueError("archive is not a deterministic gzip stream")
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
            fields = [
                int(header[6 + index * 8 : 14 + index * 8], 16)
                for index in range(13)
            ]
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


def read_regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode):
        raise ValueError(f"{label} is not a regular non-symlink file")
    return path.read_bytes()


def canonical(member: Member, mode: int, label: str) -> None:
    if not stat.S_ISREG(member.mode) or stat.S_IMODE(member.mode) != mode:
        raise ValueError(f"overlay type/mode changed: {label}")
    if (
        member.uid
        or member.gid
        or member.mtime
        or member.devmajor
        or member.devminor
        or member.rdevmajor
        or member.rdevminor
        or member.nlink != 1
    ):
        raise ValueError(f"overlay metadata changed: {label}")


def text_member(members: dict[str, Member], name: str) -> str:
    try:
        return members[name].data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"non-UTF-8 script: {name}") from exc


def require_once(text: str, token: str, label: str) -> None:
    if text.count(token) != 1:
        raise ValueError(f"required {label} is absent or duplicated")


def validate_helper(data: bytes, label: str) -> None:
    if len(data) < 64 or data[:4] != b"\x7fELF" or data[4:6] != b"\x02\x01":
        raise ValueError(f"{label} is not little-endian ELF64")
    if struct.unpack_from("<H", data, 18)[0] != 183:
        raise ValueError(f"{label} is not AArch64")
    program_offset = struct.unpack_from("<Q", data, 32)[0]
    program_size = struct.unpack_from("<H", data, 54)[0]
    program_count = struct.unpack_from("<H", data, 56)[0]
    for index in range(program_count):
        offset = program_offset + index * program_size
        if offset + 4 > len(data):
            raise ValueError(f"truncated {label} program table")
        if struct.unpack_from("<I", data, offset)[0] == 3:  # PT_INTERP
            raise ValueError(f"{label} is dynamically linked")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=pathlib.Path, required=True)
    parser.add_argument("--candidate", type=pathlib.Path, required=True)
    parser.add_argument("--source-dir", type=pathlib.Path, required=True)
    parser.add_argument("--keymap", type=pathlib.Path, required=True)
    parser.add_argument("--unicode-helper", type=pathlib.Path, required=True)
    parser.add_argument("--keymap-verifier", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        baseline_data = read_regular(args.baseline, "Candidate Z initramfs")
        candidate_data = read_regular(args.candidate, "Candidate AA initramfs")
        keymap = read_regular(args.keymap, "generated Gemini keymap")
        helper = read_regular(args.unicode_helper, "console mode helper")
        verifier = read_regular(args.keymap_verifier, "console keymap verifier")
        if digest(baseline_data) != Z_INITRAMFS_SHA256:
            raise ValueError("baseline is not exact Candidate Z initramfs")
        if digest(keymap) != KEYMAP_SHA256 or len(keymap) != 2311:
            raise ValueError("generated Gemini keymap identity mismatch")
        validate_helper(helper, "console mode helper")
        validate_helper(verifier, "console keymap verifier")
        if digest(helper) != UNICODE_HELPER_SHA256:
            raise ValueError("console mode helper identity mismatch")
        if digest(verifier) != KEYMAP_VERIFIER_SHA256:
            raise ValueError("console keymap verifier identity mismatch")
        experiment_dir = args.source_dir.parent
        unicode_source = read_regular(
            experiment_dir / "src/console-unicode-mode.c", "console mode helper source"
        )
        verifier_source = read_regular(
            experiment_dir / "src/console-keymap-verify.c", "console keymap verifier source"
        )
        if digest(unicode_source) != UNICODE_SOURCE_SHA256:
            raise ValueError("console mode helper source identity mismatch")
        if digest(verifier_source) != VERIFIER_SOURCE_SHA256:
            raise ValueError("console keymap verifier source identity mismatch")

        baseline = parse_newc(baseline_data)
        candidate = parse_newc(candidate_data)
        if set(candidate) != set(baseline) | ADDED_MEMBERS or ADDED_MEMBERS & set(baseline):
            raise ValueError("Candidate AA inventory is not exact Z plus three members")
        changed = {name for name in baseline if candidate[name] != baseline[name]}
        if changed != CHANGED_MEMBERS:
            raise ValueError(f"inherited member delta changed: {sorted(changed)}")
        for name in baseline:
            if name not in CHANGED_MEMBERS and candidate[name] != baseline[name]:
                raise ValueError(f"unapproved inherited member changed: {name}")

        source_names = {
            "init": "init",
            "bin/local-shell": "local-shell",
            "bin/x-record": "x-record",
        }
        for member_name, source_name in source_names.items():
            canonical(candidate[member_name], 0o755, member_name)
            source = read_regular(args.source_dir / source_name, source_name)
            if candidate[member_name].data != source:
                raise ValueError(f"embedded overlay differs from source: {source_name}")
        canonical(candidate["bin/console-unicode-mode"], 0o755, "console helper")
        canonical(candidate["bin/console-keymap-verify"], 0o755, "keymap verifier")
        canonical(candidate["etc/gemini-us.bkeymap"], 0o444, "Gemini keymap")
        if candidate["bin/console-unicode-mode"].data != helper:
            raise ValueError("embedded console helper differs from built helper")
        if candidate["bin/console-keymap-verify"].data != verifier:
            raise ValueError("embedded keymap verifier differs from built verifier")
        if candidate["etc/gemini-us.bkeymap"].data != keymap:
            raise ValueError("embedded keymap differs from validated keymap")
        if digest(candidate["bin/busybox"].data) != BUSYBOX_SHA256:
            raise ValueError("Candidate Z BusyBox changed")

        init = text_member(candidate, "init")
        shell = text_member(candidate, "bin/local-shell")
        recorder = text_member(candidate, "bin/x-record")
        require_once(init, f"readonly MARKER='{MARKER}'", "AA R1 init marker")
        require_once(recorder, f"readonly MARKER='{MARKER}'", "AA R1 recorder marker")
        require_once(shell, f"printf '%s\\n' '{MARKER}'", "visible AA R1 marker")
        require_once(shell, "export PS1='GEMINI-AA-R1# '", "AA R1 prompt")
        require_once(
            shell, "export PS1='GEMINI-AA-R1-KEYMAP-FAIL# '", "recovery prompt"
        )
        verify_token = '/bin/console-keymap-verify --verify "$KEYMAP"'
        if shell.count(verify_token) != 2:
            raise ValueError("expected existing-map and post-load verification")
        for token, count in (
            ("keymap_status=loaded", 2),
            ("keymap_reason=none", 2),
        ):
            if shell.count(token) != count:
                raise ValueError(f"keymap respawn token count changed: {token}")
        required_order = (
            "keymap_actual_sha256=",
            "[ \"$keymap_actual_sha256\" = \"$KEYMAP_SHA256\" ]",
            "/bin/console-unicode-mode",
            "keymap_reason=existing-readback",
            ">/run/console-keymap-existing.status 2>&1",
            "keymap_origin=already-loaded-verified",
            "keymap_reason=preflight",
            "/bin/console-keymap-verify --preflight \"$KEYMAP\"",
            ">/run/console-keymap-preflight.status 2>&1",
            "/bin/busybox loadkmap <\"$KEYMAP\"",
            "keymap_reason=readback",
            ">/run/console-keymap-verify.status 2>&1",
            "keymap_origin=loaded-now",
            "keyboard_map=loaded",
        )
        for token in required_order:
            require_once(shell, token, f"keymap gate token {token}")
        positions = [
            shell.index(required_order[0]),
            shell.index(required_order[1]),
            shell.index(required_order[2]),
            shell.index(required_order[3]),
            shell.index(verify_token),
            shell.index(required_order[4]),
            shell.index(required_order[5]),
            shell.index(required_order[6]),
            shell.index(required_order[7]),
            shell.index(required_order[8]),
            shell.index(required_order[9]),
            shell.index(required_order[10]),
            shell.rindex(verify_token),
            shell.index(required_order[11]),
            shell.index(required_order[12]),
            shell.index(required_order[13]),
        ]
        if positions != sorted(positions):
            raise ValueError("Unicode/preflight/load/readback/shell ordering changed")
        if shell.rindex("exec /bin/busybox ash -i") < positions[-1]:
            raise ValueError("successful interactive shell precedes the loaded-map gate")
        for token in (
            "readonly EXPECTED_DISPATCH='reboot is an alias for /bin/reboot'",
            "/bin/busybox ash -ic 'type reboot' 2>/dev/null",
            "reboot_dispatch=invalid",
            "reboot_dispatch=validated",
            "keyboard_map=failed reason=$keymap_reason tty1_shell=recovery-only",
            "type reboot to use Candidate Z watchdog recovery",
        ):
            if token not in shell:
                raise ValueError(f"dispatch/recovery contract absent: {token}")
        if shell.count("exec /bin/busybox ash -i") != 2:
            raise ValueError("expected one recovery and one successful interactive shell")
        for forbidden in ("dumpkmap", "LOADED_KEYMAP", "loaded_sha256=", "roundtrip=exact"):
            if forbidden in shell:
                raise ValueError(f"obsolete byte-roundtrip gate remains: {forbidden}")
        for token in (
            "first_entry=preflight-then-load-or-existing-exact-map",
            "readback=all-2048-kernel-entries-exact-high-halves-hole-and-all-others-absent",
            "table3=allocated",
            "verifier=KDGKBENT",
        ):
            if token not in shell:
                raise ValueError(f"whole-table runtime evidence token absent: {token}")

        background = "\n".join(
            (init, recorder, text_member(candidate, "bin/x-probe"), text_member(candidate, "etc/inittab"))
        )
        for token in ("/dev/tty0", "/dev/tty1", "/dev/tty2", "/dev/console"):
            if token in background:
                raise ValueError(f"background path gained a visible-console sink: {token}")
        if "/dev/watchdog" in "\n".join((init, shell, recorder)):
            raise ValueError("automatic AA path gained watchdog access")
        require_once(recorder, "output=/dev/ttyS0", "serial-only recorder")

        print("validation=candidate-aa-initramfs")
        print(f"candidate_initramfs_sha256={digest(candidate_data)}")
        print("baseline=exact-candidate-z")
        print("changed_members=init,bin/local-shell,bin/x-record")
        print(
            "added_members=bin/console-keymap-verify,bin/console-unicode-mode,"
            "etc/gemini-us.bkeymap"
        )
        print(f"keymap_sha256={KEYMAP_SHA256}")
        print(f"unicode_helper_sha256={digest(helper)}")
        print(f"keymap_verifier_sha256={digest(verifier)}")
        print(
            "runtime_gate=sha256-K_UNICODE-existing-KDG-or-preflight-load-"
            "KDGKBENT-2048-kernel-entries"
        )
        print("watchdog_recovery=byte-exact-candidate-z")
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
