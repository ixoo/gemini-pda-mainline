#!/usr/bin/env python3
"""Require exact READY plus completed effect planning before CPU8."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


SOURCE_SHA256 = "20feaad24a8fb68f1f4d6a77d2457c36749aa5feeea88667e3118a4781ad11c5"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-31-mainline-a72-effect-plan-stage-ledger"
    / "scripts/validate-pretrigger.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source pre-trigger validator changed")

text = SOURCE.read_text(encoding="utf-8")
old_candidate = "b78ac044977749af97864676cc64b34224ce348ff8d9c14b41a67f21a453e8c1"
new_candidate = "42c984ee72fe93e7f6157598dd479a9348a03d733df7948e4e4c14aa356c78ee"
if text.count(old_candidate) != 1:
    raise SystemExit("unsafe expected-pair pre-trigger candidate derivation")
text = text.replace(old_candidate, new_candidate)

namespace = {"__file__": str(SCRIPT), "__name__": "_expected_pair_pretrigger"}
exec(compile(text, str(SOURCE), "exec"), namespace)
source_classify = namespace["classify"]
source_values = namespace["values"]
Classification = namespace["Classification"]


def classify(text: str) -> tuple[str, str]:
    result, boot_id = source_classify(text)
    observed = source_values(text)
    expected = {
        "effect_derive_target0_count": "0",
        "effect_derive_target0_line": "",
        "effect_derive_target1_count": "0",
        "effect_derive_target1_line": "",
        "effect_plan_preconditions_count": "0",
        "effect_plan_preconditions_line": "",
        "effect_plan_derive_count": "0",
        "effect_plan_derive_line": "",
        "effect_plan_validate_count": "0",
        "effect_plan_validate_line": "",
        "effect_plan_complete_count": "1",
    }
    for key, required in expected.items():
        if observed.get(key) != required:
            raise Classification(f"{key}-mismatch")
    if not observed.get("effect_plan_complete_line", "").endswith(
        "ARM64_LATE_CPU_EFFECT_PLAN_V1 stage=complete ret=0"
    ):
        raise Classification("effect-plan-complete-line-mismatch")
    return result, boot_id


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    args = parser.parse_args()
    try:
        result, boot_id = classify(
            args.capture.read_text(encoding="utf-8", errors="replace")
        )
        reason = "exact-ready-and-effect-plan-complete-zero-execution-contract"
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
