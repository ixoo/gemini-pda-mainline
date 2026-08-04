#!/usr/bin/env python3
"""Apply the finite kthread-unpark correction to the exact phase parent."""

from __future__ import annotations

import argparse
from pathlib import Path


class EditError(RuntimeError):
    pass


FIELD_PARENT = "\tint wake_result;\n"
FIELD_CHILD = "\tint unpark_issued;\n"

ACTIVATE8_PARENT = (
    '\tpr_emerg("gemini-a72-sc-phase phase=wake8-before\\n");\n'
    "\tmt6797_a72_sc_result8.wake_result =\n"
    "\t\twake_up_process(mt6797_a72_sc_task8);\n"
    '\tpr_emerg("gemini-a72-sc-phase phase=wake8-after\\n");\n'
)
ACTIVATE8_CHILD = (
    '\tpr_emerg("gemini-a72-sc-phase phase=unpark8-before\\n");\n'
    "\tkthread_unpark(mt6797_a72_sc_task8);\n"
    "\tmt6797_a72_sc_result8.unpark_issued = 1;\n"
    '\tpr_emerg("gemini-a72-sc-phase phase=unpark8-after\\n");\n'
)

ACTIVATE9_PARENT = (
    '\tpr_emerg("gemini-a72-sc-phase phase=wake9-before\\n");\n'
    "\tmt6797_a72_sc_result9.wake_result =\n"
    "\t\twake_up_process(mt6797_a72_sc_task9);\n"
    '\tpr_emerg("gemini-a72-sc-phase phase=wake9-after\\n");\n'
)
ACTIVATE9_CHILD = (
    '\tpr_emerg("gemini-a72-sc-phase phase=unpark9-before\\n");\n'
    "\tkthread_unpark(mt6797_a72_sc_task9);\n"
    "\tmt6797_a72_sc_result9.unpark_issued = 1;\n"
    '\tpr_emerg("gemini-a72-sc-phase phase=unpark9-after\\n");\n'
)

PASS_GATE_PARENT = (
    "\t\t !result9->create_error && result8->wake_result >= 0 &&\n"
    "\t\t result8->wake_result <= 1 && result9->wake_result >= 0 &&\n"
    "\t\t result9->wake_result <= 1 && result8->ready_complete == 1 &&\n"
)
PASS_GATE_CHILD = (
    "\t\t !result9->create_error && result8->unpark_issued == 1 &&\n"
    "\t\t result9->unpark_issued == 1 && result8->ready_complete == 1 &&\n"
)

TERMINAL_FIELDS_PARENT = "sc_wake8=%d sc_wake9=%d"
TERMINAL_FIELDS_CHILD = "sc_unpark8=%d sc_unpark9=%d"

TERMINAL_ARGS_PARENT = "\t\t result8->wake_result, result9->wake_result,\n"
TERMINAL_ARGS_CHILD = "\t\t result8->unpark_issued, result9->unpark_issued,\n"

TRANSFORMATIONS = (
    ("result-field", FIELD_PARENT, FIELD_CHILD),
    ("CPU8-activation", ACTIVATE8_PARENT, ACTIVATE8_CHILD),
    ("CPU9-activation", ACTIVATE9_PARENT, ACTIVATE9_CHILD),
    ("pass-gate", PASS_GATE_PARENT, PASS_GATE_CHILD),
    ("terminal-fields", TERMINAL_FIELDS_PARENT, TERMINAL_FIELDS_CHILD),
    ("terminal-arguments", TERMINAL_ARGS_PARENT, TERMINAL_ARGS_CHILD),
)


def transform_text(text: str) -> str:
    """Return the exact child text, rejecting any non-unique parent anchor."""
    transformed = text
    for name, old, new in TRANSFORMATIONS:
        old_count = transformed.count(old)
        if old_count != 1:
            raise EditError(
                f"{name}: expected one parent anchor, found {old_count}"
            )
        if new in transformed:
            raise EditError(f"{name}: child replacement already present")
        transformed = transformed.replace(old, new, 1)
    return transformed


def edit(source: Path) -> None:
    path = source / "arch/arm64/kernel/psci.c"
    original = path.read_text(encoding="utf-8")
    path.write_text(transform_text(original), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    args = parser.parse_args()
    edit(args.source)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
