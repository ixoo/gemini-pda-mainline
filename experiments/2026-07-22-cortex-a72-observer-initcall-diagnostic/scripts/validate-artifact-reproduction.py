#!/usr/bin/env python3
"""Require two Candidate AF artifact trees to be byte- and mode-identical."""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import re
import stat
import sys


BOOT_MEMBER = "gemini-a72-observer-initcall-diagnostic.boot.img"
EXECUTABLE_MEMBERS = {
    "console-keymap-verify",
    "console-unicode-mode",
    "input-event-capture",
}
EXPECTED_MEMBERS = {
    "Image.gz",
    "SHA256SUMS",
    "System.map",
    "analysis.txt",
    "boot-validation.txt",
    "console-keymap-verify",
    "console-unicode-mode",
    BOOT_MEMBER,
    "gemini-a72-observer-initcall-diagnostic-initramfs.img",
    "gemini-us.bkeymap",
    "input-event-capture",
    "kernel.config",
    "mt6797-gemini-pda-a72-observer-initcall-diagnostic.dtb",
    "package-validation.txt",
    "provenance.txt",
    "serializer.txt",
    "source-build.json",
}


def inventory(root: pathlib.Path) -> dict[str, tuple[int, str]]:
    info = root.lstat()
    if root.is_symlink() or not stat.S_ISDIR(info.st_mode):
        raise ValueError(f"unsafe artifact directory: {root}")
    result: dict[str, tuple[int, str]] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        path_info = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(path_info.st_mode):
            raise ValueError(f"unexpected non-regular artifact member: {relative}")
        result[relative] = (
            stat.S_IMODE(path_info.st_mode),
            hashlib.sha256(path.read_bytes()).hexdigest(),
        )
    if not result:
        raise ValueError("empty Candidate AF artifact")
    return result


def validate_tree(root: pathlib.Path, members: dict[str, tuple[int, str]]) -> None:
    if set(members) != EXPECTED_MEMBERS:
        raise ValueError("Candidate AF artifact inventory changed")
    for name, (mode, _) in members.items():
        expected_mode = 0o755 if name in EXECUTABLE_MEMBERS else 0o600
        if mode != expected_mode:
            raise ValueError(f"Candidate AF artifact mode changed: {name}")
    lines = (root / "SHA256SUMS").read_text(encoding="ascii").splitlines()
    seen: set[str] = set()
    for line in lines:
        fields = line.split(maxsplit=1)
        if len(fields) != 2 or re.fullmatch(r"[0-9a-f]{64}", fields[0]) is None:
            raise ValueError("malformed Candidate AF artifact manifest")
        name = fields[1].removeprefix("*").removeprefix("./")
        if name in seen or name == "SHA256SUMS" or name not in members:
            raise ValueError("unsafe or duplicate Candidate AF manifest member")
        if fields[0] != members[name][1]:
            raise ValueError(f"Candidate AF artifact checksum mismatch: {name}")
        seen.add(name)
    if seen != EXPECTED_MEMBERS - {"SHA256SUMS"}:
        raise ValueError("Candidate AF manifest is not the exact artifact inventory")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("first", type=pathlib.Path)
    parser.add_argument("second", type=pathlib.Path)
    args = parser.parse_args()
    try:
        first_root = args.first.resolve(strict=True)
        second_root = args.second.resolve(strict=True)
        if first_root == second_root or first_root.samefile(second_root):
            raise ValueError("reproduction requires two independent artifact trees")
        first = inventory(first_root)
        second = inventory(second_root)
        validate_tree(first_root, first)
        validate_tree(second_root, second)
        if first != second:
            names = set(first) | set(second)
            changed = sorted(name for name in names if first.get(name) != second.get(name))
            raise ValueError("Candidate AF artifacts differ: " + ",".join(changed[:3]))
        if BOOT_MEMBER not in first:
            raise ValueError("Candidate AF boot member is absent")
        print("validation=candidate-af-a72-observer-initcall-artifact-reproduction")
        print(f"members={len(first)}")
        print(f"boot_sha256={first[BOOT_MEMBER][1]}")
        print("bytes_identical=yes")
        print("modes_identical=yes")
        return 0
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
