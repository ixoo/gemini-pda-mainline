#!/usr/bin/env python3
"""Validate and decode one attributable READY predicate diagnostic frame."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
from typing import NoReturn


SOURCE_SHA256 = "c617550e84260388144e702bb3361d44291ed62f0ef0bb425b80b08555705406"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-30-mainline-a72-provenance-serviceability-composition"
    / "scripts/validate-pretrigger.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source pre-trigger validator changed")

source_text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("f694ddb95649db38ad72d08dcb2f81688608dca44782f08cfe4412e06b26204a", "7ac6f42938365d8bb1de49803a46287186e9a25347039975c48c386d0c1d6272", 1),
    ('"profile_blocked_count": "0",', '"profile_blocked_count": "1",', 1),
)
for old, new, count in replacements:
    actual = source_text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe predicate-diagnostic validator derivation: expected {count}, found {actual}: {old}"
        )
    source_text = source_text.replace(old, new)

base: dict[str, object] = {
    "__file__": str(SCRIPT),
    "__name__": "a72_ready_plan_predicate_diagnostic_base_validator",
}
exec(compile(source_text, str(SOURCE), "exec"), base)
BaseClassification = base["Classification"]
base_classify = base["classify"]
frame_values = base["values"]

PLAN_BITS = (
    "null", "abi", "profile", "target-weight", "cpu8", "cpu9",
    "compiled-caps", "early-caps", "target-caps", "required-caps",
    "conflict-caps", "classified-weight", "local-planned",
    "effects-planned", "hwcaps-planned", "evidence", "effects-empty",
    "hwcap-empty", "target-classified-weight", "target-local-exact",
    "target-subset", "target-present-cap", "target-absent-classified",
    "target-absent-present", "global-present-cap",
    "global-absent-classified", "identity",
)
EVIDENCE_BITS = (
    "abi", "parent", "config", "pair", "binding", "blockers",
    "expected-mpidr", "expected-midr", "target-cpu", "system-valid",
    "ctr-mask", "ctr-width", "ctr-res1", "ssbs", "spectre-v2",
    "spectre-v4", "bhb-state", "bhb-detail", "gic-policy", "identity",
    "observed-mpidr", "observed-midr", "observed-revidr", "target-cap",
    "policy-valid", "policy-conduit", "policy-flags", "policy-v4",
    "policy-pair",
)
DIAGNOSTIC = re.compile(
    r"(?:^|\s)A72_READY_PLAN_DIAG_V1 ret=(-?\d+) "
    r"plan=(0x[0-9a-f]+) evidence=(0x[0-9a-f]+)(?:\s|$)"
)


class Classification(RuntimeError):
    """The frame is not the one exact failure-only observer contract."""


def reject(reason: str) -> NoReturn:
    raise Classification(reason)


def names(mask: int, schema: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(name for bit, name in enumerate(schema) if mask & (1 << bit))


def classify(text: str) -> tuple[str, str, int, int]:
    try:
        _, boot_id = base_classify(text)  # type: ignore[operator]
        observed = frame_values(text)  # type: ignore[operator]
    except BaseClassification as error:  # type: ignore[misc]
        reject(str(error))
    if observed.get("ready_plan_diag_count") != "1":
        reject("ready-plan-diagnostic-count-mismatch")
    if observed.get("proof_mask_24000_count") != "1":
        reject("proof-mask-count-mismatch")
    line = observed.get("ready_plan_diag_line", "")
    match = DIAGNOSTIC.search(line)
    if match is None:
        reject("ready-plan-diagnostic-line-malformed")
    if int(match.group(1)) != -22:
        reject("validator-return-mismatch")
    plan = int(match.group(2), 16)
    evidence = int(match.group(3), 16)
    if plan == 0:
        reject("failed-validator-with-zero-plan-mask")
    if plan & ~((1 << len(PLAN_BITS)) - 1):
        reject("unknown-plan-diagnostic-bit")
    if evidence & ~((1 << len(EVIDENCE_BITS)) - 1):
        reject("unknown-evidence-diagnostic-bit")
    return "attributable-predicate-diagnostic-zero-execution", boot_id, plan, evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    args = parser.parse_args()
    try:
        result, boot_id, plan, evidence = classify(
            args.capture.read_text(encoding="utf-8", errors="replace")
        )
        reason = "exact-observer-identity-blocked-zero-execution-diagnostic"
    except Classification as error:
        result, boot_id, plan, evidence, reason = (
            "rejected", "unknown", 0, 0, str(error)
        )
    print(f"diagnostic_classification={result}")
    print(f"diagnostic_reason={reason}")
    print(f"boot_id={boot_id}")
    print(f"plan_mask={plan:#x}")
    print("plan_failures=" + (",".join(names(plan, PLAN_BITS)) or "none"))
    print(f"evidence_mask={evidence:#x}")
    print("evidence_failures=" + (",".join(names(evidence, EVIDENCE_BITS)) or "none"))
    print("trigger_executions=0")
    print("cpu8_requests=0")
    print("cpu9_requests=0")
    print("cpu_off_requests=0")
    print("retries=0")
    return 0 if result == "attributable-predicate-diagnostic-zero-execution" else 3


if __name__ == "__main__":
    raise SystemExit(main())
