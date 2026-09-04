#!/usr/bin/env python3
"""Apply the live MT6797 zero-divider decoder repair and focused test."""

from __future__ import annotations

import argparse
from pathlib import Path


def replace_once(path: Path, before: str, after: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(before) != 1:
        raise SystemExit(f"expected one source anchor in {path}: {before!r}")
    path.write_text(text.replace(before, after), encoding="utf-8")


def production(source_root: Path) -> None:
    source = source_root / "drivers/soc/mediatek/mt6797-dvfsp-clock-state.c"
    replace_once(
        source,
        "\tswitch (selector) {\n\tcase 8:\n",
        "\tswitch (selector) {\n\tcase 0:\n\tcase 8:\n",
    )


LIVE_TEST = r'''
static void mt6797_clock_state_live_zero_dividers_test(struct kunit *test)
{
	struct mt6797_dvfsp_clock_readback clock;
	struct mt6797_bigidvfs_readback big;
	struct mt6797_dvfsp_clock_state state;

	mt6797_clock_state_valid(&clock, &big);
	clock.armplldiv_ckdiv = 0x00000008;
	big.pll_pcw = 0xb9b13b14;
	big.pll_enable_posdiv = 0x00ff1101;
	KUNIT_ASSERT_EQ(test,
			mt6797_dvfsp_clock_state_decode(&clock, &big, &state), 0);
	KUNIT_EXPECT_EQ(test,
			state.cluster[MT6797_DVFSP_CLOCK_STATE_CLUSTER_LL].divider_selector,
			0U);
	KUNIT_EXPECT_EQ(test,
			state.cluster[MT6797_DVFSP_CLOCK_STATE_CLUSTER_L].divider_selector,
			0U);
	KUNIT_EXPECT_EQ(test,
			state.cluster[MT6797_DVFSP_CLOCK_STATE_CLUSTER_B].divider_selector,
			8U);
	KUNIT_EXPECT_EQ(test,
			state.cluster[MT6797_DVFSP_CLOCK_STATE_CLUSTER_CCI].divider_selector,
			0U);
	KUNIT_EXPECT_EQ(test,
			state.cluster[MT6797_DVFSP_CLOCK_STATE_CLUSTER_LL].frequency_khz,
			897000U);
	KUNIT_EXPECT_EQ(test,
			state.cluster[MT6797_DVFSP_CLOCK_STATE_CLUSTER_L].frequency_khz,
			1274000U);
	KUNIT_EXPECT_EQ(test,
			state.cluster[MT6797_DVFSP_CLOCK_STATE_CLUSTER_B].frequency_khz,
			750000U);
	KUNIT_EXPECT_EQ(test,
			state.cluster[MT6797_DVFSP_CLOCK_STATE_CLUSTER_CCI].frequency_khz,
			629500U);
}
'''


def tests(source_root: Path) -> None:
    test = source_root / "drivers/soc/mediatek/mt6797-dvfsp-clock-state-test.c"
    replace_once(
        test,
        "\tstatic const u32 selector[] = {\n"
        "\t\t8, 9, 10, 11, 17, 18, 19, 20, 25, 26, 27, 28, 29,\n"
        "\t};\n"
        "\tstatic const u32 expected[] = {\n"
        "\t\t1976000, 1482000, 988000, 494000, 1580800, 1185600,\n",
        "\tstatic const u32 selector[] = {\n"
        "\t\t0, 8, 9, 10, 11, 17, 18, 19, 20, 25, 26, 27, 28, 29,\n"
        "\t};\n"
        "\tstatic const u32 expected[] = {\n"
        "\t\t1976000, 1976000, 1482000, 988000, 494000, 1580800, 1185600,\n",
    )
    replace_once(
        test,
        "\tclock.armplldiv_ckdiv &= ~GENMASK(4, 0);\n"
        "\tKUNIT_EXPECT_EQ(test,\n"
        "\t\t\tmt6797_dvfsp_clock_state_decode(&clock, &big, &state),\n"
        "\t\t\t-EPROTO);\n",
        "\tclock.armplldiv_ckdiv =\n"
        "\t\t(clock.armplldiv_ckdiv & ~GENMASK(4, 0)) | 1;\n"
        "\tKUNIT_EXPECT_EQ(test,\n"
        "\t\t\tmt6797_dvfsp_clock_state_decode(&clock, &big, &state),\n"
        "\t\t\t-EPROTO);\n",
    )
    replace_once(
        test,
        "\nstatic void mt6797_clock_state_encoding_guards_test(struct kunit *test)\n",
        LIVE_TEST
        + "\nstatic void mt6797_clock_state_encoding_guards_test(struct kunit *test)\n",
    )
    replace_once(
        test,
        "\tKUNIT_CASE(mt6797_clock_state_zero_pcw_test),\n"
        "\tKUNIT_CASE(mt6797_clock_state_encoding_guards_test),\n",
        "\tKUNIT_CASE(mt6797_clock_state_zero_pcw_test),\n"
        "\tKUNIT_CASE(mt6797_clock_state_live_zero_dividers_test),\n"
        "\tKUNIT_CASE(mt6797_clock_state_encoding_guards_test),\n",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--phase", choices=("production", "tests"), required=True)
    args = parser.parse_args()
    if args.phase == "production":
        production(args.source_root)
    else:
        tests(args.source_root)


if __name__ == "__main__":
    main()
