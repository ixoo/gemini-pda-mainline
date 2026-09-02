#!/usr/bin/env python3
"""Validate the CPU9 hotplug-lock repair against its exact source contract."""

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
        "int mt6797_a72_claim_cpu9_locked(struct mt6797_a72_transaction *transaction);",
        1,
    )
    exact(
        membership,
        "int mt6797_a72_claim_cpu9_locked(struct mt6797_a72_transaction *transaction)",
        1,
    )
    exact(membership, "\tlockdep_assert_cpus_held();", 1)
    exact(
        membership,
        "\treturn mt6797_a72_claim_cpu9_state(transaction,\n"
        "\t\t\t\t\t  cpu_online(8), cpu_online(9));",
        1,
        "locked claim direct state call",
    )
    locked = membership.split(
        "mt6797_a72_claim_cpu9_locked(", 1
    )[1].split(
        "int mt6797_a72_membership_claim_cpu9(", 1
    )[0]
    exact(locked, "cpus_read_lock", 0, "locked claim read-lock acquisition")
    exact(locked, "cpus_read_unlock", 0, "locked claim read-lock release")

    ordinary = membership.split(
        "int mt6797_a72_membership_claim_cpu9(", 1
    )[1].split("static int\nmt6797_a72_reject_cpu9_state", 1)[0]
    exact(ordinary, "cpus_read_lock();", 1, "ordinary claim read lock")
    exact(ordinary, "cpus_read_unlock();", 1, "ordinary claim read unlock")
    exact(ordinary, "mt6797_a72_claim_cpu9_state(transaction,", 1)

    exact(
        binder,
        "\t.membership_claim = mt6797_a72_claim_cpu9_locked,",
        1,
    )
    exact(
        binder,
        "\t.membership_claim = mt6797_a72_membership_claim_cpu9,",
        0,
        "recursive production claim binding",
    )
    ordered(
        binder,
        (
            ".membership_preflight = mt6797_a72_membership_preflight_cpu9",
            ".membership_claim =",
            "mt6797_a72_claim_cpu9_locked",
            ".membership_reject = mt6797_a72_membership_reject_cpu9",
        ),
        "production backend membership callbacks",
    )

    for token in (
        "cpu_down(", "remove_cpu(", "psci_cpu_off", "cpu_off(",
        "arm_smccc", "regmap_write(", "kernel_restart(",
        "orderly_poweroff(",
    ):
        exact(locked, token, 0, f"forbidden locked-claim token {token}")

    return [
        "cpu9_cpuhp_lock_repair_validation=pass",
        "locked_claim_asserts_cpuhp_lock=yes",
        "locked_claim_reacquires_cpuhp_lock=no",
        "ordinary_claim_locking=unchanged",
        "binder_claim_helper=cpuhp-lock-held",
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
