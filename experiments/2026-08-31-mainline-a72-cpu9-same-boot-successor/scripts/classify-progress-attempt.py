#!/usr/bin/env python3
"""Classify one live CPU9 attempt with progress-ledger status fields."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
from pathlib import Path
import re
import sys


SOURCE_SHA256 = "897c32656a5a66587fc0e74b30e90c2f7a384e15007e497bd970a8b24e860d38"
VALIDATOR_SHA256 = "4ad80105fd840ea02ca57c3dff1dd9fbe10b81047d06169b3981f4caa130867e"
SCRIPT = Path(__file__).resolve()
SOURCE = SCRIPT.with_name("classify-attempt.py")
VALIDATOR = SCRIPT.with_name("validate-progress-pretrigger.py")
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source CPU9 attempt classifier changed")
if hashlib.sha256(VALIDATOR.read_bytes()).hexdigest() != VALIDATOR_SHA256:
    raise SystemExit("CPU9 progress pre-trigger validator changed")


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


source = load("cpu9_parent_attempt", SOURCE)
progress_pretrigger = load("cpu9_progress_pretrigger", VALIDATOR)
parent_combined_status = source.combined_status
PROGRESS_KEYS = ("cpu9_progress_stage", "cpu9_progress_ret")


def combined_status(status: str):
    tokens = status.split()
    if not tokens or tokens[0] != source.STATUS_PREFIX:
        raise source.Classification("terminal-status-prefix-mismatch")
    pairs = []
    for token in tokens[1:]:
        if token.count("=") != 1:
            raise source.Classification("terminal-status-token-malformed")
        pairs.append(tuple(token.split("=", 1)))
    expected_cpu9 = (
        source.CPU9_STATUS_KEYS[:4]
        + PROGRESS_KEYS
        + source.CPU9_STATUS_KEYS[4:]
    )
    expected = tuple(source.source.STATUS_KEYS) + expected_cpu9
    if tuple(key for key, _ in pairs) != expected:
        raise source.Classification("terminal-progress-status-field-inventory-changed")
    values = dict(pairs)
    if re.fullmatch(r"(?:[0-9]|10)", values["cpu9_progress_stage"]) is None:
        raise source.Classification("terminal-progress-stage-malformed")
    if re.fullmatch(r"-?\d+", values["cpu9_progress_ret"]) is None:
        raise source.Classification("terminal-progress-result-malformed")
    normalized = [
        f"{key}={value}" for key, value in pairs if key not in PROGRESS_KEYS
    ]
    return parent_combined_status(source.STATUS_PREFIX + " " + " ".join(normalized))


source.PRE = progress_pretrigger
source.combined_status = combined_status


def progress_fields(trigger: str) -> tuple[str, str]:
    normalized = trigger.replace("\r", "")
    if source.END not in normalized or source.BEGIN not in normalized:
        return "unavailable", "unavailable"
    after_begin = normalized[normalized.index(source.BEGIN) + len(source.BEGIN):]
    observed = source.fields(after_begin[: after_begin.index(source.END)])
    status = observed.get("post_status", "")
    values = dict(
        token.split("=", 1) for token in status.split()[1:] if token.count("=") == 1
    )
    return (
        values.get("cpu9_progress_stage", "unavailable"),
        values.get("cpu9_progress_ret", "unavailable"),
    )


def classify_progress_begin_failure(trigger: str) -> tuple[str, str]:
    normalized = trigger.replace("\r", "")
    after_begin = normalized[normalized.index(source.BEGIN) + len(source.BEGIN):]
    observed = source.fields(after_begin[: after_begin.index(source.END)])
    status, cpu9 = combined_status(observed.get("post_status", ""))
    raw = dict(
        token.split("=", 1)
        for token in observed.get("post_status", "").split()[1:]
        if token.count("=") == 1
    )
    expected_cpu9 = {
        "cpu9_controller_consumed": "1",
        "cpu9_operation_ret": "-74",
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
        not source.cpu8_terminal_exact(status, observed.get("cpu_online"))
        or observed.get("cpu_online") != "0-8"
        or observed.get("cpu_offline") != "9"
        or status["operation_ret"] != "-74"
        or status["cpu9_requests"] != "0"
        or any(cpu9[key] != value for key, value in expected_cpu9.items())
        or raw.get("cpu9_progress_stage") != "1"
        or raw.get("cpu9_progress_ret") != "-74"
    ):
        raise source.Classification("CPU9-progress-begin-failure-shape-changed")
    return (
        "cpu9-progress-begin-failure",
        "CPU8-online-progress-stage=1-ret=-74-CPU9-request-not-issued",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pretrigger", type=Path, required=True)
    parser.add_argument("--trigger", type=Path, required=True)
    args = parser.parse_args()
    pretrigger = args.pretrigger.read_text(encoding="utf-8", errors="replace")
    trigger = args.trigger.read_text(encoding="utf-8", errors="replace")
    try:
        try:
            result, reason = source.classify(pretrigger, trigger)
        except source.Classification as error:
            if str(error) != "CPU9-pre-request-result-inconsistent":
                raise
            result, reason = classify_progress_begin_failure(trigger)
        stage, progress_ret = progress_fields(trigger)
        if result == "cpu8-cpu9-online-accounting-advanced" and (
            stage != "10" or progress_ret != "0"
        ):
            raise source.Classification("CPU9-success-without-progress-return-proof")
    except (source.Classification, progress_pretrigger.Classification) as error:
        result, reason = "rejected", str(error)
        stage, progress_ret = "unknown", "unknown"
    print(f"runtime_classification={result}")
    print(f"runtime_reason={reason}")
    print(f"cpu9_progress_stage={stage}")
    print(f"cpu9_progress_ret={progress_ret}")
    print("trigger_attempts=1" if result != "rejected" else "trigger_attempts=unknown")
    print("cpu8_request_maximum=1")
    print("cpu9_request_maximum=1")
    print("cpu_off_requests=0")
    print("retries=0")
    print("native_reboot_requested=no")
    return 0 if result != "rejected" else 3


if __name__ == "__main__":
    raise SystemExit(main())
