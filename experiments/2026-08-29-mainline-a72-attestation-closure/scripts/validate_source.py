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
    require(signature.endswith("("), f"invalid function signature: {signature}")
    search = 0
    while True:
        start = text.find(signature, search)
        require(start >= 0, f"function absent: {signature}")
        parameter = start + len(signature) - 1
        parameter_depth = 0
        closing = -1
        for index in range(parameter, len(text)):
            if text[index] == "(":
                parameter_depth += 1
            elif text[index] == ")":
                parameter_depth -= 1
                if parameter_depth == 0:
                    closing = index
                    break
        require(closing >= 0, f"unterminated parameters: {signature}")
        opening = closing + 1
        while opening < len(text) and text[opening].isspace():
            opening += 1
        if opening < len(text) and text[opening] == "{":
            break
        search = start + len(signature)
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


def validate_runtime_fix(root: Path) -> list[str]:
    results = validate_validator(root)
    core = (root / "arch/arm64/kernel/late_cpu_profile.c").read_text()
    complete = function(core, "late_expected_pair_complete(")
    require(
        "!memchr_inv(expected->source_identity, 0," in complete
        and "sizeof(expected->source_identity)" in complete,
        "runtime-safe source-identity empty check absent",
    )
    require(
        "late_profile_identity_empty(expected->source_identity)" not in complete,
        "runtime validator retains an init-only helper call",
    )
    results.append("entry_identity_check=runtime-safe")
    return results


def validate_stack_fix(root: Path) -> list[str]:
    results = validate_runtime_fix(root)
    core = (root / "arch/arm64/kernel/late_cpu_profile.c").read_text()
    prepare = function(core, "arm64_prepare_late_cpu_profile(")
    require(
        "static struct arm64_late_cpu_evidence profile_evidence __initdata;"
        in core,
        "prepare evidence workspace is not reclaimable static storage",
    )
    require(
        "static struct arm64_late_cpu_plan draft __initdata;" in core,
        "plan draft workspace is not reclaimable static storage",
    )
    require(
        "struct arm64_late_cpu_evidence profile_evidence =" not in prepare
        and "struct arm64_late_cpu_plan draft =" not in prepare,
        "whole prepare workspace remains on the stack",
    )
    for token in (
        "memset(&profile_evidence, 0, sizeof(profile_evidence));",
        "profile_evidence.abi = ARM64_LATE_CPU_PLAN_ABI;",
        "memset(&draft, 0, sizeof(draft));",
        "draft.abi = ARM64_LATE_CPU_PLAN_ABI;",
    ):
        require(token in prepare, f"prepare workspace reset absent: {token}")
    require(
        prepare.index("memset(&profile_evidence")
        < prepare.index("late_profile.prepare(&profile_evidence"),
        "evidence workspace is not reset before profile preparation",
    )
    results.append("prepare_workspaces=static-initdata-reset")
    return results


def validate_system_policy(root: Path) -> list[str]:
    results = validate_stack_fix(root)
    header = (root / "arch/arm64/include/asm/late_cpu_profile.h").read_text()
    core = (root / "arch/arm64/kernel/late_cpu_profile.c").read_text()
    cpufeature = (root / "arch/arm64/kernel/cpufeature.c").read_text()
    proton = (root / "arch/arm64/kernel/proton-pack.c").read_text()
    smp = (root / "arch/arm64/kernel/smp.c").read_text()

    for token in (
        "arm64_collect_late_cpu_runtime_system_policy(void);",
        "arm64_late_cpu_collect_system(",
        "arm64_late_cpu_collect_policy(",
    ):
        require(header.count(token) == 1,
                f"system-policy declaration count changed: {token}")
    require(header.count(
        "arm64_collect_late_cpu_runtime_system_policy(void)"
    ) == 2, "system-policy declaration/stub count changed")

    system_owner = function(
        cpufeature, "arm64_late_cpu_collect_system("
    )
    for token in (
        "system_capabilities_finalized()",
        "memchr_inv(system, 0, sizeof(*system))",
        "read_sanitised_ftr_reg(SYS_ID_AA64PFR1_EL1)",
        "ID_AA64PFR1_EL1_SSBS_SHIFT",
        "if (ssbs > 2)",
        "system->ctr_sys_val = arm64_ftr_reg_ctrel0.sys_val;",
        "system->ctr_strict_mask = arm64_ftr_reg_ctrel0.strict_mask;",
        "system->ssbs = !!ssbs;",
        "ARM64_LATE_CPU_SYSTEM_CAP_CTR_VALID",
        "ARM64_LATE_CPU_SYSTEM_CAP_SSBS_VALID",
    ):
        require(token in system_owner, f"system owner gate absent: {token}")
    for forbidden in ("read_cpuid_cachetype", "read_sysreg_s", "0xb4448004"):
        require(forbidden not in system_owner,
                f"system owner bypasses sanitized state: {forbidden}")

    state_map = function(proton, "late_cpu_current_mitigation_state(")
    conduit_map = function(proton, "late_cpu_current_smccc_conduit(")
    v4_map = function(proton, "late_cpu_current_v4_policy(")
    mitigation_owner = function(
        proton, "arm64_late_cpu_collect_policy("
    )
    for source, tokens in (
        (state_map, (
            "case SPECTRE_UNAFFECTED:",
            "ARM64_LATE_CPU_MITIGATION_UNAFFECTED",
            "case SPECTRE_MITIGATED:",
            "ARM64_LATE_CPU_MITIGATION_MITIGATED",
            "case SPECTRE_VULNERABLE:",
            "ARM64_LATE_CPU_MITIGATION_VULNERABLE",
            "return -ERANGE;",
        )),
        (conduit_map, (
            "arm_smccc_1_1_get_conduit()",
            "case SMCCC_CONDUIT_NONE:",
            "ARM64_LATE_CPU_SMCCC_NONE",
            "case SMCCC_CONDUIT_SMC:",
            "ARM64_LATE_CPU_SMCCC_SMC",
            "case SMCCC_CONDUIT_HVC:",
            "ARM64_LATE_CPU_SMCCC_HVC",
            "return -ERANGE;",
        )),
        (v4_map, (
            "READ_ONCE(__spectre_v4_policy)",
            "SPECTRE_V4_POLICY_MITIGATION_DYNAMIC",
            "ARM64_LATE_CPU_V4_POLICY_DYNAMIC",
            "SPECTRE_V4_POLICY_MITIGATION_ENABLED",
            "ARM64_LATE_CPU_V4_POLICY_FORCE_ON",
            "SPECTRE_V4_POLICY_MITIGATION_DISABLED",
            "ARM64_LATE_CPU_V4_POLICY_FORCE_OFF",
            "return -ERANGE;",
        )),
    ):
        for token in tokens:
            require(token in source, f"owner mapping absent: {token}")
    for token in (
        "READ_ONCE(system_bhb_mitigations)",
        "bhb_methods & ~GENMASK(BHB_INSN, BHB_LOOP)",
        "system_capabilities_finalized()",
        "arm64_get_spectre_v2_state()",
        "arm64_get_spectre_v4_state()",
        "arm64_get_spectre_bhb_state()",
        "policy->mitigations_off = cpu_mitigations_off();",
        "policy->nospectre_v2 = READ_ONCE(__nospectre_v2);",
        "policy->valid = ARM64_LATE_CPU_TARGET_POLICY_VALID_MASK;",
        "get_spectre_bhb_loop_value()",
        "system->bhb_system_method = bhb_methods;",
        "ARM64_LATE_CPU_SYSTEM_CAP_EFFECTS_VALID",
    ):
        require(token in mitigation_owner,
                f"mitigation owner gate absent: {token}")
    require("saved_command_line" not in mitigation_owner + conduit_map + v4_map,
            "policy was reconstructed from command-line text")

    collect = function(
        core, "arm64_collect_late_cpu_runtime_system_policy("
    )
    complete = function(core, "late_runtime_system_policy_complete(")
    storage = function(core, "late_runtime_evidence_storage_complete(")
    seal = function(core, "arm64_seal_late_cpu_runtime_evidence(")
    prepare = function(core, "arm64_prepare_late_cpu_profile(")
    for token in (
        "LATE_RUNTIME_EVIDENCE_OPEN",
        "LATE_RUNTIME_IDENTITY_UNCOLLECTED",
        "system_capabilities_finalized()",
        "cpus_have_cap(ARM64_ALWAYS_SYSTEM)",
        "late_runtime_evidence_storage_empty()",
        "arm64_late_cpu_collect_system(&system)",
        "arm64_late_cpu_collect_policy(&policy, &system)",
        "system.valid != ARM64_LATE_CPU_SYSTEM_CAP_VALID_MASK",
        "policy.valid != ARM64_LATE_CPU_TARGET_POLICY_VALID_MASK",
        "late_runtime_evidence.system_cap = system;",
        "target < ARM64_LATE_CPU_MAX_TARGETS",
        "late_runtime_evidence.target_policy[target] = policy;",
    ):
        require(token in collect, f"core collection gate absent: {token}")
    for token in (
        "system->valid != ARM64_LATE_CPU_SYSTEM_CAP_VALID_MASK",
        "!system->ctr_strict_mask",
        "system->ssbs > 1",
        "ARM64_LATE_CPU_MITIGATION_UNAFFECTED",
        "ARM64_LATE_CPU_MITIGATION_VULNERABLE",
        "ARM64_LATE_CPU_BHB_STATE_UNAFFECTED",
        "ARM64_LATE_CPU_BHB_STATE_VULNERABLE",
        "system->bhb_system_method & ~GENMASK(3, 0)",
        "first->valid != ARM64_LATE_CPU_TARGET_POLICY_VALID_MASK",
        "memcmp(first, &late_runtime_evidence.target_policy[target]",
    ):
        require(token in complete, f"sealed completeness gate absent: {token}")
    for token in (
        "late_runtime_evidence.blocker_mask",
        "!late_runtime_system_policy_complete()",
        "memchr_inv(&late_runtime_evidence.target_cap[target], 0,",
    ):
        require(token in storage, f"sealed storage gate absent: {token}")
    require("late_runtime_evidence_storage_complete()" in seal,
            "seal does not require a complete system-policy record")
    require("late_runtime_evidence_storage_empty()" not in seal,
            "seal still requires an empty runtime record")
    for token in (
        "LATE_RUNTIME_EVIDENCE_SEALED_SYSTEM_POLICY",
        "LATE_RUNTIME_EVIDENCE_SEALED_IDENTITY_SYSTEM_POLICY",
    ):
        require(token in core, f"sealed state absent: {token}")
    require("LATE_RUNTIME_EVIDENCE_SEALED_EMPTY" not in core,
            "empty sealed state remains reachable")
    require("LATE_RUNTIME_EVIDENCE_SEALED_IDENTITY," not in core,
            "identity-only sealed state remains reachable")

    ordering_tokens = (
        "if (!late_profile_runtime_fields_empty(&profile_evidence))",
        "late_profile_identity_cross_bound(",
        "draft.evidence.binding = late_runtime_evidence.binding;",
        "draft.evidence.system_cap =\n"
        "\t\t\t\tlate_runtime_evidence.system_cap;",
        "draft.evidence.target_policy[target] =",
    )
    for token in ordering_tokens:
        require(token in prepare, f"runtime merge gate absent: {token}")
    runtime_reject, cross_bind, binding_merge, system_merge, policy_merge = (
        prepare.index(token) for token in ordering_tokens
    )
    require(runtime_reject < cross_bind < binding_merge < system_merge < policy_merge,
            "runtime system-policy merge is not cross-bound and ordered")
    require(
        "runtime_state ==\n"
        "\t\t    LATE_RUNTIME_EVIDENCE_SEALED_IDENTITY_SYSTEM_POLICY"
        in prepare,
        "unbound system-policy evidence can reach the draft",
    )

    collect_call = "arm64_collect_late_cpu_runtime_system_policy();"
    require(smp.count(collect_call) == 1,
            "system-policy collection call count changed")
    require(
        smp.index("arm64_collect_late_cpu_runtime_identity();")
        < smp.index(collect_call)
        < smp.index("arm64_seal_late_cpu_runtime_evidence();")
        < smp.index("arm64_prepare_late_cpu_profile();")
        < smp.index("setup_system_features();"),
        "system-policy collection lifecycle changed",
    )

    owned = system_owner + state_map + conduit_map + v4_map + mitigation_owner
    private = collect + complete + storage + seal
    for forbidden in (
        "cpu_on", "cpu_off", "psci", "add_cpu", "retry",
        "ARM64_LATE_CPU_PROFILE_READY", "arm64_commit_late_cpu_profile",
    ):
        require(forbidden not in owned + private,
                f"slice 3 contains a forbidden later-stage action: {forbidden}")
    results.extend([
        "system_cap_owner=cpufeature-sanitized-state",
        "target_policy_owner=proton-pack-private-state",
        "system_policy_seal=complete-or-fault",
        "system_policy_merge=identity-cross-bound",
        "target_cap_producer=absent",
        "architecture_commit=absent",
        "ready_publication=unchanged",
    ])
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument(
        "--stage",
        choices=("schema", "validator", "runtime-fix", "stack-fix",
                 "system-policy"),
        required=True,
    )
    args = parser.parse_args()
    root = args.source_root.resolve()
    if args.stage == "schema":
        results = validate_schema(root)
    elif args.stage == "validator":
        results = validate_validator(root)
    elif args.stage == "runtime-fix":
        results = validate_runtime_fix(root)
    elif args.stage == "stack-fix":
        results = validate_stack_fix(root)
    else:
        results = validate_system_policy(root)
    print(f"validation=mainline-a72-{args.stage}-source-pass")
    for result in results:
        print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
