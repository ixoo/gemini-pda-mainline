#!/usr/bin/env python3
"""Apply the exact post-0479 CPU9 membership-begin lock repair."""

from __future__ import annotations

from pathlib import Path


PARENT_HASHES = {
    "arch/arm64/include/asm/mt6797_a72_membership.h":
        "fe02e703f60035b06cb516d3b2c18f50c097eb55e531bf94bfb403b4faabf729",
    "arch/arm64/kernel/mt6797_a72_membership.c":
        "06b526d4f4b14a8f2f4070217a8e8f742adf05559941551a06d1e9f4dd379910",
    "drivers/soc/mediatek/mt6797-a72-cpu9-binder.c":
        "4473c3a8198fe1d41275ec46ae6ef28358d50c1417d9c2b6d8bd19f986e8235f",
}


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(
            f"CPU_ON membership lock repair anchor changed: {path}: {old}"
        )
    path.write_text(text.replace(old, new), encoding="utf-8")


def apply(root: Path) -> None:
    header = root / "arch/arm64/include/asm/mt6797_a72_membership.h"
    replace_once(
        header,
        "int mt6797_a72_membership_begin_cpu9_on(struct mt6797_a72_transaction *transaction);",
        "int mt6797_a72_membership_begin_cpu9_on(struct mt6797_a72_transaction *transaction);\n"
        "int mt6797_a72_begin_cpu9_on_locked(struct mt6797_a72_transaction *transaction);",
    )

    membership = root / "arch/arm64/kernel/mt6797_a72_membership.c"
    replace_once(
        membership,
        "int mt6797_a72_membership_begin_cpu9_on(struct mt6797_a72_transaction *transaction)\n"
        "{\n"
        "\tint ret;\n\n"
        "\tcpus_read_lock();",
        "int mt6797_a72_begin_cpu9_on_locked(struct mt6797_a72_transaction *transaction)\n"
        "{\n"
        "\tlockdep_assert_cpus_held();\n"
        "\treturn mt6797_a72_begin_cpu9_on_state(transaction,\n"
        "\t\t\t\t\t     cpu_online(8), cpu_online(9));\n"
        "}\n\n"
        "int mt6797_a72_membership_begin_cpu9_on(struct mt6797_a72_transaction *transaction)\n"
        "{\n"
        "\tint ret;\n\n"
        "\tcpus_read_lock();",
    )

    binder = root / "drivers/soc/mediatek/mt6797-a72-cpu9-binder.c"
    replace_once(
        binder,
        "\t.membership_begin_cpu_on = mt6797_a72_membership_begin_cpu9_on,",
        "\t.membership_begin_cpu_on = mt6797_a72_begin_cpu9_on_locked,",
    )
