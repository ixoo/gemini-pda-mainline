#!/usr/bin/env python3
"""Validate pristine CPU8/CPU9 state for the CPUHP lock repair."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
from pathlib import Path


SOURCE_SHA256 = "3edab4c7d0f83a3323a0a6b02c939b754ac9de59c36e1f8044155059d11aa3f4"
SCRIPT = Path(__file__).resolve()
SOURCE = SCRIPT.with_name("validate-progress-raw-lane-pretrigger.py")
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source progress raw-lane pre-trigger validator changed")

spec = importlib.util.spec_from_file_location("cpu9_progress_raw_lane_pretrigger", SOURCE)
assert spec is not None and spec.loader is not None
source = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source)

OLD_CANDIDATE = source.NEW_CANDIDATE
NEW_CANDIDATE = "0904c5a293fea22f6993cb25ab8d775ed539d57c8fac7a7a6c50b67e2916f293"
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
        reason = "exact-ready-pristine-CPU9-CPUHP-lock-repair-contract"
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
