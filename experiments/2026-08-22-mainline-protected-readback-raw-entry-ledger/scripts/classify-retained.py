#!/usr/bin/env python3
"""Classify the exact two-record raw-entry ledger from a private pstore capture."""

from __future__ import annotations

import argparse
from pathlib import Path


PREFIX = b"GEMINI_PROTECTED_READBACK_LEDGER_V1 token=GPRB-20260821-A "
BEFORE = PREFIX + b"checkpoint=before-clock slot=173 crc32=08f2fe56\n"
AFTER = PREFIX + b"checkpoint=after-clock slot=174 crc32=e477a18e\n"
MAX_TOTAL_BYTES = 4_194_304


def classify_payload(payload: bytes) -> tuple[str, str, int, int]:
    before = payload.count(BEFORE)
    after = payload.count(AFTER)
    tagged = payload.count(PREFIX)
    if tagged != before + after or before > 1 or after > 1 or after > before:
        return "rejected-attribution", "malformed-duplicate-or-foreign-record", before, after
    if before == 0:
        return "neither", "raw-entry-mapping-or-first-commit-not-established", before, after
    if after == 0:
        return "before-clock-only", "protected-clock-call-entered-and-did-not-return", before, after
    return "before-and-after-clock", "protected-clock-call-returned", before, after


def read_capture(capture: Path) -> tuple[bytes, int]:
    pstore = capture / "pstore"
    if not pstore.is_dir() or pstore.is_symlink():
        raise ValueError("capture pstore directory missing or unsafe")
    files = sorted(pstore.iterdir())
    if any(not path.is_file() or path.is_symlink() for path in files):
        raise ValueError("capture contains unsafe pstore entry")
    total = sum(path.stat().st_size for path in files)
    if total > MAX_TOTAL_BYTES:
        raise ValueError("capture exceeds bounded pstore size")
    return b"".join(path.read_bytes() for path in files), len(files)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", type=Path, required=True)
    args = parser.parse_args()
    try:
        payload, files = read_capture(args.capture)
        result, reason, before, after = classify_payload(payload)
    except ValueError as error:
        result, reason, before, after, files = (
            "rejected-attribution",
            str(error).replace(" ", "-"),
            0,
            0,
            0,
        )
    print(f"runtime_classification={result}")
    print(f"runtime_reason={reason}")
    print(f"before_clock_record_count={before}")
    print(f"after_clock_record_count={after}")
    print(f"pstore_file_count={files}")
    print("cpu8_cpu9_admission=closed")
    print("claim_scope=two-checkpoint-raw-entry-ledger-only")
    return 3 if result == "rejected-attribution" else 0


if __name__ == "__main__":
    raise SystemExit(main())
