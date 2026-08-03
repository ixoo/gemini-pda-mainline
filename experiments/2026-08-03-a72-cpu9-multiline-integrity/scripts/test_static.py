#!/usr/bin/env python3
"""Validate the CPU8/CPU9 multiline-integrity source contract and mutations."""

from __future__ import annotations

import argparse
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"error: {message}")


def pattern(writer: int, round_: int, line: int, word: int) -> int:
    mask = (1 << 64) - 1
    value = 0x9E3779B97F4A7C15
    value ^= writer << 60
    value ^= round_ << 32
    value ^= line << 8
    value ^= word
    value ^= (value << 13) & mask
    value ^= value >> 7
    value ^= (value << 17) & mask
    return value & mask


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    args = parser.parse_args()
    source = args.source
    psci = (source / "arch/arm64/kernel/psci.c").read_text()
    cpu = (source / "kernel/cpu.c").read_text()
    hps = (
        source
        / "drivers/misc/mediatek/base/power/mt6797/mt_hotplug_strategy_algo.c"
    ).read_text()

    require(psci.count("gemini-a72-pair-v5") == 2, "pair-v5 inventory changed")
    require(psci.count("gemini-a72-pair-v4") == 0, "obsolete pair-v4 remains")
    require(psci.count("gemini-a72-pair-v2") == 3, "pair-v2 inventory changed")
    for token in (
        "#define MT6797_A72_COH_ROUNDS 1024",
        "#define MT6797_A72_COH_SPIN_BUDGET (1U << 24)",
        "static int mt6797_a72_coh_wait_turn(int expected, unsigned int *budget)",
        "static void mt6797_a72_coh_ipi(void *unused)",
        "smp_call_function_many(&targets, mt6797_a72_coh_ipi, NULL, true);",
        "unsigned long delay = 2000;",
        "msecs_to_jiffies(1000)",
    ):
        require(token in psci, f"scalar parent contract missing: {token}")
    require(
        "if (cpu == 8 || cpu == 9)" in cpu and "return -EPERM;" in cpu,
        "public CPU8/9 veto changed",
    )
    for token in (
        "atomic_cmpxchg(&mt6797_a72_hps_down_reported,",
        "atomic_inc(&mt6797_a72_hps_down_count);",
        "void mt6797_a72_hps_down_snapshot(",
        "hotplug_ret = cpu_down(cpu);",
    ):
        require(token in hps, f"inherited HPS contract missing: {token}")

    for token in (
        "#define MT6797_A72_ML_ROUNDS 64",
        "#define MT6797_A72_ML_LINES 256",
        "#define MT6797_A72_ML_WORDS 8",
        "#define MT6797_A72_ML_SPIN_BUDGET (1U << 24)",
        "#define MT6797_A72_ML_HASH_INIT 1469598103934665603ULL",
        "#define MT6797_A72_ML_HASH_PRIME 1099511628211ULL",
        "u64 words[MT6797_A72_ML_WORDS];",
        "} __aligned(64);",
        "mt6797_a72_ml_data[MT6797_A72_ML_LINES] __aligned(64);",
        "value ^= (u64)writer << 60;",
        "value ^= (u64)round << 32;",
        "value ^= (u64)line << 8;",
        "value ^= (u64)word;",
        "value ^= value << 13;",
        "value ^= value >> 7;",
        "value ^= value << 17;",
        "while (READ_ONCE(mt6797_a72_ml_turn) != expected)",
        "if (!(*budget)--)",
        "WRITE_ONCE(mt6797_a72_ml_data[line].words[word], value);",
        "READ_ONCE(mt6797_a72_ml_data[line].words[word]);",
        "if (actual != expected)",
        "return -EILSEQ;",
        "smp_call_function_many(&targets, mt6797_a72_ml_ipi, NULL, true);",
        "ml_result8.write_hash == ml_result9.read_hash",
        "ml_result9.write_hash == ml_result8.read_hash",
        "hps_reported == 1 && hps_cpu == 9 && hps_error == -EPERM",
        "ml_rounds=64 ml_lines=256 ml_words=8",
        "ml_hash8w=%016llx ml_hash8r=%016llx",
        "ml_hash9w=%016llx ml_hash9r=%016llx",
        "ml_bad_round=%d ml_bad_line=%d ml_bad_word=%d",
        "ml_expected=%016llx ml_actual=%016llx",
    ):
        require(token in psci, f"multiline contract missing: {token}")
    require(psci.count("smp_call_function_many(") == 2, "cross-call count changed")
    require(psci.count("cpumask_set_cpu(8, &targets);") == 1, "CPU8 mask changed")
    require(psci.count("cpumask_set_cpu(9, &targets);") == 1, "CPU9 mask changed")
    require(psci.count("smp_wmb();") >= 6, "write barriers missing")
    require(psci.count("smp_rmb();") >= 3, "read barriers missing")

    vectors = {
        (8, 1, 0, 0): 0x1D9953EF09F34DAD,
        (9, 1, 0, 0): 0x0DB953EF09F34DAD,
        (8, 64, 255, 7): 0x7D9258512A5E9294,
        (9, 64, 255, 7): 0x6DB258512A5E9294,
    }
    for inputs, expected in vectors.items():
        require(pattern(*inputs) == expected, f"pattern vector changed: {inputs}")
    require(len(set(vectors.values())) == len(vectors), "pattern dimensions alias")

    multiline = psci.split("#define MT6797_A72_ML_ROUNDS", 1)[1].split(
        "static void mt6797_a72_hold_workfn", 1
    )[0]
    for forbidden in (
        "cpu_down(",
        "cpu_up(",
        "psci_ops",
        "regulator_",
        "mtk_wdt",
        "writel",
        "writew",
        "writeb",
        "schedule_timeout",
        "msleep",
        "kmalloc",
        "vmalloc",
    ):
        require(forbidden not in multiline, f"multiline path has forbidden action: {forbidden}")

    mutations = {
        "wrong-rounds": psci.replace("#define MT6797_A72_ML_ROUNDS 64", "#define MT6797_A72_ML_ROUNDS 63", 1),
        "wrong-lines": psci.replace("#define MT6797_A72_ML_LINES 256", "#define MT6797_A72_ML_LINES 255", 1),
        "wrong-words": psci.replace("#define MT6797_A72_ML_WORDS 8", "#define MT6797_A72_ML_WORDS 7", 1),
        "unbounded-wait": psci.replace(
            "static int mt6797_a72_ml_wait_turn(int expected, unsigned int *budget)\n"
            "{\n"
            "\twhile (READ_ONCE(mt6797_a72_ml_turn) != expected) {\n"
            "\t\tif (!(*budget)--)\n"
            "\t\t\treturn -ETIMEDOUT;\n",
            "static int mt6797_a72_ml_wait_turn(int expected, unsigned int *budget)\n"
            "{\n"
            "\twhile (READ_ONCE(mt6797_a72_ml_turn) != expected) {\n",
            1,
        ),
        "missing-read-once": psci.replace("READ_ONCE(mt6797_a72_ml_turn)", "mt6797_a72_ml_turn", 1),
        "missing-write-once": psci.replace("WRITE_ONCE(mt6797_a72_ml_turn, 9);", "mt6797_a72_ml_turn = 9;", 1),
        "wrong-pattern-writer": psci.replace("value ^= (u64)writer << 60;", "value ^= (u64)writer << 59;", 1),
        "wrong-pattern-round": psci.replace("value ^= (u64)round << 32;", "value ^= (u64)round << 31;", 1),
        "missing-compare": psci.replace("\t\t\tif (actual != expected) {", "\t\t\tif (false) {", 1),
        "wrong-target": psci.replace("cpumask_set_cpu(9, &targets);", "cpumask_set_cpu(7, &targets);", 1),
        "async-ml": psci.replace("mt6797_a72_ml_ipi, NULL, true);", "mt6797_a72_ml_ipi, NULL, false);", 1),
        "missing-write-barrier": psci.replace("\t\t\tsmp_wmb();\n\t\t\tWRITE_ONCE(mt6797_a72_ml_turn, 9);", "\t\t\tWRITE_ONCE(mt6797_a72_ml_turn, 9);", 1),
        "missing-hash-crosscheck": psci.replace("\t    ml_result8.write_hash == ml_result9.read_hash &&\n", "", 1),
        "missing-parent-gate": psci.replace("\tif (mt6797_a72_coh_passed()) {", "\tif (true) {", 1),
        "non-static-working-set": psci.replace(
            "static struct mt6797_a72_ml_line\n\tmt6797_a72_ml_data",
            "struct mt6797_a72_ml_line\n\tmt6797_a72_ml_data",
            1,
        ),
        "incomplete-terminal": psci.replace(" ml_actual=%016llx", "", 1),
    }
    for name, mutated in mutations.items():
        require(mutated != psci, f"mutation did not apply: {name}")
    require("#define MT6797_A72_ML_ROUNDS 64" not in mutations["wrong-rounds"], "round mutation survived")
    require("#define MT6797_A72_ML_LINES 256" not in mutations["wrong-lines"], "line mutation survived")
    require("#define MT6797_A72_ML_WORDS 8" not in mutations["wrong-words"], "word mutation survived")
    require("if (!(*budget)--" not in mutations["unbounded-wait"].split("mt6797_a72_ml_wait_turn", 1)[1].split("}", 1)[0], "wait mutation survived")
    require("mt6797_a72_ml_turn = 9" in mutations["missing-write-once"], "write mutation failed")
    require("if (false)" in mutations["missing-compare"], "compare mutation failed")
    require("cpumask_set_cpu(7" in mutations["wrong-target"], "target mutation failed")
    require("NULL, false" in mutations["async-ml"], "wait-mode mutation failed")
    require("if (true)" in mutations["missing-parent-gate"], "parent-gate mutation failed")
    require(
        mutations["incomplete-terminal"].count("ml_actual=%016llx")
        == psci.count("ml_actual=%016llx") - 1,
        "terminal mutation did not remove exactly one field",
    )

    print("validation=cpu9-multiline-integrity-source")
    print(f"pattern_vectors={len(vectors)}-passed")
    print(f"mutations={len(mutations)}-rejected")
    print("result=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
