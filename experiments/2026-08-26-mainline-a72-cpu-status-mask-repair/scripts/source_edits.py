#!/usr/bin/env python3
"""Apply deterministic CPU-status-mask repair edits to post-0381 sources."""

from __future__ import annotations

import argparse
from pathlib import Path
from textwrap import dedent


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"{path}: expected one anchor: {old.splitlines()[0]}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def production(root: Path) -> None:
    platform = root / "drivers/soc/mediatek/mt6797-a72-platform-state.c"
    replace_once(
        platform,
        "#define MT6797_SPM_CPU_EXT_BUCK_ISO\t\t0x290\n\n",
        "#define MT6797_SPM_CPU_EXT_BUCK_ISO\t\t0x290\n\n"
        "#define MT6797_A72_CPU_PWR_STATUS_MASK\t\tGENMASK(7, 6)\n\n",
    )
    replace_once(
        platform,
        "\tif (first->spm_cpu_pwr_status != second->spm_cpu_pwr_status)\n"
        "\t\tmovement |= MT6797_A72_PLATFORM_MOVED_SPM_CPU_PWR_STATUS;\n"
        "\tif (first->spm_cpu_pwr_status_2nd != second->spm_cpu_pwr_status_2nd)\n"
        "\t\tmovement |= MT6797_A72_PLATFORM_MOVED_SPM_CPU_PWR_STATUS_2ND;\n",
        "\tif ((first->spm_cpu_pwr_status ^ second->spm_cpu_pwr_status) &\n"
        "\t    MT6797_A72_CPU_PWR_STATUS_MASK)\n"
        "\t\tmovement |= MT6797_A72_PLATFORM_MOVED_SPM_CPU_PWR_STATUS;\n"
        "\tif ((first->spm_cpu_pwr_status_2nd ^\n"
        "\t     second->spm_cpu_pwr_status_2nd) &\n"
        "\t    MT6797_A72_CPU_PWR_STATUS_MASK)\n"
        "\t\tmovement |= MT6797_A72_PLATFORM_MOVED_SPM_CPU_PWR_STATUS_2ND;\n",
    )


def tests(root: Path) -> None:
    test = root / "drivers/soc/mediatek/mt6797-a72-platform-state-test.c"
    replace_once(
        test,
        "\tstate.samples[1].spm_cpu_pwr_status = 1;\n"
        "\tret = mt6797_a72_platform_state_capture(&test_ops, &state, &snapshot,\n",
        "\tstate.samples[1].spm_cpu_pwr_status = BIT(6);\n"
        "\tret = mt6797_a72_platform_state_capture(&test_ops, &state, &snapshot,\n",
    )
    replace_once(
        test,
        "\tcase MT6797_A72_PLATFORM_MOVED_SPM_CPU_PWR_STATUS:\n"
        "\t\tsample->spm_cpu_pwr_status = 1;\n"
        "\t\tbreak;\n"
        "\tcase MT6797_A72_PLATFORM_MOVED_SPM_CPU_PWR_STATUS_2ND:\n"
        "\t\tsample->spm_cpu_pwr_status_2nd = 1;\n",
        "\tcase MT6797_A72_PLATFORM_MOVED_SPM_CPU_PWR_STATUS:\n"
        "\t\tsample->spm_cpu_pwr_status = BIT(6);\n"
        "\t\tbreak;\n"
        "\tcase MT6797_A72_PLATFORM_MOVED_SPM_CPU_PWR_STATUS_2ND:\n"
        "\t\tsample->spm_cpu_pwr_status_2nd = BIT(6);\n",
    )
    anchor = "static void mt6797_state_masked_noise_test(struct kunit *test)\n"
    identity_test = dedent("""\
        static void mt6797_state_each_a72_identity_bit_test(struct kunit *test)
        {
        \tstatic const u32 status_bits[] = { BIT(6), BIT(7) };
        \tunsigned int word;
        \tunsigned int bit;

        \tfor (word = 0; word < 2; word++) {
        \t\tfor (bit = 0; bit < ARRAY_SIZE(status_bits); bit++) {
        \t\t\tstruct mt6797_state_test_context state = { };
        \t\t\tstruct mt6797_a72_platform_state_failure failure;
        \t\t\tstruct mt6797_a72_platform_state snapshot;
        \t\t\tu32 expected;
        \t\t\tint ret;

        \t\t\tif (word == 0) {
        \t\t\t\tstate.samples[1].spm_cpu_pwr_status = status_bits[bit];
        \t\t\t\texpected = MT6797_A72_PLATFORM_MOVED_SPM_CPU_PWR_STATUS;
        \t\t\t} else {
        \t\t\t\tstate.samples[1].spm_cpu_pwr_status_2nd = status_bits[bit];
        \t\t\t\texpected = MT6797_A72_PLATFORM_MOVED_SPM_CPU_PWR_STATUS_2ND;
        \t\t\t}
        \t\t\tret = mt6797_a72_platform_state_capture(&test_ops, &state,
        \t\t\t\t\t\t\t\t&snapshot, &failure);
        \t\t\tKUNIT_EXPECT_EQ(test, ret, -EAGAIN);
        \t\t\tKUNIT_EXPECT_EQ(test, state.calls, 2U);
        \t\t\tKUNIT_EXPECT_TRUE(test, failure.samples_valid);
        \t\t\tKUNIT_EXPECT_EQ(test, failure.movement_mask, expected);
        \t\t\tmt6797_state_expect_zero(test, &snapshot, sizeof(snapshot));
        \t\t}
        \t}
        }

        """)
    replace_once(test, anchor, identity_test + anchor)
    replace_once(
        test,
        "\tstate.samples[1].spm_pwr_status = 1;\n"
        "\tstate.samples[1].spm_pwr_status_2nd = 1;\n"
        "\tstate.samples[1].mp2_sync_dcm = BIT(7);\n",
        "\tstate.samples[0].spm_cpu_pwr_status = 0x003dcf08;\n"
        "\tstate.samples[1].spm_cpu_pwr_status = 0x003dc708;\n"
        "\tstate.samples[0].spm_cpu_pwr_status_2nd = 0x003defff;\n"
        "\tstate.samples[1].spm_cpu_pwr_status_2nd = 0x003dc7ff;\n"
        "\tstate.samples[1].spm_pwr_status = 1;\n"
        "\tstate.samples[1].spm_pwr_status_2nd = 1;\n"
        "\tstate.samples[1].mp2_sync_dcm = BIT(7);\n",
    )
    replace_once(
        test,
        "\tKUNIT_EXPECT_TRUE(test, snapshot.valid);\n"
        "\tmt6797_state_expect_zero(test, &failure, sizeof(failure));\n"
        "}\n\nstatic struct kunit_case mt6797_state_cases[] = {\n",
        "\tKUNIT_EXPECT_TRUE(test, snapshot.valid);\n"
        "\tKUNIT_EXPECT_EQ(test, snapshot.spm_cpu_pwr_status,\n"
        "\t\t\t(u32)0x003dc708);\n"
        "\tKUNIT_EXPECT_EQ(test, snapshot.spm_cpu_pwr_status_2nd,\n"
        "\t\t\t(u32)0x003dc7ff);\n"
        "\tmt6797_state_expect_zero(test, &failure, sizeof(failure));\n"
        "}\n\nstatic struct kunit_case mt6797_state_cases[] = {\n",
    )
    replace_once(
        test,
        "\tKUNIT_CASE(mt6797_state_each_movement_test),\n"
        "\tKUNIT_CASE(mt6797_state_masked_noise_test),\n",
        "\tKUNIT_CASE(mt6797_state_each_movement_test),\n"
        "\tKUNIT_CASE(mt6797_state_each_a72_identity_bit_test),\n"
        "\tKUNIT_CASE(mt6797_state_masked_noise_test),\n",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--phase", choices=("production", "tests"), required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    (production if args.phase == "production" else tests)(root)


if __name__ == "__main__":
    main()
