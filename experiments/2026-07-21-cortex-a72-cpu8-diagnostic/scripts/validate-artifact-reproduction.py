#!/usr/bin/env python3
"""Require two Candidate AE artifact trees to be byte- and mode-identical."""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import stat
import sys


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
        raise ValueError("empty Candidate AE artifact")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("first", type=pathlib.Path)
    parser.add_argument("second", type=pathlib.Path)
    args = parser.parse_args()
    try:
        first = inventory(args.first)
        second = inventory(args.second)
        if first != second:
            first_names = set(first)
            second_names = set(second)
            details = []
            if first_names != second_names:
                details.append("inventory")
            if any(first.get(name) != second.get(name) for name in first_names & second_names):
                details.append("bytes-or-modes")
            raise ValueError("Candidate AE artifacts differ: " + ",".join(details))
        boot_names = [name for name in first if name == "gemini-cpu8.boot.img"]
        if boot_names != ["gemini-cpu8.boot.img"]:
            raise ValueError("Candidate AE boot member is absent")
        print("validation=candidate-ae-artifact-reproduction")
        print(f"members={len(first)}")
        print(f"boot_sha256={first['gemini-cpu8.boot.img'][1]}")
        print("bytes_identical=yes")
        print("modes_identical=yes")
        return 0
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
