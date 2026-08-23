#!/usr/bin/env python3
"""Mutation tests for the admitted protected-clock definition."""

from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PATCH = SCRIPT_DIR.parents[2] / "patches/v7.1.3/0336-pstore-qualify-Gemini-protected-clock-call-in-first-dmesg.patch"
spec = importlib.util.spec_from_file_location("protected_clock_validate",
                                              SCRIPT_DIR / "validate.py")
assert spec and spec.loader
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def main() -> None:
    original = PATCH.read_text(encoding="utf-8")
    mutations = (
        original.replace("checkpoint=before-clock", "checkpoint=after-clock", 1),
        original.replace("checkpoint=after-clock", "checkpoint=before-clock", 1),
        original.replace("slot=1 crc32=183854b2", "slot=3 crc32=183854b2", 1),
        original.replace("slot=2 crc32=d14b85aa", "slot=4 crc32=d14b85aa", 1),
        original + "\n+\tmemcpy_toio(ledger, record, size);\n",
        original + "\n+\tmt6797_dvfsp_clock_backend_read(dev, &record);\n",
        original + "\n+\tmt6797_bigidvfs_backend_read(dev, &record);\n",
        original + "\n+\tarm_smccc_smc(0, 0, 0, 0, 0, 0, 0, 0, &res);\n",
        original + "\n+\tcpu_up(8);\n",
        original + "\nSigned-off-by: Synthetic <synthetic@example.invalid>\n",
    )
    if not all(mutation != original for mutation in mutations):
        raise AssertionError("a mutation did not change the patch")
    rejected = 0
    for mutation in mutations:
        try:
            validator.validate_patch_text(mutation)
        except AssertionError:
            rejected += 1
    if rejected != len(mutations):
        raise AssertionError(f"rejected {rejected} of {len(mutations)} unsafe mutations")
    print("validation=protected-clock-first-dmesg-call-mutations")
    print(f"unsafe_mutations_rejected={rejected}")
    print("device_access=none")
    print("hardware_write=none")
    print("result=pass")


if __name__ == "__main__":
    main()
