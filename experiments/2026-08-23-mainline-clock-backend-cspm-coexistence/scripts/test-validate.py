#!/usr/bin/env python3
"""Mutation tests for the CSPM coexistence definition validator."""

from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PATCH = SCRIPT_DIR.parents[2] / "patches/v7.1.3/0335-soc-mediatek-share-CSPM-through-MT6797-handoff.patch"
spec = importlib.util.spec_from_file_location("cspm_coexist_validate",
                                              SCRIPT_DIR / "validate.py")
assert spec and spec.loader
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def main() -> None:
    original = PATCH.read_text(encoding="utf-8")
    mutations = (
        original.replace("+\t\taccess-controllers = <&dvfsp_handoff>;\n", "", 1),
        original.replace('+\t\treg-names = "mcumixed";',
                         '+\t\treg-names = "mcumixed", "cspm";', 1),
        original.replace("-\tbackend->cspm = devm_platform_ioremap_resource_byname(pdev, \"cspm\");",
                         "+\tbackend->cspm = devm_platform_ioremap_resource_byname(pdev, \"cspm\");", 1),
        original.replace("mutex_lock(&handoff->transfer_lock);",
                         "mutex_lock(&handoff->lock);", 1),
        original.replace("mutex_unlock(&handoff->transfer_lock);",
                         "mutex_unlock(&handoff->lock);", 1),
        original.replace("cspm_owner=handoff", "cspm_owner=clock", 1),
        original + "\n+\tstatus = \"okay\";\n",
        original + "\n+\tmt6797_bigidvfs_backend_read(dev, &record);\n",
        original + "\n+\tpsci_ops.cpu_on(8, 0);\n",
        original + "\nSigned-off-by: Synthetic <synthetic@example.invalid>\n",
    )
    if not all(mutation != original for mutation in mutations):
        raise AssertionError("a mutation did not change the patch")
    rejected = 0
    for mutation in mutations:
        try:
            validator.validate_patch_text(mutation)
        except (AssertionError, ValueError):
            rejected += 1
    if rejected != len(mutations):
        raise AssertionError(f"rejected {rejected} of {len(mutations)} unsafe mutations")
    print("validation=clock-backend-cspm-coexistence-mutations")
    print(f"unsafe_mutations_rejected={rejected}")
    print("device_access=none")
    print("hardware_write=none")
    print("result=pass")


if __name__ == "__main__":
    main()
