#!/usr/bin/env python3
"""Apply the exact post-0477 CPU9 CPU-hotplug lock repair."""

from __future__ import annotations

from pathlib import Path


PARENT_HASHES = {
    "arch/arm64/include/asm/mt6797_a72_membership.h":
        "8a7cf3087913f320473bc045a9f033f7d768c37f4074911a52af64d5fba42dff",
    "arch/arm64/kernel/mt6797_a72_membership.c":
        "e4a46dbbbd5d3e47e846a19ea9395fcc1a307d84e97764724359e49cbd65d35c",
    "drivers/soc/mediatek/mt6797-a72-cpu9-binder.c":
        "525fd6ad261e828e34a6609a0d12370c95b8c14bda6f13814a230ea5f9a1b2ad",
}


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"CPUHP lock repair anchor changed: {path}: {old}")
    path.write_text(text.replace(old, new), encoding="utf-8")


def apply(root: Path) -> None:
    header = root / "arch/arm64/include/asm/mt6797_a72_membership.h"
    replace_once(
        header,
        "int mt6797_a72_membership_claim_cpu9(struct mt6797_a72_transaction *transaction);",
        "int mt6797_a72_membership_claim_cpu9(struct mt6797_a72_transaction *transaction);\n"
        "int mt6797_a72_claim_cpu9_locked(struct mt6797_a72_transaction *transaction);",
    )

    membership = root / "arch/arm64/kernel/mt6797_a72_membership.c"
    replace_once(
        membership,
        "#include <linux/cpu.h>\n#include <linux/errno.h>",
        "#include <linux/cpu.h>\n#include <linux/cpuhplock.h>\n#include <linux/errno.h>",
    )
    replace_once(
        membership,
        "int mt6797_a72_membership_claim_cpu9(struct mt6797_a72_transaction *transaction)\n"
        "{\n"
        "\tint ret;\n\n"
        "\tcpus_read_lock();",
        "int mt6797_a72_claim_cpu9_locked(struct mt6797_a72_transaction *transaction)\n"
        "{\n"
        "\tlockdep_assert_cpus_held();\n"
        "\treturn mt6797_a72_claim_cpu9_state(transaction,\n"
        "\t\t\t\t\t  cpu_online(8), cpu_online(9));\n"
        "}\n\n"
        "int mt6797_a72_membership_claim_cpu9(struct mt6797_a72_transaction *transaction)\n"
        "{\n"
        "\tint ret;\n\n"
        "\tcpus_read_lock();",
    )

    binder = root / "drivers/soc/mediatek/mt6797-a72-cpu9-binder.c"
    replace_once(
        binder,
        "\t.membership_claim = mt6797_a72_membership_claim_cpu9,",
        "\t.membership_claim = mt6797_a72_claim_cpu9_locked,",
    )
