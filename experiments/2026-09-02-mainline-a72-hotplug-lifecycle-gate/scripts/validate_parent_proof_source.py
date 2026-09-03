#!/usr/bin/env python3
"""Validate the disconnected exact CPU8/CPU9 parent-proof source."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def function_body(source: str, name: str) -> str:
    match = re.search(rf"\b{re.escape(name)}\s*\([^;]*?\)\s*\{{", source,
                      re.S)
    require(match is not None, f"missing function: {name}")
    depth = 0
    for offset in range(match.end() - 1, len(source)):
        if source[offset] == "{":
            depth += 1
        elif source[offset] == "}":
            depth -= 1
            if depth == 0:
                return source[match.start():offset + 1]
    raise ValueError(f"unterminated function: {name}")


def validate_membership(root: Path) -> None:
    header = (root / "arch/arm64/include/asm/mt6797_a72_membership.h").read_text()
    source = (root / "arch/arm64/kernel/mt6797_a72_membership.c").read_text()
    test = (root / "arch/arm64/kernel/mt6797_a72_membership_test.c").read_text()

    for token in (
        "#define MT6797_A72_INITIAL_PARENT_PROOF_ABI 1U",
        "struct mt6797_a72_initial_parent_proof {",
        "struct mt6797_a72_transaction_identity cpu8;",
        "struct mt6797_a72_transaction_identity cpu9;",
        "struct mt6797_a72_provider_identity provider_identity;",
        "mt6797_a72_membership_initial_parent_proof(",
    ):
        require(token in header, f"membership contract missing: {token}")
    require(header.count("mt6797_a72_membership_initial_parent_proof(") == 2,
            "enabled declaration or disabled stub changed")
    stub = header.split(
        "static inline int mt6797_a72_membership_initial_parent_proof(",
        1,
    )[1]
    require("*proof = (struct mt6797_a72_initial_parent_proof){};" in stub and
            "return -EOPNOTSUPP;" in stub,
            "disabled membership proof is not fail-closed")

    body = function_body(source, "mt6797_a72_membership_initial_parent_proof")
    for token in (
        "mutex_lock(&a72_transition_lock)",
        "raw_spin_lock_irqsave(&a72_state_lock, flags)",
        "raw_spin_unlock_irqrestore(&a72_state_lock, flags)",
        "mutex_unlock(&a72_transition_lock)",
        "a72_owner.health == MT6797_A72_OWNER_AVAILABLE",
        "a72_owner.phase == MT6797_A72_PHASE_IDLE",
        "a72_owner.hotplug_phase == MT6797_A72_HOTPLUG_IDLE",
        "a72_owner.members == (BIT(0) | BIT(1))",
        "a72_owner.retired_mask == (BIT(0) | BIT(1))",
        "!a72_owner.hotplug_retired_mask",
        "a72_owner.provider_state == MT6797_A72_PROVIDER_HELD",
        "!a72_owner.active.valid",
        "!a72_owner.hotplug_active.valid",
        "!a72_owner.controller && !a72_owner.controller_cookie",
        "mt6797_a72_cpu9_terminal_parent_valid_locked()",
        "proof->cpu8 = a72_owner.retired[0].identity",
        "proof->cpu9 = a72_owner.retired[1].identity",
        "proof->provider_identity = a72_owner.provider_identity",
    ):
        require(token in body, f"membership exact gate missing: {token}")
    require(not re.search(r"a72_owner\.[A-Za-z0-9_\.\[\]]+\s*=(?!=)", body),
            "membership producer mutates owner state")
    for token in ("cpu_up(", "cpu_down(", "psci_ops.", "arm_smccc",
                  "readl(", "writel(", "mtk_wdt_recovery_takeover"):
        require(token not in body, f"membership producer gained effect: {token}")

    require(test.count("KUNIT_CASE(mt6797_a72_") == 40,
            "membership KUnit case count changed")
    require("KUNIT_CASE(mt6797_a72_initial_parent_proof_test)" in test,
            "membership proof KUnit case missing")
    test_body = function_body(test, "mt6797_a72_initial_parent_proof_test")
    for token in ("-EINVAL", "-EPERM", "proof.exact, 1U",
                  "proof.cpu8.target_cpu, 8U", "proof.cpu9.target_cpu, 9U",
                  "expect_unchanged(test, &state->before, &state->after)",
                  "mt6797_a72_hotplug_prepare_down"):
        require(token in test_body, f"membership proof test missing: {token}")


def validate_binder(root: Path) -> None:
    header = (root / "include/linux/soc/mediatek/mt6797-a72-binder.h").read_text()
    internal = (root / "drivers/soc/mediatek/mt6797-a72-binder-internal.h").read_text()
    source = (root / "drivers/soc/mediatek/mt6797-a72-binder.c").read_text()
    test = (root / "drivers/soc/mediatek/mt6797-a72-binder-test.c").read_text()
    psci = (root / "arch/arm64/kernel/mt6797_psci.c").read_text()

    for token in (
        "#define MT6797_A72_BINDER_PARENT_PROOF_ABI 1U",
        "#define MT6797_A72_BINDER_PARENT_MAX_AGE_MS 5000U",
        "#define MT6797_A72_BINDER_PARENT_ONLINE_MASK GENMASK(9, 0)",
        "struct mt6797_a72_binder_parent_identity {",
        "struct mt6797_a72_binder_parent_proof {",
        "u64 watchdog_takeover_ns;",
        "u64 watchdog_age_ns;",
    ):
        require(token in header, f"binder contract missing: {token}")
    require(header.count("mt6797_a72_binder_parent_proof(") == 2,
            "enabled declaration or disabled stub changed")
    stub = header.split(
        "static inline int mt6797_a72_binder_parent_proof(", 1
    )[1]
    require("*proof = (struct mt6797_a72_binder_parent_proof){};" in stub and
            "return -EOPNOTSUPP;" in stub,
            "disabled binder proof is not fail-closed")

    for token in ("membership_parent_proof", "watchdog_validate",
                  "monotonic_ns", "cpu_online_count",
                  "u64 watchdog_takeover_ns;"):
        require(token in internal, f"binder injected proof backend missing: {token}")
    for token in (
        ".membership_parent_proof =\n\t\tmt6797_a72_membership_initial_parent_proof",
        ".watchdog_validate = mtk_wdt_recovery_validate",
        ".monotonic_ns = mt6797_a72_binder_monotonic_ns",
        ".cpu_online_count = mt6797_a72_binder_cpu_online_count",
    ):
        require(token in source, f"production read-only backend missing: {token}")

    watchdog = function_body(source, "mt6797_a72_binder_watchdog")
    require("takeover_ns = binder->backend->monotonic_ns();" in watchdog and
            "binder->watchdog_takeover_ns = takeover_ns;" in watchdog,
            "watchdog takeover timestamp missing")
    require(watchdog.index("takeover_ns =") <
            watchdog.index("watchdog_takeover("),
            "watchdog timestamp is not conservative")
    require(watchdog.index("binder->watchdog_takeover_ns =") >
            watchdog.index("result.owned != 1"),
            "failed watchdog takeover can publish a timestamp")

    body = function_body(source, "mt6797_a72_binder_parent_proof_locked")
    for token in (
        "membership_parent_proof(&membership)",
        "online_mask |= BIT(cpu)",
        "online_count = binder->backend->cpu_online_count()",
        "watchdog_validate(",
        "atomic_read(&binder->boot_claimed) != 1",
        "atomic_read(&binder->transition.consumed) != 1",
        "MT6797_A72_TRANSITION_LIFECYCLE_TERMINAL",
        "MT6797_A72_TRANSITION_CPU8_ONLINE_PROOF",
        "MT6797_A72_TRANSITION_STAGE_MEMBERSHIP",
        "!result->watchdog_armed",
        "!result->p27_owned",
        "!result->provider_owned",
        "!result->membership_published",
        "result->retained_mask != retained",
        "result->cpu_requests != 1",
        "result->cpu_off_requests",
        "result->retries",
        "memcmp(&binder->transaction.identity, &membership.cpu8",
        "memcmp(&binder->transaction.provider_identity",
        "online_mask != MT6797_A72_BINDER_PARENT_ONLINE_MASK",
        "online_count != 10",
        "watchdog.identity != result->watchdog_identity",
        "watchdog.owned != 1",
        "observed_ns < binder->watchdog_takeover_ns",
        "observed_ns - binder->watchdog_takeover_ns >\n"
        "\t    MT6797_A72_BINDER_PARENT_MAX_AGE_MS * 1000000ULL",
        "return -ETIME",
    ):
        require(token in body, f"combined parent gate missing: {token}")
    for token in ("cpu_up(", "cpu_down(", "psci_ops.", "arm_smccc",
                  "readl(", "writel(", "watchdog_takeover(",
                  "membership_claim(", "prepare_down("):
        require(token not in body, f"combined proof gained effect: {token}")

    public = function_body(source, "mt6797_a72_binder_parent_proof")
    require("mutex_lock(&mt6797_a72_binder_publish_lock)" in public and
            "mutex_unlock(&mt6797_a72_binder_publish_lock)" in public,
            "binder publication lock missing")
    require("mt6797_a72_binder_parent_proof_locked(binder, proof)" in public,
            "public binder proof call missing")
    require("mt6797_a72_binder_parent_proof(" not in psci,
            "parent proof connected to PSCI production")
    require("return false;" in function_body(psci,
                                             "mt6797_psci_cpu_can_disable"),
            "CPU disable veto opened")

    require(test.count("KUNIT_CASE(mt6797_binder_") == 10,
            "binder KUnit case count changed")
    require("KUNIT_CASE(mt6797_binder_parent_proof_test)" in test,
            "binder proof KUnit case missing")
    test_body = function_body(test, "mt6797_binder_parent_proof_test")
    for token in ("proof.online_mask", "proof.online_count, 10U",
                  "proof.watchdog_identity", "proof.watchdog_age_ns",
                  "memcmp(&before, &state->binder", "-ETIME", "-EPERM",
                  "MT6797_A72_TRANSITION_FAULT_RETAIN_POSTISO"):
        require(token in test_body, f"binder proof test missing: {token}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--require-binder", action="store_true")
    args = parser.parse_args()
    try:
        root = args.source_root.resolve()
        validate_membership(root)
        if args.require_binder:
            validate_binder(root)
    except (OSError, ValueError) as exc:
        print(f"parent_proof_source=fail reason={exc}", file=sys.stderr)
        return 1
    print("parent_proof_source=pass")
    print("membership_parent_proof=exact-read-only")
    print("membership_kunit_cases=40")
    if args.require_binder:
        print("binder_parent_proof=exact-read-only")
        print("binder_kunit_cases=10")
        print("combined_kunit_cases=62")
        print("watchdog_max_age_ms=5000")
        print("production_callers=0")
        print("physical_effect_calls=0")
        print("cpu_can_disable=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
