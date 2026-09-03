#!/usr/bin/env python3
"""Add a behavior-neutral, self-describing CPU9 readback mismatch bitmap."""

from __future__ import annotations

import argparse
from pathlib import Path


HEADER_ANCHOR = "#define MT6797_A72_HOTPLUG_BIGIDVFS_VALUES 4U\n"
HEADER_ADDITION = r'''

/* Word 25 keeps legacy 0/1 values distinguishable from this bitmap. */
#define MT6797_A72_HOTPLUG_READBACK_BITMAP_V1 BIT(31)
#define MT6797_A72_HOTPLUG_MISMATCH_BASELINE_NULL BIT(0)
#define MT6797_A72_HOTPLUG_MISMATCH_POST_NULL BIT(1)
#define MT6797_A72_HOTPLUG_MISMATCH_BASELINE_INVALID BIT(2)
#define MT6797_A72_HOTPLUG_MISMATCH_BASELINE_STATUS_CPU8 BIT(3)
#define MT6797_A72_HOTPLUG_MISMATCH_BASELINE_STATUS2_CPU8 BIT(4)
#define MT6797_A72_HOTPLUG_MISMATCH_BASELINE_STATUS_CPU9 BIT(5)
#define MT6797_A72_HOTPLUG_MISMATCH_BASELINE_STATUS2_CPU9 BIT(6)
#define MT6797_A72_HOTPLUG_MISMATCH_BASELINE_CCI_BEFORE BIT(7)
#define MT6797_A72_HOTPLUG_MISMATCH_BASELINE_CCI_AFTER BIT(8)
#define MT6797_A72_HOTPLUG_MISMATCH_POST_INVALID BIT(9)
#define MT6797_A72_HOTPLUG_MISMATCH_POST_STATUS_CPU8 BIT(10)
#define MT6797_A72_HOTPLUG_MISMATCH_POST_STATUS2_CPU8 BIT(11)
#define MT6797_A72_HOTPLUG_MISMATCH_POST_STATUS_CPU9 BIT(12)
#define MT6797_A72_HOTPLUG_MISMATCH_POST_STATUS2_CPU9 BIT(13)
#define MT6797_A72_HOTPLUG_MISMATCH_POST_CCI_BEFORE BIT(14)
#define MT6797_A72_HOTPLUG_MISMATCH_POST_CCI_AFTER BIT(15)
#define MT6797_A72_HOTPLUG_MISMATCH_MP2_CPUSYS_PWR_CON BIT(16)
#define MT6797_A72_HOTPLUG_MISMATCH_CPU8_PWR_CON BIT(17)
#define MT6797_A72_HOTPLUG_MISMATCH_EXT_ISO BIT(18)
#define MT6797_A72_HOTPLUG_MISMATCH_DCM BIT(19)
#define MT6797_A72_HOTPLUG_MISMATCH_CCI_REQUEST BIT(20)
#define MT6797_A72_HOTPLUG_MISMATCH_PROVIDER BIT(21)
#define MT6797_A72_HOTPLUG_MISMATCH_CLOCK BIT(22)
#define MT6797_A72_HOTPLUG_MISMATCH_BIGIDVFS BIT(23)
#define MT6797_A72_HOTPLUG_MISMATCH_MASK GENMASK(23, 0)
'''

DECLARATION_ANCHOR = r'''bool mt6797_a72_hotplug_readback_proves_cpu9_off(
	const struct mt6797_a72_hotplug_readback *baseline,
	const struct mt6797_a72_hotplug_readback *post_state);
'''
DECLARATION_REPLACEMENT = r'''u32 mt6797_a72_hotplug_readback_mismatch(
	const struct mt6797_a72_hotplug_readback *baseline,
	const struct mt6797_a72_hotplug_readback *post_state);
bool mt6797_a72_hotplug_readback_proves_cpu9_off(
	const struct mt6797_a72_hotplug_readback *baseline,
	const struct mt6797_a72_hotplug_readback *post_state);
'''

PREDICATE_OLD = r'''bool mt6797_a72_hotplug_readback_proves_cpu9_off(
	const struct mt6797_a72_hotplug_readback *baseline,
	const struct mt6797_a72_hotplug_readback *post_state)
{
	if (!baseline || !post_state ||
	    !mt6797_a72_hotplug_status_exact(baseline, true) ||
	    !mt6797_a72_hotplug_status_exact(post_state, false))
		return false;
	return baseline->spm_mp2_cpusys_pwr_con ==
			post_state->spm_mp2_cpusys_pwr_con &&
		baseline->spm_mp2_cpu0_pwr_con ==
			post_state->spm_mp2_cpu0_pwr_con &&
		!((baseline->spm_cpu_ext_buck_iso ^
		   post_state->spm_cpu_ext_buck_iso) &
		  MT6797_A72_HOTPLUG_EXT_ISO_MASK) &&
		!((baseline->mp2_sync_dcm ^ post_state->mp2_sync_dcm) &
		  MT6797_A72_HOTPLUG_DCM_MASK) &&
		!((baseline->cci_mp2_port_control ^
		   post_state->cci_mp2_port_control) &
		  MT6797_A72_HOTPLUG_CCI_REQUEST_MASK) &&
		!memcmp(baseline->provider, post_state->provider,
			sizeof(baseline->provider)) &&
		!memcmp(baseline->clock, post_state->clock,
			sizeof(baseline->clock)) &&
		!memcmp(baseline->bigidvfs, post_state->bigidvfs,
			sizeof(baseline->bigidvfs));
}
'''

PREDICATE_NEW = r'''u32 mt6797_a72_hotplug_readback_mismatch(
	const struct mt6797_a72_hotplug_readback *baseline,
	const struct mt6797_a72_hotplug_readback *post_state)
{
	u32 mismatch = 0;

	if (!baseline) {
		mismatch |= MT6797_A72_HOTPLUG_MISMATCH_BASELINE_NULL;
	} else {
		if (!baseline->valid)
			mismatch |= MT6797_A72_HOTPLUG_MISMATCH_BASELINE_INVALID;
		if (!(baseline->spm_cpu_pwr_status &
		      MT6797_A72_HOTPLUG_CPU8_STATUS))
			mismatch |= MT6797_A72_HOTPLUG_MISMATCH_BASELINE_STATUS_CPU8;
		if (!(baseline->spm_cpu_pwr_status_2nd &
		      MT6797_A72_HOTPLUG_CPU8_STATUS))
			mismatch |= MT6797_A72_HOTPLUG_MISMATCH_BASELINE_STATUS2_CPU8;
		if (!(baseline->spm_cpu_pwr_status &
		      MT6797_A72_HOTPLUG_CPU9_STATUS))
			mismatch |= MT6797_A72_HOTPLUG_MISMATCH_BASELINE_STATUS_CPU9;
		if (!(baseline->spm_cpu_pwr_status_2nd &
		      MT6797_A72_HOTPLUG_CPU9_STATUS))
			mismatch |= MT6797_A72_HOTPLUG_MISMATCH_BASELINE_STATUS2_CPU9;
		if (baseline->cci_status_before & MT6797_A72_HOTPLUG_CCI_PENDING)
			mismatch |= MT6797_A72_HOTPLUG_MISMATCH_BASELINE_CCI_BEFORE;
		if (baseline->cci_status_after & MT6797_A72_HOTPLUG_CCI_PENDING)
			mismatch |= MT6797_A72_HOTPLUG_MISMATCH_BASELINE_CCI_AFTER;
	}
	if (!post_state) {
		mismatch |= MT6797_A72_HOTPLUG_MISMATCH_POST_NULL;
	} else {
		if (!post_state->valid)
			mismatch |= MT6797_A72_HOTPLUG_MISMATCH_POST_INVALID;
		if (!(post_state->spm_cpu_pwr_status &
		      MT6797_A72_HOTPLUG_CPU8_STATUS))
			mismatch |= MT6797_A72_HOTPLUG_MISMATCH_POST_STATUS_CPU8;
		if (!(post_state->spm_cpu_pwr_status_2nd &
		      MT6797_A72_HOTPLUG_CPU8_STATUS))
			mismatch |= MT6797_A72_HOTPLUG_MISMATCH_POST_STATUS2_CPU8;
		if (post_state->spm_cpu_pwr_status &
		    MT6797_A72_HOTPLUG_CPU9_STATUS)
			mismatch |= MT6797_A72_HOTPLUG_MISMATCH_POST_STATUS_CPU9;
		if (post_state->spm_cpu_pwr_status_2nd &
		    MT6797_A72_HOTPLUG_CPU9_STATUS)
			mismatch |= MT6797_A72_HOTPLUG_MISMATCH_POST_STATUS2_CPU9;
		if (post_state->cci_status_before & MT6797_A72_HOTPLUG_CCI_PENDING)
			mismatch |= MT6797_A72_HOTPLUG_MISMATCH_POST_CCI_BEFORE;
		if (post_state->cci_status_after & MT6797_A72_HOTPLUG_CCI_PENDING)
			mismatch |= MT6797_A72_HOTPLUG_MISMATCH_POST_CCI_AFTER;
	}
	if (!baseline || !post_state)
		return mismatch;
	if (baseline->spm_mp2_cpusys_pwr_con !=
	    post_state->spm_mp2_cpusys_pwr_con)
		mismatch |= MT6797_A72_HOTPLUG_MISMATCH_MP2_CPUSYS_PWR_CON;
	if (baseline->spm_mp2_cpu0_pwr_con !=
	    post_state->spm_mp2_cpu0_pwr_con)
		mismatch |= MT6797_A72_HOTPLUG_MISMATCH_CPU8_PWR_CON;
	if ((baseline->spm_cpu_ext_buck_iso ^
	     post_state->spm_cpu_ext_buck_iso) &
	    MT6797_A72_HOTPLUG_EXT_ISO_MASK)
		mismatch |= MT6797_A72_HOTPLUG_MISMATCH_EXT_ISO;
	if ((baseline->mp2_sync_dcm ^ post_state->mp2_sync_dcm) &
	    MT6797_A72_HOTPLUG_DCM_MASK)
		mismatch |= MT6797_A72_HOTPLUG_MISMATCH_DCM;
	if ((baseline->cci_mp2_port_control ^
	     post_state->cci_mp2_port_control) &
	    MT6797_A72_HOTPLUG_CCI_REQUEST_MASK)
		mismatch |= MT6797_A72_HOTPLUG_MISMATCH_CCI_REQUEST;
	if (memcmp(baseline->provider, post_state->provider,
		   sizeof(baseline->provider)))
		mismatch |= MT6797_A72_HOTPLUG_MISMATCH_PROVIDER;
	if (memcmp(baseline->clock, post_state->clock,
		   sizeof(baseline->clock)))
		mismatch |= MT6797_A72_HOTPLUG_MISMATCH_CLOCK;
	if (memcmp(baseline->bigidvfs, post_state->bigidvfs,
		   sizeof(baseline->bigidvfs)))
		mismatch |= MT6797_A72_HOTPLUG_MISMATCH_BIGIDVFS;
	return mismatch;
}

bool mt6797_a72_hotplug_readback_proves_cpu9_off(
	const struct mt6797_a72_hotplug_readback *baseline,
	const struct mt6797_a72_hotplug_readback *post_state)
{
	return !mt6797_a72_hotplug_readback_mismatch(baseline, post_state);
}
'''

BINDING_OLD = r'''		.readback_mismatch = binding->down_result.snapshots == 2 &&
			!mt6797_a72_hotplug_readback_proves_cpu9_off(
				&binding->down_result.baseline,
				&binding->down_result.post_state),
'''
BINDING_NEW = r'''		.readback_mismatch = binding->down_result.snapshots == 2 ?
			MT6797_A72_HOTPLUG_READBACK_BITMAP_V1 |
			mt6797_a72_hotplug_readback_mismatch(
				&binding->down_result.baseline,
				&binding->down_result.post_state) : 0,
'''

TEST_ANCHOR = "static void mt6797_hotplug_readback_rejections(struct kunit *test)\n"
TEST_ADDITION = r'''static void mt6797_hotplug_readback_bitmap(struct kunit *test)
{
	struct mt6797_hotplug_test_state *state = test->priv;
	struct mt6797_a72_hotplug_readback baseline = state->samples[0];
	struct mt6797_a72_hotplug_readback post = state->samples[1];

	KUNIT_EXPECT_EQ(test, mt6797_a72_hotplug_readback_mismatch(
		&baseline, &post), 0U);
	KUNIT_EXPECT_EQ(test, mt6797_a72_hotplug_readback_mismatch(
		NULL, &post), (u32)MT6797_A72_HOTPLUG_MISMATCH_BASELINE_NULL);
	KUNIT_EXPECT_EQ(test, mt6797_a72_hotplug_readback_mismatch(
		&baseline, NULL), (u32)MT6797_A72_HOTPLUG_MISMATCH_POST_NULL);
#define EXPECT_BASELINE(field, change, expected) do { \
	baseline = state->samples[0]; \
	baseline.field change; \
	KUNIT_EXPECT_EQ(test, mt6797_a72_hotplug_readback_mismatch( \
		&baseline, &post), (u32)(expected)); \
} while (0)
#define EXPECT_POST(field, change, expected) do { \
	post = state->samples[1]; \
	post.field change; \
	KUNIT_EXPECT_EQ(test, mt6797_a72_hotplug_readback_mismatch( \
		&state->samples[0], &post), (u32)(expected)); \
} while (0)
	EXPECT_BASELINE(valid, = false,
		MT6797_A72_HOTPLUG_MISMATCH_BASELINE_INVALID);
	EXPECT_BASELINE(spm_cpu_pwr_status,
		&= ~MT6797_A72_HOTPLUG_CPU8_STATUS,
		MT6797_A72_HOTPLUG_MISMATCH_BASELINE_STATUS_CPU8);
	EXPECT_BASELINE(spm_cpu_pwr_status_2nd,
		&= ~MT6797_A72_HOTPLUG_CPU8_STATUS,
		MT6797_A72_HOTPLUG_MISMATCH_BASELINE_STATUS2_CPU8);
	EXPECT_BASELINE(spm_cpu_pwr_status,
		&= ~MT6797_A72_HOTPLUG_CPU9_STATUS,
		MT6797_A72_HOTPLUG_MISMATCH_BASELINE_STATUS_CPU9);
	EXPECT_BASELINE(spm_cpu_pwr_status_2nd,
		&= ~MT6797_A72_HOTPLUG_CPU9_STATUS,
		MT6797_A72_HOTPLUG_MISMATCH_BASELINE_STATUS2_CPU9);
	EXPECT_BASELINE(cci_status_before,
		= MT6797_A72_HOTPLUG_CCI_PENDING,
		MT6797_A72_HOTPLUG_MISMATCH_BASELINE_CCI_BEFORE);
	EXPECT_BASELINE(cci_status_after,
		= MT6797_A72_HOTPLUG_CCI_PENDING,
		MT6797_A72_HOTPLUG_MISMATCH_BASELINE_CCI_AFTER);
	EXPECT_POST(valid, = false, MT6797_A72_HOTPLUG_MISMATCH_POST_INVALID);
	EXPECT_POST(spm_cpu_pwr_status,
		&= ~MT6797_A72_HOTPLUG_CPU8_STATUS,
		MT6797_A72_HOTPLUG_MISMATCH_POST_STATUS_CPU8);
	EXPECT_POST(spm_cpu_pwr_status_2nd,
		&= ~MT6797_A72_HOTPLUG_CPU8_STATUS,
		MT6797_A72_HOTPLUG_MISMATCH_POST_STATUS2_CPU8);
	EXPECT_POST(spm_cpu_pwr_status,
		|= MT6797_A72_HOTPLUG_CPU9_STATUS,
		MT6797_A72_HOTPLUG_MISMATCH_POST_STATUS_CPU9);
	EXPECT_POST(spm_cpu_pwr_status_2nd,
		|= MT6797_A72_HOTPLUG_CPU9_STATUS,
		MT6797_A72_HOTPLUG_MISMATCH_POST_STATUS2_CPU9);
	EXPECT_POST(cci_status_before, = MT6797_A72_HOTPLUG_CCI_PENDING,
		MT6797_A72_HOTPLUG_MISMATCH_POST_CCI_BEFORE);
	EXPECT_POST(cci_status_after, = MT6797_A72_HOTPLUG_CCI_PENDING,
		MT6797_A72_HOTPLUG_MISMATCH_POST_CCI_AFTER);
	EXPECT_POST(spm_mp2_cpusys_pwr_con, ^= 1,
		MT6797_A72_HOTPLUG_MISMATCH_MP2_CPUSYS_PWR_CON);
	EXPECT_POST(spm_mp2_cpu0_pwr_con, ^= 1,
		MT6797_A72_HOTPLUG_MISMATCH_CPU8_PWR_CON);
	EXPECT_POST(spm_cpu_ext_buck_iso,
		^= MT6797_A72_HOTPLUG_EXT_ISO_MASK,
		MT6797_A72_HOTPLUG_MISMATCH_EXT_ISO);
	EXPECT_POST(mp2_sync_dcm, ^= BIT(0),
		MT6797_A72_HOTPLUG_MISMATCH_DCM);
	EXPECT_POST(cci_mp2_port_control, ^= BIT(0),
		MT6797_A72_HOTPLUG_MISMATCH_CCI_REQUEST);
	EXPECT_POST(provider[0], ^= 1,
		MT6797_A72_HOTPLUG_MISMATCH_PROVIDER);
	EXPECT_POST(clock[0], ^= 1, MT6797_A72_HOTPLUG_MISMATCH_CLOCK);
	EXPECT_POST(bigidvfs[0], ^= 1,
		MT6797_A72_HOTPLUG_MISMATCH_BIGIDVFS);
#undef EXPECT_POST
#undef EXPECT_BASELINE
}

'''
CASE_ANCHOR = "\tKUNIT_CASE(mt6797_hotplug_readback_rejections),\n"
CASE_REPLACEMENT = (
    "\tKUNIT_CASE(mt6797_hotplug_readback_bitmap),\n" + CASE_ANCHOR
)


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
    header = root / "drivers/soc/mediatek/mt6797-a72-hotplug-executor-internal.h"
    source = root / "drivers/soc/mediatek/mt6797-a72-hotplug-executor.c"
    test = root / "drivers/soc/mediatek/mt6797-a72-hotplug-executor-test.c"
    binding = root / "drivers/soc/mediatek/mt6797-a72-hotplug-binding.c"

    replace_once(header, HEADER_ANCHOR, HEADER_ANCHOR + HEADER_ADDITION)
    replace_once(header, DECLARATION_ANCHOR, DECLARATION_REPLACEMENT)
    replace_once(source, PREDICATE_OLD, PREDICATE_NEW)
    replace_once(binding, BINDING_OLD, BINDING_NEW)
    replace_once(test, TEST_ANCHOR, TEST_ADDITION + TEST_ANCHOR)
    replace_once(test, CASE_ANCHOR, CASE_REPLACEMENT)


if __name__ == "__main__":
    main()
