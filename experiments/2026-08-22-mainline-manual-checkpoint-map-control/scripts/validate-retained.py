#!/usr/bin/env python3
"""Bind empty retained recovery to the exact mapping-control candidate."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
from pathlib import Path


SOURCE_SHA256 = "1f2f886225240b5cb738784cd88ed0499f0b97121830a3a8fc8468afddb7899a"
CANDIDATE = "dd513384c78ee8378e1e4bf515f89b99ca87ed6ed86c1d38ec37f8aadd693b5b"
SCRIPT_DIR = Path(__file__).resolve().parent
SOURCE_PATH = (
    SCRIPT_DIR.parents[1]
    / "2026-08-21-mainline-manual-checkpoint-prefix-control/scripts/validate-retained.py"
)
if not SOURCE_PATH.is_file() or SOURCE_PATH.is_symlink():
    raise SystemExit("retained validator source is missing or unsafe")
if hashlib.sha256(SOURCE_PATH.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("retained validator source identity changed")
SPEC = importlib.util.spec_from_file_location("manual_checkpoint_map_retained_source", SOURCE_PATH)
assert SPEC and SPEC.loader
SOURCE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SOURCE)
SOURCE.CANDIDATE = CANDIDATE
SOURCE.SOURCE.CANDIDATE = CANDIDATE

PREFIX = SOURCE.PREFIX
FIRST = SOURCE.FIRST
SECOND = SOURCE.SECOND
EMPTY_HEADER = SOURCE.EMPTY_HEADER
MAX_PSTORE_BYTES = SOURCE.MAX_PSTORE_BYTES


def classify_text(path: Path) -> tuple[str, str]:
    result, reason = SOURCE.classify_text(path)
    if result != "live-pass-recovered-empty":
        raise ValueError("unexpected-retained-record-after-map-control")
    return result, reason


def classify(path: Path) -> tuple[str, str]:
    try:
        return classify_text(path)
    except (OSError, UnicodeError, ValueError) as error:
        return "rejected-attribution", str(error).replace(" ", "-")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    args = parser.parse_args()
    result, reason = classify(args.capture)
    print(f"retained_classification={result}")
    print(f"retained_reason={reason}")
    print("cpu8_cpu9_admission=closed")
    print("claim_scope=manual-checkpoint-map-cross-version-recovery-only")
    return 3 if result == "rejected-attribution" else 0


if __name__ == "__main__":
    raise SystemExit(main())
