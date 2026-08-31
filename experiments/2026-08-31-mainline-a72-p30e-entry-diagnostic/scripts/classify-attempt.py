#!/usr/bin/env python3
"""Classify one P30E entry-diagnostic CPU8 trigger on its accepted boot."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "6f2063d9254ff4d956f30faefe36481392b60011083b4980c5583a2b68ae39f5"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-31-mainline-a72-sram-p28-terminal-diagnostic"
    / "scripts/classify-attempt.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source attempt classifier changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("Classify one SRAM/P28 diagnostic CPU8 trigger on its accepted boot.", "Classify one P30E entry-diagnostic CPU8 trigger on its accepted boot.", 1),
    (
        '    "sram_sealed",\n)',
        '    "sram_sealed", "p30e_prepare_attempted", "p30e_prepare_ret",\n'
        '    "p30e_arm_attempted", "p30e_arm_ret", "p30e_armed",\n'
        '    "p30e_readback_attempted", "p30e_readback_ret",\n'
        '    "p30e_controller_state", "p30e_target_state",\n'
        '    "p30e_target_sequence", "p30e_controller_sequence",\n'
        ')',
        1,
    ),
    (
        'if result["binder_abi"] != "2" or result["sram_required"] != "0xfff":',
        'if result["binder_abi"] != "3" or result["sram_required"] != "0xfff":',
        1,
    ),
    (
        '    if (\n'
        '        ret == 0 and consumed == "1" and requests == "1"\n'
        '        and online == "0-8" and offline == "9"\n'
        '    ):\n'
        '        return "cpu8-online", f"terminal-success-and-live-cpu-list-{reason}"',
        '    if (\n'
        '        ret == 0 and consumed == "1" and requests == "1"\n'
        '        and online == "0-8" and offline == "9"\n'
        '    ):\n'
        '        success_p30e = {\n'
        '            "p30e_prepare_attempted": "1", "p30e_prepare_ret": "0",\n'
        '            "p30e_arm_attempted": "1", "p30e_arm_ret": "0",\n'
        '            "p30e_armed": "1", "p30e_readback_attempted": "0",\n'
        '        }\n'
        '        if any(status[key] != value for key, value in success_p30e.items()):\n'
        '            raise Classification("cpu8-online-P30E-prefix-mismatch")\n'
        '        return "cpu8-online", f"terminal-success-and-live-cpu-list-{reason}"',
        1,
    ),
    (
        '    if online == "0-7" and offline == "8-9" and ret != 0 and consumed == "1":\n'
        '        branch = (\n'
        '            "terminal-pre-request-error" if requests == "0"\n'
        '            else "terminal-request-bearing-error"\n'
        '        )\n'
        '        return branch, f"ret={ret}-{reason}"',
        '    if online == "0-7" and offline == "8-9" and ret != 0 and consumed == "1":\n'
        '        common = {\n'
        '            "p30e_prepare_attempted": "1", "p30e_prepare_ret": "0",\n'
        '            "p30e_arm_attempted": "1", "p30e_arm_ret": "0",\n'
        '            "p30e_armed": "1", "p30e_readback_attempted": "1",\n'
        '            "p30e_controller_state": "1", "p30e_controller_sequence": "1",\n'
        '        }\n'
        '        if requests != "1" or any(status[key] != value for key, value in common.items()):\n'
        '            raise Classification("P30E-request-prefix-or-readback-mismatch")\n'
        '        target = status["p30e_target_state"]\n'
        '        expected = {\n'
        '            "0": ("-11", "0", "p30e-armed-empty"),\n'
        '            "2": ("-11", "0", "p30e-target-claimed"),\n'
        '            "3": ("0", "1", "p30e-target-published"),\n'
        '        }\n'
        '        if target not in expected:\n'
        '            raise Classification("P30E-target-state-outside-decision-set")\n'
        '        readback_ret, sequence, branch = expected[target]\n'
        '        if status["p30e_readback_ret"] != readback_ret or status["p30e_target_sequence"] != sequence:\n'
        '            raise Classification("P30E-target-state-sequence-or-readback-mismatch")\n'
        '        return branch, f"ret={ret}-{reason}"',
        1,
    ),
    (
        '    raise Classification("terminal-status-and-cpu-list-inconsistent")',
        '    if (\n'
        '        online == "0-7" and offline == "8-9" and ret == -11\n'
        '        and consumed == "0" and requests == "0"\n'
        '        and status["trigger_consumed"] == "1"\n'
        '        and status["trigger_executions"] == "1"\n'
        '        and status["entry_trace_ret"] == "-5"\n'
        '        and status["terminal_trace_ret"] == "0"\n'
        '        and status["failure_stage"] == "0"\n'
        '        and status["derive_stage"] == "0"\n'
        '    ):\n'
        '        p30e_zero = {\n'
        '            "p30e_prepare_attempted": "0", "p30e_prepare_ret": "0",\n'
        '            "p30e_arm_attempted": "0", "p30e_arm_ret": "0",\n'
        '            "p30e_armed": "0", "p30e_readback_attempted": "0",\n'
        '            "p30e_readback_ret": "0", "p30e_controller_state": "0",\n'
        '            "p30e_target_state": "0", "p30e_target_sequence": "0",\n'
        '            "p30e_controller_sequence": "0",\n'
        '        }\n'
        '        if any(status[key] != value for key, value in p30e_zero.items()):\n'
        '            raise Classification("pre-core-EAGAIN-P30E-zero-prefix-mismatch")\n'
        '        return "terminal-ready-token-unavailable", (\n'
        '            f"ret={ret}-pre-core-zero-request-zero-P30E-{reason}"\n'
        '        )\n'
        '    raise Classification("terminal-status-and-cpu-list-inconsistent")',
        1,
    ),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe P30E attempt classifier derivation: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {"__file__": str(SCRIPT), "__name__": "_p30e_entry_classifier"}
exec(compile(text, str(SOURCE), "exec"), namespace)
globals().update({
    key: value
    for key, value in namespace.items()
    if key not in {"__builtins__", "__file__", "__name__"}
})

if __name__ == "__main__":
    raise SystemExit(namespace["main"]())
