#!/usr/bin/env python3
"""Validate the exact CPU9 completion-path CPU-hotplug lock repair."""

from __future__ import annotations

import argparse
from pathlib import Path


def exact(text: str, token: str, count: int, label: str | None = None) -> None:
    actual = text.count(token)
    if actual != count:
        raise ValueError(
            f"{label or token} count changed: expected {count}, got {actual}"
        )


def ordered(text: str, tokens: tuple[str, ...], label: str) -> None:
    positions = [text.index(token) for token in tokens]
    if positions != sorted(positions) or len(set(positions)) != len(positions):
        raise ValueError(f"{label} ordering changed")


def function_body(text: str, start: str, end: str) -> str:
    return text.split(start, 1)[1].split(end, 1)[0]


def validate(root: Path) -> list[str]:
    header = (
        root / "arch/arm64/include/asm/mt6797_a72_membership.h"
    ).read_text(encoding="utf-8")
    membership = (
        root / "arch/arm64/kernel/mt6797_a72_membership.c"
    ).read_text(encoding="utf-8")
    binder = (
        root / "drivers/soc/mediatek/mt6797-a72-cpu9-binder.c"
    ).read_text(encoding="utf-8")

    exact(membership, "#include <linux/cpuhplock.h>", 1)
    for name in (
        "mt6797_a72_publish_cpu9_success_locked",
        "mt6797_a72_finalize_cpu9_success_locked",
    ):
        exact(header, f"int {name}(", 1, f"{name} declaration")
        exact(membership, f"{name}(", 1, f"{name} definition")
    exact(membership, "\tlockdep_assert_cpus_held();", 4)

    publish_locked = function_body(
        membership,
        "int\nmt6797_a72_publish_cpu9_success_locked(",
        "int\nmt6797_a72_membership_publish_cpu9_success(",
    )
    finalize_locked = function_body(
        membership,
        "int\nmt6797_a72_finalize_cpu9_success_locked(",
        "int\nmt6797_a72_membership_finalize_cpu9_success(",
    )
    for body, state, label in (
        (publish_locked, "mt6797_a72_publish_cpu9_success_state", "publish"),
        (finalize_locked, "mt6797_a72_finalize_cpu9_success_state", "finalize"),
    ):
        exact(body, "lockdep_assert_cpus_held();", 1, f"locked {label} assertion")
        exact(body, "cpus_read_lock", 0, f"locked {label} read lock")
        exact(body, "cpus_read_unlock", 0, f"locked {label} read unlock")
        exact(body, state, 1, f"locked {label} state call")
        exact(body, "cpu_online(8), cpu_online(9)", 1, f"locked {label} topology")

    ordinary_publish = function_body(
        membership,
        "int\nmt6797_a72_membership_publish_cpu9_success(",
        "static int\nmt6797_a72_finalize_cpu9_success_state(",
    )
    ordinary_finalize = function_body(
        membership,
        "int\nmt6797_a72_membership_finalize_cpu9_success(",
        "#ifdef CONFIG_ARM64_MT6797_A72_P24_OWNER_TEST_SEED",
    )
    for body, state, label in (
        (ordinary_publish, "mt6797_a72_publish_cpu9_success_state", "publish"),
        (ordinary_finalize, "mt6797_a72_finalize_cpu9_success_state", "finalize"),
    ):
        exact(body, "cpus_read_lock();", 1, f"ordinary {label} read lock")
        exact(body, "cpus_read_unlock();", 1, f"ordinary {label} read unlock")
        exact(body, state, 1, f"ordinary {label} state call")

    exact(
        binder,
        "\t.membership_claim = mt6797_a72_claim_cpu9_locked,",
        1,
    )
    exact(
        binder,
        "\t.membership_begin_cpu_on = mt6797_a72_begin_cpu9_on_locked,",
        1,
    )
    exact(
        binder,
        "\t\t\tmt6797_a72_publish_cpu9_success_locked,",
        1,
    )
    exact(
        binder,
        "\t\t\tmt6797_a72_finalize_cpu9_success_locked,",
        1,
    )
    exact(
        binder,
        "\t\t\tmt6797_a72_membership_publish_cpu9_success,",
        0,
        "recursive production publish binding",
    )
    exact(
        binder,
        "\t\t\tmt6797_a72_membership_finalize_cpu9_success,",
        0,
        "recursive production finalize binding",
    )
    ordered(
        binder,
        (
            ".membership_claim = mt6797_a72_claim_cpu9_locked",
            ".membership_begin_cpu_on = mt6797_a72_begin_cpu9_on_locked",
            ".membership_publish_success =",
            "mt6797_a72_publish_cpu9_success_locked",
            ".membership_finalize_success =",
            "mt6797_a72_finalize_cpu9_success_locked",
        ),
        "production CPU9 completion callbacks",
    )

    for body, label in (
        (publish_locked, "publish"),
        (finalize_locked, "finalize"),
    ):
        for token in (
            "cpu_down(", "remove_cpu(", "psci_cpu_off", "cpu_off(",
            "arm_smccc", "regmap_write(", "kernel_restart(",
            "orderly_poweroff(",
        ):
            exact(body, token, 0, f"forbidden locked-{label} token {token}")

    return [
        "cpu9_completion_lock_repair_validation=pass",
        "locked_publish_asserts_cpuhp_lock=yes",
        "locked_publish_reacquires_cpuhp_lock=no",
        "locked_finalize_asserts_cpuhp_lock=yes",
        "locked_finalize_reacquires_cpuhp_lock=no",
        "ordinary_completion_locking=unchanged",
        "binder_publish_helper=cpuhp-lock-held",
        "binder_finalize_helper=cpuhp-lock-held",
        "binder_claim_begin_helpers=cpuhp-lock-held-unchanged",
        "new_cpu_request_paths=0",
        "new_cpu_off_paths=0",
        "new_retry_paths=0",
        "new_cluster_effect_paths=0",
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    for marker in validate(args.source_root.resolve()):
        print(marker)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
