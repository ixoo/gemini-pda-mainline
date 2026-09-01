#!/usr/bin/env python3
"""Classify one CPU9 progress raw-lane repair runtime attempt."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import sys


SOURCE_SHA256 = "14fff19f823c8bbe28cb11e941186754acf816a862be3d4f694f95c18e354b3c"
VALIDATOR_SHA256 = "3edab4c7d0f83a3323a0a6b02c939b754ac9de59c36e1f8044155059d11aa3f4"
SCRIPT = Path(__file__).resolve()
SOURCE = SCRIPT.with_name("classify-progress-errno-diagnostic-attempt.py")
VALIDATOR = SCRIPT.with_name("validate-progress-raw-lane-pretrigger.py")
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source CPU9 progress errno attempt classifier changed")
if hashlib.sha256(VALIDATOR.read_bytes()).hexdigest() != VALIDATOR_SHA256:
    raise SystemExit("CPU9 progress raw-lane pre-trigger validator changed")


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


base = load("cpu9_progress_errno_attempt", SOURCE)
pretrigger = load("cpu9_progress_raw_lane_pretrigger", VALIDATOR)
progress = base.progress
progress.progress_pretrigger = pretrigger
progress.source.PRE = pretrigger
errno_stage_one = base.classify_progress_begin_failure


def classify_progress_failure(trigger: str) -> tuple[str, str]:
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
    stage = raw.get("cpu9_progress_stage")
    progress_ret = raw.get("cpu9_progress_ret")
    if stage == "1":
        return errno_stage_one(trigger)
    if (
        stage not in {"2", "3", "4", "5", "6"}
        or progress_ret is None
        or progress_ret == "0"
        or not progress.source.cpu8_terminal_exact(
            status, observed.get("cpu_online")
        )
        or observed.get("cpu_online") != "0-8"
        or observed.get("cpu_offline") != "9"
        or status["operation_ret"] != progress_ret
        or status["cpu9_requests"] != "0"
        or cpu9["cpu9_controller_consumed"] != "1"
        or cpu9["cpu9_failure_stage"] != "7"
        or cpu9["cpu9_cpu_requests"] != "0"
        or cpu9["cpu9_cpu_off_requests"] != "0"
        or cpu9["cpu9_retries"] != "0"
        or cpu9["cpu9_attempted"] != "0"
        or cpu9["cpu9_membership_published"] != "0"
    ):
        raise progress.source.Classification(
            "CPU9-progress-raw-lane-failure-shape-changed"
        )
    names = {
        "2": "ready-token",
        "3": "derive",
        "4": "publish",
        "5": "prepare",
        "6": "add-cpu-dispatch",
    }
    return (
        f"cpu9-progress-checkpoint-failure-{names[stage]}",
        f"CPU8-online-progress-stage={stage}-ret={progress_ret}-CPU9-request-not-issued",
    )


progress.classify_progress_begin_failure = classify_progress_failure


if __name__ == "__main__":
    raise SystemExit(progress.main())
