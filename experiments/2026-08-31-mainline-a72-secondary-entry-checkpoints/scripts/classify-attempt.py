#!/usr/bin/env python3
"""Classify one checkpoint-instrumented P30E CPU8 trigger."""

from __future__ import annotations

import hashlib
from pathlib import Path
import re


SOURCE_SHA256 = "a361c6cc3a7379c26fa044b23d46608ce6d5936f3dd4be1f72a7d0f3d497ceb2"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-31-mainline-a72-p30e-entry-diagnostic"
    / "scripts/classify-attempt.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source P30E attempt classifier changed")

namespace = {"__file__": str(SCRIPT), "__name__": "_checkpoint_classifier"}
exec(compile(SOURCE.read_text(encoding="utf-8"), str(SOURCE), "exec"), namespace)

keys = list(namespace["STATUS_KEYS"])
target_index = keys.index("p30e_target_state")
if "p30e_target_reason" in keys:
    raise SystemExit("source classifier already gained a target reason")
keys.insert(target_index + 1, "p30e_target_reason")
namespace["STATUS_KEYS"] = tuple(keys)

source_terminal_fields = namespace["terminal_fields"]
source_terminal_fields.__globals__["STATUS_KEYS"] = tuple(keys)


def terminal_fields(status: str) -> dict[str, str]:
    if status.count("binder_abi=4") != 1 or "binder_abi=3" in status:
        raise namespace["Classification"]("terminal-diagnostic-ABI-4-mismatch")
    result = source_terminal_fields(status.replace("binder_abi=4", "binder_abi=3", 1))
    result["binder_abi"] = "4"
    return result


namespace["terminal_fields"] = terminal_fields
source_classify = namespace["classify"]
source_classify.__globals__["terminal_fields"] = terminal_fields
source_classify.__globals__["STATUS_KEYS"] = tuple(keys)


def classify(pretrigger: str, trigger: str) -> tuple[str, str]:
    result, reason = source_classify(pretrigger, trigger)
    match = re.search(r"(?:^|-)p30e_target_reason=(-?\d+)(?:-|$)", reason)
    if match is None:
        raise namespace["Classification"]("P30E-target-reason-absent")
    checkpoint = int(match.group(1))
    if result == "p30e-target-claimed":
        if checkpoint < 0 or checkpoint > 7:
            raise namespace["Classification"]("P30E-claimed-checkpoint-out-of-range")
        result = f"p30e-target-claimed-checkpoint-{checkpoint}"
    elif result in {
        "p30e-armed-empty", "terminal-ready-token-unavailable", "cpu8-online"
    } and checkpoint != 0:
        raise namespace["Classification"]("P30E-non-readback-reason-nonzero")
    return result, reason


namespace["classify"] = classify
namespace["main"].__globals__["classify"] = classify
globals().update({
    key: value
    for key, value in namespace.items()
    if key not in {"__builtins__", "__file__", "__name__"}
})

if __name__ == "__main__":
    raise SystemExit(namespace["main"]())
