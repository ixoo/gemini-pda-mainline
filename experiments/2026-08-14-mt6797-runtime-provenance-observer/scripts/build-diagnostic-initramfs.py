#!/usr/bin/env python3
"""Build the vendor-RNDIS provenance initramfs from exact Candidate AC."""

from __future__ import annotations

import argparse
from dataclasses import replace
import gzip
import hashlib
import importlib.util
from pathlib import Path
import stat
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
SOURCE_DIR = SCRIPT_DIR.parent / "initramfs"
PARSER = SCRIPT_DIR.parents[1] / "2026-07-21-usb-gadget-ethernet" / "scripts" / "validate-initramfs.py"
PARSER_SHA256 = "6ffaa2cb0c0aa8520be344abe585c91734420d9e6a37f5ed9875f20828e8c570"
BASELINE_SHA256 = "166c0f03ab9ca1062f36d55132141b4be5f06187380d17ab2f6e9e7db75d1dd3"
SOURCE_TO_MEMBER = {
    "init": "init",
    "usb-net": "bin/usb-net",
    "provenance-record": "bin/provenance-record",
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def pad4(data: bytearray) -> None:
    data.extend(b"\0" * ((-len(data)) & 3))


def encode_newc(members: dict[str, object]) -> bytes:
    raw = bytearray()
    for inode, name in enumerate(sorted(members), 1):
        member = members[name]
        encoded_name = name.encode() + b"\0"
        fields = (
            inode,
            member.mode,
            member.uid,
            member.gid,
            member.nlink,
            member.mtime,
            len(member.data),
            member.devmajor,
            member.devminor,
            member.rdevmajor,
            member.rdevminor,
            len(encoded_name),
            0,
        )
        raw.extend(b"070701" + b"".join(f"{value:08x}".encode() for value in fields))
        raw.extend(encoded_name)
        pad4(raw)
        raw.extend(member.data)
        pad4(raw)
    trailer = b"TRAILER!!!\0"
    fields = (len(members) + 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, len(trailer), 0)
    raw.extend(b"070701" + b"".join(f"{value:08x}".encode() for value in fields))
    raw.extend(trailer)
    pad4(raw)
    compressed = bytearray(gzip.compress(bytes(raw), compresslevel=9, mtime=0))
    compressed[9] = 3
    return bytes(compressed)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        raise SystemExit("error: refusing to overwrite output")
    if digest(PARSER.read_bytes()) != PARSER_SHA256:
        raise SystemExit("error: pinned Candidate AC parser changed")
    baseline = args.baseline.read_bytes()
    if args.baseline.is_symlink() or digest(baseline) != BASELINE_SHA256:
        raise SystemExit("error: exact Candidate AC initramfs changed")

    spec = importlib.util.spec_from_file_location("candidate_ac_parser", PARSER)
    if spec is None or spec.loader is None:
        raise SystemExit("error: cannot load Candidate AC parser")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    baseline_members = module.parse_newc(baseline)
    members = dict(baseline_members)
    source_names = {path.name for path in SOURCE_DIR.iterdir()}
    if source_names != set(SOURCE_TO_MEMBER):
        raise SystemExit("error: diagnostic initramfs source inventory changed")
    for source_name, member_name in SOURCE_TO_MEMBER.items():
        source_path = SOURCE_DIR / source_name
        info = source_path.lstat()
        if source_path.is_symlink() or not stat.S_ISREG(info.st_mode):
            raise SystemExit(f"error: unsafe source: {source_name}")
        source = source_path.read_bytes()
        if b"/dev/mmc" in source or b"reboot -" in source or b"/dev/watchdog" in source:
            raise SystemExit(f"error: unsafe device action in source: {source_name}")
        if member_name in members:
            members[member_name] = replace(members[member_name], data=source)
        else:
            template = members["bin/ac-record"]
            members[member_name] = replace(template, data=source)

    candidate = encode_newc(members)
    parsed = module.parse_newc(candidate)
    if set(parsed) != set(members):
        raise SystemExit("error: candidate inventory changed")
    for source_name, member_name in SOURCE_TO_MEMBER.items():
        if parsed[member_name].data != (SOURCE_DIR / source_name).read_bytes():
            raise SystemExit(f"error: embedded source mismatch: {source_name}")
    for name in set(parsed) - {"init", "bin/usb-net", "bin/provenance-record"}:
        if name not in baseline_members or parsed[name] != baseline_members[name]:
            raise SystemExit(f"error: unexpected baseline member delta: {name}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(candidate)
    args.output.chmod(0o600)
    print(f"output={args.output}")
    print(f"baseline_sha256={BASELINE_SHA256}")
    print(f"candidate_sha256={digest(candidate)}")
    print("changed_members=init,bin/usb-net")
    print("added_members=bin/provenance-record")
    print("device_storage_access=none")
    print("automatic_reboot=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
