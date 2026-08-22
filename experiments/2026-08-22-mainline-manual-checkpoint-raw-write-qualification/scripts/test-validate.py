#!/usr/bin/env python3
"""Mutation tests for the manual raw-entry write definition validator."""

from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PATCH = SCRIPT_DIR.parents[2] / "patches/v7.1.3/0332-pstore-qualify-Gemini-manual-raw-entry-write.patch"
spec = importlib.util.spec_from_file_location("raw_write_validate", SCRIPT_DIR / "validate.py")
assert spec and spec.loader
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def main() -> None:
    original = PATCH.read_text(encoding="utf-8")
    mutations = (
        original.replace("default n", "default y", 1),
        original.replace("readl(slot) == ~0U", "readl(slot) == 0", 1),
        original.replace("checkpoint != 0", "checkpoint > 1", 1),
        original.replace("second = false;", "second = first;", 1),
        original.replace("writel(GEMINI_PRB_SIGNATURE, slot);", "", 1),
        original.replace("GEMINI_MANUAL_RAW_WRITE_QUALIFICATION_LIVE_V1", "GEMINI_CHANGED", 1),
        original.replace("first, gemini_prb_stage, first, 0, 0, 0, 0", "first, gemini_prb_stage, first, 1, 0, 0, 0", 1),
        original + "\n+\tmt6797_dvfsp_clock_backend_read(dev, &record);\n",
        original + "\n+\tmt6797_bigidvfs_backend_read(dev, &record);\n",
        original + "\n+\tpsci_ops.cpu_on(8, 0);\n",
        original + "\n+\tregulator_enable(regulator);\n",
        original + "\nSigned-off-by: Synthetic <synthetic@example.invalid>\n",
    )
    rejected = 0
    for mutation in mutations:
        try:
            validator.validate_patch_text(mutation)
        except AssertionError:
            rejected += 1
    if rejected != len(mutations):
        raise AssertionError(f"rejected {rejected} of {len(mutations)} unsafe mutations")
    print("validation=manual-checkpoint-raw-write-qualification-mutations")
    print(f"unsafe_mutations_rejected={rejected}")
    print("device_access=none")
    print("hardware_write=none")
    print("result=pass")


if __name__ == "__main__":
    main()
