#!/usr/bin/env python3
"""Classify one trace-softfail transcript after an accepted live frame."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import re


SCRIPT_DIR = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("pretrigger", SCRIPT_DIR / "validate-pretrigger.py")
assert SPEC is not None and SPEC.loader is not None
PRE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PRE)
BEGIN = "__GEMINI_A72_LIVE_TRIGGER_BEGIN__"
END = "__GEMINI_A72_LIVE_TRIGGER_END__"
COMMIT = ("trigger_commit=yes "
          "token_sha256=dffc3cca86392738e4b247ac21bec30474ef4b909df9cb9d3f92a9118dfa5b8f")
TERMINAL = re.compile(
    r"GEMINI_A72_ADMISSION_LIVE_V1 state=terminal trigger_consumed=1 "
    r"trigger_executions=1 operation_ret=(-?\d+) core_consumed=([01]) "
    r"entry_trace_ret=(-?\d+) terminal_trace_ret=(-?\d+) "
    r"cpu_requests=([01]) cpu9_requests=0 cpu_off_requests=0 retries=0"
)


class Classification(RuntimeError):
    """The attempt transcript is inconsistent or unattributable."""


def classify(pretrigger: str, trigger: str) -> tuple[str, str]:
    PRE.classify(pretrigger)
    if trigger.count(COMMIT) != 1:
        raise Classification("exact-trigger-commit-absent-or-duplicated")
    if trigger.count(BEGIN) != 1:
        raise Classification("trigger-begin-absent-or-duplicated")
    if trigger.count(END) == 0:
        return "trigger-boundary-transport-loss", "commit-observed-terminal-frame-absent"
    if trigger.count(END) != 1:
        raise Classification("trigger-end-duplicated")
    section = trigger[trigger.index(BEGIN) + len(BEGIN):trigger.index(END)].replace("\r", "")
    expected = {
        "pre_status": PRE.ARMED,
        "trigger_write_status": "0", "remount_ro_status": "0",
        "cpu9_request": "none", "cpu_off_request": "none",
        "retry_request": "none", "reboot_request": "none",
    }
    fields: dict[str, str] = {}
    for raw in section.splitlines():
        line = raw.strip()
        if "=" in line:
            key, value = line.split("=", 1)
            if re.fullmatch(r"[a-z0-9_]+", key):
                if key in fields:
                    raise Classification(f"duplicate-field-{key}")
                fields[key] = value
    for key, value in expected.items():
        if fields.get(key) != value:
            raise Classification(f"{key}-mismatch")
    terminal = TERMINAL.fullmatch(fields.get("post_status", ""))
    if terminal is None:
        raise Classification("terminal-status-absent-or-malformed")
    ret_text, consumed, entry_trace, terminal_trace, requests = terminal.groups()
    ret = int(ret_text)
    online, offline = fields.get("cpu_online"), fields.get("cpu_offline")
    trace_reason = f"entry-trace={entry_trace}-terminal-trace={terminal_trace}"
    if ret == 0 and consumed == "1" and requests == "1" and online == "0-8" and offline == "9":
        return "cpu8-online", f"terminal-success-and-live-cpu-list-{trace_reason}"
    if (online == "0-7" and offline == "8-9" and ret != 0 and
            (consumed, requests) in (("0", "0"), ("1", "0"), ("1", "1"))):
        return ("terminal-admission-error",
                f"ret={ret_text}-consumed={consumed}-requests={requests}-{trace_reason}")
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
