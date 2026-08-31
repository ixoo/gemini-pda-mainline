#!/usr/bin/env python3
"""Classify the P27 diagnostic CPU8 trigger on its accepted boot."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import re


SCRIPT_DIR = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "p27_diagnostic_pretrigger", SCRIPT_DIR / "validate-pretrigger.py"
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
    r"cpu_requests=([01]) cpu9_requests=0 cpu_off_requests=0 retries=0 "
    r"binder_snapshot_ret=(-?\d+) binder_abi=(\d+) lifecycle=(\d+) "
    r"terminal=(\d+) last_stage=(\d+) stage_errno=(-?\d+) "
    r"rollback_errno=(-?\d+) checkpoint_errno=(-?\d+) attempted=([01]) "
    r"watchdog_armed=([01]) p27_owned=([01]) rollback_mask=(0x[0-9a-f]+) "
    r"retained_mask=(0x[0-9a-f]+) p27a_op=(\d+) p27a_error=(-?\d+) "
    r"p27a_attempted=(0x[0-9a-f]+) p27a_completed=(0x[0-9a-f]+) "
    r"p27a_spm_before=(0x[0-9a-f]+) p27a_spm_after=(0x[0-9a-f]+) "
    r"p27a_bpll=(0x[0-9a-f]+) p27a_owned=([01]) p27a_sealed=([01]) "
    r"p27r_op=(\d+) p27r_error=(-?\d+) p27r_attempted=(0x[0-9a-f]+) "
    r"p27r_completed=(0x[0-9a-f]+) p27r_spm_before=(0x[0-9a-f]+) "
    r"p27r_spm_after=(0x[0-9a-f]+) p27r_bpll=(0x[0-9a-f]+) "
    r"p27r_owned=([01]) p27r_sealed=([01])"
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

    terminal = TERMINAL.fullmatch(observed.get("post_status", ""))
    if terminal is None:
        raise Classification("terminal-status-absent-or-malformed")
    values = terminal.groups()
    ret = int(values[0])
    consumed = values[1]
    requests = values[6]
    diagnostic = (
        f"binder-ret={values[7]}-abi={values[8]}-lifecycle={values[9]}-"
        f"terminal={values[10]}-stage={values[11]}-stage-errno={values[12]}-"
        f"rollback-errno={values[13]}-checkpoint-errno={values[14]}-"
        f"attempted={values[15]}-watchdog={values[16]}-p27-owned={values[17]}-"
        f"rollback-mask={values[18]}-retained-mask={values[19]}-"
        f"p27a-op={values[20]}-p27a-error={values[21]}-"
        f"p27a-attempted={values[22]}-p27a-completed={values[23]}-"
        f"p27a-spm={values[24]}:{values[25]}-p27a-bpll={values[26]}-"
        f"p27a-owned={values[27]}-p27a-sealed={values[28]}-"
        f"p27r-op={values[29]}-p27r-error={values[30]}-"
        f"p27r-attempted={values[31]}-p27r-completed={values[32]}-"
        f"p27r-spm={values[33]}:{values[34]}-p27r-bpll={values[35]}-"
        f"p27r-owned={values[36]}-p27r-sealed={values[37]}"
    )
    stage_reason = (
        f"failure-stage={values[4]}-derive-stage={values[5]}-"
        f"entry-trace={values[2]}-terminal-trace={values[3]}-{diagnostic}"
    )
    online = observed.get("cpu_online")
    offline = observed.get("cpu_offline")
    if (ret == 0 and consumed == "1" and requests == "1" and
            online == "0-8" and offline == "9"):
        return "cpu8-online", f"terminal-success-and-live-cpu-list-{stage_reason}"
    if online == "0-7" and offline == "8-9" and ret != 0 and consumed == "1":
        branch = "terminal-pre-request-error" if requests == "0" else "terminal-request-bearing-error"
        return branch, f"ret={ret}-{stage_reason}"
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
