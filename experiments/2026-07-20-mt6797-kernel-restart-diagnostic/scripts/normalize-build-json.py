#!/usr/bin/env python3
"""Write canonical package provenance with generated_utc removed."""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

from ab_contract import read_regular


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        if args.output.exists() or args.output.is_symlink():
            raise ValueError("refusing to overwrite normalized build provenance")
        value = json.loads(read_regular(args.input, "package build provenance").decode("utf-8"))
        if not isinstance(value, dict) or "generated_utc" not in value:
            raise ValueError("package build provenance lacks generated_utc")
        del value["generated_utc"]
        encoded = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode("utf-8")
        descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
        return 0
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
