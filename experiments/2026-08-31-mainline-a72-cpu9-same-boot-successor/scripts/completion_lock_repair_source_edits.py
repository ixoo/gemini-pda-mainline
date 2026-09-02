#!/usr/bin/env python3
"""Apply the exact post-0480 CPU9 completion-path lock repair."""

from __future__ import annotations

from pathlib import Path


PARENT_HASHES = {
    "arch/arm64/include/asm/mt6797_a72_membership.h":
        "1c7f7fdda0d68c5d1e982c99a3af03fcef0463008a075857ba7e1c623aaea6ee",
    "arch/arm64/kernel/mt6797_a72_membership.c":
        "c3036934f0d85cfbb40ac880036be121b58773ca179ec822a71a4b6907d883bc",
    "drivers/soc/mediatek/mt6797-a72-cpu9-binder.c":
        "02039c88aba2ba3301c29d24bbee352fca1c4475e85c1fd23f03d469578af470",
}


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(
            f"CPU9 completion lock repair anchor changed: {path}: {old}"
        )
    path.write_text(text.replace(old, new), encoding="utf-8")


def apply(root: Path) -> None:
    header = root / "arch/arm64/include/asm/mt6797_a72_membership.h"
    replace_once(
        header,
        "int mt6797_a72_membership_publish_cpu9_success(struct mt6797_a72_transaction *transaction);\n"
        "int mt6797_a72_membership_finalize_cpu9_success(struct mt6797_a72_transaction *transaction);",
        "int mt6797_a72_membership_publish_cpu9_success(struct mt6797_a72_transaction *transaction);\n"
        "int mt6797_a72_publish_cpu9_success_locked(struct mt6797_a72_transaction *transaction);\n"
        "int mt6797_a72_membership_finalize_cpu9_success(struct mt6797_a72_transaction *transaction);\n"
        "int mt6797_a72_finalize_cpu9_success_locked(struct mt6797_a72_transaction *transaction);",
    )

    membership = root / "arch/arm64/kernel/mt6797_a72_membership.c"
    replace_once(
        membership,
        "int\n"
        "mt6797_a72_membership_publish_cpu9_success(struct mt6797_a72_transaction *transaction)\n"
        "{\n"
        "\tint ret;\n\n"
        "\tcpus_read_lock();",
        "int mt6797_a72_publish_cpu9_success_locked(\n"
        "\tstruct mt6797_a72_transaction *transaction)\n"
        "{\n"
        "\tlockdep_assert_cpus_held();\n"
        "\treturn mt6797_a72_publish_cpu9_success_state(transaction,\n"
        "\t\t\t\t\t       cpu_online(8), cpu_online(9));\n"
        "}\n\n"
        "int\n"
        "mt6797_a72_membership_publish_cpu9_success(struct mt6797_a72_transaction *transaction)\n"
        "{\n"
        "\tint ret;\n\n"
        "\tcpus_read_lock();",
    )
    replace_once(
        membership,
        "int\n"
        "mt6797_a72_membership_finalize_cpu9_success(struct mt6797_a72_transaction *transaction)\n"
        "{\n"
        "\tint ret;\n\n"
        "\tcpus_read_lock();",
        "int mt6797_a72_finalize_cpu9_success_locked(\n"
        "\tstruct mt6797_a72_transaction *transaction)\n"
        "{\n"
        "\tlockdep_assert_cpus_held();\n"
        "\treturn mt6797_a72_finalize_cpu9_success_state(transaction,\n"
        "\t\t\t\t\t\tcpu_online(8), cpu_online(9));\n"
        "}\n\n"
        "int\n"
        "mt6797_a72_membership_finalize_cpu9_success(struct mt6797_a72_transaction *transaction)\n"
        "{\n"
        "\tint ret;\n\n"
        "\tcpus_read_lock();",
    )

    binder = root / "drivers/soc/mediatek/mt6797-a72-cpu9-binder.c"
    replace_once(
        binder,
        "\t\t.membership_publish_success =\n"
        "\t\t\tmt6797_a72_membership_publish_cpu9_success,\n"
        "\t\t.membership_finalize_success =\n"
        "\t\t\tmt6797_a72_membership_finalize_cpu9_success,",
        "\t\t.membership_publish_success =\n"
        "\t\t\tmt6797_a72_publish_cpu9_success_locked,\n"
        "\t\t.membership_finalize_success =\n"
        "\t\t\tmt6797_a72_finalize_cpu9_success_locked,",
    )
