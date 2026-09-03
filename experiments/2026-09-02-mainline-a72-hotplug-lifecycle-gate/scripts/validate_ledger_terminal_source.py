#!/usr/bin/env python3
"""Fail-closed oracle for the record-4 terminal-boundary repair."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys


DOWN_EXCEPTION = """\
\tif (record->stage >= GEMINI_A72_HOTPLUG_DOWN_PREPARED &&
\t    (!record->down_generation || !record->down_cookie) &&
\t    !(record->stage == GEMINI_A72_HOTPLUG_DOWN_PREPARED &&
\t      record->terminal == GEMINI_A72_HOTPLUG_REJECTED_PRECOMMIT))
\t\treturn false;
"""
RESTORE_EXCEPTION = """\
\tif (record->stage >= GEMINI_A72_HOTPLUG_RESTORE_PREPARED &&
\t    (!record->restore_generation || !record->restore_cookie) &&
\t    !(record->stage == GEMINI_A72_HOTPLUG_RESTORE_PREPARED &&
\t      record->terminal == GEMINI_A72_HOTPLUG_RESTORE_FAULT))
\t\treturn false;
"""
PRECOMMIT_SEQUENCE = """\
\tif (record->terminal == GEMINI_A72_HOTPLUG_REJECTED_PRECOMMIT)
\t\treturn record->stage <= GEMINI_A72_HOTPLUG_CPU_OFF_COMMITTED;
"""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def function_body(text: str, name: str) -> str:
    match = re.search(rf"\b{name}\s*\([^;]*?\)\s*\{{", text, re.S)
    require(match is not None, f"function missing: {name}")
    start = match.end()
    depth = 1
    for index in range(start, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start:index]
    raise ValueError(f"unterminated function: {name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        root = args.source_root.resolve()
        public = (root / "include/linux/gemini_a72_hotplug_ledger.h").read_text()
        internal = (
            root / "fs/pstore/gemini_a72_hotplug_ledger_internal.h"
        ).read_text()
        source = (root / "fs/pstore/gemini_a72_hotplug_ledger.c").read_text()
        test = (
            root / "fs/pstore/gemini_a72_hotplug_ledger_test.c"
        ).read_text()

        for token in (
            "GEMINI_A72_HOTPLUG_DOWN_PREPARED",
            "GEMINI_A72_HOTPLUG_CPU_OFF_COMMITTED",
            "GEMINI_A72_HOTPLUG_RESTORE_PREPARED",
            "GEMINI_A72_HOTPLUG_REJECTED_PRECOMMIT = 1",
            "GEMINI_A72_HOTPLUG_RESTORE_FAULT",
        ):
            require(token in public, f"public terminal contract missing: {token}")
        for token in (
            "GEMINI_A72_HOTPLUG_LEDGER_COPY_WORDS 27U",
            "GEMINI_A72_HOTPLUG_LEDGER_COPIES 2U",
            "GEMINI_A72_HOTPLUG_LEDGER_INTEGRITY_WORD 26U",
            "GEMINI_A72_HOTPLUG_LEDGER_MAX_RECORDS 16U",
            "GEMINI_A72_HOTPLUG_LEDGER_WRITES_PER_RECORD 28U",
        ):
            require(token in internal, f"wire constant changed: {token}")

        shape = function_body(source, "hotplug_record_shape_valid")
        require(shape.count(DOWN_EXCEPTION.strip()) == 1,
                "down-preparation exception is not exact")
        require(shape.count(RESTORE_EXCEPTION.strip()) == 1,
                "restore-preparation exception is not exact")
        for token in (
            "record->generation > GEMINI_A72_HOTPLUG_LEDGER_MAX_RECORDS",
            "record->cpu_off_calls > 1",
            "record->affinity_calls > 1",
            "record->cpu8_ipi_calls > 1",
            "record->cpu_on_calls > 1",
            "record->online_mask & ~GEMINI_A72_HOTPLUG_LEDGER_ONLINE_MASK",
            "record->members & ~GEMINI_A72_HOTPLUG_LEDGER_MEMBERS_MASK",
        ):
            require(token in shape, f"shape bound changed: {token}")

        sequence = function_body(source, "hotplug_sequence_valid")
        require(sequence.count(PRECOMMIT_SEQUENCE.strip()) == 1,
                "CPU_OFF-commit terminal boundary is not exact")
        require("record->stage != owner->next_stage" in sequence,
                "ordered-stage gate changed")
        require("record->stage >= GEMINI_A72_HOTPLUG_RESTORE_PREPARED" in
                sequence, "restore terminal lower bound changed")

        require(test.count("KUNIT_CASE(hotplug_") == 13,
                "record-4 KUnit case count changed")
        for name in (
            "hotplug_down_prepare_terminal_test",
            "hotplug_off_commit_terminal_test",
            "hotplug_restore_prepare_terminal_test",
        ):
            body = function_body(test, name)
            require(f"KUNIT_CASE({name})" in test,
                    f"KUnit case not registered: {name}")
            require("KUNIT_EXPECT_TRUE(test, owner.sealed)" in body,
                    f"terminal does not prove sealing: {name}")
            require("gemini_a72_hotplug_ledger_read_latest(" in body,
                    f"terminal does not prove decoding: {name}")

        down_test = function_body(test, "hotplug_down_prepare_terminal_test")
        for token in (
            "record.down_generation = 0",
            "record.down_cookie = 0",
            "latest.down_generation, 0U",
            "latest.down_cookie, 0ULL",
            "GEMINI_A72_HOTPLUG_REJECTED_PRECOMMIT",
        ):
            require(token in down_test, f"down-preparation proof missing: {token}")
        off_test = function_body(test, "hotplug_off_commit_terminal_test")
        for token in (
            "stage < GEMINI_A72_HOTPLUG_CPU_OFF_COMMITTED",
            "GEMINI_A72_HOTPLUG_REJECTED_PRECOMMIT",
            "latest.cpu_off_calls, 0U",
        ):
            require(token in off_test, f"CPU_OFF-commit proof missing: {token}")
        restore_test = function_body(
            test, "hotplug_restore_prepare_terminal_test"
        )
        for token in (
            "record.restore_generation = 0",
            "record.restore_cookie = 0",
            "latest.restore_generation, 0U",
            "latest.restore_cookie, 0ULL",
            "GEMINI_A72_HOTPLUG_RESTORE_FAULT",
        ):
            require(token in restore_test,
                    f"restore-preparation proof missing: {token}")

        for token in (
            "state.writes, 451U",
            "latest.generation, 16U",
            "static const u32 stages[] = { 1, 2, 3, 4, 5, 6, 7, 9, 10, 11,",
        ):
            require(token in test, f"success-path invariant changed: {token}")

        combined = public + internal + source + test
        for token in (
            "cpu_up(", "cpu_down(", "remove_cpu(", "add_cpu(",
            "psci_ops.", "cpu_psci_ops.", "arm_smccc",
            "smp_call_function", "mtk_wdt_recovery_takeover(",
            "mtk_wdt_recovery_reload(",
        ):
            require(token not in combined,
                    f"terminal repair gained physical effect: {token}")
    except (OSError, ValueError) as exc:
        print(f"ledger_terminal_source=fail reason={exc}", file=sys.stderr)
        return 1
    print("ledger_terminal_source=pass")
    print("terminal_boundaries=down-prepare,cpu-off-commit,restore-prepare")
    print("wire_format_changed=false")
    print("successful_records_max=16")
    print("successful_word_writes_max=451")
    print("focused_kunit_cases=13")
    print("production_callers_added=0")
    print("physical_effect_calls=0")
    print("boot_candidate=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
