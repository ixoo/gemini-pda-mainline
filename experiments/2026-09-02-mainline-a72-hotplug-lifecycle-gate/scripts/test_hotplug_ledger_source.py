#!/usr/bin/env python3
"""Require unsafe record-4 ledger source mutations to fail closed."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile


MUTATIONS = (
    ("fs/pstore/gemini_a72_hotplug_ledger.c", "GEMINI_A72_HOTPLUG_LEDGER_BASE 0x44414000ULL", "GEMINI_A72_HOTPLUG_LEDGER_BASE 0x44415000ULL"),
    ("fs/pstore/gemini_a72_hotplug_ledger_internal.h", "0x4c483947U", "0x4c483946U"),
    ("fs/pstore/gemini_a72_hotplug_ledger_internal.h", "0x00010001U", "0x00010002U"),
    ("fs/pstore/gemini_a72_hotplug_ledger_internal.h", "COPY_WORDS 27U", "COPY_WORDS 26U"),
    ("fs/pstore/gemini_a72_hotplug_ledger_internal.h", "INTEGRITY_WORD 26U", "INTEGRITY_WORD 25U"),
    ("fs/pstore/gemini_a72_hotplug_ledger_internal.h", "MAX_RECORDS 16U", "MAX_RECORDS 17U"),
    ("fs/pstore/gemini_a72_hotplug_ledger.c", "owner->newest_copy ^ 1U", "owner->newest_copy"),
    ("fs/pstore/gemini_a72_hotplug_ledger.c", "!start && !size", "start == size"),
    ("fs/pstore/gemini_a72_hotplug_ledger.c", "wire[26] = cpu_to_le32(hotplug_integrity(wire))", "wire[26] = cpu_to_le32(0)"),
    ("fs/pstore/gemini_a72_hotplug_ledger.c", "memcmp(wire, readback, sizeof(wire))", "false"),
    ("fs/pstore/gemini_a72_hotplug_ledger.c", "owner->records >= GEMINI_A72_HOTPLUG_LEDGER_MAX_RECORDS", "false"),
    ("fs/pstore/gemini_a72_hotplug_ledger.c", "record->cpu_off_calls > 1", "record->cpu_off_calls > 2"),
    ("fs/pstore/gemini_a72_hotplug_ledger.c", "record->online_mask & ~GEMINI_A72_HOTPLUG_LEDGER_ONLINE_MASK", "false"),
    ("fs/pstore/gemini_a72_hotplug_ledger.c", "record->session_id != session_id", "false"),
    ("fs/pstore/gemini_a72_hotplug_ledger.c", "candidate.generation == record->generation", "false"),
    ("fs/pstore/gemini_a72_hotplug_ledger.c", "GEMINI_A72_HOTPLUG_LEDGER_RESERVE_SIZE 0x000e0000ULL", "GEMINI_A72_HOTPLUG_LEDGER_RESERVE_SIZE 0x000d0000ULL"),
    ("fs/pstore/gemini_a72_hotplug_ledger.c", "hotplug_attempted = true", "hotplug_attempted = false"),
    ("fs/pstore/gemini_a72_hotplug_ledger.c", "ioremap_wc(GEMINI_A72_HOTPLUG_LEDGER_BASE", "ioremap(GEMINI_A72_HOTPLUG_LEDGER_BASE"),
    ("fs/pstore/Kconfig", "depends on PSTORE_GEMINI_CPU9_PROGRESS_LEDGER=y", "depends on PSTORE_RAM=y"),
    ("fs/pstore/gemini_a72_hotplug_ledger_test.c", "state.writes, 451U", "state.writes, 452U"),
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    source = args.source_root.resolve()
    validator = Path(__file__).resolve().with_name(
        "validate_hotplug_ledger_source.py"
    )
    rejected = 0
    with tempfile.TemporaryDirectory(prefix="hotplug-ledger-mutations-") as name:
        root = Path(name)
        for index, (relative, old, new) in enumerate(MUTATIONS):
            mutated = root / str(index)
            for path in (
                "include/linux/gemini_a72_hotplug_ledger.h",
                "fs/pstore/gemini_a72_hotplug_ledger_internal.h",
                "fs/pstore/gemini_a72_hotplug_ledger.c",
                "fs/pstore/gemini_a72_hotplug_ledger_test.c",
                "fs/pstore/Kconfig",
                "fs/pstore/Makefile",
            ):
                destination = mutated / path
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source / path, destination)
            target = mutated / relative
            text = target.read_text(encoding="utf-8")
            if text.count(old) != 1:
                raise SystemExit(f"mutation anchor changed: {relative}: {old}")
            target.write_text(text.replace(old, new, 1), encoding="utf-8")
            result = subprocess.run(
                ("python3", str(validator), "--source-root", str(mutated)),
                check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            if result.returncode == 0:
                raise SystemExit(f"unsafe mutation accepted: {relative}: {old}")
            rejected += 1
    print("hotplug_ledger_mutations=pass")
    print(f"unsafe_mutations_rejected={rejected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
