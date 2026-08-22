#!/usr/bin/env python3
"""Bind the retained recovery gate to the exact prefix-refusal candidate."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
from pathlib import Path


SOURCE_SHA256 = "fdaa505ccab9d3be6851b8af5b6142eb043ef36b3b128a57655f0fefbc3382a6"
CANDIDATE = "ced1f56fc56833ce47b63a98205a373276f5d666007190ec0d3bd5adb98f3901"
SCRIPT_DIR = Path(__file__).resolve().parent
SOURCE_PATH = (
    SCRIPT_DIR.parents[1]
    / "2026-08-21-mainline-manual-checkpoint-stage-control/scripts/validate-retained.py"
)
if not SOURCE_PATH.is_file() or SOURCE_PATH.is_symlink():
    raise SystemExit("retained validator source is missing or unsafe")
if hashlib.sha256(SOURCE_PATH.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("retained validator source identity changed")
SPEC = importlib.util.spec_from_file_location("manual_checkpoint_prefix_retained_source", SOURCE_PATH)
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
        raise ValueError("unexpected-retained-record-after-prefix-refusal")
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
    print("claim_scope=manual-checkpoint-prefix-cross-version-recovery-only")
    return 3 if result == "rejected-attribution" else 0


if __name__ == "__main__":
    raise SystemExit(main())
