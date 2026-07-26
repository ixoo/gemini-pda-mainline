#!/usr/bin/env python3
"""Validate the eMMC helper as a narrow transform of Candidate AO initramfs."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import pathlib
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass


BASELINE_SHA256 = "166c0f03ab9ca1062f36d55132141b4be5f06187380d17ab2f6e9e7db75d1dd3"
BUSYBOX_SHA256 = "52151e7f322f926b64049cdaa1410dc3ea6485525e0624b05813791c219ae933"


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


def read_regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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
        fields = [int(header[6 + i * 8 : 14 + i * 8], 16) for i in range(13)]
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
            raise ValueError("unsafe or unsorted newc member")
        previous = name
        members[name] = Member(
            mode, uid, gid, nlink, mtime, devmajor, devminor,
            rdevmajor, rdevminor, raw[data_start:data_end],
        )
        offset = align4(data_end)


def check_metadata(member: Member, mode: int, label: str) -> None:
    if not stat.S_ISREG(member.mode) or stat.S_IMODE(member.mode) != mode:
        raise ValueError(f"{label} mode changed")
    if any((member.uid, member.gid, member.mtime, member.devmajor,
            member.devminor, member.rdevmajor, member.rdevminor)) or member.nlink != 1:
        raise ValueError(f"{label} metadata changed")


def validate(args: argparse.Namespace) -> bytes:
    baseline_data = read_regular(args.baseline, "baseline")
    candidate_data = read_regular(args.candidate, "candidate")
    if digest(baseline_data) != BASELINE_SHA256:
        raise ValueError("baseline is not exact Candidate AO initramfs")
    baseline = parse_newc(baseline_data)
    candidate = parse_newc(candidate_data)
    expected = set(baseline) | {"bin/dd", "bin/emmc-flash-boot2"}
    if set(candidate) != expected:
        raise ValueError("initramfs inventory changed")
    for name, member in baseline.items():
        if candidate[name] != member:
            raise ValueError(f"inherited member changed: {name}")

    dd = candidate["bin/dd"]
    if not stat.S_ISLNK(dd.mode) or dd.data != b"busybox":
        raise ValueError("bin/dd is not the BusyBox symlink")
    if stat.S_IMODE(dd.mode) != 0o777 or any((dd.uid, dd.gid, dd.mtime, dd.devmajor,
                                               dd.devminor, dd.rdevmajor, dd.rdevminor)):
        raise ValueError("bin/dd metadata changed")

    helper = candidate["bin/emmc-flash-boot2"]
    check_metadata(helper, 0o755, "eMMC helper")
    source = read_regular(args.source_dir / "emmc-flash-boot2", "helper source")
    if helper.data != source:
        raise ValueError("embedded eMMC helper differs from source")
    text = helper.data.decode("utf-8")
    for token in (
        "PARTNAME)", "[ \"$partname\" = boot2 ]", "--confirm-boot2",
        "conv=fsync", "/proc/mounts", "/sys/class/block/mmcblk*/uevent",
        "result=write-synced-flushed-full-readback-verified", "backup_sha256",
    ):
        if token not in text:
            raise ValueError(f"helper safety token missing: {token}")
    if "mmcblk0p30" in text or "of=/dev/mmc" in text:
        raise ValueError("helper hard-codes a partition target")

    busybox = candidate["bin/busybox"].data
    if digest(busybox) != BUSYBOX_SHA256:
        raise ValueError("exact Candidate AO BusyBox changed")
    with tempfile.TemporaryDirectory(prefix="emmc-busybox-") as directory:
        path = pathlib.Path(directory) / "busybox"
        path.write_bytes(busybox)
        path.chmod(0o755)
        result = subprocess.run([path, "--list"], capture_output=True, text=True, check=False)
        if result.returncode or "\ndd\n" not in f"\n{result.stdout}\n":
            raise ValueError("embedded BusyBox dd applet is unavailable")
    return candidate_data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True, type=pathlib.Path)
    parser.add_argument("--candidate", required=True, type=pathlib.Path)
    parser.add_argument("--source-dir", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        data = validate(args)
    except (OSError, UnicodeError, ValueError, gzip.BadGzipFile) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print("validation=candidate-emmc-initramfs")
    print(f"candidate_sha256={digest(data)}")
    print(f"baseline_sha256={BASELINE_SHA256}")
    print(f"busybox_sha256={BUSYBOX_SHA256}")
    print("added_members=bin/dd,bin/emmc-flash-boot2")
    print("storage_access=explicit-confirmation-only")
    print("target_resolution=gpt-partname-boot2-from-sysfs")
    print("write=dd-bs4M-count4-conv-fsync")
    print("readback=full-partition-sha256")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
