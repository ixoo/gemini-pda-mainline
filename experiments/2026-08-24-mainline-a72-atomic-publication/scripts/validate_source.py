#!/usr/bin/env python3
"""Validate cumulative atomic-publication source phases."""

from __future__ import annotations

import argparse
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument(
        "--phase", choices=("finalizer", "publisher", "tests"), required=True
    )
    args = parser.parse_args()
    root = args.source_root.resolve()
    late_header = (root / "arch/arm64/include/asm/late_cpu_startup.h").read_text()
    late_source = (root / "arch/arm64/kernel/late_cpu_startup.c").read_text()
    membership_header = (
        root / "arch/arm64/include/asm/mt6797_a72_membership.h"
    ).read_text()
    membership_source = (
        root / "arch/arm64/kernel/mt6797_a72_membership.c"
    ).read_text()
    membership_test = (
        root / "arch/arm64/kernel/mt6797_a72_membership_test.c"
    ).read_text()
    platforms = (root / "arch/arm64/Kconfig.platforms").read_text()
    psci = (root / "arch/arm64/kernel/mt6797_psci.c").read_text()

    for token in (
        "arm64_late_cpu_bootstrap_commit_t",
        "arm64_late_cpu_startup_finalize_pristine",
    ):
        require(token in late_header, f"finalizer header token {token}")
        require(token in late_source, f"finalizer source token {token}")
    require("late_startup_pristine_locked(u64 allowed_claim_cookie)" in
            late_source, "claim-aware pristine predicate")
    finalizer = late_source.index(
        "arm64_late_cpu_startup_finalize_pristine(")
    prepare = late_source.index("int arm64_late_cpu_startup_prepare(")
    require(finalizer < prepare, "finalizer must precede prepare")
    body = late_source[finalizer:prepare]
    require(body.index("late_startup.bootstrap_claim_cookie = 0;") <
            body.index("ret = commit(context);") <
            body.index("raw_spin_unlock_irqrestore"),
            "P30 lock must span claim clear and callback")
    require("late_startup_pristine_locked(claim->cookie)" in body,
            "finalizer exact pristine recheck")
    require("if (late_startup.bootstrap_claim_cookie)" in
            late_source[prepare:], "prepare claim exclusion")

    if args.phase == "finalizer":
        require("ARM64_MT6797_A72_BOOTSTRAP_PUBLISHER" not in platforms,
                "publisher leaked into finalizer phase")
        print("validation=a72-atomic-publication-source")
        print("phase=finalizer")
        print("p30_lock_spans_callback=true")
        print("owner_publication=false")
        print("hardware_operations=0")
        print("result=pass")
        return

    for token in (
        "CONFIG_ARM64_MT6797_A72_BOOTSTRAP_PUBLISHER",
        "mt6797_a72_membership_publish_bootstrap",
        "mt6797_a72_membership_publish_bootstrap_locked",
        "mt6797_a72_bootstrap_owner_precheck",
        "mt6797_a72_bootstrap_replay_valid",
        "mt6797_a72_bootstrap_commit",
    ):
        require(token in membership_header or token in membership_source or
                token in platforms, f"publisher token {token}")
    require("depends on ARM64_MT6797_A72_DIRECT_STATE_COMPOSITOR" in platforms,
            "publisher direct-state dependency")
    require("depends on ARM64_MT6797_A72_A34_ELIGIBILITY_EVALUATOR" in
            platforms, "publisher A34 dependency")
    require("default n" in platforms[platforms.index(
        "config ARM64_MT6797_A72_BOOTSTRAP_PUBLISHER"):],
        "publisher is not default-off")
    locked = membership_source.index(
        "mt6797_a72_membership_publish_bootstrap_locked(")
    public = membership_source.index(
        "mt6797_a72_membership_publish_bootstrap(")
    locked_body = membership_source[locked:public]
    for token in (
        "mt6797_a72_bootstrap_owner_precheck()",
        "mt6797_a72_bootstrap_replay_valid(replay)",
        "mt6797_a72_direct_state_snapshot_locked(",
        "mt6797_a72_a34_evaluate(&workspace->observation)",
        "arm64_late_cpu_startup_claim_pristine(&workspace->claim)",
        "arm64_late_cpu_startup_finalize_pristine(",
    ):
        require(token in locked_body, f"publisher sequence {token}")
    positions = [locked_body.index(token) for token in (
        "mt6797_a72_bootstrap_owner_precheck()",
        "mt6797_a72_bootstrap_replay_valid(replay)",
        "mt6797_a72_direct_state_snapshot_locked(",
        "mt6797_a72_a34_evaluate(&workspace->observation)",
        "arm64_late_cpu_startup_claim_pristine(&workspace->claim)",
        "arm64_late_cpu_startup_finalize_pristine(",
    )]
    require(positions == sorted(positions), "publisher sequence order")
    commit = membership_source[
        membership_source.index("static int mt6797_a72_bootstrap_commit("):
        locked
    ]
    require("mt6797_a72_direct_owner_pristine_locked(owner_after)" in commit,
            "final owner pristine recheck")
    require("memcmp(&workspace->observation.direct.owner, owner_after" in
            commit, "final owner byte comparison")
    health = commit.index(
        "a72_owner.health = MT6797_A72_OWNER_AVAILABLE;")
    for token in (
        "a72_owner.diagnostic_blockers = plan->diagnostic_blockers;",
        "a72_owner.phase = plan->phase;",
        "a72_owner.bootstrap_valid = plan->bootstrap_valid;",
        "a72_owner.members_valid = plan->members_valid;",
        "a72_owner.attempts_available = plan->attempts_available;",
        "a72_owner.next_generation = plan->next_generation;",
        "a72_owner.next_cookie = plan->next_cookie;",
    ):
        require(commit.index(token) < health, f"health-last field {token}")
    require("MT6797_A72_BLOCK_MASK &\n\t\t\t~MT6797_A72_BLOCK_A34_BOOTSTRAP" in
            membership_source, "only A34 diagnostic blocker cleared")
    require("cpus_read_lock();" in membership_source[public:] and
            "mutex_lock(&a72_transition_lock);" in membership_source[public:],
            "outer lock lifetime")
    require(membership_source.count(
        "mt6797_a72_membership_publish_bootstrap(") == 1,
        "production publisher definition count")
    for forbidden in (
        "arm64_late_cpu_startup_prepare(", "mt6797_a72_provider_acquire(",
        "psci_ops.cpu_boot", "writel(", "readl(", "i2c_transfer(",
    ):
        require(forbidden not in locked_body, f"publisher effect {forbidden}")
    require('return -EAGAIN;' in psci[psci.index(
        "static int mt6797_psci_cpu_boot"):], "CPU boot veto changed")
    can_disable = psci[psci.index(
        "static bool mt6797_psci_cpu_can_disable"):]
    require("return false;" in can_disable, "CPU-disable veto changed")

    if args.phase == "publisher":
        require("atomic_publication_test_state" not in membership_test,
                "tests leaked into publisher phase")
        print("validation=a72-atomic-publication-source")
        print("phase=publisher")
        print("production_callers=0")
        print("physical_reader_binding=false")
        print("cpu_veto_change=false")
        print("hardware_operations=0")
        print("result=pass")
        return

    test_start = membership_test.index(
        "#ifdef CONFIG_ARM64_MT6797_A72_ATOMIC_PUBLICATION_KUNIT_TEST")
    test_end = membership_test.index("#endif", test_start)
    test = membership_test[test_start:test_end]
    kconfig = (root / "arch/arm64/Kconfig").read_text()
    require(test.count("KUNIT_CASE(") == 8, "focused test case count")
    for token in (
        "atomic_finalizer_success_test",
        "atomic_finalizer_failure_identity_test",
        "atomic_publication_success_repeat_test",
        "atomic_publication_replay_rejections_test",
        "atomic_publication_source_rejections_test",
        "atomic_publication_topology_rejection_test",
        "atomic_publication_p30_busy_test",
        "atomic_publication_final_owner_mismatch_test",
        'name = "mt6797-a72-atomic-publication"',
    ):
        require(token in test, f"focused test {token}")
    require("config ARM64_MT6797_A72_ATOMIC_PUBLICATION_KUNIT_TEST" in
            kconfig, "test Kconfig")
    require("select ARM64_MT6797_A72_BOOTSTRAP_PUBLISHER" in kconfig,
            "test publisher selection")
    require("select ARM64_MT6797_A72_P24_OWNER_KUNIT_TEST" in kconfig,
            "existing membership KUnit object selection")
    for forbidden in (
        "cpu_up(", "psci_cpu_on", "writel(", "readl(", "i2c_transfer(",
    ):
        require(forbidden not in test, f"test hardware effect {forbidden}")

    print("validation=a72-atomic-publication-source")
    print("phase=tests")
    print("focused_tests=8")
    print("production_callers=0")
    print("physical_reader_binding=false")
    print("cpu_veto_change=false")
    print("hardware_operations=0")
    print("cpu_requests=0")
    print("result=pass")


if __name__ == "__main__":
    main()
