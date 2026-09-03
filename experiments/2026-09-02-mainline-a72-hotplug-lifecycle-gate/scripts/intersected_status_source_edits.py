#!/usr/bin/env python3
"""Use the established MT6797 two-word intersection for CPU9-off proof."""

from __future__ import annotations

import argparse
from pathlib import Path


STATUS_OLD = r'''static bool mt6797_a72_hotplug_status_exact(
	const struct mt6797_a72_hotplug_readback *readback, bool cpu9_online)
{
	u32 required = MT6797_A72_HOTPLUG_CPU8_STATUS;
	u32 forbidden = 0;

	if (cpu9_online)
		required |= MT6797_A72_HOTPLUG_CPU9_STATUS;
	else
		forbidden = MT6797_A72_HOTPLUG_CPU9_STATUS;
	return readback->valid &&
		(readback->spm_cpu_pwr_status & required) == required &&
		(readback->spm_cpu_pwr_status_2nd & required) == required &&
		!(readback->spm_cpu_pwr_status & forbidden) &&
		!(readback->spm_cpu_pwr_status_2nd & forbidden) &&
		!((readback->cci_status_before | readback->cci_status_after) &
		  MT6797_A72_HOTPLUG_CCI_PENDING);
}
'''

STATUS_NEW = r'''static bool mt6797_a72_hotplug_status_exact(
	const struct mt6797_a72_hotplug_readback *readback, bool cpu9_online)
{
	u32 required = MT6797_A72_HOTPLUG_CPU8_STATUS;
	u32 forbidden = 0;

	if (cpu9_online)
		required |= MT6797_A72_HOTPLUG_CPU9_STATUS;
	else
		forbidden = MT6797_A72_HOTPLUG_CPU9_STATUS;
	return readback->valid &&
		(readback->spm_cpu_pwr_status & required) == required &&
		(readback->spm_cpu_pwr_status_2nd & required) == required &&
		!((readback->spm_cpu_pwr_status &
		   readback->spm_cpu_pwr_status_2nd) & forbidden) &&
		!((readback->cci_status_before | readback->cci_status_after) &
		  MT6797_A72_HOTPLUG_CCI_PENDING);
}
'''

PREDICATE_OLD = r'''bool mt6797_a72_hotplug_readback_proves_cpu9_off(
	const struct mt6797_a72_hotplug_readback *baseline,
	const struct mt6797_a72_hotplug_readback *post_state)
{
	return !mt6797_a72_hotplug_readback_mismatch(baseline, post_state);
}
'''

PREDICATE_NEW = r'''bool mt6797_a72_hotplug_readback_proves_cpu9_off(
	const struct mt6797_a72_hotplug_readback *baseline,
	const struct mt6797_a72_hotplug_readback *post_state)
{
	u32 raw_cpu9_mismatch =
		MT6797_A72_HOTPLUG_MISMATCH_POST_STATUS_CPU9 |
		MT6797_A72_HOTPLUG_MISMATCH_POST_STATUS2_CPU9;
	u32 mismatch;

	if (!post_state ||
	    !mt6797_a72_hotplug_status_exact(post_state, false))
		return false;
	mismatch = mt6797_a72_hotplug_readback_mismatch(baseline, post_state);
	return !(mismatch & ~raw_cpu9_mismatch);
}
'''

TEST_OLD = r'''	KUNIT_EXPECT_TRUE(test,
			  mt6797_a72_hotplug_readback_proves_cpu9_off(&baseline, &post));
	post.spm_cpu_pwr_status |= MT6797_A72_HOTPLUG_CPU9_STATUS;
	KUNIT_EXPECT_FALSE(test,
			   mt6797_a72_hotplug_readback_proves_cpu9_off(&baseline, &post));
	post = state->samples[1];
	post.spm_cpu_pwr_status_2nd &= ~MT6797_A72_HOTPLUG_CPU8_STATUS;
'''

TEST_NEW = r'''	KUNIT_EXPECT_TRUE(test,
			  mt6797_a72_hotplug_readback_proves_cpu9_off(&baseline, &post));
	post.spm_cpu_pwr_status |= MT6797_A72_HOTPLUG_CPU9_STATUS;
	KUNIT_EXPECT_TRUE(test,
			  mt6797_a72_hotplug_readback_proves_cpu9_off(&baseline, &post));
	KUNIT_EXPECT_EQ(test, mt6797_a72_hotplug_readback_mismatch(
		&baseline, &post),
		(u32)MT6797_A72_HOTPLUG_MISMATCH_POST_STATUS_CPU9);
	post = state->samples[1];
	post.spm_cpu_pwr_status_2nd |= MT6797_A72_HOTPLUG_CPU9_STATUS;
	KUNIT_EXPECT_TRUE(test,
			  mt6797_a72_hotplug_readback_proves_cpu9_off(&baseline, &post));
	KUNIT_EXPECT_EQ(test, mt6797_a72_hotplug_readback_mismatch(
		&baseline, &post),
		(u32)MT6797_A72_HOTPLUG_MISMATCH_POST_STATUS2_CPU9);
	post.spm_cpu_pwr_status |= MT6797_A72_HOTPLUG_CPU9_STATUS;
	KUNIT_EXPECT_FALSE(test,
			   mt6797_a72_hotplug_readback_proves_cpu9_off(&baseline, &post));
	post = state->samples[1];
	post.spm_cpu_pwr_status_2nd &= ~MT6797_A72_HOTPLUG_CPU8_STATUS;
'''


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"edit anchor changed: {path}: {old.splitlines()[0]}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    source = root / "drivers/soc/mediatek/mt6797-a72-hotplug-executor.c"
    test = root / "drivers/soc/mediatek/mt6797-a72-hotplug-executor-test.c"

    replace_once(source, STATUS_OLD, STATUS_NEW)
    replace_once(source, PREDICATE_OLD, PREDICATE_NEW)
    replace_once(test, TEST_OLD, TEST_NEW)


if __name__ == "__main__":
    main()
