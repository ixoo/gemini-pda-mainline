#!/usr/bin/env python3
"""Mutation tests for the first-dmesg definition validator."""

from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PATCH = SCRIPT_DIR.parents[2] / "patches/v7.1.3/0333-pstore-qualify-Gemini-first-dmesg-raw-write.patch"
spec = importlib.util.spec_from_file_location("first_dmesg_validate", SCRIPT_DIR / "validate.py")
assert spec and spec.loader
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def main() -> None:
    original = PATCH.read_text(encoding="utf-8")
    mutations = (
        original.replace(
            "+config PSTORE_GEMINI_PROTECTED_READBACK_FIRST_DMESG_WRITE_QUALIFICATION\n"
            "+\tbool \"Gemini first dmesg raw-entry write qualification\"",
            "+config PSTORE_GEMINI_PROTECTED_READBACK_FIRST_DMESG_WRITE_QUALIFICATION\n"
            "+\tdefault y\n"
            "+\tbool \"Gemini first dmesg raw-entry write qualification\"",
            1,
        ),
        original.replace("GEMINI_PRB_LEDGER_BASE\t\tGEMINI_PRB_RESERVE_BASE",
                         "GEMINI_PRB_LEDGER_BASE\t\t0x444bf000ULL", 1),
        original.replace("GEMINI_PRB_SLOT_COUNT\t\t1",
                         "GEMINI_PRB_SLOT_COUNT\t\t2", 1),
        original.replace("GEMINI_PRB_FIRST_OWNED_SLOT\t0",
                         "GEMINI_PRB_FIRST_OWNED_SLOT\t1", 1),
        original.replace("checkpoint=manual-first slot=1", "checkpoint=manual-first slot=173", 1),
        original.replace("crc32=7785e4ce", "crc32=00000000", 1),
        original.replace("if (checkpoint != 0", "if (checkpoint > 1", 1),
        original.replace("second = false;", "second = first;", 1),
        original.replace("GEMINI_FIRST_DMESG_RAW_WRITE_QUALIFICATION_LIVE_V1",
                         "GEMINI_CHANGED", 1),
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
    print("validation=first-dmesg-raw-write-qualification-mutations")
    print(f"unsafe_mutations_rejected={rejected}")
    print("device_access=none")
    print("hardware_write=none")
    print("result=pass")


if __name__ == "__main__":
    main()
