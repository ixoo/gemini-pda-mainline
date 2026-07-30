#!/usr/bin/env python3
"""Validate exact Gate 3 serviceability initramfs plus one manual module."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import pathlib
import stat
import sys
from dataclasses import dataclass

BASELINE_SHA256 = "e0dffa04a621f60903cf4cf7280d773ec1c89c43ea63ec0f8b3a0879e7cebc0f"
MODULE_MEMBER = "lib/da9213-legacy-regulator.ko"


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


def regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def align4(value: int) -> int:
    return (value + 3) & ~3


def parse_newc(data: bytes) -> dict[str, Member]:
    if data[:10] != b"\x1f\x8b\x08\0\0\0\0\0\x02\x03":
        raise ValueError("initramfs is not canonical gzip -n -9")
    raw = gzip.decompress(data)
    offset = 0
    previous = ""
    members: dict[str, Member] = {}
    while True:
        if offset + 110 > len(raw) or raw[offset:offset + 6] != b"070701":
            raise ValueError("invalid newc header")
        header = raw[offset:offset + 110]
        fields = [
            int(header[6 + index * 8:14 + index * 8], 16)
            for index in range(13)
        ]
        (
            _inode, mode, uid, gid, nlink, mtime, size, devmajor, devminor,
            rdevmajor, rdevminor, namesize, check,
        ) = fields
        if check or namesize < 2:
            raise ValueError("invalid newc metadata")
        name_start = offset + 110
        name_end = name_start + namesize
        if name_end > len(raw) or raw[name_end - 1] != 0:
            raise ValueError("invalid newc name")
        name = raw[name_start:name_end - 1].decode("utf-8")
        data_start = align4(name_end)
        data_end = data_start + size
        if data_end > len(raw):
            raise ValueError("truncated newc member")
        if name == "TRAILER!!!":
            if size or any(raw[align4(data_end):]):
                raise ValueError("invalid newc trailer")
            return members
        name = name.removeprefix("./") or "."
        parts = pathlib.PurePosixPath(name).parts
        if name in members or name < previous or name.startswith("/") or ".." in parts:
            raise ValueError("unsafe, duplicate, or unsorted newc member")
        previous = name
        members[name] = Member(
            mode, uid, gid, nlink, mtime, devmajor, devminor,
            rdevmajor, rdevminor, raw[data_start:data_end],
        )
        offset = align4(data_end)


def inherited_equal(expected: Member, actual: Member) -> bool:
    if stat.S_ISDIR(expected.mode) and stat.S_ISDIR(actual.mode):
        return (
            expected.mode == actual.mode
            and expected.uid == actual.uid
            and expected.gid == actual.gid
            and expected.mtime == actual.mtime
            and expected.devmajor == actual.devmajor
            and expected.devminor == actual.devminor
            and expected.rdevmajor == actual.rdevmajor
            and expected.rdevminor == actual.rdevminor
            and expected.data == actual.data
            and expected.nlink > 0
            and actual.nlink > 0
        )
    return expected == actual


def validate(
    baseline_path: pathlib.Path,
    candidate_path: pathlib.Path,
    module_path: pathlib.Path,
) -> bytes:
    baseline_data = regular(baseline_path, "Gate 3 initramfs")
    if digest(baseline_data) != BASELINE_SHA256:
        raise ValueError("baseline is not the exact Gate 3 initramfs")
    candidate_data = regular(candidate_path, "module initramfs")
    module_data = regular(module_path, "DA921x module")
    baseline = parse_newc(baseline_data)
    candidate = parse_newc(candidate_data)
    if set(candidate) != set(baseline) | {"lib", MODULE_MEMBER}:
        raise ValueError("initramfs inventory changed beyond lib and the module")
    for name, member in baseline.items():
        if not inherited_equal(member, candidate[name]):
            raise ValueError(f"inherited Gate 3 member changed: {name}")
    lib = candidate["lib"]
    if (
        not stat.S_ISDIR(lib.mode)
        or stat.S_IMODE(lib.mode) != 0o755
        or lib.uid or lib.gid or lib.mtime
        or lib.devmajor or lib.devminor or lib.rdevmajor or lib.rdevminor
    ):
        raise ValueError("added lib directory metadata changed")
    module = candidate[MODULE_MEMBER]
    if (
        not stat.S_ISREG(module.mode)
        or stat.S_IMODE(module.mode) != 0o400
        or module.uid or module.gid or module.mtime
        or module.devmajor or module.devminor
        or module.rdevmajor or module.rdevminor
        or module.nlink != 1
    ):
        raise ValueError("embedded module metadata changed")
    if module.data != module_data:
        raise ValueError("embedded module differs from packaged module")
    needle = MODULE_MEMBER.encode()
    for name, member in baseline.items():
        if stat.S_ISREG(member.mode) and needle in member.data:
            raise ValueError(f"inherited member unexpectedly names module: {name}")
    return candidate_data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=pathlib.Path)
    parser.add_argument("--candidate", required=True, type=pathlib.Path)
    parser.add_argument("--module", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        data = validate(args.baseline, args.candidate, args.module)
    except (OSError, UnicodeError, ValueError, gzip.BadGzipFile) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print("validation=exact-gate3-plus-manual-da921x-module")
    print(f"candidate_sha256={digest(data)}")
    print(f"baseline_sha256={BASELINE_SHA256}")
    print(f"module_sha256={digest(regular(args.module, 'DA921x module'))}")
    print("added_members=lib,lib/da9213-legacy-regulator.ko")
    print("changed_inherited_members=none")
    print("automatic_invocation=none")
    print("manual_post_serviceability_load=/lib/da9213-legacy-regulator.ko")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
