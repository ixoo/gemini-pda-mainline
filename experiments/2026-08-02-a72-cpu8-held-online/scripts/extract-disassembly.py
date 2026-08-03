#!/usr/bin/env python3
"""Extract named functions from an objdump stream without loading it whole."""

import argparse
import re
import sys
from pathlib import Path


LABEL = re.compile(r"^[0-9a-fA-F]+ <([^>]+)>:$")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("symbols", nargs="+")
    args = parser.parse_args()
    requested = set(args.symbols)
    if len(requested) != len(args.symbols):
        raise SystemExit("duplicate requested symbol")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    outputs = {
        symbol: (args.output_dir / f"{symbol}.txt").open("w")
        for symbol in args.symbols
    }
    found = set()
    current = None
    try:
        for line in sys.stdin:
            match = LABEL.match(line.rstrip("\n"))
            if match:
                current = match.group(1) if match.group(1) in requested else None
                if current:
                    found.add(current)
            if current:
                outputs[current].write(line)
    finally:
        for output in outputs.values():
            output.close()
    missing = requested - found
    if missing:
        raise SystemExit("missing disassembly: " + ", ".join(sorted(missing)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
