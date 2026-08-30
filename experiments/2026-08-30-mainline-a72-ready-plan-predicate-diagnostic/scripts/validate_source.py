#!/usr/bin/env python3
"""Validate the read-only Gemini READY-plan predicate diagnostic."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re

import source_edits


PLAN_BITS = 27
EVIDENCE_BITS = 29
RISK_TOKENS = (
    "cpu_up(",
    "cpu_down(",
    "add_cpu(",
    "remove_cpu(",
    "psci_cpu_on",
    "psci_cpu_off",
    "cpu_off(",
    "reboot",
    "retry",
    "writel(",
    "writeq(",
    "write_sysreg(",
    "regmap_write(",
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
    """Return the unique C function containing ``signature``."""
    search = 0
    definition: tuple[int, int] | None = None
    while True:
        start = text.find(signature, search)
        if start < 0:
            break
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
        if opening < len(text) and text[opening] == "{":
            require(definition is None,
                    f"multiple function definitions: {signature}")
            definition = (start, opening)
        search = start + len(signature)
    require(definition is not None, f"function body absent: {signature}")
    start, opening = definition
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start:index + 1]
    raise ValidationError(f"unterminated function: {signature}")


def enum_names(text: str, prefix: str) -> list[str]:
    return re.findall(rf"^\s*({prefix}[A-Z0-9_]+)(?:\s*=\s*\d+)?,?$", text,
                      flags=re.MULTILINE)


def validate(root: Path) -> list[str]:
    path = root / source_edits.TARGET
    require(path.is_file() and not path.is_symlink(), "target source absent")
    text = path.read_text(encoding="utf-8")

    require(text.count("enum mt6797_a72_evidence_diag_bit {") == 1,
            "evidence diagnostic schema count changed")
    require(text.count("enum mt6797_a72_plan_diag_bit {") == 1,
            "plan diagnostic schema count changed")
    require(text.count(source_edits.CONTRACT_NEW) == 1,
            "private contract definition count changed")
    require(source_edits.CONTRACT_OLD in text,
            "public validator wrapper definition absent")
    require(text.count("A72_READY_PLAN_DIAG_V1") == 1,
            "versioned diagnostic marker count changed")

    evidence = function(text, "mt6797_a72_bound_expectation_diagnostic(")
    plan = function(text, "mt6797_a72_plan_validation_diagnostic(")
    contract = function(text, "mt6797_a72_validate_cap_plan_contract(")
    wrapper = function(text, "mt6797_a72_validate_cap_plan(")
    diagnostic = evidence + plan + wrapper

    evidence_names = enum_names(text, "A72_EVD_")
    plan_names = enum_names(text, "A72_PVD_")
    require(len(evidence_names) == EVIDENCE_BITS,
            "evidence diagnostic bit count changed")
    require(len(set(evidence_names)) == EVIDENCE_BITS,
            "evidence diagnostic bit names are not unique")
    require(len(plan_names) == PLAN_BITS, "plan diagnostic bit count changed")
    require(len(set(plan_names)) == PLAN_BITS,
            "plan diagnostic bit names are not unique")
    for name in evidence_names:
        require(evidence.count(name) == 1,
                f"evidence diagnostic coverage changed: {name}")
    for name in plan_names:
        require(plan.count(name) == 1,
                f"plan diagnostic coverage changed: {name}")

    require(contract.count("A72_READY_PLAN_DIAG_V1") == 0,
            "contract owns diagnostic output")
    require(wrapper.count(
        "ret = mt6797_a72_validate_cap_plan_contract(plan);") == 1,
        "wrapper does not call the original contract exactly once")
    require(wrapper.count("if (ret)") == 1,
            "diagnostic is not guarded by contract failure")
    require(wrapper.count("return ret;") == 1,
            "wrapper does not return the original contract result")
    require(wrapper.count("return 0;") == 0,
            "wrapper bypasses the contract result")
    require(wrapper.index("if (ret)") < wrapper.index("A72_READY_PLAN_DIAG_V1")
            < wrapper.index("return ret;"),
            "failure-only diagnostic ordering changed")
    require(text.count(".validate_plan = mt6797_a72_validate_cap_plan,") == 1,
            "profile no longer uses the diagnostic-preserving wrapper")
    require(".validate_plan = mt6797_a72_validate_cap_plan_contract," not in text,
            "profile bypasses the wrapper")

    for token in RISK_TOKENS:
        require(token not in diagnostic.lower(),
                f"diagnostic contains action token: {token}")

    # The original function remains the sole decision owner.  Its full body is
    # deliberately not reimplemented here; deterministic replay from the
    # pinned parent and the exact one-name source edit provide that proof.
    require(contract.count("return -EINVAL;") >= 8,
            "contract rejection paths changed unexpectedly")
    require(contract.rstrip().endswith("return 0;\n}"),
            "contract success return changed")

    return [
        "source_validation=pass",
        f"target_sha256={sha256(path)}",
        "validator_return_owner=unchanged-contract",
        f"diagnostic_plan_bits={PLAN_BITS}",
        f"diagnostic_evidence_bits={EVIDENCE_BITS}",
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
