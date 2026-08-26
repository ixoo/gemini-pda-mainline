#!/usr/bin/env python3
"""Validate generated Gemini retained transition-ledger source."""

from __future__ import annotations

import argparse
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--phase", choices=("production", "tests"),
                        required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    kconfig = (root / "fs/pstore/Kconfig").read_text(encoding="utf-8")
    makefile = (root / "fs/pstore/Makefile").read_text(encoding="utf-8")
    ram = (root / "fs/pstore/ram.c").read_text(encoding="utf-8")
    source = (root / "fs/pstore/gemini_transition_ledger.c").read_text(
        encoding="utf-8")
    internal = (root / "fs/pstore/gemini_transition_ledger_internal.h").read_text(
        encoding="utf-8")
    public = (root / "include/linux/gemini_transition_ledger.h").read_text(
        encoding="utf-8")

    require(kconfig.count("config PSTORE_GEMINI_TRANSITION_LEDGER\n") == 1,
            "production Kconfig")
    require("select CRC32" in kconfig, "CRC32 dependency")
    require(makefile.count("gemini_transition_ledger.o") == 1,
            "production object")
    require(ram.count("#ifdef CONFIG_PSTORE_GEMINI_TRANSITION_LEDGER") == 1,
            "isolated Gemini ramoops bypass")
    for token in (
        "GEMINI_TRANSITION_LEDGER_BASE 0x44410000ULL",
        "GEMINI_TRANSITION_LEDGER_RESERVE_SIZE 0x000e0000ULL",
        "GEMINI_TRANSITION_LEDGER_PAYLOAD_BYTES",
        "GEMINI_TRANSITION_LEDGER_COPIES 2U",
        "GEMINI_TRANSITION_LEDGER_COPY_WORDS 9U",
        "crc32_le(~0U",
        "target = owner->have_valid ? owner->newest_copy ^ 1U : 0;",
        "GEMINI_TRANSITION_LEDGER_INTEGRITY_WORD), 0);",
        "gemini_transition_ledger_integrity(wire)",
        "owner->sealed = true;",
        "owner->last_stage + 1 == stage",
        "void (*sync)(void *context);",
        "EXPORT_SYMBOL_GPL(gemini_transition_ledger_begin)",
        "EXPORT_SYMBOL_GPL(gemini_transition_ledger_checkpoint)",
    ):
        require(token in source + internal, f"production token: {token}")
    invalidate = source.index("GEMINI_TRANSITION_LEDGER_INTEGRITY_WORD), 0);")
    payload = source.index("for (word = 0; word <", invalidate)
    commit = source.index("le32_to_cpu(wire[", payload)
    require(invalidate < payload < commit,
            "invalidate, payload, integrity ordering")
    require(source.count("gemini_transition_ledger_begin(") == 1,
            "begin definition only; no caller")
    require(source.count("gemini_transition_ledger_checkpoint(") == 1,
            "checkpoint definition only; no caller")
    require("release" not in public, "no release API")
    for token in ("cpu_up(", "add_cpu(", "psci_", "watchdog", "arm_smccc"):
        require(token not in source, f"forbidden production effect: {token}")
    require("->barrier(" not in source,
            "no collision with the architecture barrier() macro")

    if args.phase == "tests":
        test_source = (root / "fs/pstore/gemini_transition_ledger_test.c").read_text(
            encoding="utf-8")
        require(kconfig.count(
            "config PSTORE_GEMINI_TRANSITION_LEDGER_KUNIT_TEST\n") == 1,
            "test Kconfig")
        require(makefile.count("gemini_transition_ledger_test.o") == 1,
                "test object")
        require(test_source.count(
            "KUNIT_CASE(gemini_transition_ledger_") == 6,
            "six focused cases")
        for token in (
            '"gemini-transition-ledger"',
            "gemini_transition_ledger_sequence_test",
            "gemini_transition_ledger_raw_header_test",
            "gemini_transition_ledger_rejections_test",
            "gemini_transition_ledger_torn_write_test",
            "gemini_transition_ledger_corrupt_copy_test",
            "gemini_transition_ledger_terminal_one_shot_test",
            "latest.generation, 19U",
            "last_write_word",
        ):
            require(token in test_source, f"test token: {token}")
        require("GEMINI_LEDGER_TEST_WRITES" not in test_source,
                "no unused full write-history stack fixture")
        for token in ("ioremap", "readl(", "writel(", "msleep", "udelay",
                      "cpu_up(", "psci_", "watchdog"):
            require(token not in test_source,
                    f"hardware-free test token: {token}")
    else:
        require("PSTORE_GEMINI_TRANSITION_LEDGER_KUNIT_TEST\n\tbool" not in
                kconfig, "tests absent from production phase")
        require(not (root / "fs/pstore/gemini_transition_ledger_test.c").exists(),
                "test source absent")

    print(f"source_phase={args.phase}")
    print("retained_zone_count=1")
    print("alternating_copies=2")
    print("wire_words_per_copy=9")
    print("success_checkpoint_updates=19")
    print("production_callers=0")
    print("physical_retained_writes=0")
    print("device_action=none")
    print("source_validation=pass")


if __name__ == "__main__":
    main()
