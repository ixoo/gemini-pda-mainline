#!/usr/bin/env python3
"""Validate the hardware-free CPU9 down and distinct-restore owner."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"owner_source_validation=fail reason={message}")


def collapse(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def braced(source: str, start: str, label: str) -> str:
    first = source.find(start)
    require(first >= 0, f"{label}: start missing")
    opening = source.find("{", first)
    require(opening >= 0, f"{label}: opening brace missing")
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[first:index + 1]
    raise SystemExit(f"owner_source_validation=fail reason={label}: unterminated")


def ordered(source: str, tokens: tuple[str, ...], label: str) -> None:
    cursor = 0
    for token in tokens:
        position = source.find(token, cursor)
        require(position >= 0, f"{label}: missing/out-of-order {token}")
        cursor = position + len(token)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--require-tests", action="store_true")
    parser.add_argument("--require-terminal-parent-fix", action="store_true")
    args = parser.parse_args()
    root = args.source_root.resolve()
    header = (root / "arch/arm64/include/asm/mt6797_a72_membership.h").read_text(
        encoding="utf-8")
    source = (root / "arch/arm64/kernel/mt6797_a72_membership.c").read_text(
        encoding="utf-8")
    test_path = root / "arch/arm64/kernel/mt6797_a72_membership_test.c"
    test = test_path.read_text(encoding="utf-8") if test_path.is_file() else ""
    mt_psci = (root / "arch/arm64/kernel/mt6797_psci.c").read_text(
        encoding="utf-8")

    require("#define MT6797_A72_ATTEMPT_CPU9_RESTORE BIT(4)" in header,
            "distinct restore attempt missing")
    require("#define MT6797_A72_ATTEMPT_MASK GENMASK(4, 0)" in header,
            "attempt mask does not include restore")
    for name in (
        "mt6797_a72_hotplug_identity",
        "mt6797_a72_hotplug_budgets",
        "mt6797_a72_cpu9_off_proof",
        "mt6797_a72_hotplug_transaction",
        "mt6797_a72_hotplug_snapshot",
    ):
        require(header.count(f"struct {name} {{") == 1,
                f"one {name} definition")

    functions = (
        "mt6797_a72_hotplug_prepare_down",
        "mt6797_a72_hotplug_validate_down",
        "mt6797_a72_hotplug_commit_off",
        "mt6797_a72_hotplug_prove_off",
        "mt6797_a72_hotplug_complete_down",
        "mt6797_a72_hotplug_fail_down",
        "mt6797_a72_hotplug_prepare_restore",
        "mt6797_a72_hotplug_begin_restore",
        "mt6797_a72_hotplug_complete_restore",
        "mt6797_a72_hotplug_fail_restore",
        "mt6797_a72_hotplug_snapshot",
    )
    bodies: list[str] = []
    for name in functions:
        require(header.count(f"{name}(") == 1,
                f"one declaration for {name}")
        require(source.count(f"{name}(") == 1,
                f"one definition for {name}")
        bodies.append(braced(source, f"{name}(", name))

    finalizer = braced(source,
                       "mt6797_a72_finalize_cpu9_success_state(",
                       "initial CPU9 finalizer")
    ordered(collapse(finalizer), (
        "a72_owner.members == (BIT(0) | BIT(1))",
        "a72_owner.phase = MT6797_A72_PHASE_IDLE;",
        "a72_owner.hotplug_phase = MT6797_A72_HOTPLUG_IDLE;",
    ), "hotplug opening after initial CPU9 finalization")

    preflight = collapse(bodies[0])
    parent_validator = (
        "mt6797_a72_cpu9_terminal_parent_valid_locked()"
        if args.require_terminal_parent_fix else
        "mt6797_a72_cpu9_retired_parent_valid_locked(BIT(0) | BIT(1))"
    )
    for token in (
        "cpu != 9 || target != CPUHP_OFFLINE",
        "a72_owner.members != (BIT(0) | BIT(1))",
        "a72_owner.provider_state != MT6797_A72_PROVIDER_HELD",
        parent_validator,
        "!cpu8_online || !cpu9_online",
        "MT6797_A72_ATTEMPT_CPU9_OFF",
        "MT6797_A72_HOTPLUG_OPERATION_CPU9_DOWN",
        "minted.identity.parent_generation",
        "minted.identity.parent_cookie",
    ):
        require(token in preflight, f"down preflight missing {token}")
    ordered(preflight, (
        "a72_owner.attempts_available &= ~MT6797_A72_ATTEMPT_CPU9_OFF;",
        "a72_owner.attempts_consumed |= MT6797_A72_ATTEMPT_CPU9_OFF;",
        "a72_owner.hotplug_active = minted;",
        "a72_owner.hotplug_phase = MT6797_A72_HOTPLUG_DOWN_FROZEN;",
    ), "one-shot down mint")

    if args.require_terminal_parent_fix:
        cpu8_retired = collapse(braced(
            source, "mt6797_a72_cpu8_retired_valid_locked(",
            "CPU8 retired validator"))
        cpu9_parent = collapse(braced(
            source, "mt6797_a72_cpu9_retired_parent_valid_locked(",
            "active CPU9 parent validator"))
        terminal_parent = collapse(braced(
            source, "mt6797_a72_cpu9_terminal_parent_valid_locked(",
            "terminal CPU9 parent validator"))
        for token in (
            "a72_owner.health == MT6797_A72_OWNER_AVAILABLE",
            "a72_owner.members == expected_members",
            "a72_owner.retired_mask & BIT(0)",
            "ARM64_LATE_CPU_STARTUP_OP_CPU8_UP",
            "cpu8->cpu8_success_published",
        ):
            require(token in cpu8_retired,
                    f"CPU8 retired validator missing {token}")
        for token in (
            "!(a72_owner.retired_mask & BIT(1))",
            "mt6797_a72_cpu8_retired_valid_locked(expected_members)",
        ):
            require(token in cpu9_parent,
                    f"active CPU9 parent validator missing {token}")
        for token in (
            "a72_owner.retired_mask == (BIT(0) | BIT(1))",
            "mt6797_a72_cpu8_retired_valid_locked(BIT(0) | BIT(1))",
            "cpu9->valid",
            "cpu9->a36_valid",
            "cpu9->p30_token_valid",
            "cpu9->p17_p18_published",
            "ARM64_LATE_CPU_STARTUP_OP_CPU9_UP",
            "cpu9->identity.target_cpu == 9",
            "cpu9->identity.cpuhp_target == CPUHP_ONLINE",
            "cpu9->identity.target_mpidr == 0x201",
            "cpu9->identity.generation != ~0ULL",
            "cpu9->identity.cookie != ~0ULL",
            "cpu9->identity.generation != cpu8->identity.generation",
            "cpu9->identity.cookie != cpu8->identity.cookie",
            "cpu9->controller_cookie == cpu9->identity.cookie",
            "cpu9->public_preflight == MT6797_A72_PUBLIC_ADMISSION_CLAIMED",
            "cpu9->budgets.cpu_on == MT6797_A72_BUDGET_CONSUMED",
            "mt6797_a72_cpu9_cluster_budgets_empty(cpu9)",
            "!cpu9->p27_valid",
            "!cpu9->provider_acquire_valid",
            "!cpu9->provider_rejection_valid",
            "!cpu9->provider_abort_valid",
            "!cpu9->p28_valid",
            "!cpu9->p29_valid",
            "!cpu9->p32_valid",
            "!cpu9->p32r_valid",
            "!cpu9->cpu8_success_published",
            "cpu9->cpu9_success_published",
        ):
            require(token in terminal_parent,
                    f"terminal CPU9 parent validator missing {token}")
        require("parent = &a72_owner.retired[1];" in preflight,
                "down transaction is not linked to finalized CPU9")

    validate = collapse(bodies[1])
    for token in (
        "!tasks_frozen",
        "target == CPUHP_OFFLINE",
        "cpu8_online && cpu9_online",
        "a72_owner.controller == current",
        "MT6797_A72_HOTPLUG_DOWN_VALIDATED",
    ):
        require(token in validate, f"down validation missing {token}")

    commit = collapse(bodies[2])
    ordered(commit, (
        "budgets.cpu_off == MT6797_A72_BUDGET_AVAILABLE",
        "budgets.cpu_off = MT6797_A72_BUDGET_CONSUMED;",
        "off_committed = 1;",
        "MT6797_A72_HOTPLUG_OFF_COMMITTED",
    ), "CPU_OFF commit budget")

    prove = collapse(bodies[3])
    ordered(prove, (
        "budgets.affinity == MT6797_A72_BUDGET_AVAILABLE",
        "budgets.affinity = MT6797_A72_BUDGET_CONSUMED;",
        "if (!mt6797_a72_hotplug_off_proof_valid_locked(proof))",
        "mt6797_a72_hotplug_fault_locked(-EIO);",
        "off_proven = 1;",
        "MT6797_A72_HOTPLUG_OFF_PROVEN",
    ), "single affinity proof")
    proof_validator = collapse(braced(
        source, "mt6797_a72_hotplug_off_proof_valid_locked(",
        "off proof validator"))
    for token in (
        "affinity_attempted == 1",
        "affinity_level == MT6797_A72_AFFINITY_LEVEL0",
        "affinity_state == MT6797_A72_AFFINITY_STATE_OFF",
        "cpu9_per_core_off == 1",
        "cpu8_responsive == 1",
        "shared_state_unchanged == 1",
        "online_mask_after == BIT(0)",
        "transaction_generation == active->identity.generation",
        "transaction_cookie == active->identity.cookie",
    ):
        require(token in proof_validator, f"off proof missing {token}")

    complete_down = collapse(bodies[4])
    ordered(complete_down, (
        "off_committed == 1",
        "off_proven == 1",
        "cpu8_online && !cpu9_online",
        "a72_owner.members = BIT(0);",
        "mt6797_a72_hotplug_retire_locked(0, MT6797_A72_HOTPLUG_OFFLINE);",
    ), "down completion")

    fail_down = collapse(bodies[5])
    for token in (
        "case MT6797_A72_HOTPLUG_DOWN_FROZEN:",
        "case MT6797_A72_HOTPLUG_DOWN_VALIDATED:",
        "if (!a72_owner.hotplug_active.off_committed)",
        "MT6797_A72_HOTPLUG_REJECTED",
        "case MT6797_A72_HOTPLUG_OFF_COMMITTED:",
        "case MT6797_A72_HOTPLUG_OFF_PROVEN:",
        "mt6797_a72_hotplug_fault_locked(error);",
    ):
        require(token in fail_down, f"down failure boundary missing {token}")

    restore = collapse(bodies[6])
    for token in (
        "cpu != 9 || target != CPUHP_ONLINE",
        "a72_owner.hotplug_phase != MT6797_A72_HOTPLUG_OFFLINE",
        "a72_owner.hotplug_retired_mask != BIT(0)",
        "a72_owner.members != BIT(0)",
        "!cpu8_online || cpu9_online",
        "MT6797_A72_ATTEMPT_CPU9_RESTORE",
        "!a72_owner.next_generation || !a72_owner.next_cookie",
        "a72_owner.next_generation == ~0ULL",
        "a72_owner.next_cookie == ~0ULL",
        "MT6797_A72_HOTPLUG_OPERATION_CPU9_RESTORE",
        "minted.identity.parent_generation = parent->identity.generation;",
        "minted.identity.parent_cookie = parent->identity.cookie;",
        "minted.budgets.cpu_on = MT6797_A72_BUDGET_AVAILABLE;",
    ):
        require(token in restore, f"restore mint missing {token}")
    ordered(restore, (
        "a72_owner.attempts_available &= ~MT6797_A72_ATTEMPT_CPU9_RESTORE;",
        "a72_owner.attempts_consumed |= MT6797_A72_ATTEMPT_CPU9_RESTORE;",
        "MT6797_A72_HOTPLUG_RESTORE_FROZEN",
    ), "distinct restore attempt")

    begin_restore = collapse(bodies[7])
    ordered(begin_restore, (
        "budgets.cpu_on == MT6797_A72_BUDGET_AVAILABLE",
        "budgets.cpu_on = MT6797_A72_BUDGET_CONSUMED;",
        "MT6797_A72_HOTPLUG_RESTORE_ON_ISSUED",
    ), "single restore CPU_ON")
    complete_restore = collapse(bodies[8])
    ordered(complete_restore, (
        "budgets.cpu_on == MT6797_A72_BUDGET_CONSUMED",
        "cpu8_online && cpu9_online",
        "restored = 1;",
        "a72_owner.members = BIT(0) | BIT(1);",
        "mt6797_a72_hotplug_retire_locked(1, MT6797_A72_HOTPLUG_RESTORED);",
    ), "restore completion")
    fail_restore = collapse(bodies[9])
    require("mt6797_a72_hotplug_fault_locked(error);" in fail_restore,
            "restore failure is not terminal")

    physical_scope = "\n".join(bodies)
    for forbidden in (
        "psci_ops", "arm_smccc", "readl(", "writel(", "regmap_",
        "watchdog", "smp_call_function", "cpu_down(", "cpu_up(",
    ):
        require(forbidden not in physical_scope,
                f"hardware-free owner gained effect: {forbidden}")
    for callback in (
        "cpu_down_preflight", "cpu_down_validate", "cpu_down_complete",
        "cpu_down_failed",
    ):
        require(f".{callback}" not in mt_psci,
                f"MT6797 callback unexpectedly bound: {callback}")
    veto = collapse(braced(mt_psci,
                            "static bool mt6797_psci_cpu_can_disable(",
                            "MT6797 disable veto"))
    require(veto.endswith("{ return false; }"), "disable veto opened")

    if args.require_tests:
        cases = (
            "mt6797_a72_hotplug_success_lifecycle",
            "mt6797_a72_hotplug_entry_rejections",
            "mt6797_a72_hotplug_precommit_rejection",
            "mt6797_a72_hotplug_postcommit_fault",
            "mt6797_a72_hotplug_restore_fault",
        )
        for case in cases:
            require(test.count(f"KUNIT_CASE({case})") == 1,
                    f"one KUnit case for {case}")
            require(test.count(f"static void {case}(") == 1,
                    f"one KUnit definition for {case}")
        require("proof.shared_state_unchanged = 0;" in test,
                "postcommit negative proof missing")
        require("mt6797_a72_hotplug_fail_restore(&state->hotplug, -ETIMEDOUT)"
                in collapse(test), "restore terminal failure test missing")

    print("source_phase=hardware-free-cpu9-down-restore-owner")
    print("cpu9_down_attempts=1")
    print("affinity_attempts=1")
    print("cpu9_restore_attempts=1")
    print("precommit_failure=rejected-without-membership-change")
    print("postcommit_failure=reset-only-fault")
    print("restore_identity=distinct-and-parent-linked")
    print("mt6797_callbacks=unset")
    print("mt6797_cpu_can_disable=false")
    print("physical_effect_calls=0")
    print("terminal_parent_validation=" +
          ("pass" if args.require_terminal_parent_fix else "not-requested"))
    print(f"focused_kunit_cases={5 if args.require_tests else 0}")
    print("boot_candidate=false")
    print("device_action=false")
    print("owner_source_validation=pass")


if __name__ == "__main__":
    main()
