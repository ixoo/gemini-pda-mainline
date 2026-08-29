#!/usr/bin/env python3
"""Validate dormant expected-pair schema and entry-validator source."""

from __future__ import annotations

import argparse
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent


class ValidationError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def function(text: str, signature: str) -> str:
    start = text.find(signature)
    require(start >= 0, f"function absent: {signature}")
    opening = text.find("{", start)
    require(opening >= 0, f"function body absent: {signature}")
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start:index + 1]
    raise ValidationError(f"unterminated function: {signature}")


def validate_schema(root: Path) -> list[str]:
    header = (root / "arch/arm64/include/asm/late_cpu_profile.h").read_text()
    core = (root / "arch/arm64/kernel/late_cpu_profile.c").read_text()
    require(header.count("#define ARM64_LATE_CPU_EXPECTED_PAIR_ABI\t1") == 1,
            "expected-pair ABI changed")
    require(header.count("struct arm64_late_cpu_expected_pair {") == 1,
            "expected-pair schema count changed")
    require(header.count("struct arm64_late_cpu_expected_pair expected_pair;") == 1,
            "evidence does not own one expected pair")
    require("ARM64_LATE_CPU_EXPECT_FIELD_COUNT," in header,
            "field-count terminator missing")
    enum_block = header.split(
        "enum arm64_late_cpu_expected_pair_field {", 1
    )[1].split("};", 1)[0]
    fields = [line for line in enum_block.splitlines()
              if "ARM64_LATE_CPU_EXPECT_" in line]
    require(len(fields) == 29, "28 fields plus terminator not exact")
    require(
        "GENMASK_ULL(ARM64_LATE_CPU_EXPECT_FIELD_COUNT - 1, 0)" in header,
        "field-valid mask is not exact",
    )
    schema = header.split("struct arm64_late_cpu_expected_pair {", 1)[1].split(
        "};", 1
    )[0]
    for token in (
        "u64 source_identity[ARM64_LATE_CPU_ID_WORDS];",
        "u64 capsule_identity[ARM64_LATE_CPU_MAX_TARGETS];",
        "u64 mpidr[ARM64_LATE_CPU_MAX_TARGETS];",
        "u64 clidr_el1;",
        "u64 id_aa64isar1;",
        "u32 id_isar5;",
        "u32 id_mmfr3;",
        "u32 id_pfr1;",
    ):
        require(token in schema, f"schema token absent: {token}")
    require("current-boot observation" in header,
            "prior-cycle provenance comment absent")
    require(".expected_pair" not in header, "schema contains an active initializer")
    storage = function(core, "late_runtime_evidence_storage_empty(")
    require("memchr_inv(&late_runtime_evidence.expected_pair, 0," in storage,
            "private runtime storage does not reject expectations")
    return [
        "expected_pair_abi=1",
        "expected_pair_valid_fields=28",
        "active_expectations=0",
        "runtime_expectation_injection=blocked",
    ]


def validate_validator(root: Path) -> list[str]:
    results = validate_schema(root)
    header = (root / "arch/arm64/include/asm/late_cpu_profile.h").read_text()
    core = (root / "arch/arm64/kernel/late_cpu_profile.c").read_text()
    smp = (root / "arch/arm64/kernel/smp.c").read_text()
    require(header.count("arm64_validate_late_cpu_expected_target") == 2,
            "validator declaration/stub count changed")
    complete = function(core, "late_expected_pair_complete(")
    matcher = function(core, "late_expected_target_matches(")
    validator = function(core, "arm64_validate_late_cpu_expected_target(")
    for token in (
        "expected->abi != ARM64_LATE_CPU_EXPECTED_PAIR_ABI",
        "expected->valid != ARM64_LATE_CPU_EXPECTED_PAIR_VALID_MASK",
        "late_profile_identity_empty(expected->source_identity)",
        "!expected->capsule_identity[target]",
        "expected->mpidr[target] !=",
        "expected->midr !=",
    ):
        require(token in complete, f"complete-contract gate absent: {token}")
    comparisons = (
        "mpidr[target] == mpidr",
        "midr == info->reg_midr",
        "revidr == info->reg_revidr",
        "cntfrq == info->reg_cntfrq",
        "ctr == read_cpuid_cachetype()",
        "dczid == info->reg_dczid",
        "clidr_el1 == read_sysreg(clidr_el1)",
        "id_aa64dfr0 == info->reg_id_aa64dfr0",
        "id_aa64isar0 == info->reg_id_aa64isar0",
        "id_aa64isar1 == info->reg_id_aa64isar1",
        "id_aa64mmfr0 == info->reg_id_aa64mmfr0",
        "id_aa64mmfr1 == info->reg_id_aa64mmfr1",
        "id_aa64pfr0 == info->reg_id_aa64pfr0",
        "id_aa64pfr1 == info->reg_id_aa64pfr1",
        "id_isar0 == aarch32->reg_id_isar0",
        "id_isar1 == aarch32->reg_id_isar1",
        "id_isar2 == aarch32->reg_id_isar2",
        "id_isar3 == aarch32->reg_id_isar3",
        "id_isar4 == aarch32->reg_id_isar4",
        "id_isar5 == aarch32->reg_id_isar5",
        "id_mmfr0 == aarch32->reg_id_mmfr0",
        "id_mmfr1 == aarch32->reg_id_mmfr1",
        "id_mmfr2 == aarch32->reg_id_mmfr2",
        "id_mmfr3 == aarch32->reg_id_mmfr3",
        "id_pfr0 == aarch32->reg_id_pfr0",
        "id_pfr1 == aarch32->reg_id_pfr1",
    )
    for token in comparisons:
        require(token in matcher, f"entry comparison absent: {token}")
    require(matcher.count("expected->") == 26,
            "target-local comparison count changed")
    for token in (
        "/* Pairs with READY publication of late_plan and late_receipt. */",
        "ARM64_LATE_CPU_PROFILE_READY",
        "cpumask_test_cpu(cpu, &late_plan.target_cpus)",
        "cpu != smp_processor_id()",
        "!late_expected_pair_complete(&late_plan)",
        "target == ARM64_LATE_CPU_MAX_TARGETS",
        "this_cpu_ptr(&cpu_data)",
        "? 0 : -ERANGE",
    ):
        require(token in validator, f"validator gate absent: {token}")
    for forbidden in ("cpu_off", "cpu_die_early", "psci", "add_cpu", "retry"):
        require(forbidden not in complete + matcher + validator,
                f"forbidden validator action: {forbidden}")

    call = "expectation_ret = arm64_validate_late_cpu_expected_target(cpu);"
    require(smp.count(call) == 1, "entry validator call count changed")
    require(
        smp.index("cpuinfo_store_cpu();") < smp.index(call)
        < smp.index("store_cpu_topology(cpu);")
        < smp.index("notify_cpu_starting(cpu);")
        < smp.index("set_cpu_online(cpu, true);"),
        "entry validator ordering changed",
    )
    failure = smp[smp.index(call):smp.index("store_cpu_topology(cpu);")]
    require("update_cpu_boot_status(CPU_STUCK_IN_KERNEL);" in failure,
            "failure boot status missing")
    require("cpu_park_loop();" in failure, "failure does not park")
    for forbidden in ("cpu_die_early", "cpu_off", "op_cpu_kill", "psci"):
        require(forbidden not in failure, f"forbidden entry failure action: {forbidden}")
    require(core.count("ARM64_LATE_CPU_EXPECTED_PAIR_ABI") == 1,
            "no active expected-pair producer is allowed")
    results.extend([
        "entry_comparisons=26",
        "entry_location=after-cpuinfo-before-notify-online",
        "entry_failure=boot-status-and-park",
        "cpu_request_paths=0",
        "cpu_off_paths=0",
        "retry_paths=0",
    ])
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--stage", choices=("schema", "validator"), required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    results = validate_schema(root) if args.stage == "schema" else validate_validator(root)
    print(f"validation=mainline-a72-{args.stage}-source-pass")
    for result in results:
        print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
