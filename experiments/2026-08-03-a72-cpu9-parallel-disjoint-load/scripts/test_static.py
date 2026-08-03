#!/usr/bin/env python3
"""Validate the CPU8/CPU9 parallel disjoint-load source contract."""

from __future__ import annotations

import argparse
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"error: {message}")


def pattern(writer: int, round_: int, line: int, word: int) -> int:
    mask = (1 << 64) - 1
    value = 0xD6E8FEB86659FD93
    value ^= writer << 60
    value ^= round_ << 32
    value ^= line << 8
    value ^= word
    value ^= (value << 13) & mask
    value ^= value >> 7
    value ^= (value << 17) & mask
    return value & mask


def validate(psci: str, cpu: str, hps: str) -> None:
    require(psci.count("gemini-a72-pair-v6") == 2, "pair-v6 inventory changed")
    require(psci.count("gemini-a72-pair-v5") == 0, "obsolete pair-v5 remains")
    require(psci.count("gemini-a72-pair-v2") == 3, "pair-v2 inventory changed")
    for token in (
        "#define MT6797_A72_ML_ROUNDS 64",
        "#define MT6797_A72_ML_LINES 256",
        "mt6797_a72_ml_result8.write_hash ==",
        "mt6797_a72_ml_result9.read_hash",
        "if (mt6797_a72_ml_passed()) {",
        "hps_reported == 1 && hps_cpu == 9 && hps_error == -EPERM",
    ):
        require(token in psci, f"pair-v5 parent contract missing: {token}")
    require(
        "if (cpu == 8 || cpu == 9)" in cpu and "return -EPERM;" in cpu,
        "public CPU8/9 veto changed",
    )
    for token in (
        "atomic_cmpxchg(&mt6797_a72_hps_down_reported,",
        "atomic_inc(&mt6797_a72_hps_down_count);",
        "hotplug_ret = cpu_down(cpu);",
    ):
        require(token in hps, f"inherited HPS contract missing: {token}")

    for token in (
        "#define MT6797_A72_PL_ROUNDS 128",
        "#define MT6797_A72_PL_LINES 1024",
        "#define MT6797_A72_PL_WORDS 8",
        "#define MT6797_A72_PL_SPIN_BUDGET (1U << 26)",
        "mt6797_a72_pl_data[MT6797_A72_PL_LINES] __aligned(64);",
        "int parity = writer == 8 ? 0 : 1;",
        "for (line = parity; line < MT6797_A72_PL_LINES; line += 2)",
        "while (atomic_read(counter) != expected)",
        "if (!(*budget)--)",
        "WRITE_ONCE(mt6797_a72_pl_data[line].words[word], value);",
        "READ_ONCE(mt6797_a72_pl_data[line].words[word]);",
        "if (actual != expected)",
        "atomic_inc(&mt6797_a72_pl_ready);",
        "smp_wmb();\n\t\tatomic_inc(&mt6797_a72_pl_written);",
        "atomic_inc(&mt6797_a72_pl_written);",
        "atomic_inc(&mt6797_a72_pl_verified);",
        "2 * round, &budget",
        "smp_call_function_many(&targets, mt6797_a72_pl_ipi,",
        "\t\t\t\t\t       NULL, true);",
        "pl_result8.write_hash == pl_result9.read_hash",
        "pl_result9.write_hash == pl_result8.read_hash",
        "pl_ready == 2 * MT6797_A72_PL_ROUNDS",
        "pl_written == 2 * MT6797_A72_PL_ROUNDS",
        "pl_verified == 2 * MT6797_A72_PL_ROUNDS",
        "pl_rounds=128 pl_lines=1024 pl_words=8",
        "pl_bad_round=%d pl_bad_line=%d pl_bad_word=%d",
        "pl_expected=%016llx pl_actual=%016llx",
    ):
        require(token in psci, f"parallel-load contract missing: {token}")
    require(psci.count("smp_call_function_many(") == 3, "cross-call count changed")
    require(psci.count("cpumask_set_cpu(8, &targets);") == 1, "CPU8 mask changed")
    require(psci.count("cpumask_set_cpu(9, &targets);") == 1, "CPU9 mask changed")

    vectors = {
        (8, 1, 0, 0): 0x1200D76628084AA8,
        (9, 1, 1, 0): 0x0220D726AA2C0BAA,
        (8, 128, 1022, 7): 0x13902DDF6542D293,
        (9, 128, 1023, 7): 0x03B02D9FE7669391,
    }
    for inputs, expected in vectors.items():
        require(pattern(*inputs) == expected, f"pattern vector changed: {inputs}")
    require(len(set(vectors.values())) == len(vectors), "pattern dimensions alias")

    parallel = psci.split("#define MT6797_A72_PL_ROUNDS", 1)[1].split(
        "static void mt6797_a72_coh_workfn", 1
    )[0]
    for forbidden in (
        "cpu_down(", "cpu_up(", "psci_ops", "regulator_", "mtk_wdt",
        "writel", "writew", "writeb", "schedule_timeout", "msleep",
        "kmalloc", "vmalloc",
    ):
        require(forbidden not in parallel, f"parallel path has forbidden action: {forbidden}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    args = parser.parse_args()
    psci = (args.source / "arch/arm64/kernel/psci.c").read_text()
    cpu = (args.source / "kernel/cpu.c").read_text()
    hps = (
        args.source
        / "drivers/misc/mediatek/base/power/mt6797/mt_hotplug_strategy_algo.c"
    ).read_text()
    validate(psci, cpu, hps)

    mutations = {
        "wrong-rounds": ("#define MT6797_A72_PL_ROUNDS 128", "#define MT6797_A72_PL_ROUNDS 127"),
        "wrong-lines": ("#define MT6797_A72_PL_LINES 1024", "#define MT6797_A72_PL_LINES 1023"),
        "wrong-words": ("#define MT6797_A72_PL_WORDS 8", "#define MT6797_A72_PL_WORDS 7"),
        "wrong-parity": ("int parity = writer == 8 ? 0 : 1;", "int parity = writer == 8 ? 1 : 0;"),
        "wrong-stride": ("line += 2", "line += 1"),
        "unbounded-wait": ("\t\tif (!(*budget)--)\n\t\t\treturn -ETIMEDOUT;\n", ""),
        "missing-read-once": ("READ_ONCE(mt6797_a72_pl_data[line].words[word])", "mt6797_a72_pl_data[line].words[word]"),
        "missing-write-once": ("WRITE_ONCE(mt6797_a72_pl_data[line].words[word], value);", "mt6797_a72_pl_data[line].words[word] = value;"),
        "wrong-barrier-target": ("2 * round, &budget", "2 * round - 1, &budget"),
        "missing-counter": ("\t\tatomic_inc(&mt6797_a72_pl_written);\n", ""),
        "missing-write-barrier": ("\t\tsmp_wmb();\n\t\tatomic_inc(&mt6797_a72_pl_written);", "\t\tatomic_inc(&mt6797_a72_pl_written);"),
        "missing-compare": ("\t\t\tif (actual != expected) {", "\t\t\tif (false) {"),
        "wrong-target": ("cpumask_set_cpu(9, &targets);", "cpumask_set_cpu(7, &targets);"),
        "async-parallel": ("\t\t\t\t\t       NULL, true);", "\t\t\t\t\t       NULL, false);"),
        "missing-parent-gate": ("\t\tif (mt6797_a72_ml_passed()) {", "\t\tif (true) {"),
        "missing-hash-crosscheck": ("\t    pl_result8.write_hash == pl_result9.read_hash &&\n", ""),
        "non-static-working-set": ("static struct mt6797_a72_pl_line\n\tmt6797_a72_pl_data", "struct mt6797_a72_pl_line\n\tmt6797_a72_pl_data"),
        "incomplete-terminal": (" pl_actual=%016llx", ""),
    }
    for name, (old, new) in mutations.items():
        require(psci.count(old) >= 1, f"mutation anchor absent: {name}")
        mutated = psci.replace(old, new, 1)
        try:
            validate(mutated, cpu, hps)
        except SystemExit:
            continue
        raise SystemExit(f"error: mutation was not rejected: {name}")

    print("validation=cpu9-parallel-disjoint-load-source")
    print(f"pattern_vectors={len(vectors)}-passed")
    print(f"mutations={len(mutations)}-rejected")
    print("result=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
