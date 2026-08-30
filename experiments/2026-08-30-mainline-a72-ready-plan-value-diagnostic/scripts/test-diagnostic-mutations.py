#!/usr/bin/env python3
"""Reject decision-changing mutations of the runtime value frame."""

from __future__ import annotations

import importlib.util
import hashlib
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "ready_plan_value_diagnostic", SCRIPT_DIR / "validate-diagnostic.py"
)
if SPEC is None or SPEC.loader is None:
    raise SystemExit("cannot load value diagnostic validator")
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)

SOURCE = (
    SCRIPT_DIR.parents[1]
    / "2026-08-30-mainline-a72-ready-plan-predicate-diagnostic"
    / "scripts/test-diagnostic-mutations.py"
)
SOURCE_SHA256 = "ae5ce60bb85820784665205ccde9ca483b472f18855c0005e4e54c18494627fb"
if not SOURCE.is_file() or hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source predicate mutation frame changed")
namespace = {"__file__": str(SOURCE), "__name__": "value_frame_source"}
exec(compile(SOURCE.read_text(encoding="utf-8"), str(SOURCE), "exec"), namespace)
FRAME = namespace["FRAME"].replace(
    "7ac6f42938365d8bb1de49803a46287186e9a25347039975c48c386d0c1d6272",
    "1c08f1fc9c2153965983eb469ea58babe7740fc4e3e7f14d799a060a44649d28",
).replace(
    "ready_plan_diag_line=[    0.085595] mt6797-psci: A72_READY_PLAN_DIAG_V1 ret=-22 plan=0x288380 evidence=0x2000000\n",
    "ready_plan_diag_line=[    0.085595] mt6797-psci: A72_READY_PLAN_DIAG_V1 ret=-22 plan=0x288380 evidence=0x2000000\n"
    "ready_plan_values_count=1\n"
    "ready_plan_values_line=[    0.085600] mt6797-psci: A72_READY_PLAN_VALUES_V1 128 3 4 8 10 20 1 1\n",
)


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError(f"mutation anchor count changed: {old!r}")
    return text.replace(old, new, 1)


def main() -> int:
    result = VALIDATOR.classify(FRAME)
    if result[0] != "attributable-value-diagnostic-zero-execution":
        raise SystemExit("known-good value frame was rejected")
    mutations = (
        ("wrong-candidate", "installed_full_sha256=1c08f1fc", "installed_full_sha256=00000000"),
        ("missing-values", "ready_plan_values_count=1", "ready_plan_values_count=0"),
        ("bad-ncaps", "A72_READY_PLAN_VALUES_V1 128", "A72_READY_PLAN_VALUES_V1 0"),
        ("high-bitmap", " 3 4 8 10 20 1 1", " 100000000000000000000000000000000 4 8 10 20 1 1"),
        ("bad-conduit", " 10 20 1 1", " 10 20 3 1"),
        ("wrong-return", "ret=-22", "ret=0"),
        ("zero-plan", "plan=0x288380", "plan=0x0"),
        ("unknown-evidence", "evidence=0x2000000", "evidence=0x20000000"),
        ("profile-unblocked", "profile_blocked_count=1", "profile_blocked_count=0"),
        ("cpu8-online", "cpu_online=0-7", "cpu_online=0-8"),
        ("cpu-request", "cpu_requests=0 cpu9_requests=0", "cpu_requests=1 cpu9_requests=0"),
        ("trigger-consumed", "trigger_consumed=0", "trigger_consumed=1"),
        ("storage-write", "device_storage_writes=none", "device_storage_writes=boot2"),
    )
    rejected = 0
    for label, old, new in mutations:
        try:
            VALIDATOR.classify(replace_once(FRAME, old, new))
        except VALIDATOR.Classification:
            rejected += 1
        else:
            raise SystemExit(f"unsafe runtime mutation accepted: {label}")
    print(f"unsafe_runtime_mutations_rejected={rejected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
