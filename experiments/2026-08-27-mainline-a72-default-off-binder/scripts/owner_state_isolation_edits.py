#!/usr/bin/env python3
"""Apply the exact owner/P30 KUnit state-isolation repair."""

from __future__ import annotations

import argparse
from pathlib import Path


TARGET = Path("arch/arm64/kernel/mt6797_a72_membership_test.c")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    require(text.count(old) == 1, f"{label} anchor count changed")
    return text.replace(old, new, 1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    path = args.source_root.resolve() / TARGET
    require(path.is_file() and not path.is_symlink(), "test source absent or unsafe")
    text = path.read_text(encoding="utf-8")

    basic_seed = "\tmt6797_a72_membership_test_seed_available();"
    cpu9_seed = "\tmt6797_a72_membership_test_seed_available_cpu9();"
    require(text.count(basic_seed) == 11, "basic seed inventory changed")
    require(text.count(cpu9_seed) == 6, "CPU9 seed inventory changed")
    text = text.replace(basic_seed, "\tmt6797_a72_owner_seed_available();")
    text = text.replace(cpu9_seed, "\tmt6797_a72_owner_seed_available_cpu9();")

    init_anchor = """static int mt6797_a72_owner_test_init(struct kunit *test)
{
"""
    helpers = """static void mt6797_a72_owner_reset_state(void)
{
\tarm64_late_cpu_startup_test_reset();
\tmt6797_a72_membership_test_reset();
}

static void mt6797_a72_owner_seed_available(void)
{
\tarm64_late_cpu_startup_test_reset();
\tmt6797_a72_membership_test_seed_available();
}

static void mt6797_a72_owner_seed_available_cpu9(void)
{
\tarm64_late_cpu_startup_test_reset();
\tmt6797_a72_membership_test_seed_available_cpu9();
}

"""
    text = replace_once(text, init_anchor, helpers + init_anchor,
                        "owner helper insertion")
    text = replace_once(
        text,
        "\ttest->priv = state;\n\tmt6797_a72_membership_test_reset();\n",
        "\ttest->priv = state;\n\tmt6797_a72_owner_reset_state();\n",
        "owner case reset",
    )

    text = replace_once(
        text,
        "\tret = mt6797_psci_ops.cpu_up_preflight(8, CPUHP_AP_ONLINE);\n"
        "\tKUNIT_EXPECT_EQ(test, ret, -EINVAL);\n"
        "\towner_observe(&state->after);\n",
        "\tret = mt6797_psci_ops.cpu_up_preflight(8, CPUHP_AP_ONLINE);\n"
        "\tKUNIT_EXPECT_EQ(test, ret,\n"
        "\t\tIS_ENABLED(CONFIG_MTK_MT6797_A72_DEFAULT_OFF_BINDER) ?\n"
        "\t\t\t-EAGAIN : -EINVAL);\n"
        "\towner_observe(&state->after);\n",
        "public hook intermediate expectation",
    )
    text = replace_once(
        text,
        "\tKUNIT_EXPECT_EQ(test, ret, -EPERM);\n"
        "\tret = mt6797_psci_ops.cpu_up_validate(9, 0, CPUHP_AP_ONLINE);\n"
        "\tKUNIT_EXPECT_EQ(test, ret, -EINVAL);\n",
        "\tKUNIT_EXPECT_EQ(test, ret,\n"
        "\t\tIS_ENABLED(CONFIG_MTK_MT6797_A72_DEFAULT_OFF_BINDER) ?\n"
        "\t\t\t-EAGAIN : -EPERM);\n"
        "\tret = mt6797_psci_ops.cpu_up_validate(9, 0, CPUHP_AP_ONLINE);\n"
        "\tKUNIT_EXPECT_EQ(test, ret,\n"
        "\t\tIS_ENABLED(CONFIG_MTK_MT6797_A72_DEFAULT_OFF_BINDER) ?\n"
        "\t\t\t-EAGAIN : -EINVAL);\n",
        "internal hook binder expectations",
    )

    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
