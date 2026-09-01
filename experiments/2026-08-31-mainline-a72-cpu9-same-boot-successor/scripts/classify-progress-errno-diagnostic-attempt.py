#!/usr/bin/env python3
"""Classify one CPU9 progress errno diagnostic runtime attempt."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import sys


SOURCE_SHA256 = "c72ec553233aba2a1c425d416c9d2da49c7d5045a840560ad473f04d82b335b3"
VALIDATOR_SHA256 = "eeeb5ec90aea300c143564866158f314022e8576dcde93292900713b31ec5a31"
SCRIPT = Path(__file__).resolve()
SOURCE = SCRIPT.with_name("classify-mapping-fix-attempt.py")
VALIDATOR = SCRIPT.with_name("validate-progress-errno-diagnostic-pretrigger.py")
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source CPU9 mapping-fix attempt classifier changed")
if hashlib.sha256(VALIDATOR.read_bytes()).hexdigest() != VALIDATOR_SHA256:
    raise SystemExit("CPU9 progress errno pre-trigger validator changed")


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


base = load("cpu9_mapping_fix_attempt", SOURCE)
pretrigger = load("cpu9_progress_errno_pretrigger", VALIDATOR)
progress = base.source
progress.progress_pretrigger = pretrigger
progress.source.PRE = pretrigger


def classify_progress_begin_failure(trigger: str) -> tuple[str, str]:
    normalized = trigger.replace("\r", "")
    after_begin = normalized[normalized.index(progress.source.BEGIN) +
                             len(progress.source.BEGIN):]
    observed = progress.source.fields(
        after_begin[:after_begin.index(progress.source.END)]
    )
    status, cpu9 = progress.combined_status(observed.get("post_status", ""))
    raw = dict(
        token.split("=", 1)
        for token in observed.get("post_status", "").split()[1:]
        if token.count("=") == 1
    )
    progress_ret = raw.get("cpu9_progress_ret")
    if progress_ret not in {"-74", "-117"}:
        raise progress.source.Classification(
            "CPU9-progress-errno-outside-diagnostic-result-map"
        )
    expected_cpu9 = {
        "cpu9_controller_consumed": "1",
        "cpu9_operation_ret": progress_ret,
        "cpu9_failure_stage": "7",
        "cpu9_derive_stage": "0",
        "cpu9_binder_snapshot_ret": "-11",
        "cpu9_abi": "0",
        "cpu9_lifecycle": "0",
        "cpu9_terminal": "0",
        "cpu9_last_stage": "0",
        "cpu9_stage_errno": "0",
        "cpu9_checkpoint_errno": "0",
        "cpu9_attempted": "0",
        "cpu9_membership_published": "0",
        "cpu9_cpu_requests": "0",
        "cpu9_cpu_off_requests": "0",
        "cpu9_retries": "0",
        "cpu9_retained_mask": "0x0",
    }
    if (
        not progress.source.cpu8_terminal_exact(
            status, observed.get("cpu_online")
        )
        or observed.get("cpu_online") != "0-8"
        or observed.get("cpu_offline") != "9"
        or status["operation_ret"] != progress_ret
        or status["cpu9_requests"] != "0"
        or any(cpu9[key] != value for key, value in expected_cpu9.items())
        or raw.get("cpu9_progress_stage") != "1"
    ):
        raise progress.source.Classification(
            "CPU9-progress-errno-diagnostic-failure-shape-changed"
        )
    if progress_ret == "-74":
        return (
            "cpu9-progress-cpu8-copy-crc-failure",
            "CPU8-online-progress-stage=1-ret=-74-invalid-CPU8-copy-CRCs",
        )
    return (
        "cpu9-progress-lane-header-malformed",
        "CPU8-online-progress-stage=1-ret=-117-malformed-progress-lane-header",
    )


progress.classify_progress_begin_failure = classify_progress_begin_failure


if __name__ == "__main__":
    raise SystemExit(progress.main())
