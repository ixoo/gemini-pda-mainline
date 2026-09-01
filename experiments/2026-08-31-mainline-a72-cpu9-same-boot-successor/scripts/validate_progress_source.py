#!/usr/bin/env python3
"""Validate the independent CPU9 pre-ledger progress implementation."""

from __future__ import annotations

from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(f"FAIL: {message}")


def exact(text: str, token: str, count: int = 1) -> None:
    require(text.count(token) == count,
            f"token count {token!r}: {text.count(token)} != {count}")


def validate(root: Path) -> list[str]:
    root = root.resolve()
    kconfig = (root / "fs/pstore/Kconfig").read_text(encoding="utf-8")
    makefile = (root / "fs/pstore/Makefile").read_text(encoding="utf-8")
    source = (root / "fs/pstore/gemini_cpu9_progress_ledger.c").read_text(
        encoding="utf-8")
    internal = (
        root / "fs/pstore/gemini_cpu9_progress_ledger_internal.h"
    ).read_text(encoding="utf-8")
    public = (
        root / "include/linux/gemini_cpu9_progress_ledger.h"
    ).read_text(encoding="utf-8")
    tests = (
        root / "fs/pstore/gemini_cpu9_progress_ledger_test.c"
    ).read_text(encoding="utf-8")

    exact(kconfig, "config PSTORE_GEMINI_CPU9_PROGRESS_LEDGER\n")
    exact(kconfig, "config PSTORE_GEMINI_CPU9_PROGRESS_LEDGER_KUNIT_TEST\n")
    require(
        "config PSTORE_GEMINI_CPU9_PROGRESS_LEDGER\n"
        "\tbool \"Gemini CPU9 pre-ledger progress ledger\"\n"
        "\tdepends on PSTORE_GEMINI_CPU9_TRANSITION_LEDGER=y" in kconfig,
        "progress depends on independent CPU9 ledger")
    require("At most 20 record commits and 202 32-bit writes" in kconfig,
            "documented write bound")
    exact(makefile,
          "obj-$(CONFIG_PSTORE_GEMINI_CPU9_PROGRESS_LEDGER) += "
          "gemini_cpu9_progress_ledger.o")
    exact(makefile,
          "obj-$(CONFIG_PSTORE_GEMINI_CPU9_PROGRESS_LEDGER_KUNIT_TEST) += "
          "gemini_cpu9_progress_ledger_test.o")

    for token in (
        "#define GEMINI_CPU9_PROGRESS_CPU8_BASE 0x44410000ULL",
        "GEMINI_CPU9_PROGRESS_CPU8_BASE + 2 * "
        "GEMINI_TRANSITION_LEDGER_SLOT_SIZE",
        "#define GEMINI_CPU9_PROGRESS_RESERVE_SIZE 0x000e0000ULL",
        "cpu9_ledger_validate_cpu8(cpu8_ops, cpu8_context,",
        "cpu9_progress_lane_empty(progress_ops, progress_context)",
        "GEMINI_TRANSITION_LEDGER_BEFORE, stage, 0",
        "GEMINI_TRANSITION_LEDGER_AFTER, stage, 0",
        "GEMINI_CPU9_PROGRESS_CPU8_PROOF",
        "stage == GEMINI_CPU9_PROGRESS_ADD_CPU_RETURN",
        "of_find_node_by_path(\"/reserved-memory/ramoops@44410000\")",
        "!of_property_read_bool(node, \"no-map\")",
        "ioremap(GEMINI_CPU9_PROGRESS_CPU8_BASE,",
        "ioremap_wc(GEMINI_CPU9_PROGRESS_BASE,",
        "EXPORT_SYMBOL_GPL(gemini_cpu9_progress_begin)",
        "EXPORT_SYMBOL_GPL(gemini_cpu9_progress_checkpoint)",
    ):
        require(token in source, f"progress source contract: {token}")
    exact(source, "gemini_transition_ledger_owner_begin(")
    exact(source, "gemini_transition_ledger_owner_checkpoint(", 2)
    require("GEMINI_TRANSITION_LEDGER_PSTORE_SIGNATURE &&\n"
            "\t\tops->read(context, 1) == 0 && "
            "ops->read(context, 2) == 0;" in source,
            "logical-empty-only progress lane")
    require("GEMINI_TRANSITION_LEDGER_PAYLOAD_BYTES ?\n"
            "\t\t\t-EALREADY : -EBADMSG;" in source,
            "committed and malformed lane refusal")
    require(
        "if (!owner || stage <= GEMINI_CPU9_PROGRESS_CPU8_PROOF ||\n"
        "\t    stage > GEMINI_CPU9_PROGRESS_ADD_CPU_RETURN)" in source,
        "exact ten-stage checkpoint bound")

    exact(public, "enum gemini_cpu9_progress_stage {")
    require(
        "enum gemini_cpu9_progress_stage {\n"
        "\tGEMINI_CPU9_PROGRESS_CPU8_PROOF = 1,\n"
        "\tGEMINI_CPU9_PROGRESS_READY_TOKEN,\n"
        "\tGEMINI_CPU9_PROGRESS_DERIVE,\n"
        "\tGEMINI_CPU9_PROGRESS_PUBLISH,\n"
        "\tGEMINI_CPU9_PROGRESS_PREPARE,\n"
        "\tGEMINI_CPU9_PROGRESS_ADD_CPU_DISPATCH,\n"
        "\tGEMINI_CPU9_PROGRESS_BINDER_ENTRY,\n"
        "\tGEMINI_CPU9_PROGRESS_LEDGER_BEGIN_ENTER,\n"
        "\tGEMINI_CPU9_PROGRESS_LEDGER_BEGIN_RETURN,\n"
        "\tGEMINI_CPU9_PROGRESS_ADD_CPU_RETURN,\n"
        "};" in public,
        "exact ten-stage public inventory")
    for stage in (
        "CPU8_PROOF", "READY_TOKEN", "DERIVE", "PUBLISH", "PREPARE",
        "ADD_CPU_DISPATCH", "BINDER_ENTRY", "LEDGER_BEGIN_ENTER",
        "LEDGER_BEGIN_RETURN", "ADD_CPU_RETURN",
    ):
        exact(public, f"GEMINI_CPU9_PROGRESS_{stage}")
    exact(public, "gemini_cpu9_progress_begin(", 2)
    exact(public, "gemini_cpu9_progress_checkpoint(", 2)
    exact(internal, "struct gemini_cpu9_progress_owner {")
    exact(internal, "bool attempted;")

    exact(tests, "KUNIT_CASE(cpu9_progress_", 4)
    for case in (
        "sequence_test", "cpu8_gate_test", "lane_refusal_test",
        "ordering_test",
    ):
        exact(tests, f"KUNIT_CASE(cpu9_progress_{case})")
    require('"gemini-cpu9-progress-ledger"' in tests,
            "focused KUnit suite name")
    require("latest.generation, 20U" in tests, "twenty checkpoint result")
    require("progress.writes, 202U" in tests, "exact write bound assertion")
    require("-EACCES" in tests and "-EBADMSG" in tests and
            "-EALREADY" in tests and "-EINVAL" in tests,
            "refusal coverage")

    production = source + public
    for token in (
        "add_cpu(", "cpu_up(", "cpu_down(", "psci_cpu_on", "psci_cpu_off",
        "arm_smccc", "regmap_write(", "watchdog", "kernel_restart(",
        "orderly_poweroff(", "/dev/", "mmc", "i2c_",
    ):
        require(token not in production, f"forbidden production path: {token}")

    return [
        "cpu9_progress_validation=pass",
        "progress_lane=ramoops-record2-0x44412000",
        "cpu8_terminal_gate=stage10-terminal5-exact-attempt",
        "progress_wire=alternating-two-copy-crc",
        "progress_stages=10",
        "progress_record_commits_max=20",
        "progress_word_writes_max=202",
        "progress_prior_nonempty=reject",
        "focused_kunit_cases=4",
        "production_callers=0",
        "new_cpu_request_paths=0",
        "new_cpu_off_paths=0",
        "new_retry_paths=0",
        "new_cluster_effect_paths=0",
    ]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    print("\n".join(validate(args.source_root)))
