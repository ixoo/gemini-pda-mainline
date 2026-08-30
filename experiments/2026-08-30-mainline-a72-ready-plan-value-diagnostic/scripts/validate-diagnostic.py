#!/usr/bin/env python3
"""Validate and decode one attributable READY plan value frame."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
from typing import NoReturn


SOURCE_SHA256 = "3ea7296b8431f19343b63d9f7fbefb11360b1a370cd9727cc069cb49e6673407"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-30-mainline-a72-ready-plan-predicate-diagnostic"
    / "scripts/validate-diagnostic.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source predicate diagnostic validator changed")

source_text = SOURCE.read_text(encoding="utf-8")
old_candidate = "7ac6f42938365d8bb1de49803a46287186e9a25347039975c48c386d0c1d6272"
new_candidate = "1c08f1fc9c2153965983eb469ea58babe7740fc4e3e7f14d799a060a44649d28"
if source_text.count(old_candidate) != 1:
    raise SystemExit("unsafe value diagnostic validator derivation")
source_text = source_text.replace(old_candidate, new_candidate)

base: dict[str, object] = {
    "__file__": str(SCRIPT),
    "__name__": "a72_ready_plan_value_diagnostic_base_validator",
}
exec(compile(source_text, str(SOURCE), "exec"), base)
BaseClassification = base["Classification"]
base_classify = base["classify"]
frame_values = base["frame_values"]
plan_names = base["names"]
PLAN_BITS = base["PLAN_BITS"]
EVIDENCE_BITS = base["EVIDENCE_BITS"]

VALUES = re.compile(
    r"(?:^|\s)A72_READY_PLAN_VALUES_V1 (\d+)"
    r" ([0-9a-f,]+) ([0-9a-f,]+) ([0-9a-f,]+)"
    r" ([0-9a-f,]+) ([0-9a-f,]+) (\d+) (\d+)(?:\s|$)"
)


class Classification(RuntimeError):
    """The frame is not the one exact failure-only value-observer contract."""


def reject(reason: str) -> NoReturn:
    raise Classification(reason)


def bitmap(value: str, ncaps: int) -> int:
    parsed = int(value.replace(",", ""), 16)
    if parsed >> ncaps:
        reject("value-bitmap-exceeds-arm64-ncaps")
    return parsed


def classify(
    text: str,
) -> tuple[str, str, int, int, int, tuple[int, ...], tuple[int, int]]:
    try:
        _, boot_id, plan, evidence = base_classify(text)  # type: ignore[operator]
        observed = frame_values(text)  # type: ignore[operator]
    except BaseClassification as error:  # type: ignore[misc]
        reject(str(error))
    if observed.get("ready_plan_values_count") != "1":
        reject("ready-plan-values-count-mismatch")
    line = observed.get("ready_plan_values_line", "")
    match = VALUES.search(line)
    if match is None:
        reject("ready-plan-values-line-malformed")
    ncaps = int(match.group(1))
    if not 1 <= ncaps <= 256:
        reject("arm64-ncaps-out-of-range")
    bitmaps = tuple(bitmap(match.group(index), ncaps) for index in range(2, 7))
    conduits = (int(match.group(7)), int(match.group(8)))
    if any(value not in (0, 1, 2) for value in conduits):
        reject("policy-conduit-out-of-range")
    return (
        "attributable-value-diagnostic-zero-execution",
        boot_id,
        plan,
        evidence,
        ncaps,
        bitmaps,
        conduits,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    args = parser.parse_args()
    try:
        result, boot_id, plan, evidence, ncaps, bitmaps, conduits = classify(
            args.capture.read_text(encoding="utf-8", errors="replace")
        )
        reason = "exact-value-observer-blocked-zero-execution"
    except Classification as error:
        result, boot_id, plan, evidence, ncaps = "rejected", "unknown", 0, 0, 0
        bitmaps, conduits, reason = (0, 0, 0, 0, 0), (0, 0), str(error)
    labels = ("early_caps", "target_caps", "required_caps", "target0_local_caps", "target1_local_caps")
    print(f"diagnostic_classification={result}")
    print(f"diagnostic_reason={reason}")
    print(f"boot_id={boot_id}")
    print(f"plan_mask={plan:#x}")
    print("plan_failures=" + (",".join(plan_names(plan, PLAN_BITS)) or "none"))  # type: ignore[operator]
    print(f"evidence_mask={evidence:#x}")
    print("evidence_failures=" + (",".join(plan_names(evidence, EVIDENCE_BITS)) or "none"))  # type: ignore[operator]
    print(f"arm64_ncaps={ncaps}")
    for label, value in zip(labels, bitmaps, strict=True):
        print(f"{label}={value:#x}")
    print(f"target0_policy_conduit={conduits[0]}")
    print(f"target1_policy_conduit={conduits[1]}")
    print("trigger_executions=0")
    print("cpu8_requests=0")
    print("cpu9_requests=0")
    print("cpu_off_requests=0")
    print("retries=0")
    return 0 if result == "attributable-value-diagnostic-zero-execution" else 3


if __name__ == "__main__":
    raise SystemExit(main())
