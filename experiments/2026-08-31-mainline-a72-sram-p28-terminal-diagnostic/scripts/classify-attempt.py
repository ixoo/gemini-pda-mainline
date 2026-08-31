#!/usr/bin/env python3
"""Classify one SRAM/P28 diagnostic CPU8 trigger on its accepted boot."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import re


SCRIPT_DIR = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "sram_p28_diagnostic_pretrigger", SCRIPT_DIR / "validate-pretrigger.py"
)
assert SPEC is not None and SPEC.loader is not None
PRE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PRE)

BEGIN = "__GEMINI_A72_LIVE_TRIGGER_BEGIN__"
END = "__GEMINI_A72_LIVE_TRIGGER_END__"
TOKEN_SHA256 = "dffc3cca86392738e4b247ac21bec30474ef4b909df9cb9d3f92a9118dfa5b8f"
COMMIT = f"trigger_commit=yes\ntoken_sha256={TOKEN_SHA256}"
STATUS_PREFIX = "GEMINI_A72_ADMISSION_LIVE_V1"
STATUS_KEYS = (
    "state", "trigger_consumed", "trigger_executions", "operation_ret",
    "core_consumed", "entry_trace_ret", "terminal_trace_ret",
    "failure_stage", "derive_stage", "cpu_requests", "cpu9_requests",
    "cpu_off_requests", "retries", "binder_snapshot_ret", "binder_abi",
    "lifecycle", "terminal", "last_stage", "stage_errno",
    "rollback_errno", "checkpoint_errno", "attempted", "watchdog_armed",
    "p27_owned", "rollback_mask", "retained_mask", "p27a_op",
    "p27a_error", "p27a_attempted", "p27a_completed", "p27a_spm_before",
    "p27a_spm_after", "p27a_bpll", "p27a_owned", "p27a_sealed",
    "p27r_op", "p27r_error", "p27r_attempted", "p27r_completed",
    "p27r_spm_before", "p27r_spm_after", "p27r_bpll", "p27r_owned",
    "p27r_sealed", "p28_begin_attempted", "p28_begin_ret", "p28_begun",
    "sram_returned", "sram_ret", "sram_match", "sram_required",
    "p28_complete_attempted", "p28_complete_ret", "sram_abi",
    "sram_attempted", "sram_completed", "sram_mv",
    "sram_selector_first", "sram_calibration_first",
    "sram_selector_second", "sram_calibration_second", "sram_attempt_id",
    "sram_cookie", "sram_error", "sram_effect_attempted", "sram_verified",
    "sram_sealed",
)
HEX_KEYS = {
    "rollback_mask", "retained_mask", "p27a_attempted", "p27a_completed",
    "p27a_spm_before", "p27a_spm_after", "p27a_bpll", "p27r_attempted",
    "p27r_completed", "p27r_spm_before", "p27r_spm_after", "p27r_bpll",
    "sram_match", "sram_required", "sram_attempted", "sram_completed",
    "sram_selector_first", "sram_calibration_first", "sram_selector_second",
    "sram_calibration_second",
}


class Classification(RuntimeError):
    """The attempt transcript is inconsistent or unattributable."""


def fields(section: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in section.replace("\r", "").splitlines():
        line = raw.strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if not re.fullmatch(r"[a-z0-9_]+", key):
            continue
        if key in result:
            raise Classification(f"duplicate-field-{key}")
        result[key] = value
    return result


def terminal_fields(status: str) -> dict[str, str]:
    tokens = status.split()
    if not tokens or tokens[0] != STATUS_PREFIX:
        raise Classification("terminal-status-prefix-mismatch")
    pairs: list[tuple[str, str]] = []
    for token in tokens[1:]:
        if token.count("=") != 1:
            raise Classification("terminal-status-token-malformed")
        pairs.append(tuple(token.split("=", 1)))
    if tuple(key for key, _ in pairs) != STATUS_KEYS:
        raise Classification("terminal-status-field-inventory-or-order-changed")
    result = dict(pairs)
    for key, value in result.items():
        pattern = r"0x[0-9a-f]+" if key in HEX_KEYS else r"-?\d+"
        if key == "state":
            if value != "terminal":
                raise Classification("terminal-state-mismatch")
        elif re.fullmatch(pattern, value) is None:
            raise Classification(f"terminal-field-malformed-{key}")
    if result["binder_abi"] != "2" or result["sram_required"] != "0xfff":
        raise Classification("terminal-diagnostic-abi-or-required-mask-mismatch")
    for key in ("cpu9_requests", "cpu_off_requests", "retries"):
        if result[key] != "0":
            raise Classification(f"terminal-{key}-nonzero")
    return result


def classify(pretrigger: str, trigger: str) -> tuple[str, str]:
    _, pretrigger_boot_id = PRE.classify(pretrigger)
    normalized = trigger.replace("\r", "")
    if normalized.count(COMMIT) != 1:
        raise Classification("exact-trigger-commit-absent-or-duplicated")
    if normalized.count(BEGIN) != 1:
        raise Classification("trigger-begin-absent-or-duplicated")
    after_begin = normalized[normalized.index(BEGIN) + len(BEGIN):]
    observed = fields(
        after_begin if END not in after_begin else after_begin[:after_begin.index(END)]
    )
    if observed.get("boot_id") != pretrigger_boot_id:
        raise Classification("trigger-boot-id-mismatch")
    if normalized.count(END) == 0:
        return (
            "trigger-boundary-transport-loss",
            "boot-bound-commit-observed-terminal-frame-absent",
        )
    if normalized.count(END) != 1 or normalized.index(END) < normalized.index(BEGIN):
        raise Classification("trigger-boundaries-invalid")

    expected = {
        "boot_id": pretrigger_boot_id,
        "pre_status": PRE.ARMED,
        "trigger_commit": "yes",
        "token_sha256": TOKEN_SHA256,
        "trigger_write_status": "0",
        "remount_ro_status": "0",
        "cpu9_request": "none",
        "cpu_off_request": "none",
        "retry_request": "none",
        "reboot_request": "none",
    }
    for key, value in expected.items():
        if observed.get(key) != value:
            raise Classification(f"{key}-mismatch")

    status = terminal_fields(observed.get("post_status", ""))
    reason = "-".join(f"{key}={status[key]}" for key in STATUS_KEYS)
    ret = int(status["operation_ret"])
    consumed = status["core_consumed"]
    requests = status["cpu_requests"]
    online = observed.get("cpu_online")
    offline = observed.get("cpu_offline")
    if (
        ret == 0 and consumed == "1" and requests == "1"
        and online == "0-8" and offline == "9"
    ):
        return "cpu8-online", f"terminal-success-and-live-cpu-list-{reason}"
    if online == "0-7" and offline == "8-9" and ret != 0 and consumed == "1":
        branch = (
            "terminal-pre-request-error" if requests == "0"
            else "terminal-request-bearing-error"
        )
        return branch, f"ret={ret}-{reason}"
    raise Classification("terminal-status-and-cpu-list-inconsistent")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pretrigger", type=Path, required=True)
    parser.add_argument("--trigger", type=Path, required=True)
    args = parser.parse_args()
    try:
        result, reason = classify(
            args.pretrigger.read_text(encoding="utf-8", errors="replace"),
            args.trigger.read_text(encoding="utf-8", errors="replace"),
        )
    except (Classification, PRE.Classification) as error:
        result, reason = "rejected", str(error)
    print(f"runtime_classification={result}")
    print(f"runtime_reason={reason}")
    print("trigger_attempts=1" if result != "rejected" else "trigger_attempts=unknown")
    print("cpu9_requests=0")
    print("cpu_off_requests=0")
    print("retries=0")
    print("native_reboot_requested=no")
    return 0 if result != "rejected" else 3


if __name__ == "__main__":
    raise SystemExit(main())
