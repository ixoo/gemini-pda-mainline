#!/usr/bin/env python3
"""Classify the exact CPU8 repeat plus bounded per-CPU accounting evidence."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
from pathlib import Path
import re


SOURCE_SHA256 = "4a17b7bf12beda716141884d6dae26c54d38a04dcd574c61e591e78d27a0dcdf"
SCRIPT = Path(__file__).resolve()
SOURCE = SCRIPT.with_name("classify-attempt.py")
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source attempt classifier changed")

spec = importlib.util.spec_from_file_location("expected_pair_attempt_classifier", SOURCE)
assert spec is not None and spec.loader is not None
source = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source)
if not callable(getattr(source, "classify", None)):
    raise SystemExit("source attempt classifier contract changed")


def cpu8_stat(value: str) -> tuple[int, ...]:
    if re.fullmatch(r"cpu8(?: +[0-9]+){10}", value) is None:
        raise source.Classification("CPU8-accounting-sample-malformed")
    return tuple(int(field) for field in value.split()[1:])


def classify(pretrigger: str, trigger: str) -> tuple[str, str]:
    result, reason = source.classify(pretrigger, trigger)
    if result != "cpu8-online":
        return result, reason

    normalized = trigger.replace("\r", "")
    after_begin = normalized[
        normalized.index(source.BEGIN) + len(source.BEGIN):
    ]
    observed = source.fields(
        after_begin[:after_begin.index(source.END)]
    )
    first = cpu8_stat(observed.get("cpu8_stat_first", ""))
    second = cpu8_stat(observed.get("cpu8_stat_second", ""))
    delta = sum(second) - sum(first)
    if delta <= 0:
        raise source.Classification("CPU8-accounting-did-not-advance")
    return (
        "cpu8-online-accounting-advanced",
        f"second-independent-online-proof-cpu8-accounting-delta={delta}-{reason}",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pretrigger", type=Path, required=True)
    parser.add_argument("--trigger", type=Path, required=True)
    args = parser.parse_args()
    try:
        result, reason = classify(
            args.pretrigger.read_text(encoding="utf-8", errors="replace"),
            args.trigger.read_text(encoding="utf-8", errors="replace"),
        )
    except (source.Classification, source.pretrigger_module.Classification) as error:
        result, reason = "rejected", str(error)
    print(f"runtime_classification={result}")
    print(f"runtime_reason={reason}")
    print("trigger_attempts=1" if result != "rejected" else "trigger_attempts=unknown")
    print("cpu9_requests=0")
    print("cpu_off_requests=0")
    print("retries=0")
    print("native_reboot_requested=no")
    return 0 if result != "rejected" else 3

if __name__ == "__main__":
    raise SystemExit(main())
