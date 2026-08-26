#!/usr/bin/env python3
"""Emit bounded in-memory BusyBox shell commands for an exact probe payload."""

from __future__ import annotations

import argparse
import base64
from pathlib import Path


CHUNK_SIZE = 768
VARIABLE = "__a72_probe_payload"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("probe", type=Path)
    args = parser.parse_args()
    probe = args.probe.resolve()
    if not probe.is_file() or probe.is_symlink():
        raise SystemExit("probe is missing or unsafe")
    payload = base64.b64encode(probe.read_bytes()).decode("ascii")
    print(f"{VARIABLE}=''")
    for offset in range(0, len(payload), CHUNK_SIZE):
        chunk = payload[offset:offset + CHUNK_SIZE]
        print(f'{VARIABLE}="${{{VARIABLE}}}{chunk}"')
    print(
        "printf '\\n'; printf '%s' \"$__a72_probe_payload\" | "
        "/bin/busybox base64 -d | /bin/busybox sh"
    )
    print(f"unset {VARIABLE}")


if __name__ == "__main__":
    main()
