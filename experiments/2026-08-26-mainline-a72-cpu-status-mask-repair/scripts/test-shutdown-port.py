#!/usr/bin/env python3
"""Test fail-closed TCP shutdown confirmation without device access."""

from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "confirm_shutdown_port", SCRIPT_DIR / "confirm-shutdown-port.py"
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def run(sequence: list[bool], required: int = 3) -> int | None:
    values = iter(sequence)
    return MODULE.wait_for_closed(
        lambda: next(values),
        attempts=len(sequence),
        required_consecutive=required,
        interval=0,
        sleep=lambda _: None,
    )


assert run([True, False, False, False]) == 4
assert run([False, False, True, False, False, False]) == 6
assert run([True, True, True, True]) is None
assert run([False, False, True, False, False]) is None

for attempts, required in ((0, 1), (2, 0), (2, 3)):
    try:
        MODULE.wait_for_closed(
            lambda: False,
            attempts=attempts,
            required_consecutive=required,
            interval=0,
            sleep=lambda _: None,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("invalid shutdown bounds accepted")

print("shutdown_sequences_accepted=2")
print("shutdown_sequences_rejected=2")
print("invalid_bounds_rejected=3")
print("required_consecutive_closures=3")
print("device_action=none")
print("result=pass")
