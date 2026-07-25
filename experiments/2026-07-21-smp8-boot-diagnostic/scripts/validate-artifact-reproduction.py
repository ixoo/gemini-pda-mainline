#!/usr/bin/env python3
"""Require two Candidate AD artifact trees to be byte- and mode-identical."""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import stat
import sys


def inventory(root: pathlib.Path) -> dict[str, tuple[int, bytes]]:
    if root.is_symlink() or not root.is_dir():
        raise ValueError("artifact root is unsafe")
    output: dict[str, tuple[int, bytes]] = {}
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        info = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(info.st_mode):
            raise ValueError(f"artifact entry is not a regular file: {relative}")
        output[relative] = (stat.S_IMODE(info.st_mode), path.read_bytes())
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--first", type=pathlib.Path, required=True)
    parser.add_argument("--second", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        first = inventory(args.first.resolve(strict=True))
        second = inventory(args.second.resolve(strict=True))
        if first != second:
            differing = sorted(
                name for name in set(first) | set(second) if first.get(name) != second.get(name)
            )
            raise ValueError(f"artifact reproduction differs: {','.join(differing)}")
        boot = first.get("gemini-smp8.boot.img")
        if boot is None:
            raise ValueError("Candidate AD boot member is absent")
        print("validation=candidate-ad-artifact-reproduction")
        print(f"file_count={len(first)}")
        print("bytes=identical")
        print("modes=identical")
        print(f"boot_sha256={hashlib.sha256(boot[1]).hexdigest()}")
        print("hardware_write=none")
        return 0
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
