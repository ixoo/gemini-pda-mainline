#!/usr/bin/env python3
"""Mutation tests for the first-dmesg clock-entry definition validator."""

from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PATCH = SCRIPT_DIR.parents[2] / "patches/v7.1.3/0334-pstore-qualify-Gemini-clock-entry-in-first-dmesg.patch"
spec = importlib.util.spec_from_file_location("clock_first_dmesg_validate",
                                              SCRIPT_DIR / "validate.py")
assert spec and spec.loader
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def main() -> None:
    original = PATCH.read_text(encoding="utf-8")
    mutations = (
        original.replace("+\tdefault n\n", "+\tdefault y\n", 1),
        original.replace("GEMINI_PRB_LEDGER_BASE\t\tGEMINI_PRB_RESERVE_BASE",
                         "GEMINI_PRB_LEDGER_BASE\t\t0x444bf000ULL", 1),
        original.replace("GEMINI_PRB_SLOT_COUNT\t\t2",
                         "GEMINI_PRB_SLOT_COUNT\t\t3", 1),
        original.replace("GEMINI_PRB_FIRST_OWNED_SLOT\t0",
                         "GEMINI_PRB_FIRST_OWNED_SLOT\t1", 1),
        original.replace("checkpoint=driver-init slot=1",
                         "checkpoint=driver-init slot=173", 1),
        original.replace("checkpoint=probe-enter slot=2",
                         "checkpoint=probe-enter slot=174", 1),
        original.replace("crc32=6197fd57", "crc32=00000000", 1),
        original.replace("crc32=61636940", "crc32=00000000", 1),
        original.replace("stage=probe-complete writes=2",
                         "stage=probe-complete writes=3", 1),
        original.replace("protected=0 bigidvfs=0 cpu=0",
                         "protected=1 bigidvfs=0 cpu=0", 1),
        original + "\n+\tmt6797_dvfsp_clock_backend_read(dev, &record);\n",
        original + "\n+\tmt6797_bigidvfs_backend_read(dev, &record);\n",
        original + "\n+\tclk_prepare_enable(backend->clk);\n",
        original + "\n+\twritel(value, backend->base);\n",
        original + "\n+\tpsci_ops.cpu_on(8, 0);\n",
        original + "\nSigned-off-by: Synthetic <synthetic@example.invalid>\n",
    )
    require_changes = [mutation != original for mutation in mutations]
    if not all(require_changes):
        raise AssertionError("a mutation did not change the patch")
    rejected = 0
    for mutation in mutations:
        try:
            validator.validate_patch_text(mutation)
        except AssertionError:
            rejected += 1
    if rejected != len(mutations):
        raise AssertionError(f"rejected {rejected} of {len(mutations)} unsafe mutations")
    print("validation=clock-backend-first-dmesg-entry-mutations")
    print(f"unsafe_mutations_rejected={rejected}")
    print("device_access=none")
    print("hardware_write=none")
    print("result=pass")


if __name__ == "__main__":
    main()
