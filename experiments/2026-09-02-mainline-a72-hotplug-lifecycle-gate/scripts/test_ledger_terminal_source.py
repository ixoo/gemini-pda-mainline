#!/usr/bin/env python3
"""Require unsafe record-4 terminal-boundary mutations to fail closed."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile


MUTATIONS = (
    (
        "fs/pstore/gemini_a72_hotplug_ledger.c",
        "record->stage == GEMINI_A72_HOTPLUG_DOWN_PREPARED &&\n"
        "\t      record->terminal == GEMINI_A72_HOTPLUG_REJECTED_PRECOMMIT",
        "record->stage >= GEMINI_A72_HOTPLUG_DOWN_PREPARED &&\n"
        "\t      record->terminal == GEMINI_A72_HOTPLUG_REJECTED_PRECOMMIT",
    ),
    (
        "fs/pstore/gemini_a72_hotplug_ledger.c",
        "record->stage == GEMINI_A72_HOTPLUG_DOWN_PREPARED &&\n"
        "\t      record->terminal == GEMINI_A72_HOTPLUG_REJECTED_PRECOMMIT",
        "record->stage == GEMINI_A72_HOTPLUG_DOWN_PREPARED ||\n"
        "\t      record->terminal == GEMINI_A72_HOTPLUG_REJECTED_PRECOMMIT",
    ),
    (
        "fs/pstore/gemini_a72_hotplug_ledger.c",
        "record->terminal == GEMINI_A72_HOTPLUG_REJECTED_PRECOMMIT))\n"
        "\t\treturn false;",
        "record->terminal == GEMINI_A72_HOTPLUG_RESTORE_FAULT))\n"
        "\t\treturn false;",
    ),
    (
        "fs/pstore/gemini_a72_hotplug_ledger.c",
        "record->stage == GEMINI_A72_HOTPLUG_RESTORE_PREPARED &&\n"
        "\t      record->terminal == GEMINI_A72_HOTPLUG_RESTORE_FAULT",
        "record->stage >= GEMINI_A72_HOTPLUG_RESTORE_PREPARED &&\n"
        "\t      record->terminal == GEMINI_A72_HOTPLUG_RESTORE_FAULT",
    ),
    (
        "fs/pstore/gemini_a72_hotplug_ledger.c",
        "record->stage == GEMINI_A72_HOTPLUG_RESTORE_PREPARED &&\n"
        "\t      record->terminal == GEMINI_A72_HOTPLUG_RESTORE_FAULT",
        "record->stage == GEMINI_A72_HOTPLUG_RESTORE_PREPARED ||\n"
        "\t      record->terminal == GEMINI_A72_HOTPLUG_RESTORE_FAULT",
    ),
    (
        "fs/pstore/gemini_a72_hotplug_ledger.c",
        "record->terminal == GEMINI_A72_HOTPLUG_RESTORE_FAULT))\n"
        "\t\treturn false;",
        "record->terminal == GEMINI_A72_HOTPLUG_REJECTED_PRECOMMIT))\n"
        "\t\treturn false;",
    ),
    (
        "fs/pstore/gemini_a72_hotplug_ledger.c",
        "return record->stage <= GEMINI_A72_HOTPLUG_CPU_OFF_COMMITTED;",
        "return record->stage <= GEMINI_A72_HOTPLUG_TARGET_DISABLE_VALID;",
    ),
    (
        "fs/pstore/gemini_a72_hotplug_ledger.c",
        "return record->stage <= GEMINI_A72_HOTPLUG_CPU_OFF_COMMITTED;",
        "return record->stage <= GEMINI_A72_HOTPLUG_RESTORE_PREPARED;",
    ),
    (
        "fs/pstore/gemini_a72_hotplug_ledger_test.c",
        "\tKUNIT_CASE(hotplug_down_prepare_terminal_test),\n",
        "",
    ),
    (
        "fs/pstore/gemini_a72_hotplug_ledger_test.c",
        "\tKUNIT_CASE(hotplug_off_commit_terminal_test),\n",
        "",
    ),
    (
        "fs/pstore/gemini_a72_hotplug_ledger_test.c",
        "\tKUNIT_CASE(hotplug_restore_prepare_terminal_test),\n",
        "",
    ),
    (
        "fs/pstore/gemini_a72_hotplug_ledger_test.c",
        "\trecord.down_generation = 0;\n",
        "\trecord.down_generation = 8;\n",
    ),
    (
        "fs/pstore/gemini_a72_hotplug_ledger_test.c",
        "\trecord.down_cookie = 0;\n",
        "\trecord.down_cookie = 1;\n",
    ),
    (
        "fs/pstore/gemini_a72_hotplug_ledger_test.c",
        "\trecord.restore_generation = 0;\n",
        "\trecord.restore_generation = 9;\n",
    ),
    (
        "fs/pstore/gemini_a72_hotplug_ledger_test.c",
        "\trecord.restore_cookie = 0;\n",
        "\trecord.restore_cookie = 1;\n",
    ),
    (
        "fs/pstore/gemini_a72_hotplug_ledger_test.c",
        "latest.cpu_off_calls, 0U",
        "latest.cpu_off_calls, 1U",
    ),
    (
        "fs/pstore/gemini_a72_hotplug_ledger_test.c",
        "state.writes, 451U",
        "state.writes, 452U",
    ),
    (
        "fs/pstore/gemini_a72_hotplug_ledger_internal.h",
        "GEMINI_A72_HOTPLUG_LEDGER_MAX_RECORDS 16U",
        "GEMINI_A72_HOTPLUG_LEDGER_MAX_RECORDS 17U",
    ),
)

SOURCE_PATHS = (
    "include/linux/gemini_a72_hotplug_ledger.h",
    "fs/pstore/gemini_a72_hotplug_ledger_internal.h",
    "fs/pstore/gemini_a72_hotplug_ledger.c",
    "fs/pstore/gemini_a72_hotplug_ledger_test.c",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    source = args.source_root.resolve()
    validator = Path(__file__).resolve().with_name(
        "validate_ledger_terminal_source.py"
    )
    rejected = 0
    with tempfile.TemporaryDirectory(
        prefix="hotplug-ledger-terminal-mutations-"
    ) as name:
        root = Path(name)
        for index, (relative, old, new) in enumerate(MUTATIONS):
            mutated = root / str(index)
            for path in SOURCE_PATHS:
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
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if result.returncode == 0:
                raise SystemExit(f"unsafe mutation accepted: {relative}: {old}")
            rejected += 1
    print("ledger_terminal_mutations=pass")
    print(f"unsafe_mutations_rejected={rejected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
