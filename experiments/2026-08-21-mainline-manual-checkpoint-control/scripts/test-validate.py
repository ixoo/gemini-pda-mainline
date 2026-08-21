#!/usr/bin/env python3
"""Reject unsafe mutations of the manual-checkpoint control patch."""

from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[2]
SPEC = importlib.util.spec_from_file_location("manual_checkpoint_validator", SCRIPT_DIR / "validate.py")
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)
PATCH = ROOT / "patches/v7.1.3/0327-pstore-add-Gemini-manual-checkpoint-control.patch"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def rejected(text: str) -> bool:
    try:
        VALIDATOR.validate_patch(text)
    except AssertionError:
        return True
    return False


def main() -> None:
    original = PATCH.read_text(encoding="utf-8")
    VALIDATOR.validate_patch(original)
    mutations = (
        original.replace("-- \n2.39.5", "Signed-off-by: Synthetic <nobody@example.invalid>\n-- \n2.39.5", 1),
        original.replace("GMCP-20260821-A", "GMCP-WRONG", 1),
        original.replace("9576f05d", "00000000", 1),
        original.replace("checkpoint=manual-second", "checkpoint=manual-first", 1),
        original.replace("\tdefault n", "\tdefault y", 1),
        original.replace("depends on !MTK_MT6797_DVFSP_CLOCK_BACKEND",
                         "depends on MTK_MT6797_DVFSP_CLOCK_BACKEND", 1),
        original.replace("second = first && gemini_protected_readback_ledger_checkpoint(1);",
                         "second = gemini_protected_readback_ledger_checkpoint(1);", 1),
        original.replace("late_initcall(gemini_protected_readback_manual_control_init);",
                         "device_initcall(gemini_protected_readback_manual_control_init);", 1),
        original.replace("\treturn 0;", "\treturn -EIO;", 1),
        original.replace("+\tbool first;", "+\twritel(1, NULL);\n+\tbool first;", 1),
        original.replace("+\tbool first;", "+\tmt6797_dvfsp_clock_backend_read(NULL, NULL);\n+\tbool first;", 1),
        original.replace(
            "+\tsecond = first && gemini_protected_readback_ledger_checkpoint(1);",
            "+\tsecond = first && gemini_protected_readback_ledger_checkpoint(1);\n"
            "+\tgemini_protected_readback_ledger_checkpoint(1);",
            1,
        ),
    )
    require(all(text != original for text in mutations), "a mutation did not alter the patch")
    require(all(rejected(text) for text in mutations), "an unsafe mutation escaped")
    print("validation=mainline-manual-checkpoint-control-mutations")
    print(f"unsafe_mutations_rejected={len(mutations)}")
    print("device_access=none")
    print("hardware_write=none")
    print("result=pass")


if __name__ == "__main__":
    main()
