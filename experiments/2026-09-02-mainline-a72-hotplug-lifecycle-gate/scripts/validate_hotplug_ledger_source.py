#!/usr/bin/env python3
"""Fail-closed source oracle for the disconnected record-4 ledger."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys


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
        internal = (root / "fs/pstore/gemini_a72_hotplug_ledger_internal.h").read_text()
        source = (root / "fs/pstore/gemini_a72_hotplug_ledger.c").read_text()
        test = (root / "fs/pstore/gemini_a72_hotplug_ledger_test.c").read_text()
        kconfig = (root / "fs/pstore/Kconfig").read_text()
        makefile = (root / "fs/pstore/Makefile").read_text()

        for token in (
            "GEMINI_A72_HOTPLUG_BINDING_PARENT = 1",
            "GEMINI_A72_HOTPLUG_CPU_OFF_COMMITTED",
            "GEMINI_A72_HOTPLUG_CPU_OFF_RETURNED",
            "GEMINI_A72_HOTPLUG_RESTORE_COMPLETE",
            "GEMINI_A72_HOTPLUG_REJECTED_PRECOMMIT = 1",
            "GEMINI_A72_HOTPLUG_RESTORED_SUCCESS",
            "u64 session_id;",
            "u64 watchdog_identity;",
            "u32 cpu_off_calls;",
            "u32 affinity_calls;",
            "u32 cpu8_ipi_calls;",
            "u32 cpu_on_calls;",
            "u32 readback_mismatch;",
        ):
            require(token in public, f"public contract missing: {token}")
        require(public.count("gemini_a72_hotplug_ledger_begin(") == 2,
                "enabled declaration or disabled begin stub changed")
        require(public.count("gemini_a72_hotplug_ledger_checkpoint(") == 2,
                "enabled declaration or disabled checkpoint stub changed")

        exact_constants = (
            "GEMINI_A72_HOTPLUG_LEDGER_PSTORE_SIGNATURE 0x43474244U",
            "GEMINI_A72_HOTPLUG_LEDGER_MAGIC 0x4c483947U",
            "GEMINI_A72_HOTPLUG_LEDGER_VERSION_WORD 0x00010001U",
            "GEMINI_A72_HOTPLUG_LEDGER_HEADER_WORDS 3U",
            "GEMINI_A72_HOTPLUG_LEDGER_COPY_WORDS 27U",
            "GEMINI_A72_HOTPLUG_LEDGER_COPIES 2U",
            "GEMINI_A72_HOTPLUG_LEDGER_INTEGRITY_WORD 26U",
            "GEMINI_A72_HOTPLUG_LEDGER_SLOT_SIZE 0x1000U",
            "GEMINI_A72_HOTPLUG_LEDGER_MAX_RECORDS 16U",
            "GEMINI_A72_HOTPLUG_LEDGER_WRITES_PER_RECORD 28U",
        )
        for token in exact_constants:
            require(token in internal, f"wire constant changed: {token}")

        for token in (
            "GEMINI_A72_HOTPLUG_LEDGER_RESERVE_BASE 0x44410000ULL",
            "GEMINI_A72_HOTPLUG_LEDGER_BASE 0x44414000ULL",
            "GEMINI_A72_HOTPLUG_LEDGER_RESERVE_SIZE 0x000e0000ULL",
            'of_find_node_by_path("/reserved-memory/ramoops@44410000")',
            "resource.start != GEMINI_A72_HOTPLUG_LEDGER_RESERVE_BASE",
            "resource_size(&resource) != GEMINI_A72_HOTPLUG_LEDGER_RESERVE_SIZE",
            "ioremap_wc(GEMINI_A72_HOTPLUG_LEDGER_BASE",
        ):
            require(token in source, f"record-4 ownership gate missing: {token}")

        begin = function_body(source, "gemini_a72_hotplug_ledger_owner_begin")
        for token in (
            "signature == ~0U && start == ~0U && size == ~0U",
            "GEMINI_A72_HOTPLUG_LEDGER_PSTORE_SIGNATURE",
            "!start && !size",
            "-EALREADY",
            "-EBADMSG",
            "owner->next_generation = 1",
            "owner->next_stage = GEMINI_A72_HOTPLUG_BINDING_PARENT",
        ):
            require(token in begin, f"empty-only owner gate missing: {token}")
        for token in ("memset(", "clear", "repair", "retry"):
            require(token not in begin.lower(), f"owner begin gained forbidden action: {token}")

        shape = function_body(source, "hotplug_record_shape_valid")
        for token in (
            "record->cpu_off_calls > 1",
            "record->affinity_calls > 1",
            "record->cpu8_ipi_calls > 1",
            "record->cpu_on_calls > 1",
            "record->online_mask & ~GEMINI_A72_HOTPLUG_LEDGER_ONLINE_MASK",
            "record->members & ~GEMINI_A72_HOTPLUG_LEDGER_MEMBERS_MASK",
        ):
            require(token in shape, f"record shape budget missing: {token}")

        checkpoint = function_body(
            source, "gemini_a72_hotplug_ledger_owner_checkpoint"
        )
        for token in (
            "wire[26] = cpu_to_le32(hotplug_integrity(wire))",
            "GEMINI_A72_HOTPLUG_LEDGER_INTEGRITY_WORD), 0",
            "word < GEMINI_A72_HOTPLUG_LEDGER_INTEGRITY_WORD",
            "hotplug_read_wire(ops, context, target, readback)",
            "memcmp(wire, readback, sizeof(wire))",
            "GEMINI_A72_HOTPLUG_LEDGER_PSTORE_SIGNATURE",
            "owner->records >= GEMINI_A72_HOTPLUG_LEDGER_MAX_RECORDS",
            "owner->newest_copy ^ 1U",
        ):
            require(token in checkpoint, f"commit protocol missing: {token}")
        require(checkpoint.index("hotplug_read_wire(") <
                checkpoint.index("if (!owner->header_committed)"),
                "header can publish before full-copy readback")
        require(checkpoint.index("ops->write(context, 1") <
                checkpoint.index("ops->write(context, 0"),
                "raw signature is not committed last")
        require("record->session_id != session_id" in checkpoint,
                "record is not bound to the exact session")

        latest = function_body(source, "gemini_a72_hotplug_ledger_read_latest")
        for token in (
            "copy < GEMINI_A72_HOTPLUG_LEDGER_COPIES",
            "hotplug_wire_valid",
            "candidate.generation == record->generation",
            "candidate.generation > record->generation",
        ):
            require(token in latest, f"unique-newest decoder missing: {token}")
        wire_valid = function_body(source, "hotplug_wire_valid")
        require("hotplug_integrity(wire)" in wire_valid,
                "decoder no longer verifies CRC")
        require("hotplug_record_shape_valid(record)" in wire_valid,
                "decoder no longer validates semantic shape")

        require(test.count("KUNIT_CASE(hotplug_") == 10,
                "record-4 KUnit case count changed")
        for token in (
            "state.writes, 451U",
            "latest.generation, 16U",
            "hotplug_nonempty_refusal_test",
            "hotplug_cpu_off_return_terminal_test",
            "hotplug_readback_fault_test",
            "hotplug_crc_and_ambiguity_test",
        ):
            require(token in test, f"KUnit proof missing: {token}")

        require("config PSTORE_GEMINI_A72_HOTPLUG_LEDGER\n" in kconfig,
                "record-4 Kconfig missing")
        require("depends on PSTORE_GEMINI_CPU9_PROGRESS_LEDGER=y" in kconfig,
                "record-4 parent Kconfig changed")
        require("CONFIG_PSTORE_GEMINI_A72_HOTPLUG_LEDGER) += gemini_a72_hotplug_ledger.o" in makefile,
                "record-4 Makefile entry missing")
        require("CONFIG_PSTORE_GEMINI_A72_HOTPLUG_LEDGER_KUNIT_TEST) += gemini_a72_hotplug_ledger_test.o" in makefile,
                "record-4 KUnit Makefile entry missing")

        added = public + internal + source + test
        for token in (
            "cpu_up(", "cpu_down(", "remove_cpu(", "add_cpu(",
            "psci_ops.", "cpu_psci_ops.", "arm_smccc", "smp_call_function",
            "mtk_wdt_recovery_takeover(", "mtk_wdt_recovery_reload(",
        ):
            require(token not in added, f"disconnected slice gained effect: {token}")
        require("mt6797_psci_cpu_can_disable" not in added,
                "CPU-disable veto touched by ledger slice")
        production_begin = function_body(
            source, "gemini_a72_hotplug_ledger_begin"
        )
        require("hotplug_attempted = true" in production_begin,
                "production owner is no longer one-shot")
    except (OSError, ValueError) as exc:
        print(f"hotplug_ledger_source=fail reason={exc}", file=sys.stderr)
        return 1
    print("hotplug_ledger_source=pass")
    print("record_index=4")
    print("record_base=0x44414000")
    print("wire_copy_words=27")
    print("successful_records_max=16")
    print("successful_word_writes_max=451")
    print("kunit_cases=10")
    print("production_callers=0")
    print("physical_effect_calls=0")
    print("boot_candidate=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
