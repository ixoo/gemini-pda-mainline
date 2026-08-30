#!/usr/bin/env python3
"""Validate the failure-only Gemini READY-plan value observer."""

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
    wrapper = function(
        text, "static int __init\nmt6797_a72_validate_cap_plan("
    )

    require(wrapper == source_edits.NEW,
            "validator wrapper differs from the exact value observer")
    require(text.count("A72_READY_PLAN_DIAG_V1") == 1,
            "predicate marker count changed")
    require(text.count("A72_READY_PLAN_VALUES_V1") == 1,
            "value marker count changed")
    require(wrapper.count(
        "ret = mt6797_a72_validate_cap_plan_contract(plan);") == 1,
        "original contract call changed")
    require(wrapper.count("if (ret) {") == 1,
            "failure-only guard changed")
    require(wrapper.count("if (plan)") == 1,
            "plan null guard changed")
    require(wrapper.count("return ret;") == 1 and "return 0;" not in wrapper,
            "original validator return changed")
    require(wrapper.index("A72_READY_PLAN_DIAG_V1") <
            wrapper.index("A72_READY_PLAN_VALUES_V1") <
            wrapper.index("return ret;"), "diagnostic ordering changed")
    require(wrapper.count("%*pb") == 5, "bitmap field count changed")
    for field in (
        "plan->early_local_caps", "plan->target_local_caps",
        "plan->required_local_caps", "plan->target[0].local_caps",
        "plan->target[1].local_caps",
        "plan->evidence.target_policy[0].smccc_conduit",
        "plan->evidence.target_policy[1].smccc_conduit",
    ):
        require(wrapper.count(field) == 1,
                f"exact value field changed: {field}")
    require(text.count(".validate_plan = mt6797_a72_validate_cap_plan,") == 1,
            "profile no longer uses the return-preserving wrapper")
    require(".validate_plan = mt6797_a72_validate_cap_plan_contract," not in text,
            "profile bypasses the observer wrapper")
    for token in RISK_TOKENS:
        require(token not in wrapper.lower(),
                f"observer contains action token: {token}")

    return [
        "source_validation=pass",
        f"target_sha256={sha256(path)}",
        "validator_return_owner=unchanged-contract",
        "value_bitmap_fields=5",
        "value_policy_fields=2",
        "diagnostic_success_logging=none",
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
