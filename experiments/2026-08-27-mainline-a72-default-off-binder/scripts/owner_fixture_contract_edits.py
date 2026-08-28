#!/usr/bin/env python3
"""Align the MT6797 A72 owner KUnit fixtures with the Binder contract."""

from __future__ import annotations

import argparse
from pathlib import Path


TEST_SOURCE = Path("arch/arm64/kernel/mt6797_a72_membership_test.c")


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
    path = args.source_root.resolve() / TEST_SOURCE
    require(path.is_file() and not path.is_symlink(),
            "membership test source absent or unsafe")
    text = path.read_text(encoding="utf-8")

    common_cpu8 = """\t\t.da921x_page = MT6797_A72_A36_DA921X_PAGE,
\t\t.buckb_vsel = MT6797_A72_A36_BUCKB_VSEL,
\t\t.spm_218 = MT6797_A72_A36_SPM_218,
\t\t.spm_290 = MT6797_A72_A36_SPM_290,
\t\t.secure_sentinels_stable = 1,
\t\t.protected_clock_valid = 1,
\t\t.pstore_console_available = 1,
"""
    text = replace_once(text, common_cpu8, "", "common CPU8 prestate")
    cpu8_anchor = """\tif (cpu == 8) {
\t\tprestate.operation = ARM64_LATE_CPU_STARTUP_OP_CPU8_UP;
\t\tprestate.target_mpidr = 0x200;
"""
    cpu8_replacement = """\tif (cpu == 8) {
\t\tprestate.operation = ARM64_LATE_CPU_STARTUP_OP_CPU8_UP;
\t\tprestate.da921x_page = MT6797_A72_A36_DA921X_PAGE;
\t\tprestate.buckb_vsel = MT6797_A72_A36_BUCKB_VSEL;
\t\tprestate.spm_218 = MT6797_A72_A36_SPM_218;
\t\tprestate.spm_290 = MT6797_A72_A36_SPM_290;
\t\tprestate.secure_sentinels_stable = 1;
\t\tprestate.protected_clock_valid = 1;
\t\tprestate.pstore_console_available = 1;
\t\tprestate.target_mpidr = 0x200;
"""
    text = replace_once(text, cpu8_anchor, cpu8_replacement,
                        "CPU8 prestate branch")
    text = replace_once(
        text,
        "\tbad_ready.plan_identity[0] = 0;\n",
        "\tmemset(bad_ready.plan_identity, 0,\n"
        "\t       sizeof(bad_ready.plan_identity));\n",
        "invalid plan identity fixture",
    )

    for function in (
        "mt6797_a72_owner_r03_p29_rejects_and_retires",
        "mt6797_a72_owner_r03_p29_mutations_rejected",
    ):
        start = text.find(f"static void {function}(struct kunit *test)")
        require(start >= 0, f"{function} absent")
        end = text.find("\nstatic void ", start + 1)
        require(end >= 0, f"{function} terminator absent")
        body = text[start:end]
        old = (
            "\tret = mt6797_a72_test_seed_cpu8_p27(&state->transaction);\n"
            "\tKUNIT_ASSERT_EQ(test, ret, 0);\n"
            "\tret = mt6797_a72_membership_begin_provider_acquire("
            "&state->transaction);\n"
        )
        new = (
            "\tret = mt6797_a72_test_seed_cpu8_p27(&state->transaction);\n"
            "\tKUNIT_ASSERT_EQ(test, ret, 0);\n"
            "\tret = mt6797_a72_membership_preflight_up(8, CPUHP_ONLINE);\n"
            "\tKUNIT_ASSERT_EQ(test, ret, 0);\n"
            "\tret = mt6797_a72_membership_begin_provider_acquire("
            "&state->transaction);\n"
        )
        require(body.count(old) == 1,
                f"{function} P29 preflight anchor count changed")
        body = body.replace(old, new, 1)
        text = text[:start] + body + text[end:]

    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
