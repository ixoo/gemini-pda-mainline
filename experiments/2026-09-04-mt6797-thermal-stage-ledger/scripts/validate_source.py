#!/usr/bin/env python3
"""Validate the exact MT6797 thermal-stage ledger source result."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def read(root: Path, relative: str) -> str:
    path = root / relative
    require(path.is_file() and not path.is_symlink(), f"missing source: {relative}")
    return path.read_text(encoding="utf-8")


def between(text: str, start: str, end: str) -> str:
    require(text.count(start) == 1, f"non-unique start anchor: {start}")
    tail = text.split(start, 1)[1]
    require(tail.count(end) >= 1, f"missing end anchor: {end}")
    return tail.split(end, 1)[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root

    kconfig = read(root, "fs/pstore/Kconfig")
    makefile = read(root, "fs/pstore/Makefile")
    public = read(root, "include/linux/gemini_mt6797_thermal_ledger.h")
    internal = read(root, "fs/pstore/gemini_mt6797_thermal_ledger_internal.h")
    owner = read(root, "fs/pstore/gemini_mt6797_thermal_ledger.c")
    tests = read(root, "fs/pstore/gemini_mt6797_thermal_ledger_test.c")
    transaction_h = read(root, "drivers/thermal/mediatek/auxadc_thermal_internal.h")
    thermal = read(root, "drivers/thermal/mediatek/auxadc_thermal.c")
    transaction_test = read(
        root, "drivers/thermal/mediatek/mt6797_auxadc_transaction_test.c"
    )

    for symbol in (
        "PSTORE_GEMINI_MT6797_THERMAL_LEDGER",
        "PSTORE_GEMINI_MT6797_THERMAL_LEDGER_KUNIT_TEST",
    ):
        require(kconfig.count(f"config {symbol}\n") == 1, f"bad {symbol} Kconfig")
    require(kconfig.count("\tdepends on MTK_SOC_THERMAL=y\n") == 1,
            "thermal owner dependency changed")
    require(kconfig.count("\tselect CRC32\n") >= 2, "CRC32 selection absent")
    require(makefile.count("gemini_mt6797_thermal_ledger.o") == 1,
            "owner Makefile entry changed")
    require(makefile.count("gemini_mt6797_thermal_ledger_test.o") == 1,
            "test Makefile entry changed")

    operation_block = between(
        public,
        "enum gemini_mt6797_thermal_ledger_operation {",
        "};",
    )
    operations = re.findall(
        r"^\s*GEMINI_MT6797_THERMAL_([A-Z0-9_]+)(?:\s*=.*)?,?$",
        operation_block,
        re.MULTILINE,
    )
    require(len(operations) == 23, f"operation count changed: {len(operations)}")
    for token in (
        "GEMINI_MT6797_THERMAL_LEDGER_BEFORE = 1",
        "GEMINI_MT6797_THERMAL_LEDGER_AFTER",
        "GEMINI_MT6797_THERMAL_LEDGER_TERMINAL",
        "GEMINI_MT6797_THERMAL_LEDGER_SUCCESS = 1",
        "GEMINI_MT6797_THERMAL_LEDGER_FAILURE",
    ):
        require(token in public, f"missing public contract: {token}")
    for token in (
        "GEMINI_MT6797_THERMAL_LEDGER_COPY_WORDS 12U",
        "GEMINI_MT6797_THERMAL_LEDGER_COPIES 2U",
        "GEMINI_MT6797_THERMAL_LEDGER_MAX_RECORDS 96U",
        "GEMINI_MT6797_THERMAL_LEDGER_ATTEMPT_ID 0x54484d4c00000001ULL",
    ):
        require(token in internal, f"missing wire contract: {token}")

    for token in (
        "#define GEMINI_MT6797_THERMAL_LEDGER_BASE 0x44415000ULL",
        'strcmp(model,\n\t\t   "Planet Computers Gemini PDA (thermal serviceability)")',
        'of_find_node_by_path("/reserved-memory/ramoops@44410000")',
        'of_find_node_by_path("/thermal@1100b000")',
        "ioremap_wc(GEMINI_MT6797_THERMAL_LEDGER_BASE",
        "thermal_copy_word(target,",
        "memcmp(wire, readback, sizeof(wire))",
    ):
        require(token in owner, f"missing owner gate: {token}")
    require(owner.count("ops->write(context, 0,") == 1,
            "signature publication count changed")
    require(owner.find("ops->write(context, 0,") > owner.find("memcmp(wire, readback"),
            "signature is not published after data readback")
    for forbidden in (
        "cpu_up(", "cpu_down(", "psci", "kernel_restart(", "emergency_restart(",
        "orderly_poweroff(", "filp_open(", "blkdev_get", "mmcblk", "watchdog",
    ):
        require(forbidden not in owner.lower(), f"forbidden owner action: {forbidden}")

    require(tests.count("KUNIT_CASE(") == 6, "ledger KUnit case count changed")
    for token in (
        "accepts_pstore_empty", "accepts_raw_empty", "alternates_crc_copies",
        "rejects_nonempty_and_bad_shape", "terminal_seals_owner",
        "readback_mismatch_seals",
    ):
        require(token in tests, f"missing ledger test: {token}")

    require(transaction_h.count("int (*trace)(void *context") == 1,
            "transaction trace hook changed")
    require("ops->trace" not in between(
        transaction_h,
        "mtk_thermal_transaction_close(void *context,",
        "static inline bool\nmtk_thermal_transaction_ops_valid",
    ), "cleanup gained tracing")
    execute = between(
        transaction_h,
        "mtk_thermal_transaction_execute(void *context,",
        "#endif /* __MTK_AUXADC_THERMAL_INTERNAL_H */",
    )
    hardware_calls = (
        "ops->enable_auxadc_clock(context)",
        "ops->enable_thermal_clock(context)",
        "ops->reset_thermal(context)",
        "ops->configure_apmixed(context)",
        "ops->wait_for_idle(context)",
        "ops->pause_disable_banks(context)",
        "ops->clear_auxadc_channel(context)",
        "ops->prepare_bank(context, bank)",
        "ops->commit_auxadc_channel(context)",
        "ops->enable_bank(context, bank)",
        "ops->release_bank(context, bank)",
        "ops->first_sample(context, bank)",
    )
    positions = []
    for call in hardware_calls:
        require(execute.count(call) == 1, f"hardware call count changed: {call}")
        positions.append(execute.index(call))
    require(positions == sorted(positions), "forward hardware order changed")
    require(execute.count("GEMINI_MT6797_THERMAL_LEDGER_BEFORE") == 12,
            "transaction before-boundary count changed")
    require(execute.count("GEMINI_MT6797_THERMAL_LEDGER_AFTER") == 12,
            "transaction after-boundary count changed")

    require(thermal.count(".trace = mt6797_thermal_trace") == 1,
            "concrete trace hook missing")
    require(thermal.count("gemini_mt6797_thermal_ledger_begin();") == 1,
            "probe begin count changed")
    for operation in operations:
        if operation.startswith("LEDGER_"):
            continue
        require(f"GEMINI_MT6797_THERMAL_{operation}" in thermal or
                f"GEMINI_MT6797_THERMAL_{operation}" in transaction_h,
                f"operation not instrumented: {operation}")
    require(transaction_test.count("KUNIT_CASE(") == 9,
            "transaction KUnit case count changed")
    for token in (
        "trace_success_order", "trace_records_failure",
        "trace_fails_before_effect", "ordinal, 64U",
    ):
        require(token in transaction_test, f"missing trace test: {token}")

    print("source_validation=pass")
    print("owned_record=5")
    print("owned_base=0x44415000")
    print("wire_copies=2")
    print("wire_words_per_copy=12")
    print("maximum_commits=96")
    print("operation_count=23")
    print("transaction_forward_operations=32")
    print("transaction_trace_events_success=64")
    print("ledger_kunit_cases=6")
    print("transaction_kunit_cases=9")
    print("cleanup_trace_events=0")
    print("cpu_or_storage_action=none")


if __name__ == "__main__":
    main()
