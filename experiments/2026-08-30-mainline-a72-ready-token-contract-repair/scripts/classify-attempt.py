#!/usr/bin/env python3
"""Classify the repaired READY-contract CPU8 trigger on its accepted boot."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import re


SCRIPT_DIR = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "ready_contract_pretrigger", SCRIPT_DIR / "validate-pretrigger.py"
)
assert SPEC is not None and SPEC.loader is not None
PRE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PRE)

BEGIN = "__GEMINI_A72_LIVE_TRIGGER_BEGIN__"
END = "__GEMINI_A72_LIVE_TRIGGER_END__"
TOKEN_SHA256 = "dffc3cca86392738e4b247ac21bec30474ef4b909df9cb9d3f92a9118dfa5b8f"
COMMIT = f"trigger_commit=yes\ntoken_sha256={TOKEN_SHA256}"
TERMINAL = re.compile(
    r"GEMINI_A72_ADMISSION_LIVE_V1 state=terminal trigger_consumed=1 "
    r"trigger_executions=1 operation_ret=(-?\d+) core_consumed=([01]) "
    r"entry_trace_ret=(-?\d+) terminal_trace_ret=(-?\d+) "
    r"failure_stage=(-?\d+) derive_stage=(-?\d+) "
    r"cpu_requests=([01]) cpu9_requests=0 cpu_off_requests=0 retries=0"
)


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


def classify(pretrigger: str, trigger: str) -> tuple[str, str]:
    _, pretrigger_boot_id = PRE.classify(pretrigger)
    normalized = trigger.replace("\r", "")
    if normalized.count(COMMIT) != 1:
        raise Classification("exact-trigger-commit-absent-or-duplicated")
    if normalized.count(BEGIN) != 1:
        raise Classification("trigger-begin-absent-or-duplicated")
    after_begin = normalized[normalized.index(BEGIN) + len(BEGIN):]
    observed = fields(after_begin if END not in after_begin else after_begin[:after_begin.index(END)])
    if observed.get("boot_id") != pretrigger_boot_id:
        raise Classification("trigger-boot-id-mismatch")
    if normalized.count(END) == 0:
        return "trigger-boundary-transport-loss", "boot-bound-commit-observed-terminal-frame-absent"
    if normalized.count(END) != 1:
        raise Classification("trigger-end-duplicated")
    if normalized.index(END) < normalized.index(BEGIN):
        raise Classification("trigger-boundaries-reversed")

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

    terminal = TERMINAL.fullmatch(observed.get("post_status", ""))
    if terminal is None:
        raise Classification("terminal-status-absent-or-malformed")
    (ret_text, consumed, entry_trace, terminal_trace,
     failure_stage, derive_stage, requests) = terminal.groups()
    ret = int(ret_text)
    online = observed.get("cpu_online")
    offline = observed.get("cpu_offline")
    stage_reason = (
        f"failure-stage={failure_stage}-derive-stage={derive_stage}-"
        f"entry-trace={entry_trace}-terminal-trace={terminal_trace}"
    )
    if (ret == 0 and consumed == "1" and requests == "1" and
            online == "0-8" and offline == "9"):
        return "cpu8-online", f"terminal-success-and-live-cpu-list-{stage_reason}"
    if online == "0-7" and offline == "8-9" and ret != 0 and consumed == "1":
        if requests == "0":
            return "terminal-pre-request-error", f"ret={ret_text}-{stage_reason}"
        if requests == "1":
            return "terminal-request-bearing-error", f"ret={ret_text}-{stage_reason}"
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
