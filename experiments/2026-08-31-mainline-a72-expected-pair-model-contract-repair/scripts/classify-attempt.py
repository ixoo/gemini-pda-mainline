#!/usr/bin/env python3
"""Classify one expected-pair model-contract CPU8 trigger."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "307c43a114edff8f4566914ca820b3649d94a1b2148e6d1c9eac2f0f1a620565"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-31-mainline-a72-expected-midr-model-guard-repair"
    / "scripts/classify-attempt.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source attempt classifier changed")

namespace = {"__file__": str(SCRIPT), "__name__": "_expected_pair_classifier"}
exec(compile(SOURCE.read_text(encoding="utf-8"), str(SOURCE), "exec"), namespace)
source_classify = namespace.get("classify")
pretrigger_module = namespace.get("PRE")
pretrigger_values = getattr(pretrigger_module, "source_values", None)
if (
    not callable(source_classify)
    or pretrigger_module is None
    or not callable(getattr(pretrigger_module, "classify", None))
    or not callable(pretrigger_values)
    or hasattr(pretrigger_module, "ARMED")
):
    raise SystemExit("source attempt classifier contract changed")


def classify(pretrigger: str, trigger: str) -> tuple[str, str]:
    """Bind the inherited attempt classifier to this candidate's exact READY."""

    result, _ = pretrigger_module.classify(pretrigger)
    if result != "serviceable-armed-zero-execution":
        raise namespace["Classification"]("pretrigger-not-serviceable-armed")
    armed = pretrigger_values(pretrigger).get("live_status")
    if not isinstance(armed, str) or not armed.startswith(
        "GEMINI_A72_ADMISSION_LIVE_V1 state=armed "
    ):
        raise namespace["Classification"]("validated-live-status-absent")

    pretrigger_module.ARMED = armed
    try:
        classification, reason = source_classify(pretrigger, trigger)
    finally:
        del pretrigger_module.ARMED
    if "binder_abi=4" in reason:
        if reason.count("binder_abi=4") != 1:
            raise namespace["Classification"]("normalized-binder-ABI-ambiguous")
        reason = reason.replace("binder_abi=4", "binder_abi=5")
    return classification, reason


namespace["classify"] = classify
namespace["main"].__globals__["classify"] = classify
globals().update({
    key: value
    for key, value in namespace.items()
    if key not in {"__builtins__", "__file__", "__name__"}
})

if __name__ == "__main__":
    raise SystemExit(namespace["main"]())
