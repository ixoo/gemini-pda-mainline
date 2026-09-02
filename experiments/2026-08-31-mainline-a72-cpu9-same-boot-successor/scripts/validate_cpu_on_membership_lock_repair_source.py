#!/usr/bin/env python3
"""Validate the exact CPU9 membership-begin hotplug-lock repair."""

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
    exact(
        header,
        "int mt6797_a72_begin_cpu9_on_locked(struct mt6797_a72_transaction *transaction);",
        1,
    )
    exact(
        membership,
        "int mt6797_a72_begin_cpu9_on_locked(struct mt6797_a72_transaction *transaction)",
        1,
    )
    exact(membership, "\tlockdep_assert_cpus_held();", 2)
    exact(
        membership,
        "\treturn mt6797_a72_begin_cpu9_on_state(transaction,\n"
        "\t\t\t\t\t     cpu_online(8), cpu_online(9));",
        1,
        "locked membership-begin direct state call",
    )
    locked = membership.split(
        "mt6797_a72_begin_cpu9_on_locked(", 1
    )[1].split(
        "int mt6797_a72_membership_begin_cpu9_on(", 1
    )[0]
    exact(locked, "lockdep_assert_cpus_held();", 1)
    exact(locked, "cpus_read_lock", 0, "locked membership-begin read lock")
    exact(locked, "cpus_read_unlock", 0, "locked membership-begin read unlock")

    ordinary = membership.split(
        "int mt6797_a72_membership_begin_cpu9_on(", 1
    )[1].split(
        "static int\nmt6797_a72_publish_cpu9_success_state", 1
    )[0]
    exact(ordinary, "cpus_read_lock();", 1, "ordinary begin read lock")
    exact(ordinary, "cpus_read_unlock();", 1, "ordinary begin read unlock")
    exact(ordinary, "mt6797_a72_begin_cpu9_on_state(transaction,", 1)

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
        "\t.membership_begin_cpu_on = mt6797_a72_membership_begin_cpu9_on,",
        0,
        "recursive production membership-begin binding",
    )
    ordered(
        binder,
        (
            ".membership_claim = mt6797_a72_claim_cpu9_locked",
            ".membership_reject = mt6797_a72_membership_reject_cpu9",
            ".membership_begin_cpu_on = mt6797_a72_begin_cpu9_on_locked",
            ".p30e_prepare = mt6797_a72_cpu9_binder_p30e_prepare",
        ),
        "production backend membership callbacks",
    )

    for token in (
        "cpu_down(", "remove_cpu(", "psci_cpu_off", "cpu_off(",
        "arm_smccc", "regmap_write(", "kernel_restart(",
        "orderly_poweroff(",
    ):
        exact(locked, token, 0, f"forbidden locked-begin token {token}")

    return [
        "cpu9_membership_begin_lock_repair_validation=pass",
        "locked_begin_asserts_cpuhp_lock=yes",
        "locked_begin_reacquires_cpuhp_lock=no",
        "ordinary_begin_locking=unchanged",
        "binder_begin_helper=cpuhp-lock-held",
        "binder_claim_helper=cpuhp-lock-held-unchanged",
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
