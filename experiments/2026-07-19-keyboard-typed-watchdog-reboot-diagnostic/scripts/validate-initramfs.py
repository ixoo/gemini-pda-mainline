#!/usr/bin/env python3
"""Validate Candidate Y's exact four-member initramfs delta from Candidate X."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import pathlib
import stat
import sys
from dataclasses import dataclass


X_INITRAMFS_SHA256 = "b54ce3cd75e7947ed867165e31abbf6ee6cbac7d41d171435f99bba7825bc769"
BUSYBOX_SHA256 = "52151e7f322f926b64049cdaa1410dc3ea6485525e0624b05813791c219ae933"
HELPER_SHA256 = "b9b555ce176a8bb29b492a73f06288784baf4f54786bed514ff1230efd732602"
MARKER = "GEMINI_KEYBOARD_TYPED_WATCHDOG_REBOOT_20260719_Y"
ALLOWED_DELTAS = {"init", "bin/local-shell", "bin/reboot", "bin/x-record"}


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
    members: dict[str, Member] = {}
    previous = ""
    while True:
        if offset + 110 > len(raw):
            raise ValueError("truncated newc header")
        header = raw[offset:offset + 110]
        if header[:6] != b"070701":
            raise ValueError("archive is not crc-free newc")
        try:
            fields = [int(header[6 + index * 8:14 + index * 8], 16) for index in range(13)]
        except ValueError as exc:
            raise ValueError("invalid newc numeric field") from exc
        (_ino, mode, uid, gid, nlink, mtime, size, devmajor, devminor,
         rdevmajor, rdevminor, namesize, check) = fields
        if check != 0 or namesize < 2:
            raise ValueError("invalid newc checksum/name size")
        name_start = offset + 110
        name_end = name_start + namesize
        if name_end > len(raw) or raw[name_end - 1] != 0:
            raise ValueError("truncated or unterminated newc name")
        try:
            stored_name = raw[name_start:name_end - 1].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("non-UTF-8 newc member name") from exc
        data_start = align4(name_end)
        data_end = data_start + size
        if data_end > len(raw):
            raise ValueError("truncated newc member data")
        if stored_name == "TRAILER!!!":
            if size != 0 or any(raw[align4(data_end):]):
                raise ValueError("invalid newc trailer or nonzero trailing padding")
            break
        name = stored_name.removeprefix("./")
        if name == "":
            name = "."
        parts = pathlib.PurePosixPath(name).parts
        if stored_name.startswith("/") or ".." in parts or name in members:
            raise ValueError("unsafe or duplicate newc member")
        if previous and name < previous:
            raise ValueError("newc members are not canonically sorted")
        previous = name
        members[name] = Member(
            mode, uid, gid, nlink, mtime, devmajor, devminor,
            rdevmajor, rdevminor, raw[data_start:data_end]
        )
        offset = align4(data_end)
    return members


def read_regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode):
        raise ValueError(f"{label} is not a regular non-symlink file")
    return path.read_bytes()


def text_member(members: dict[str, Member], name: str) -> str:
    member = members[name]
    if not stat.S_ISREG(member.mode):
        raise ValueError(f"script member is not regular: {name}")
    try:
        return member.data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"script member is not UTF-8: {name}") from exc


def require(text: str, token: str, label: str) -> None:
    if token not in text:
        raise ValueError(f"required {label} is absent")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=pathlib.Path, required=True)
    parser.add_argument("--candidate", type=pathlib.Path, required=True)
    parser.add_argument("--source-dir", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        baseline_data = read_regular(args.baseline, "Candidate X initramfs")
        candidate_data = read_regular(args.candidate, "Candidate Y initramfs")
        if digest(baseline_data) != X_INITRAMFS_SHA256:
            raise ValueError("baseline is not exact Candidate X initramfs")
        baseline = parse_newc(baseline_data)
        candidate = parse_newc(candidate_data)
        if set(candidate) != set(baseline):
            raise ValueError("Candidate Y archive inventory differs from X")
        if not ALLOWED_DELTAS <= set(candidate):
            raise ValueError("Candidate X lacks an approved overlay member")
        changed: set[str] = set()
        for name in baseline:
            if candidate[name] != baseline[name]:
                changed.add(name)
            if name not in ALLOWED_DELTAS and candidate[name] != baseline[name]:
                raise ValueError(f"unapproved archive member changed: {name}")
        if changed != ALLOWED_DELTAS:
            raise ValueError("Candidate Y does not change exactly four approved members")
        for name in ALLOWED_DELTAS:
            member = candidate[name]
            if not stat.S_ISREG(member.mode) or stat.S_IMODE(member.mode) != 0o755:
                raise ValueError(f"overlay type/mode changed: {name}")
            if member.uid or member.gid or member.mtime:
                raise ValueError(f"overlay ownership/timestamp changed: {name}")
            source = read_regular(args.source_dir / pathlib.PurePosixPath(name).name, name)
            if member.data != source:
                raise ValueError(f"archive/source mismatch: {name}")
        if digest(candidate["bin/busybox"].data) != BUSYBOX_SHA256:
            raise ValueError("exact Candidate X BusyBox changed")
        if digest(candidate["bin/input-event-capture"].data) != HELPER_SHA256:
            raise ValueError("exact Candidate X input helper changed")

        init = text_member(candidate, "init")
        local_shell = text_member(candidate, "bin/local-shell")
        reboot = text_member(candidate, "bin/reboot")
        recorder = text_member(candidate, "bin/x-record")
        probe = text_member(candidate, "bin/x-probe")
        inittab = text_member(candidate, "etc/inittab")
        require(init, f"readonly MARKER='{MARKER}'", "Y init marker")
        require(recorder, f"readonly MARKER='{MARKER}'", "Y recorder marker")
        require(local_shell, "export PS1='GEMINI-Y# '", "Y prompt")
        require(local_shell, f"printf '%s\\n' '{MARKER}'", "visible Y marker")
        require(init, "/bin/x-probe &", "independent probe")
        if probe != text_member(baseline, "bin/x-probe"):
            raise ValueError("Candidate X probe is not byte-exact")
        if inittab != text_member(baseline, "etc/inittab") or \
                "::ctrlaltdel:/bin/busybox true" not in inittab:
            raise ValueError("inittab or inert ctrl-alt-del policy changed")

        automatic = "\n".join((init, local_shell, recorder, probe, inittab))
        for token in ("/dev/watchdog", "/sys/class/watchdog", "10007000.watchdog"):
            if token in automatic:
                raise ValueError(f"automatic/background path gained watchdog access: {token}")
        if "/bin/busybox reboot" in automatic or "\n/bin/reboot" in automatic:
            raise ValueError("automatic/background path gained a reboot invocation")

        required_reboot = (
            "manual_reboot=requested trigger=typed method=mtk-wdt-expiry watchdog_armed=no storage_access=none",
            "[ ! -e \"$LIVE_WATCHDOG/interrupts\" ]",
            "[ -c /dev/watchdog0 ]",
            "[ -c /dev/kmsg ]",
            "ramoops_driver\" = ramoops",
            "[ \"$class_device\" = \"$platform_device\" ]",
            "[ \"$platform_driver\" = mtk-wdt ]",
            "[ \"$identity\" = mtk-wdt ]",
            "[ \"$timeout\" = \"$WATCHDOG_TIMEOUT_SECONDS\" ]",
            "0|unavailable",
            "manual_reboot=validated",
            "trap '' HUP INT QUIT TERM TSTP",
            "exec 3>/dev/watchdog0",
            "printf '.' >&3",
            "manual_reboot=armed watchdog0=armed handoff_ping=sent",
            "5|10|15|20|25|30|35|40",
            "manual_reboot=watchdog-expiry-failed boundary_seconds=40",
            "fd3=retained further_pings=none",
        )
        for token in required_reboot:
            require(reboot, token, f"typed watchdog contract token {token}")
        request_line = reboot.index("manual_reboot=requested")
        validated_line = reboot.index("manual_reboot=validated")
        trap_line = reboot.index("trap '' HUP INT QUIT TERM TSTP")
        open_line = reboot.index("exec 3>/dev/watchdog0")
        ping_line = reboot.index("printf '.' >&3")
        armed_line = reboot.index("manual_reboot=armed watchdog0=armed")
        if not request_line < validated_line < trap_line < open_line < ping_line < armed_line:
            raise ValueError("request/validation/trap/open/ping/armed ordering changed")
        if reboot.count("exec 3>/dev/watchdog0") != 1 or reboot.count(">&3") != 1:
            raise ValueError("watchdog fd has more than one open or write")
        for forbidden in (
            "printf 'V'", "exec 3>&-", "/bin/busybox reboot", "/bin/reboot",
            "sysrq-trigger", "/dev/mem", "/dev/mmc", "/dev/block", "/bin/dd",
            "/bin/sync", "/bin/poweroff", "/bin/halt", "/bin/kexec",
        ):
            if forbidden in reboot:
                raise ValueError(f"forbidden reboot-wrapper behavior present: {forbidden}")

        print("validation=candidate-y-initramfs")
        print(f"candidate_sha256={digest(candidate_data)}")
        print("baseline=exact-candidate-x")
        print("changed_members=init,bin/local-shell,bin/reboot,bin/x-record")
        print(f"marker={MARKER}")
        print("watchdog_ownership=typed-only")
        print("userspace_handoff_pings=one")
        print("software_reboot_fallback=none")
        print("hardware_write=none")
        return 0
    except (EOFError, OSError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
