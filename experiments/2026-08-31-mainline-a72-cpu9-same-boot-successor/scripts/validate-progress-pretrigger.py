#!/usr/bin/env python3
"""Validate pristine CPU8/CPU9 state for the progress-instrumented boot."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
from pathlib import Path


SOURCE_SHA256 = "5bdf84f1ef47796a1e87f3208922f5ec5c088e48765138acef5e34764a6844c9"
SCRIPT = Path(__file__).resolve()
SOURCE = SCRIPT.with_name("validate-pretrigger.py")
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source CPU9 pre-trigger validator changed")

spec = importlib.util.spec_from_file_location("cpu9_parent_pretrigger", SOURCE)
assert spec is not None and spec.loader is not None
source = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source)

OLD_CANDIDATE = source.NEW_CANDIDATE
NEW_CANDIDATE = "ce154daf63033fa235c4630365d5d12027d7c024fec3e9732ca07ac8ff9bbb72"
OLD_RELEASE = source.NEW_RELEASE
NEW_RELEASE = "7.1.3-gemini-cpu9-progress"
OLD_ARMED = source.ARMED
PROGRESS_ANCHOR = " cpu9_failure_stage=0 cpu9_derive_stage=0"
PROGRESS_FIELDS = " cpu9_progress_stage=0 cpu9_progress_ret=0"
if OLD_ARMED.count(PROGRESS_ANCHOR) != 1:
    raise SystemExit("source CPU9 pristine status contract changed")
ARMED = OLD_ARMED.replace(
    PROGRESS_ANCHOR, PROGRESS_ANCHOR + PROGRESS_FIELDS, 1
)
Classification = source.Classification
values = source.values
source_values = source.source_values


def classify(text: str) -> tuple[str, str]:
    observed = values(text)
    if observed.get("installed_full_sha256") != NEW_CANDIDATE:
        raise Classification("installed-full-candidate-mismatch")
    if observed.get("kernel_release") != NEW_RELEASE:
        raise Classification("kernel-release-mismatch")
    if observed.get("live_status") != ARMED:
        raise Classification("pristine-CPU9-progress-status-mismatch")

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
        reason = "exact-ready-pristine-CPU8-CPU9-progress-zero-execution-contract"
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
