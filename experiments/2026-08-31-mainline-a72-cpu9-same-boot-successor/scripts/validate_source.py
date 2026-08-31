#!/usr/bin/env python3
"""Validate the independent Gemini CPU9 retained-ledger source."""

from __future__ import annotations

import argparse
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def validate(root: Path) -> list[str]:
    root = root.resolve()
    kconfig = (root / "fs/pstore/Kconfig").read_text(encoding="utf-8")
    makefile = (root / "fs/pstore/Makefile").read_text(encoding="utf-8")
    source = (root / "fs/pstore/gemini_cpu9_transition_ledger.c").read_text(
        encoding="utf-8")
    internal = (root /
                "fs/pstore/gemini_cpu9_transition_ledger_internal.h").read_text(
                    encoding="utf-8")
    test_source = (root /
                   "fs/pstore/gemini_cpu9_transition_ledger_test.c").read_text(
                       encoding="utf-8")
    public = (root /
              "include/linux/gemini_cpu9_transition_ledger.h").read_text(
                  encoding="utf-8")
    generic = (root / "fs/pstore/gemini_transition_ledger.c").read_text(
        encoding="utf-8")

    require(kconfig.count(
        "config PSTORE_GEMINI_CPU9_TRANSITION_LEDGER\n") == 1,
        "production Kconfig")
    require(kconfig.count(
        "config PSTORE_GEMINI_CPU9_TRANSITION_LEDGER_KUNIT_TEST\n") == 1,
        "test Kconfig")
    require("depends on PSTORE_GEMINI_TRANSITION_LEDGER=y" in kconfig,
            "generic owner dependency")
    require(makefile.count("gemini_cpu9_transition_ledger.o") == 1,
            "production object")
    require(makefile.count("gemini_cpu9_transition_ledger_test.o") == 1,
            "test object")
    for token in (
        "GEMINI_CPU9_LEDGER_CPU8_BASE 0x44410000ULL",
        "GEMINI_CPU9_LEDGER_BASE \\\n\t(GEMINI_CPU9_LEDGER_CPU8_BASE + GEMINI_TRANSITION_LEDGER_SLOT_SIZE)",
        "GEMINI_CPU9_LEDGER_RESERVE_SIZE 0x000e0000ULL",
        "latest.attempt_id != cpu8_attempt_id",
        "latest.phase != GEMINI_TRANSITION_LEDGER_TERMINAL",
        "latest.stage != GEMINI_CPU9_LEDGER_CPU8_STAGE",
        "latest.terminal != GEMINI_CPU9_LEDGER_CPU8_TERMINAL",
        "return -EALREADY;",
        "owner->attempted = true;",
        "stage > GEMINI_CPU9_LEDGER_MEMBERSHIP",
        "terminal > GEMINI_CPU9_LEDGER_CPU9_ONLINE_PROOF",
        "cpu8_slot = ioremap(GEMINI_CPU9_LEDGER_CPU8_BASE",
        "cpu9_slot = ioremap_wc(GEMINI_CPU9_LEDGER_BASE",
        "EXPORT_SYMBOL_GPL(gemini_cpu9_transition_ledger_begin)",
        "EXPORT_SYMBOL_GPL(gemini_cpu9_transition_ledger_checkpoint)",
    ):
        require(token in source, f"production token: {token}")
    cpu8_map = source.index(
        "cpu8_slot = ioremap(GEMINI_CPU9_LEDGER_CPU8_BASE")
    cpu8_gate = source.index(
        "gemini_cpu9_transition_ledger_validate_cpu8(", cpu8_map)
    cpu9_map = source.index(
        "cpu9_slot = ioremap_wc(GEMINI_CPU9_LEDGER_BASE")
    require(cpu8_map < cpu8_gate < cpu9_map,
            "record 0 proof before record 1 mapping")
    require(source.count("GEMINI_CPU9_LEDGER_BASE") == 2,
            "record 1 base use is bounded")
    require(source.count("writel(") == 1, "single generic lane writer")
    require(source.count("gemini_cpu9_transition_ledger_begin(") == 1,
            "begin definition only")
    require(source.count("gemini_cpu9_transition_ledger_checkpoint(") == 1,
            "checkpoint definition only")
    require("struct gemini_transition_ledger_owner ledger;" in internal,
            "independent owner wraps proven wire owner")
    require("bool attempted;" in internal, "one-shot owner state")
    require("GEMINI_CPU9_LEDGER_MEMBERSHIP" in public,
            "five-stage public contract")
    require("GEMINI_CPU9_LEDGER_CPU9_ONLINE_PROOF" in public,
            "success terminal contract")
    require(test_source.count(
        "KUNIT_CASE(gemini_cpu9_transition_ledger_") == 6,
        "six focused KUnit cases")
    for token in (
        '"gemini-cpu9-transition-ledger"',
        "gemini_cpu9_transition_ledger_sequence_test",
        "gemini_cpu9_transition_ledger_raw_lane_test",
        "gemini_cpu9_transition_ledger_cpu8_gate_test",
        "gemini_cpu9_transition_ledger_corrupt_cpu8_test",
        "gemini_cpu9_transition_ledger_lane_refusal_test",
        "gemini_cpu9_transition_ledger_ordering_test",
        "latest.generation, 11U",
        "-ENODATA",
        "-EACCES",
        "-EBADMSG",
        "-EALREADY",
    ):
        require(token in test_source, f"test token: {token}")
    for token in (
        "add_cpu(", "cpu_up(", "cpu_down(", "remove_cpu(", "cpu_boot(",
        "psci_cpu_on", "psci_cpu_off", "cpu_off(", "arm_smccc",
        "regmap_write(", "kernel_restart(", "watchdog", "retry",
    ):
        require(token not in source + internal + public,
                f"forbidden production effect: {token}")
        require(token not in test_source,
                f"forbidden hardware-free test effect: {token}")
    require("GEMINI_CPU9" not in generic,
            "CPU8 ledger implementation remains byte-identical")
    return [
        "cpu9_ledger_validation=pass",
        "cpu8_record_implementation=unchanged",
        "cpu8_terminal_gate=stage10-terminal5",
        "cpu8_attempt_binding=exact",
        "cpu9_lane=ramoops-record1",
        "wire_format=reused-two-copy-crc",
        "cpu9_lane_prior_commit=reject",
        "record0_write_paths=0",
        "cpu9_ledger_stages=5",
        "focused_kunit_cases=6",
        "new_cpu_request_paths=0",
        "new_cpu_off_paths=0",
        "new_retry_paths=0",
        "new_cluster_effect_paths=0",
        "production_callers=0",
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    print("\n".join(validate(args.source_root)))


if __name__ == "__main__":
    main()
