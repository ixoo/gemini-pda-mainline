#!/usr/bin/env python3
"""Require exact Candidate AO initramfs plus only bin/cassini-probe."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import pathlib
import stat
import sys
from dataclasses import dataclass
from types import ModuleType

sys.dont_write_bytecode = True
import candidate_cassini as cc


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
        if offset + 110 > len(raw) or raw[offset : offset + 6] != b"070701":
            raise ValueError("invalid newc header")
        header = raw[offset : offset + 110]
        fields = [int(header[6 + index * 8 : 14 + index * 8], 16)
                  for index in range(13)]
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
        name = raw[name_start : name_end - 1].decode("utf-8")
        data_start = align4(name_end)
        data_end = data_start + size
        if data_end > len(raw):
            raise ValueError("truncated newc member")
        if name == "TRAILER!!!":
            if size or any(raw[align4(data_end) :]):
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


def load_probe_validator() -> ModuleType:
    path = pathlib.Path(__file__).resolve().parent / "validate-cassini-probe.py"
    regular(path, "Cassini probe validator")
    spec = importlib.util.spec_from_file_location("cassini_probe_validator", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Cassini probe validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def inherited_member_equal(expected: Member, actual: Member) -> bool:
    """Compare inherited members, excluding only directory archive nlink."""
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


def member_delta(expected: Member, actual: Member) -> str:
    fields = (
        "mode", "uid", "gid", "nlink", "mtime", "devmajor", "devminor",
        "rdevmajor", "rdevminor", "data",
    )
    return ",".join(
        field for field in fields
        if getattr(expected, field) != getattr(actual, field)
    ) or "unknown"


def validate(
    baseline_path: pathlib.Path,
    candidate_path: pathlib.Path,
    source_path: pathlib.Path,
    helper_path: pathlib.Path,
) -> bytes:
    baseline_data = regular(baseline_path, "exact AO initramfs")
    candidate_data = regular(candidate_path, "Cassini initramfs")
    if digest(baseline_data) != cc.AO_INITRAMFS_SHA256:
        raise ValueError("baseline is not exact Candidate AO initramfs")
    baseline = parse_newc(baseline_data)
    candidate = parse_newc(candidate_data)
    expected = set(baseline) | {"bin/cassini-probe"}
    if set(candidate) != expected:
        raise ValueError("Cassini initramfs inventory changed beyond one helper")
    for name, member in baseline.items():
        if not inherited_member_equal(member, candidate[name]):
            raise ValueError(
                f"inherited AO initramfs member changed: {name} "
                f"fields={member_delta(member, candidate[name])}"
            )

    helper = candidate["bin/cassini-probe"]
    if (
        not stat.S_ISREG(helper.mode)
        or stat.S_IMODE(helper.mode) != 0o755
        or helper.uid
        or helper.gid
        or helper.mtime
        or helper.devmajor
        or helper.devminor
        or helper.rdevmajor
        or helper.rdevminor
        or helper.nlink != 1
    ):
        raise ValueError("embedded Cassini helper metadata changed")
    if helper.data != regular(helper_path, "built Cassini helper"):
        raise ValueError("embedded Cassini helper differs from validated binary")
    probe = load_probe_validator()
    probe.validate_source(source_path)
    probe.validate_binary(helper_path)

    # Exact inheritance is the no-auto-run proof: no baseline script, including
    # /init and the USB/local shell launchers, may mention the newly added file.
    for name, member in baseline.items():
        if stat.S_ISREG(member.mode) and b"cassini-probe" in member.data:
            raise ValueError(f"inherited member unexpectedly invokes probe: {name}")
    return candidate_data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=pathlib.Path)
    parser.add_argument("--candidate", required=True, type=pathlib.Path)
    parser.add_argument("--source", required=True, type=pathlib.Path)
    parser.add_argument("--helper", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        data = validate(args.baseline, args.candidate, args.source, args.helper)
    except (
        OSError, RuntimeError, UnicodeError, ValueError, gzip.BadGzipFile
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print("validation=cassini-exact-ao-plus-fixed-probe-initramfs")
    print(f"candidate_sha256={digest(data)}")
    print(f"baseline_sha256={cc.AO_INITRAMFS_SHA256}")
    print(f"probe_source_sha256={cc.PROBE_SOURCE_SHA256}")
    print(f"probe_binary_sha256={cc.digest_path(args.helper)}")
    print("added_members=bin/cassini-probe")
    print("changed_inherited_members=none")
    print("automatic_invocation=none")
    print("manual_post_usb_invocation=required")
    print("storage_watchdog_reboot_cpu_control=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
