#!/usr/bin/env python3
"""Validate pristine CPU8/CPU9 state for the progress raw-lane repair."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
from pathlib import Path


SOURCE_SHA256 = "eeeb5ec90aea300c143564866158f314022e8576dcde93292900713b31ec5a31"
SCRIPT = Path(__file__).resolve()
SOURCE = SCRIPT.with_name("validate-progress-errno-diagnostic-pretrigger.py")
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source CPU9 progress errno pre-trigger validator changed")

spec = importlib.util.spec_from_file_location("cpu9_progress_errno_pretrigger", SOURCE)
assert spec is not None and spec.loader is not None
source = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source)

OLD_CANDIDATE = source.NEW_CANDIDATE
NEW_CANDIDATE = "1cf367e021351f8a26643d827866786a879a8d6a3e68d8143cfce40bd1db52f7"
Classification = source.Classification
ARMED = source.ARMED


def classify(text: str) -> tuple[str, str]:
    if text.count(NEW_CANDIDATE) != 1:
        raise Classification("installed-full-candidate-mismatch")
    normalized = text.replace(NEW_CANDIDATE, OLD_CANDIDATE, 1)
    return source.classify(normalized)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    args = parser.parse_args()
    try:
        result, boot_id = classify(
            args.capture.read_text(encoding="utf-8", errors="replace")
        )
        reason = "exact-ready-pristine-CPU9-progress-raw-lane-repair-contract"
    except Classification as error:
        result, boot_id, reason = "rejected", "unknown", str(error)
    print(f"pretrigger_classification={result}")
    print(f"pretrigger_reason={reason}")
    print(f"boot_id={boot_id}")
    print("trigger_executions=0")
    print("cpu8_requests=0")
    print("cpu9_requests=0")
    print("cpu_off_requests=0")
    print("retries=0")
    return 0 if result == "serviceable-armed-zero-execution" else 3


if __name__ == "__main__":
    raise SystemExit(main())
