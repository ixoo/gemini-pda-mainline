#!/usr/bin/env python3
"""Validate the owner-local Gemini CPU9 membership source boundary."""

from __future__ import annotations

from pathlib import Path


CHANGED_PATHS = (
    "arch/arm64/Kconfig.platforms",
    "arch/arm64/include/asm/mt6797_a72_membership.h",
    "arch/arm64/kernel/mt6797_a72_membership.c",
    "arch/arm64/kernel/mt6797_a72_membership_test.c",
)
FORBIDDEN = (
    "add_cpu(", "cpu_up(", "cpu_down(", "cpu_boot(", "psci_cpu_on",
    "psci_cpu_off", "cpu_off(", "arm_smccc", "regmap_write(",
    "watchdog", "kernel_restart(", "schedule_delayed_work(",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def exact(text: str, token: str, count: int = 1) -> None:
    require(text.count(token) == count,
            f"unexpected token count ({text.count(token)} != {count}): {token}")


def validate(root: Path) -> list[str]:
    root = root.resolve()
    files = {}
    for relative in CHANGED_PATHS:
        path = root / relative
        require(path.is_file() and not path.is_symlink(),
                f"changed source absent or unsafe: {relative}")
        files[relative] = path.read_text(encoding="utf-8")

    kconfig = files[CHANGED_PATHS[0]]
    header = files[CHANGED_PATHS[1]]
    source = files[CHANGED_PATHS[2]]
    tests = files[CHANGED_PATHS[3]]
    new_source = source[source.index(
        "#if IS_ENABLED(CONFIG_ARM64_MT6797_A72_CPU9_MEMBERSHIP)"):]

    exact(kconfig, "config ARM64_MT6797_A72_CPU9_MEMBERSHIP\n")
    for token in (
        "depends on ARM64_MT6797_A72_DERIVED_ADMISSION",
        "depends on MTK_MT6797_A72_DEFAULT_OFF_BINDER",
        "This option adds no caller, CPU request, CPU_OFF, watchdog action,",
    ):
        exact(kconfig, token)

    exact(header, "#define MT6797_A72_TRANSACTION_ABI 4\n")
    require("#define MT6797_A72_TRANSACTION_ABI 3\n" not in header,
            "old transaction ABI remained")
    exact(header, "enum mt6797_a72_cpu9_derive_stage {")
    exact(header, "\tu32 cpu9_success_published;\n")
    for symbol in (
        "mt6797_a72_membership_derive_cpu9(",
        "mt6797_a72_membership_derive_cpu9_diagnostic(",
        "mt6797_a72_membership_publish_cpu9(",
        "mt6797_a72_membership_preflight_cpu9(",
        "mt6797_a72_membership_claim_cpu9(",
        "mt6797_a72_membership_reject_cpu9(",
        "mt6797_a72_membership_begin_cpu9_on(",
        "mt6797_a72_membership_publish_cpu9_success(",
        "mt6797_a72_membership_finalize_cpu9_success(",
    ):
        require(header.count(symbol) >= 1, f"header API absent: {symbol}")

    for symbol in (
        "mt6797_a72_cpu9_parent_validate(",
        "mt6797_a72_membership_derive_cpu9_locked(",
        "mt6797_a72_membership_derive_cpu9_diagnostic(",
        "mt6797_a72_cpu9_cluster_budgets_empty(",
        "mt6797_a72_cpu9_retired_parent_valid_locked(",
        "mt6797_a72_membership_publish_cpu9(",
        "mt6797_a72_membership_preflight_cpu9(",
        "mt6797_a72_membership_claim_cpu9(",
        "mt6797_a72_membership_reject_cpu9(",
        "mt6797_a72_membership_begin_cpu9_on(",
        "mt6797_a72_membership_publish_cpu9_success(",
        "mt6797_a72_membership_finalize_cpu9_success(",
    ):
        require(symbol in new_source, f"source function absent: {symbol}")

    for token in (
        "parent->members != BIT(0)",
        "parent->provider_state != MT6797_A72_PROVIDER_HELD",
        "parent->attempts_consumed & MT6797_A72_ATTEMPT_CPU9_UP",
        "!cpu8->cpu8_success_published || cpu8->cpu9_success_published",
        "topology->cpu8_online != 1 || topology->cpu9_online",
        "mt6797_a72_ready_token_validate(9, ready)",
        "MT6797_A72_ATTEMPT_CPU9_UP",
        "prestate->cpu8_cluster_dcm_published = 1;",
        "budgets->preparation == MT6797_A72_BUDGET_NONE",
        "budgets->provider_acquire == MT6797_A72_BUDGET_NONE",
        "budgets->postprovider_preparation == MT6797_A72_BUDGET_NONE",
        "budgets->provider_abort == MT6797_A72_BUDGET_NONE",
        "!a72_owner.active.cpu9_success_published &&\n"
        "\t    cpu8_online && !cpu9_online) {\n"
        "\t\ta72_owner.active.budgets.cpu_on = "
        "MT6797_A72_BUDGET_CONSUMED;",
        "a72_owner.active.cpu9_success_published = 1;",
        "a72_owner.members = BIT(0) | BIT(1);",
        "a72_owner.phase = MT6797_A72_PHASE_REJECTED;",
    ):
        require(token in new_source, f"CPU9 invariant absent: {token}")

    for token in FORBIDDEN:
        require(token not in new_source, f"forbidden CPU9 path token: {token}")

    for case in (
        "mt6797_a72_owner_cpu9_parent_gate",
        "mt6797_a72_owner_cpu9_parent_mutations",
        "mt6797_a72_owner_cpu9_success_lifecycle",
        "mt6797_a72_owner_cpu9_rejection_one_shot",
    ):
        exact(tests, f"KUNIT_CASE({case})")
    require(tests.count("mt6797_a72_test_seed_cpu8_terminal(") == 5,
            "CPU8 terminal fixture inventory changed")
    for token in FORBIDDEN:
        require(token not in tests, f"forbidden test path token: {token}")

    return [
        "cpu9_membership_validation=pass",
        "transaction_abi=4",
        "cpu8_parent=retired-slot0-exact-success",
        "cpu9_attempt_binding=fresh-one-shot",
        "cpu9_owner_source=held-provider-and-member0",
        "cpu9_cluster_budgets=all-none",
        "cpu9_cpu_on_budget=one",
        "cpu9_success_members=bits0-1",
        "cpu9_rejection=retains-cpu8-provider",
        "focused_owner_kunit_cases=4",
        "new_cpu_request_paths=0",
        "new_cpu_off_paths=0",
        "new_retry_paths=0",
        "new_cluster_effect_paths=0",
        "production_callers=0",
    ]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    print("\n".join(validate(args.source_root)))
