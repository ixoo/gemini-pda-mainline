#!/usr/bin/env python3
"""Mutation tripwires for the CPU9 restore-readiness observation."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import tempfile

from validate_restore_readiness_source import validate


BINDING = "drivers/soc/mediatek/mt6797-a72-hotplug-binding.c"
BINDING_HEADER = "drivers/soc/mediatek/mt6797-a72-hotplug-binding-internal.h"
LEDGER = "fs/pstore/gemini_a72_hotplug_ledger.c"
LEDGER_INTERNAL = "fs/pstore/gemini_a72_hotplug_ledger_internal.h"
LEDGER_PUBLIC = "include/linux/gemini_a72_hotplug_ledger.h"
BINDING_TEST = "drivers/soc/mediatek/mt6797-a72-hotplug-binding-test.c"
LEDGER_TEST = "fs/pstore/gemini_a72_hotplug_ledger_test.c"
MUTATIONS = (
    (BINDING_HEADER, "MT6797_A72_RESTORE_READY_SAMPLES_MAX 51U",
     "MT6797_A72_RESTORE_READY_SAMPLES_MAX 52U"),
    (BINDING, "usleep_range(5000, 6000)", "usleep_range(5000, 7000)"),
    (BINDING, "result->sleep_calls++", "result->sleep_calls += 2"),
    (BINDING, "result->sample_calls++", "result->sample_calls += 2"),
    (BINDING, "result->ready = true", "result->ready = false"),
    (BINDING,
     "result->last.spm_cpu_pwr_status |\n\t\t       result->last.spm_cpu_pwr_status_2nd",
     "result->last.spm_cpu_pwr_status &\n\t\t       result->last.spm_cpu_pwr_status_2nd"),
    (BINDING, "mt6797_a72_platform_state_snapshot(context, &state)",
     "regmap_write(NULL, 0, 0)"),
    (BINDING, "binding->source.platform, &binding->readiness",
     "NULL, &binding->readiness"),
    (LEDGER_INTERNAL, "VERSION_WORD 0x00010002U", "VERSION_WORD 0x00010001U"),
    (LEDGER_INTERNAL, "COPY_WORDS 37U", "COPY_WORDS 36U"),
    (LEDGER, "record->restore_readiness_sleeps + 1 !=",
     "record->restore_readiness_sleeps !="),
    (LEDGER, "record->cpu_on_calls))", "false))"),
    (LEDGER_PUBLIC, "RESTORE_READINESS_SAMPLES_MAX 51U",
     "RESTORE_READINESS_SAMPLES_MAX 52U"),
)
PATHS = tuple(sorted({mutation[0] for mutation in MUTATIONS} |
                     {BINDING_TEST, LEDGER_TEST}))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    if validate(root):
        raise SystemExit("pristine edited source failed validation")
    with tempfile.TemporaryDirectory(prefix="restore-readiness-mutations-") as name:
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
    print("restore_readiness_mutations=pass")
    print(f"unsafe_mutations_rejected={len(MUTATIONS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
