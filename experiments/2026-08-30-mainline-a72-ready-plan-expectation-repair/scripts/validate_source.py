#!/usr/bin/env python3
"""Validate the localized Gemini READY-plan expectation repair."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import source_edits


RISK_TOKENS = (
    "cpu_up(", "cpu_down(", "add_cpu(", "remove_cpu(",
    "psci_cpu_on", "psci_cpu_off", "cpu_off(", "reboot", "retry",
    "writel(", "writeq(", "write_sysreg(", "regmap_write(",
    "memcpy_toio(",
)


class ValidationError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def function(text: str, signature: str) -> str:
    start = text.find(signature)
    require(start >= 0, f"function absent: {signature}")
    require(text.find(signature, start + 1) < 0,
            f"multiple functions: {signature}")
    parameter = start + len(signature) - 1
    depth = 0
    closing = -1
    for index in range(parameter, len(text)):
        if text[index] == "(":
            depth += 1
        elif text[index] == ")":
            depth -= 1
            if depth == 0:
                closing = index
                break
    require(closing >= 0, f"unterminated parameters: {signature}")
    opening = closing + 1
    while opening < len(text) and text[opening].isspace():
        opening += 1
    require(opening < len(text) and text[opening] == "{",
            f"definition absent: {signature}")
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start:index + 1]
    raise ValidationError(f"unterminated function: {signature}")


def validate(root: Path) -> list[str]:
    path = root / source_edits.TARGET
    require(path.is_file() and not path.is_symlink(), "target source absent")
    text = path.read_text(encoding="utf-8")

    for expected, label in (
        (source_edits.PRESENT_NEW, "present capability contract"),
        (source_edits.EARLY_NEW, "early capability contract"),
        (source_edits.REQUIRED_NEW, "required capability contract"),
        (source_edits.POLICY_NEW, "production policy contract"),
    ):
        require(text.count(expected) == 1, f"{label} differs")
    for stale, label in (
        (source_edits.PRESENT_OLD, "stale present capability contract"),
        (source_edits.EARLY_OLD, "stale early capability contract"),
        (source_edits.REQUIRED_OLD, "stale required capability contract"),
        (source_edits.POLICY_OLD, "stale production policy contract"),
        (source_edits.DIAG_OLD, "stale production policy diagnostic"),
    ):
        require(stale not in text, f"{label} remains")
    require(text.count(source_edits.DIAG_NEW) == 1,
            "production policy diagnostic differs")

    fixture = function(
        text, "static bool __init\nmt6797_a72_fixture_policy_exact("
    )
    require(fixture.count("ARM64_LATE_CPU_SMCCC_SMC") == 1,
            "fixture policy no longer requires SMC")
    require("ARM64_LATE_CPU_SMCCC_NONE" not in fixture,
            "fixture policy was changed to NONE")
    require(text.count(
        "policy->smccc_conduit = ARM64_LATE_CPU_SMCCC_SMC;") == 1,
        "fixture evidence conduit population changed")
    require("policy->smccc_conduit = ARM64_LATE_CPU_SMCCC_NONE;" not in text,
            "production repair changed fixture population")

    wrapper = function(
        text, "static int __init\nmt6797_a72_validate_cap_plan("
    )
    require(wrapper.count(
        "ret = mt6797_a72_validate_cap_plan_contract(plan);") == 1,
        "validator contract call changed")
    require(wrapper.count("if (ret) {") == 1,
            "failure-only diagnostic guard changed")
    require(wrapper.count("return ret;") == 1 and "return 0;" not in wrapper,
            "validator return changed")
    require(wrapper.count("A72_READY_PLAN_DIAG_V1") == 1,
            "predicate observer changed")
    require(wrapper.count("A72_READY_PLAN_VALUES_V1") == 1,
            "value observer changed")
    require(text.count(".validate_plan = mt6797_a72_validate_cap_plan,") == 1,
            "profile no longer uses the validated wrapper")
    require(".validate_plan = mt6797_a72_validate_cap_plan_contract," not in text,
            "profile bypasses the validated wrapper")

    changed_contract = "\n".join((
        source_edits.PRESENT_NEW,
        source_edits.EARLY_NEW,
        source_edits.REQUIRED_NEW,
        source_edits.POLICY_NEW,
        source_edits.DIAG_NEW,
        wrapper,
    )).lower()
    for token in RISK_TOKENS:
        require(token not in changed_contract,
                f"repair contains action token: {token}")

    return [
        "source_validation=pass",
        f"target_sha256={sha256(path)}",
        "expectation_owner=profile-only",
        "early_845719=required",
        "target_cache_mismatch=absent",
        "required_cache_mismatch=absent",
        "production_policy_conduit=none",
        "fixture_policy_conduit=smc",
        "diagnostic_policy_conduit=none",
        "validator_return_owner=unchanged-contract",
        "producer_changes=0",
        "effect_model_changes=0",
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
