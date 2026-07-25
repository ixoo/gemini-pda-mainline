#!/usr/bin/env python3
"""Remove only the package-generation timestamp from build provenance."""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import stat
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        source_info = args.input.lstat()
        if (
            args.input.is_symlink()
            or not stat.S_ISREG(source_info.st_mode)
            or not source_info.st_size
        ):
            raise ValueError("package build provenance is missing, empty, or unsafe")
        if args.output.exists() or args.output.is_symlink():
            raise ValueError("refusing to overwrite normalized provenance")
        value = json.loads(args.input.read_text(encoding="utf-8"))
        if (
            not isinstance(value, dict)
            or set(value).intersection({"build_dir", "source_dir", "artifact_dir"})
            or "generated_utc" not in value
        ):
            raise ValueError("package build provenance contract changed")
        del value["generated_utc"]
        data = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
        descriptor = os.open(
            args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
        )
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
        return 0
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
