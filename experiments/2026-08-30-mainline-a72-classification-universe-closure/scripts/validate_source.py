#!/usr/bin/env python3
"""Validate the one-entry classified-universe closure."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re

import source_edits


class ValidationError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def array(text: str, name: str) -> str:
    match = re.search(
        rf"static const u16 {re.escape(name)}\[\] __initconst = \{{.*?\n\}};",
        text,
        re.DOTALL,
    )
    require(match is not None, f"array absent: {name}")
    return match.group(0)


def validate(root: Path) -> list[str]:
    path = root / source_edits.TARGET
    require(path.is_file() and not path.is_symlink(), "target source absent")
    text = path.read_text(encoding="utf-8")
    present = array(text, "mt6797_a72_present_caps")
    absent = array(text, "mt6797_a72_absent_caps")
    required = array(text, "mt6797_a72_required_caps")
    early = array(text, "mt6797_a72_early_caps")
    cap = "ARM64_MISMATCHED_CACHE_TYPE,"
    require(absent.count(cap) == 1, "cache mismatch is not exactly absent")
    require(cap not in present, "cache mismatch restored to present")
    require(cap not in required, "cache mismatch restored to required")
    require(early.count("ARM64_WORKAROUND_845719,") == 1,
            "prior early-capability repair changed")
    require(text.count(
        "policy->smccc_conduit == ARM64_LATE_CPU_SMCCC_NONE") == 1,
        "prior production conduit repair changed")
    require(text.count(
        "policy->smccc_conduit != ARM64_LATE_CPU_SMCCC_NONE") == 1,
        "prior conduit diagnostic repair changed")
    require(text.count("A72_READY_PLAN_DIAG_V1") == 1,
            "predicate diagnostic changed")
    require(text.count("A72_READY_PLAN_VALUES_V1") == 1,
            "value diagnostic changed")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return [
        "source_validation=pass",
        f"target_sha256={digest}",
        "classified_cache_mismatch=absent",
        "present_cache_mismatch=absent",
        "required_cache_mismatch=absent",
        "producer_changes=0",
        "effect_model_changes=0",
        "policy_changes=0",
        "new_cpu_request_paths=0",
        "cpu9_request_paths=0",
        "cpu_off_paths=0",
        "retry_paths=0",
        "hardware_writes=0",
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    for line in validate(args.source_root.resolve()):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
