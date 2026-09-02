#!/usr/bin/env python3
"""Validate pristine CPU8/CPU9 state for the completion-lock repair."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
from pathlib import Path


SOURCE_SHA256 = "bd94d4e4c1f1ceba8aeb4108fb33be0a8358eb794cda27424b4f57c8c5379c88"
SCRIPT = Path(__file__).resolve()
SOURCE = SCRIPT.with_name("validate-membership-lock-repair-pretrigger.py")
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source membership-lock pre-trigger validator changed")

spec = importlib.util.spec_from_file_location("cpu9_membership_lock_pretrigger", SOURCE)
assert spec is not None and spec.loader is not None
source = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source)

OLD_CANDIDATE = source.NEW_CANDIDATE
NEW_CANDIDATE = "370ae4d0ab2b7d3ed4d6f935198abbbb76a674698509053d8f0a1e0464774f3e"
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
        reason = "exact-ready-pristine-CPU9-completion-lock-repair-contract"
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
