#!/usr/bin/env python3
"""Mutation tripwires for the intersected CPU9-off status repair."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import tempfile

from validate_intersected_status_source import validate


SOURCE = "drivers/soc/mediatek/mt6797-a72-hotplug-executor.c"
TEST = "drivers/soc/mediatek/mt6797-a72-hotplug-executor-test.c"
MUTATIONS = (
    (SOURCE,
     "readback->spm_cpu_pwr_status &\n"
     "\t\t   readback->spm_cpu_pwr_status_2nd",
     "readback->spm_cpu_pwr_status |\n"
     "\t\t   readback->spm_cpu_pwr_status_2nd"),
    (SOURCE,
     "!mt6797_a72_hotplug_status_exact(post_state, false)",
     "false"),
    (SOURCE,
     "MT6797_A72_HOTPLUG_MISMATCH_POST_STATUS_CPU9 |",
     "MT6797_A72_HOTPLUG_MISMATCH_POST_STATUS_CPU8 |"),
    (SOURCE,
     "MT6797_A72_HOTPLUG_MISMATCH_POST_STATUS_CPU9 |\n"
     "\t\tMT6797_A72_HOTPLUG_MISMATCH_POST_STATUS2_CPU9;",
     "MT6797_A72_HOTPLUG_MISMATCH_POST_STATUS_CPU9 |\n"
     "\t\tMT6797_A72_HOTPLUG_MISMATCH_BASELINE_STATUS2_CPU9;"),
    (SOURCE,
     "return !(mismatch & ~raw_cpu9_mismatch);",
     "return true;"),
    (SOURCE,
     "return !(mismatch & ~raw_cpu9_mismatch);",
     "writel(0, NULL);\n\treturn !(mismatch & ~raw_cpu9_mismatch);"),
    (TEST,
     "post.spm_cpu_pwr_status |= MT6797_A72_HOTPLUG_CPU9_STATUS;",
     "post.spm_cpu_pwr_status &= ~MT6797_A72_HOTPLUG_CPU9_STATUS;"),
    (TEST,
     "post.spm_cpu_pwr_status_2nd |= MT6797_A72_HOTPLUG_CPU9_STATUS;",
     "post.spm_cpu_pwr_status_2nd &= ~MT6797_A72_HOTPLUG_CPU9_STATUS;"),
    (TEST,
     "MT6797_A72_HOTPLUG_MISMATCH_POST_STATUS_CPU9);",
     "MT6797_A72_HOTPLUG_MISMATCH_POST_STATUS2_CPU9);"),
    (TEST,
     "KUNIT_EXPECT_TRUE(test,\n"
     "\t\t\t  mt6797_a72_hotplug_readback_proves_cpu9_off(&baseline, &post));",
     "KUNIT_EXPECT_FALSE(test,\n"
     "\t\t\t   mt6797_a72_hotplug_readback_proves_cpu9_off(&baseline, &post));"),
)
PATHS = tuple(sorted({mutation[0] for mutation in MUTATIONS}))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    if validate(root):
        raise SystemExit("pristine edited source failed validation")
    with tempfile.TemporaryDirectory(
        prefix="intersected-status-mutations-"
    ) as name:
        temp = Path(name)
        for relative in PATHS:
            target = temp / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / relative, target)
        for relative, old, new in MUTATIONS:
            path = temp / relative
            text = path.read_text(encoding="utf-8")
            if text.count(old) < 1:
                raise SystemExit(f"mutation anchor changed: {old}")
            path.write_text(text.replace(old, new, 1), encoding="utf-8")
            if not validate(temp):
                raise SystemExit(f"unsafe mutation accepted: {old}")
            shutil.copyfile(root / relative, path)
    print("intersected_status_mutations=pass")
    print(f"unsafe_mutations_rejected={len(MUTATIONS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
