#!/usr/bin/env python3
"""Mutation tripwires for the CPU9 readback bitmap source validator."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import tempfile

from validate_readback_bitmap_source import validate


MUTATIONS = (
    ("drivers/soc/mediatek/mt6797-a72-hotplug-executor-internal.h",
     "BIT(31)", "BIT(30)"),
    ("drivers/soc/mediatek/mt6797-a72-hotplug-executor-internal.h",
     "BIT(13)", "BIT(12)"),
    ("drivers/soc/mediatek/mt6797-a72-hotplug-executor.c",
     "if (!baseline)", "if (baseline)"),
    ("drivers/soc/mediatek/mt6797-a72-hotplug-executor.c",
     "if (!post_state)", "if (post_state)"),
    ("drivers/soc/mediatek/mt6797-a72-hotplug-executor.c",
     "memcmp(baseline->provider", "memcmp(post_state->provider"),
    ("drivers/soc/mediatek/mt6797-a72-hotplug-executor.c",
     "return !mt6797_a72_hotplug_readback_mismatch(baseline, post_state);",
     "return true;"),
    ("drivers/soc/mediatek/mt6797-a72-hotplug-executor.c",
     "return mismatch;", "writel(0, NULL);\n\treturn mismatch;"),
    ("drivers/soc/mediatek/mt6797-a72-hotplug-binding.c",
     "MT6797_A72_HOTPLUG_READBACK_BITMAP_V1 |", "0 |"),
    ("drivers/soc/mediatek/mt6797-a72-hotplug-binding.c",
     "binding->down_result.snapshots == 2 ?",
     "binding->down_result.snapshots >= 1 ?"),
    ("drivers/soc/mediatek/mt6797-a72-hotplug-executor-test.c",
     "KUNIT_CASE(mt6797_hotplug_readback_bitmap)",
     "KUNIT_CASE(mt6797_hotplug_readback_rejections)"),
)
PATHS = tuple(sorted({mutation[0] for mutation in MUTATIONS}))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    if validate(root):
        raise SystemExit("pristine edited source failed validation")
    with tempfile.TemporaryDirectory(prefix="readback-bitmap-mutations-") as name:
        temp = Path(name)
        for relative in PATHS:
            target = temp / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / relative, target)
        for relative, old, new in MUTATIONS:
            path = temp / relative
            text = path.read_text()
            if text.count(old) < 1:
                raise SystemExit(f"mutation anchor changed: {old}")
            path.write_text(text.replace(old, new, 1))
            if not validate(temp):
                raise SystemExit(f"unsafe mutation accepted: {old}")
            shutil.copyfile(root / relative, path)
    print("readback_bitmap_mutations=pass")
    print(f"unsafe_mutations_rejected={len(MUTATIONS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
