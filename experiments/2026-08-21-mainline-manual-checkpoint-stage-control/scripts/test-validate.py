#!/usr/bin/env python3
"""Reject unsafe mutations of the manual-checkpoint live-stage patch."""

from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[2]
SPEC = importlib.util.spec_from_file_location("stage_validator", SCRIPT_DIR / "validate.py")
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)
PATCH = ROOT / "patches/v7.1.3/0328-pstore-report-Gemini-manual-checkpoint-stage.patch"


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
        original.replace("-- \n2.39.5",
                         "Signed-off-by: Synthetic <nobody@example.invalid>\n-- \n2.39.5", 1),
        original.replace("@@ -16,6 +16,13 @@", "@@ -16,6 +16,14 @@", 1),
        original.replace("\tdefault n", "\tdefault y", 1),
        original.replace(
            "depends on PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_CONTROL=y",
            "depends on PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y", 1),
        original.replace(f"#ifdef CONFIG_{VALIDATOR.MODE}", "#if 1", 1),
        original.replace("#define GEMINI_PRB_SET_STAGE(stage) ((void)(stage))",
                         "#define GEMINI_PRB_SET_STAGE(stage) (gemini_prb_stage = (stage))", 1),
        original.replace('GEMINI_PRB_SET_STAGE("dt-refused")',
                         'GEMINI_PRB_SET_STAGE("map-refused")', 1),
        original.replace('GEMINI_PRB_SET_STAGE("prefix-refused")',
                         'GEMINI_PRB_SET_STAGE("success")', 1),
        original.replace("GEMINI_MANUAL_CHECKPOINT_STAGE_V1",
                         "GEMINI_MANUAL_CHECKPOINT_STAGE_WRONG", 1),
        original.replace(
            "first, second, gemini_prb_stage, first + second, 0, 0",
            "first, second, gemini_prb_stage, first + second, 1, 0", 1),
        original.replace(
            "first, second, gemini_prb_stage, first + second, 0, 0",
            "first, second, gemini_prb_stage, first + second, 0, 1", 1),
        original.replace('+\tGEMINI_PRB_SET_STAGE("call-entry");',
                         '+\twritel(1, NULL);\n+\tGEMINI_PRB_SET_STAGE("call-entry");', 1),
        original.replace('+\tGEMINI_PRB_SET_STAGE("call-entry");',
                         '+\tcpu_up(8);\n+\tGEMINI_PRB_SET_STAGE("call-entry");', 1),
        original.replace('+\tGEMINI_PRB_SET_STAGE("call-entry");',
                         '+\tschedule_delayed_work(NULL, 1);\n'
                         '+\tGEMINI_PRB_SET_STAGE("call-entry");', 1),
    )
    require(all(text != original for text in mutations), "a mutation did not alter patch")
    escaped = [index for index, text in enumerate(mutations, 1) if not rejected(text)]
    require(not escaped, f"unsafe mutations escaped: {escaped}")
    print("validation=mainline-manual-checkpoint-stage-control-mutations")
    print(f"unsafe_mutations_rejected={len(mutations)}")
    print("device_access=none")
    print("hardware_write=none")
    print("result=pass")


if __name__ == "__main__":
    main()
