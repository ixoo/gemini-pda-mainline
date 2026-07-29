#!/usr/bin/env python3
"""Validate an exact complete Cassini-byte Candidate Hubble artifact."""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import stat
import sys

sys.dont_write_bytecode = True
import candidate_hubble as ch


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_manifest(data: bytes) -> dict[str, str]:
    try:
        lines = data.decode("ascii").splitlines()
    except UnicodeError as exc:
        raise ValueError("Cassini checksum manifest is not ASCII") from exc
    entries: dict[str, str] = {}
    for line in lines:
        if len(line) < 68 or line[64:68] != "  ./":
            raise ValueError("Cassini checksum manifest has a malformed line")
        wanted = line[:64]
        relative = line[68:]
        path = pathlib.PurePosixPath(relative)
        if (
            ch.HEX256.fullmatch(wanted) is None
            or not relative
            or path.is_absolute()
            or len(path.parts) != 1
            or path.as_posix() != relative
            or relative in entries
        ):
            raise ValueError("Cassini checksum manifest has an unsafe entry")
        entries[relative] = wanted
    if not entries:
        raise ValueError("Cassini checksum manifest is empty")
    return entries


def inventory(root: pathlib.Path) -> dict[str, pathlib.Path]:
    info = root.lstat()
    if root.is_symlink() or not stat.S_ISDIR(info.st_mode):
        raise ValueError("artifact root is missing or unsafe")
    if stat.S_IMODE(info.st_mode) != 0o700:
        raise ValueError("artifact root mode is not exact 0700")
    files: dict[str, pathlib.Path] = {}
    for path in root.iterdir():
        member = path.name
        member_info = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(member_info.st_mode):
            raise ValueError(f"artifact contains a non-regular member: {member}")
        if not member_info.st_size:
            raise ValueError(f"artifact contains an empty member: {member}")
        files[member] = path
    return files


def validate(root: pathlib.Path, expected_name: str) -> dict[str, pathlib.Path]:
    ch.require_pins()
    if root.name != expected_name:
        raise ValueError(
            f"artifact directory name changed: expected {expected_name}"
        )
    files = inventory(root)
    manifest_path = files.get(ch.MANIFEST_MEMBER)
    if manifest_path is None:
        raise ValueError("artifact lacks exact Cassini SHA256SUMS")
    manifest = ch.read_regular(manifest_path, "Cassini SHA256SUMS")
    if digest(manifest) != ch.CASSINI_MANIFEST_SHA256:
        raise ValueError("artifact checksum manifest is not exact Cassini")
    entries = parse_manifest(manifest)
    if set(files) != set(entries) | {ch.MANIFEST_MEMBER}:
        raise ValueError("artifact inventory differs from complete Cassini")

    for name, path in files.items():
        mode = stat.S_IMODE(path.lstat().st_mode)
        expected_mode = 0o755 if name in ch.EXECUTABLE_MEMBERS else 0o600
        if mode != expected_mode:
            raise ValueError(f"artifact member mode changed: {name}")
        if name == ch.MANIFEST_MEMBER:
            continue
        if ch.digest_path(path) != entries[name]:
            raise ValueError(f"artifact member differs from Cassini: {name}")

    boot = files[ch.BOOT_MEMBER]
    if (
        boot.stat().st_size != ch.CASSINI_RAW_SIZE
        or ch.digest_path(boot) != ch.CASSINI_RAW_SHA256
    ):
        raise ValueError("raw boot image is not exact Cassini")
    padded = files[ch.PADDED_MEMBER]
    if (
        padded.stat().st_size != ch.BOOT2_SIZE
        or ch.digest_path(padded) != ch.CASSINI_PADDED_SHA256
    ):
        raise ValueError("padded boot image is not exact Cassini")
    with padded.open("rb") as stream:
        raw_prefix = stream.read(ch.CASSINI_RAW_SIZE)
        tail = stream.read()
    if raw_prefix != boot.read_bytes() or tail != b"\0" * len(tail):
        raise ValueError("padded image is not exact raw Cassini plus a zero tail")
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", required=True, type=pathlib.Path)
    parser.add_argument(
        "--expected-name",
        choices=("cassini", "hubble"),
        default="hubble",
    )
    args = parser.parse_args()
    expected = (
        ch.CASSINI_ARTIFACT_DIR
        if args.expected_name == "cassini"
        else ch.ARTIFACT_DIR
    )
    try:
        artifact = args.artifact.absolute()
        files = validate(artifact, expected)
        print("validation=hubble-exact-cassini-artifact")
        print(f"artifact={artifact.resolve(strict=True)}")
        print(f"artifact_directory_name={expected}")
        print(f"complete_member_count={len(files)}")
        print("complete_member_bytes=exact-cassini")
        print("complete_member_modes=exact-cassini")
        print(f"manifest_sha256={ch.CASSINI_MANIFEST_SHA256}")
        print(f"raw_sha256={ch.CASSINI_RAW_SHA256}")
        print(f"raw_size={ch.CASSINI_RAW_SIZE}")
        print(f"padded_sha256={ch.CASSINI_PADDED_SHA256}")
        print(f"padded_size={ch.BOOT2_SIZE}")
        print("padded_tail=all-zero")
        print("hardware_access=none")
        return 0
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
