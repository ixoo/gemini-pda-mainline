#!/usr/bin/env python3
"""Validate pristine CPU8/CPU9 state for the exact CPU-map candidate."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
from pathlib import Path


SOURCE_SHA256 = "d86e78db5996f96b0e11efebd044454719ca8f0a6636671e72a405e1047499aa"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/"
    "scripts/validate-completion-lock-repair-pretrigger.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source completion-lock pre-trigger validator changed")

spec = importlib.util.spec_from_file_location("completion_lock_pretrigger", SOURCE)
assert spec is not None and spec.loader is not None
source = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source)

OLD_CANDIDATE = source.NEW_CANDIDATE
NEW_CANDIDATE = "68ec1b7815cab7abae99cbdecabb2f0ba0dd1ddbf26943d652fcedf4d2b4e393"
Classification = source.Classification


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
        reason = "exact-ready-pristine-mt6797-cpu-map-contract"
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
