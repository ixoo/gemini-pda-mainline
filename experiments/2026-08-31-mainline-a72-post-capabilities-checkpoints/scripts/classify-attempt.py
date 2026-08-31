#!/usr/bin/env python3
"""Classify one post-capabilities P30E CPU8 trigger."""

from __future__ import annotations

import hashlib
from pathlib import Path
import re


SOURCE_SHA256 = "39866fc11d957c4e1d2cb9f7e2f58f6ca6659793896a30f23cbfb3a383c9589b"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT
    / "experiments/2026-08-31-mainline-a72-secondary-entry-checkpoints"
    / "scripts/classify-attempt.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source checkpoint attempt classifier changed")

namespace = {"__file__": str(SCRIPT), "__name__": "_postcap_classifier"}
exec(compile(SOURCE.read_text(encoding="utf-8"), str(SOURCE), "exec"), namespace)

old_keys = tuple(namespace["STATUS_KEYS"])
reason_index = old_keys.index("p30e_target_reason")
detail_keys = (
    "p30e_target_effects", "p30e_target_entry_pc", "p30e_target_entry_sp",
)
POSTCAP_STATUS_KEYS = (
    old_keys[:reason_index + 1] + detail_keys + old_keys[reason_index + 1:]
)
POSTCAP_KNOWN_EFFECTS = (
    ((1 << 26) - 1) | (1 << 61) | (1 << 62) | (1 << 63)
)
POSTCAP_SOURCE_TERMINAL_FIELDS = namespace["terminal_fields"]


def terminal_fields(status: str) -> dict[str, str]:
    tokens = status.split()
    if not tokens or tokens[0] != namespace["STATUS_PREFIX"]:
        raise namespace["Classification"]("terminal-status-prefix-mismatch")
    pairs = []
    for token in tokens[1:]:
        if token.count("=") != 1:
            raise namespace["Classification"]("terminal-status-token-malformed")
        pairs.append(tuple(token.split("=", 1)))
    if tuple(key for key, _ in pairs) != POSTCAP_STATUS_KEYS:
        raise namespace["Classification"](
            "terminal-status-field-inventory-or-order-changed"
        )
    values = dict(pairs)
    if values["binder_abi"] != "5":
        raise namespace["Classification"]("terminal-diagnostic-ABI-5-mismatch")
    for key in detail_keys:
        if re.fullmatch(r"0x[0-9a-f]+", values[key]) is None:
            raise namespace["Classification"](f"terminal-field-malformed-{key}")

    legacy_tokens = [tokens[0]]
    for key, value in pairs:
        if key in detail_keys:
            continue
        if key == "binder_abi":
            value = "4"
        legacy_tokens.append(f"{key}={value}")
    result = POSTCAP_SOURCE_TERMINAL_FIELDS(" ".join(legacy_tokens))
    result.update({key: values[key] for key in detail_keys})

    checkpoint = int(result["p30e_target_reason"])
    effects = int(result["p30e_target_effects"], 16)
    entry_pc = int(result["p30e_target_entry_pc"], 16)
    entry_sp = int(result["p30e_target_entry_sp"], 16)
    if checkpoint == 8:
        if effects == 0 or effects & ~POSTCAP_KNOWN_EFFECTS:
            raise namespace["Classification"](
                "P30E-expectation-failure-effects-invalid"
            )
    elif effects or entry_pc or entry_sp:
        raise namespace["Classification"]("P30E-non-failure-detail-nonzero")
    return result


namespace["terminal_fields"] = terminal_fields
POSTCAP_SOURCE_CLASSIFY = namespace.get("source_classify")
if not callable(POSTCAP_SOURCE_CLASSIFY):
    raise SystemExit("source pre-checkpoint classifier changed")
POSTCAP_SOURCE_CLASSIFY.__globals__["terminal_fields"] = terminal_fields


def classify(pretrigger: str, trigger: str) -> tuple[str, str]:
    result, reason = POSTCAP_SOURCE_CLASSIFY(pretrigger, trigger)
    normalized = trigger.replace("\r", "")
    after_begin = normalized[
        normalized.index(namespace["BEGIN"]) + len(namespace["BEGIN"]):
    ]
    observed = namespace["fields"](
        after_begin[:after_begin.index(namespace["END"])]
    )
    status = terminal_fields(observed.get("post_status", ""))
    reason += "-" + "-".join(
        f"{key}={status[key]}" for key in detail_keys
    )
    match = re.search(r"(?:^|-)p30e_target_reason=(-?\d+)(?:-|$)", reason)
    if match is None:
        raise namespace["Classification"]("P30E-target-reason-absent")
    checkpoint = int(match.group(1))
    if result == "p30e-target-claimed":
        if checkpoint < 0 or checkpoint > 11:
            raise namespace["Classification"](
                "P30E-claimed-checkpoint-out-of-range"
            )
        result = f"p30e-target-claimed-checkpoint-{checkpoint}"
    elif checkpoint != 0:
        raise namespace["Classification"]("P30E-non-claimed-reason-nonzero")
    return result, reason


namespace["classify"] = classify
namespace["main"].__globals__["classify"] = classify
globals().update({
    key: value
    for key, value in namespace.items()
    if key not in {"__builtins__", "__file__", "__name__"}
})
STATUS_KEYS = POSTCAP_STATUS_KEYS

if __name__ == "__main__":
    raise SystemExit(namespace["main"]())
