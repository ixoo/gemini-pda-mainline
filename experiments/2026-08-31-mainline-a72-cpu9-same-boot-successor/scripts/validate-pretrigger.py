#!/usr/bin/env python3
"""Validate exact pristine CPU8 and CPU9 controller state before one trigger."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
from pathlib import Path


SOURCE_SHA256 = "6ed44a37f0b7c495c01ef24fdb91cd469da2fbe5323c81e18db1a6355ce962c4"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-31-mainline-a72-expected-pair-model-contract-repair"
    / "scripts/validate-pretrigger.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source pre-trigger validator changed")

spec = importlib.util.spec_from_file_location("cpu8_parent_pretrigger", SOURCE)
assert spec is not None and spec.loader is not None
source = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source)

OLD_CANDIDATE = "42c984ee72fe93e7f6157598dd479a9348a03d733df7948e4e4c14aa356c78ee"
NEW_CANDIDATE = "118096351905936e8f7c1fe9b186dadb191808bc94092cbd7a67a0b936a00562"
OLD_RELEASE = "7.1.3-gemini-a72-admission-live"
NEW_RELEASE = "7.1.3-gemini-cpu9-controller"
CPU9_SUFFIX = (
    " cpu9_controller_consumed=0 cpu9_operation_ret=-115"
    " cpu9_failure_stage=0 cpu9_derive_stage=0"
    " cpu9_binder_snapshot_ret=-11 cpu9_abi=0 cpu9_lifecycle=0"
    " cpu9_terminal=0 cpu9_last_stage=0 cpu9_stage_errno=0"
    " cpu9_checkpoint_errno=0 cpu9_attempted=0"
    " cpu9_membership_published=0 cpu9_cpu_requests=0"
    " cpu9_cpu_off_requests=0 cpu9_retries=0 cpu9_retained_mask=0x0"
)

inner = getattr(source, "namespace", None)
OLD_ARMED = inner.get("ARMED") if isinstance(inner, dict) else None
if not isinstance(OLD_ARMED, str) or not OLD_ARMED.endswith(
    "p30e_controller_sequence=0"
):
    raise SystemExit("source armed contract changed")
ARMED = OLD_ARMED + CPU9_SUFFIX
Classification = source.Classification
values = source.source_values
source_values = values


def classify(text: str) -> tuple[str, str]:
    observed = values(text)
    if observed.get("installed_full_sha256") != NEW_CANDIDATE:
        raise Classification("installed-full-candidate-mismatch")
    if observed.get("kernel_release") != NEW_RELEASE:
        raise Classification("kernel-release-mismatch")
    if observed.get("live_status") != ARMED:
        raise Classification("pristine-CPU9-controller-status-mismatch")

    normalized = text
    for old, new, count in (
        (NEW_CANDIDATE, OLD_CANDIDATE, 1),
        (NEW_RELEASE, OLD_RELEASE, 1),
        ("live_status=" + ARMED, "live_status=" + OLD_ARMED, 1),
    ):
        if normalized.count(old) != count:
            raise Classification("pretrigger-normalization-boundary-changed")
        normalized = normalized.replace(old, new)
    return source.classify(normalized)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    args = parser.parse_args()
    try:
        result, boot_id = classify(
            args.capture.read_text(encoding="utf-8", errors="replace")
        )
        reason = "exact-ready-pristine-CPU8-CPU9-zero-execution-contract"
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
