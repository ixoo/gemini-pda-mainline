#!/usr/bin/env python3
"""Apply deterministic MT6797 protected-clock decoder edits."""

from __future__ import annotations

import argparse
from pathlib import Path


HEADER = r'''/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef __LINUX_SOC_MEDIATEK_MT6797_DVFSP_CLOCK_STATE_H
#define __LINUX_SOC_MEDIATEK_MT6797_DVFSP_CLOCK_STATE_H

#include <linux/bitops.h>
#include <linux/types.h>

#include <linux/soc/mediatek/mt6797-bigidvfs-backend.h>
#include <linux/soc/mediatek/mt6797-dvfsp-clock-backend.h>

#define MT6797_DVFSP_CLOCK_STATE_ABI		1
#define MT6797_DVFSP_CLOCK_STATE_PARENT_MHZ	26
#define MT6797_DVFSP_CLOCK_STATE_PCW_MASK	GENMASK(20, 0)
#define MT6797_DVFSP_CLOCK_STATE_POSDIV_MASK	GENMASK(26, 24)
#define MT6797_DVFSP_CLOCK_STATE_PCW_STROBE	BIT(31)
#define MT6797_DVFSP_CLOCK_STATE_BIG_PCW_MASK	GENMASK(30, 0)
#define MT6797_DVFSP_CLOCK_STATE_BIG_POSDIV_MASK	GENMASK(14, 12)
#define MT6797_DVFSP_CLOCK_STATE_CLUSTER_COUNT	4

enum mt6797_dvfsp_clock_state_cluster_id {
	MT6797_DVFSP_CLOCK_STATE_CLUSTER_LL,
	MT6797_DVFSP_CLOCK_STATE_CLUSTER_L,
	MT6797_DVFSP_CLOCK_STATE_CLUSTER_B,
	MT6797_DVFSP_CLOCK_STATE_CLUSTER_CCI,
};

struct mt6797_dvfsp_clock_state_cluster {
	u32 mux_selector;
	u32 divider_selector;
	u32 pll_pcw;
	u32 posdiv;
	u32 frequency_khz;
};

struct mt6797_dvfsp_clock_state {
	u32 abi;
	u32 reserved;
	u64 clock_sample_generation;
	u64 big_sample_generation;
	struct mt6797_dvfsp_clock_state_cluster
		cluster[MT6797_DVFSP_CLOCK_STATE_CLUSTER_COUNT];
};

int mt6797_dvfsp_clock_state_decode(
	const struct mt6797_dvfsp_clock_readback *clock,
	const struct mt6797_bigidvfs_readback *big,
	struct mt6797_dvfsp_clock_state *state);

#endif /* __LINUX_SOC_MEDIATEK_MT6797_DVFSP_CLOCK_STATE_H */
'''


SOURCE = r'''// SPDX-License-Identifier: GPL-2.0-only
/*
 * Pure conversion of the disabled MT6797 protected clock readbacks.
 *
 * The normal PLLs use a 21-bit PCW with 14 fractional bits and POSDIV in
 * CON1. BigiDVFS instead uses a 31-bit PCW with 24 fractional bits and keeps
 * POSDIV in a separate register. Bit 31 is a write-trigger strobe, not a
 * readable busy state. No hardware access is performed here.
 */

#include <linux/bitfield.h>
#include <linux/bitops.h>
#include <linux/errno.h>
#include <linux/math64.h>
#include <linux/module.h>
#include <linux/string.h>
#include <linux/types.h>

#include <linux/soc/mediatek/mt6797-dvfsp-clock-state.h>

struct mt6797_dvfsp_clock_divider {
	u32 numerator;
	u32 denominator;
};

static int mt6797_dvfsp_clock_divider_decode(
	u32 selector, struct mt6797_dvfsp_clock_divider *divider)
{
	if (!divider)
		return -EINVAL;

	switch (selector) {
	case 8:
		*divider = (struct mt6797_dvfsp_clock_divider){ 1, 1 };
		break;
	case 9:
		*divider = (struct mt6797_dvfsp_clock_divider){ 3, 4 };
		break;
	case 10:
		*divider = (struct mt6797_dvfsp_clock_divider){ 1, 2 };
		break;
	case 11:
		*divider = (struct mt6797_dvfsp_clock_divider){ 1, 4 };
		break;
	case 17:
		*divider = (struct mt6797_dvfsp_clock_divider){ 4, 5 };
		break;
	case 18:
		*divider = (struct mt6797_dvfsp_clock_divider){ 3, 5 };
		break;
	case 19:
		*divider = (struct mt6797_dvfsp_clock_divider){ 2, 5 };
		break;
	case 20:
		*divider = (struct mt6797_dvfsp_clock_divider){ 1, 5 };
		break;
	case 25:
		*divider = (struct mt6797_dvfsp_clock_divider){ 5, 6 };
		break;
	case 26:
		*divider = (struct mt6797_dvfsp_clock_divider){ 4, 6 };
		break;
	case 27:
		*divider = (struct mt6797_dvfsp_clock_divider){ 3, 6 };
		break;
	case 28:
		*divider = (struct mt6797_dvfsp_clock_divider){ 2, 6 };
		break;
	case 29:
		*divider = (struct mt6797_dvfsp_clock_divider){ 1, 6 };
		break;
	default:
		return -EPROTO;
	}

	return 0;
}

static int mt6797_dvfsp_clock_apply_divider(
	u64 frequency, u32 divider_selector, u32 *frequency_khz)
{
	struct mt6797_dvfsp_clock_divider divider;
	int ret;

	if (!frequency_khz || !frequency)
		return -ERANGE;

	ret = mt6797_dvfsp_clock_divider_decode(divider_selector, &divider);
	if (ret)
		return ret;

	frequency = div_u64(frequency * divider.numerator,
				divider.denominator);
	if (!frequency || frequency > U32_MAX)
		return -ERANGE;

	*frequency_khz = (u32)frequency;
	return 0;
}

static int mt6797_dvfsp_clock_frequency_decode(
	u32 pll_pcw, u32 posdiv, u32 divider_selector, u32 *frequency_khz)
{
	u64 frequency;

	if (!pll_pcw || posdiv > 2)
		return -EPROTO;

	/* Match the normal vendor order: PCW to kHz, then POSDIV. */
	frequency = ((u64)pll_pcw * MT6797_DVFSP_CLOCK_STATE_PARENT_MHZ) >> 14;
	frequency *= 1000;
	frequency = div_u64(frequency, BIT(posdiv));

	return mt6797_dvfsp_clock_apply_divider(
		frequency, divider_selector, frequency_khz);
}

static int mt6797_dvfsp_clock_big_frequency_decode(
	u32 pll_pcw, u32 posdiv, u32 divider_selector, u32 *frequency_khz)
{
	u64 frequency;

	if (!pll_pcw)
		return -EPROTO;

	/* BigiDVFS truncates to integer MHz before POSDIV and kHz conversion. */
	frequency = ((u64)pll_pcw * MT6797_DVFSP_CLOCK_STATE_PARENT_MHZ) >> 24;
	frequency = div_u64(frequency, BIT(posdiv));
	frequency *= 1000;

	return mt6797_dvfsp_clock_apply_divider(
		frequency, divider_selector, frequency_khz);
}

static int mt6797_dvfsp_clock_cluster_decode(
	u32 con1, u32 mux, u32 divider_selector,
	struct mt6797_dvfsp_clock_state_cluster *cluster)
{
	if (!cluster)
		return -EINVAL;

	cluster->mux_selector = mux;
	cluster->divider_selector = divider_selector;
	cluster->pll_pcw = con1 & MT6797_DVFSP_CLOCK_STATE_PCW_MASK;
	cluster->posdiv = FIELD_GET(MT6797_DVFSP_CLOCK_STATE_POSDIV_MASK,
				    con1);

	return mt6797_dvfsp_clock_frequency_decode(
		cluster->pll_pcw, cluster->posdiv, divider_selector,
		&cluster->frequency_khz);
}

static int mt6797_dvfsp_clock_big_cluster_decode(
	const struct mt6797_bigidvfs_readback *big, u32 mux,
	u32 divider_selector, struct mt6797_dvfsp_clock_state_cluster *cluster)
{
	if (!big || !cluster)
		return -EINVAL;

	cluster->mux_selector = mux;
	cluster->divider_selector = divider_selector;
	cluster->pll_pcw = big->pll_pcw &
		MT6797_DVFSP_CLOCK_STATE_BIG_PCW_MASK;
	cluster->posdiv = FIELD_GET(MT6797_DVFSP_CLOCK_STATE_BIG_POSDIV_MASK,
				    big->pll_enable_posdiv);

	return mt6797_dvfsp_clock_big_frequency_decode(
		cluster->pll_pcw, cluster->posdiv, divider_selector,
		&cluster->frequency_khz);
}

int mt6797_dvfsp_clock_state_decode(
	const struct mt6797_dvfsp_clock_readback *clock,
	const struct mt6797_bigidvfs_readback *big,
	struct mt6797_dvfsp_clock_state *state)
{
	int ret;

	if (!clock || !big || !state ||
	    clock->abi != MT6797_DVFSP_CLOCK_BACKEND_ABI ||
	    big->abi != MT6797_BIGIDVFS_BACKEND_ABI ||
	    clock->reserved || big->reserved ||
	    !clock->sample_generation || !big->sample_generation)
		return -EPROTO;

	memset(state, 0, sizeof(*state));
	state->abi = MT6797_DVFSP_CLOCK_STATE_ABI;
	state->clock_sample_generation = clock->sample_generation;
	state->big_sample_generation = big->sample_generation;

	ret = mt6797_dvfsp_clock_cluster_decode(
		clock->pll_ll[1], FIELD_GET(GENMASK(3, 2),
				clock->armplldiv_muxsel), FIELD_GET(GENMASK(9, 5),
				clock->armplldiv_ckdiv), &state->cluster[
				MT6797_DVFSP_CLOCK_STATE_CLUSTER_LL]);
	if (ret)
		return ret;
	ret = mt6797_dvfsp_clock_cluster_decode(
		clock->pll_l[1], FIELD_GET(GENMASK(5, 4),
				clock->armplldiv_muxsel), FIELD_GET(GENMASK(14, 10),
				clock->armplldiv_ckdiv), &state->cluster[
				MT6797_DVFSP_CLOCK_STATE_CLUSTER_L]);
	if (ret)
		return ret;
	ret = mt6797_dvfsp_clock_big_cluster_decode(
		big, FIELD_GET(GENMASK(1, 0), clock->armplldiv_muxsel),
		FIELD_GET(GENMASK(4, 0), clock->armplldiv_ckdiv),
		&state->cluster[MT6797_DVFSP_CLOCK_STATE_CLUSTER_B]);
	if (ret)
		return ret;
	ret = mt6797_dvfsp_clock_cluster_decode(
		clock->pll_cci[1], FIELD_GET(GENMASK(7, 6),
				clock->armplldiv_muxsel), FIELD_GET(GENMASK(19, 15),
				clock->armplldiv_ckdiv), &state->cluster[
				MT6797_DVFSP_CLOCK_STATE_CLUSTER_CCI]);

	return ret;
}
EXPORT_SYMBOL_GPL(mt6797_dvfsp_clock_state_decode);
'''


TEST = r'''// SPDX-License-Identifier: GPL-2.0-only
#include <kunit/test.h>
#include <linux/errno.h>
#include <linux/module.h>

#include <linux/soc/mediatek/mt6797-dvfsp-clock-state.h>

static void mt6797_clock_state_valid(
	struct mt6797_dvfsp_clock_readback *clock,
	struct mt6797_bigidvfs_readback *big)
{
	*clock = (struct mt6797_dvfsp_clock_readback) {
		.abi = MT6797_DVFSP_CLOCK_BACKEND_ABI,
		.sample_generation = 11,
		.armplldiv_muxsel = 0x55,
		.armplldiv_ckdiv = 0x42108,
		.pll_ll = { 0, 0xc1114000, 0 },
		.pll_l = { 0, 0x400c4000, 0 },
		.pll_cci = { 0, 0xc10c1d89, 0 },
	};
	*big = (struct mt6797_bigidvfs_readback) {
		.abi = MT6797_BIGIDVFS_BACKEND_ABI,
		.sample_generation = 13,
		.pll_pcw = 0xc1130000,
		.pll_enable_posdiv = 0x07001000,
	};
}

static void mt6797_clock_state_stable_strobes_test(struct kunit *test)
{
	struct mt6797_dvfsp_clock_readback clock;
	struct mt6797_bigidvfs_readback big;
	struct mt6797_dvfsp_clock_state state;

	mt6797_clock_state_valid(&clock, &big);
	KUNIT_ASSERT_EQ(test,
		mt6797_dvfsp_clock_state_decode(&clock, &big, &state), 0);
	KUNIT_EXPECT_EQ(test, state.clock_sample_generation, 11ULL);
	KUNIT_EXPECT_EQ(test, state.big_sample_generation, 13ULL);
	KUNIT_EXPECT_EQ(test,
		state.cluster[MT6797_DVFSP_CLOCK_STATE_CLUSTER_LL].frequency_khz,
		897000U);
	KUNIT_EXPECT_EQ(test,
		state.cluster[MT6797_DVFSP_CLOCK_STATE_CLUSTER_L].frequency_khz,
		1274000U);
	KUNIT_EXPECT_EQ(test,
		state.cluster[MT6797_DVFSP_CLOCK_STATE_CLUSTER_CCI].frequency_khz,
		629500U);
	KUNIT_EXPECT_EQ(test,
		state.cluster[MT6797_DVFSP_CLOCK_STATE_CLUSTER_B].pll_pcw,
		0x41130000U);
	KUNIT_EXPECT_EQ(test,
		state.cluster[MT6797_DVFSP_CLOCK_STATE_CLUSTER_B].posdiv, 1U);
	KUNIT_EXPECT_EQ(test,
		state.cluster[MT6797_DVFSP_CLOCK_STATE_CLUSTER_B].frequency_khz,
		845000U);
}

static void mt6797_clock_state_big_fields_test(struct kunit *test)
{
	struct mt6797_dvfsp_clock_readback clock;
	struct mt6797_bigidvfs_readback big;
	struct mt6797_dvfsp_clock_state state;

	mt6797_clock_state_valid(&clock, &big);
	big.pll_pcw = 0xcc000000;
	big.pll_enable_posdiv = 0x07002000;
	clock.armplldiv_ckdiv = (clock.armplldiv_ckdiv & ~GENMASK(4, 0)) | 10;
	KUNIT_ASSERT_EQ(test,
		mt6797_dvfsp_clock_state_decode(&clock, &big, &state), 0);
	KUNIT_EXPECT_EQ(test,
		state.cluster[MT6797_DVFSP_CLOCK_STATE_CLUSTER_B].pll_pcw,
		0x4c000000U);
	KUNIT_EXPECT_EQ(test,
		state.cluster[MT6797_DVFSP_CLOCK_STATE_CLUSTER_B].posdiv, 2U);
	KUNIT_EXPECT_EQ(test,
		state.cluster[MT6797_DVFSP_CLOCK_STATE_CLUSTER_B].frequency_khz,
		247000U);
}

static void mt6797_clock_state_dividers_test(struct kunit *test)
{
	static const u32 selector[] = {
		8, 9, 10, 11, 17, 18, 19, 20, 25, 26, 27, 28, 29,
	};
	static const u32 expected[] = {
		1976000, 1482000, 988000, 494000, 1580800, 1185600,
		790400, 395200, 1646666, 1317333, 988000, 658666, 329333,
	};
	struct mt6797_dvfsp_clock_readback clock;
	struct mt6797_bigidvfs_readback big;
	struct mt6797_dvfsp_clock_state state;
	int i;

	for (i = 0; i < ARRAY_SIZE(selector); i++) {
		mt6797_clock_state_valid(&clock, &big);
		big.pll_pcw = 0x4c000000;
		big.pll_enable_posdiv = 0;
		clock.armplldiv_ckdiv =
			(clock.armplldiv_ckdiv & ~GENMASK(4, 0)) | selector[i];
		KUNIT_ASSERT_EQ(test,
			mt6797_dvfsp_clock_state_decode(&clock, &big, &state), 0);
		KUNIT_EXPECT_EQ(test,
			state.cluster[MT6797_DVFSP_CLOCK_STATE_CLUSTER_B].frequency_khz,
			expected[i]);
	}
}

static void mt6797_clock_state_transport_guards_test(struct kunit *test)
{
	struct mt6797_dvfsp_clock_readback clock;
	struct mt6797_bigidvfs_readback big;
	struct mt6797_dvfsp_clock_state state;

	mt6797_clock_state_valid(&clock, &big);
	clock.sample_generation = 0;
	KUNIT_EXPECT_EQ(test,
		mt6797_dvfsp_clock_state_decode(&clock, &big, &state), -EPROTO);
	mt6797_clock_state_valid(&clock, &big);
	big.sample_generation = 0;
	KUNIT_EXPECT_EQ(test,
		mt6797_dvfsp_clock_state_decode(&clock, &big, &state), -EPROTO);
	mt6797_clock_state_valid(&clock, &big);
	clock.reserved = 1;
	KUNIT_EXPECT_EQ(test,
		mt6797_dvfsp_clock_state_decode(&clock, &big, &state), -EPROTO);
	mt6797_clock_state_valid(&clock, &big);
	big.reserved = 1;
	KUNIT_EXPECT_EQ(test,
		mt6797_dvfsp_clock_state_decode(&clock, &big, &state), -EPROTO);
}

static void mt6797_clock_state_zero_pcw_test(struct kunit *test)
{
	struct mt6797_dvfsp_clock_readback clock;
	struct mt6797_bigidvfs_readback big;
	struct mt6797_dvfsp_clock_state state;

	mt6797_clock_state_valid(&clock, &big);
	clock.pll_ll[1] = MT6797_DVFSP_CLOCK_STATE_PCW_STROBE;
	KUNIT_EXPECT_EQ(test,
		mt6797_dvfsp_clock_state_decode(&clock, &big, &state), -EPROTO);
	mt6797_clock_state_valid(&clock, &big);
	big.pll_pcw = MT6797_DVFSP_CLOCK_STATE_PCW_STROBE;
	KUNIT_EXPECT_EQ(test,
		mt6797_dvfsp_clock_state_decode(&clock, &big, &state), -EPROTO);
}

static void mt6797_clock_state_encoding_guards_test(struct kunit *test)
{
	struct mt6797_dvfsp_clock_readback clock;
	struct mt6797_bigidvfs_readback big;
	struct mt6797_dvfsp_clock_state state;

	mt6797_clock_state_valid(&clock, &big);
	clock.pll_ll[1] = 0x83114000;
	KUNIT_EXPECT_EQ(test,
		mt6797_dvfsp_clock_state_decode(&clock, &big, &state), -EPROTO);
	mt6797_clock_state_valid(&clock, &big);
	clock.armplldiv_ckdiv &= ~GENMASK(4, 0);
	KUNIT_EXPECT_EQ(test,
		mt6797_dvfsp_clock_state_decode(&clock, &big, &state), -EPROTO);
	mt6797_clock_state_valid(&clock, &big);
	big.pll_pcw = 1;
	KUNIT_EXPECT_EQ(test,
		mt6797_dvfsp_clock_state_decode(&clock, &big, &state), -ERANGE);
}

static struct kunit_case mt6797_clock_state_cases[] = {
	KUNIT_CASE(mt6797_clock_state_stable_strobes_test),
	KUNIT_CASE(mt6797_clock_state_big_fields_test),
	KUNIT_CASE(mt6797_clock_state_dividers_test),
	KUNIT_CASE(mt6797_clock_state_transport_guards_test),
	KUNIT_CASE(mt6797_clock_state_zero_pcw_test),
	KUNIT_CASE(mt6797_clock_state_encoding_guards_test),
	{}
};

static struct kunit_suite mt6797_clock_state_suite = {
	.name = "mt6797-dvfsp-clock-state",
	.test_cases = mt6797_clock_state_cases,
};
kunit_test_suite(mt6797_clock_state_suite);

MODULE_LICENSE("GPL");
'''


KCONFIG_BLOCK = r'''

config MTK_MT6797_DVFSP_CLOCK_STATE_KUNIT_TEST
	bool "KUnit tests for MT6797 protected clock-state decoding"
	depends on KUNIT=y
	depends on MTK_MT6797_DVFSP_STATE_DECODERS
	default n
	help
	  Exercise stable bit-31 strobes, the distinct normal and BigiDVFS PCW
	  and post-divider formats, every ARMPLLDIV ratio, and malformed input
	  rejection through pure in-memory records.

	  No MMIO, secure call, clock, regulator, CPU, retained RAM, storage, or
	  device action is performed. If unsure, say N.
'''


def write_exact(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--phase", choices=("repair", "tests"), required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    source = root / "drivers/soc/mediatek/mt6797-dvfsp-clock-state.c"
    header = root / "include/linux/soc/mediatek/mt6797-dvfsp-clock-state.h"
    kconfig = root / "drivers/soc/mediatek/Kconfig"
    makefile = root / "drivers/soc/mediatek/Makefile"

    if args.phase == "repair":
        write_exact(source, SOURCE)
        write_exact(header, HEADER)
        return

    text = kconfig.read_text(encoding="utf-8")
    anchor = "\nconfig MTK_MT6797_DVFSP_CLOCK_BACKEND\n"
    if text.count(anchor) != 1:
        raise SystemExit("Kconfig insertion anchor changed")
    text = text.replace(anchor, KCONFIG_BLOCK + anchor)
    write_exact(kconfig, text)

    text = makefile.read_text(encoding="utf-8")
    anchor = (
        "obj-$(CONFIG_MTK_MT6797_DVFSP_STATE_DECODERS) += "
        "mt6797-dvfsp-clock-state.o\n"
    )
    if text.count(anchor) != 1:
        raise SystemExit("Makefile insertion anchor changed")
    text = text.replace(
        anchor,
        anchor
        + "obj-$(CONFIG_MTK_MT6797_DVFSP_CLOCK_STATE_KUNIT_TEST) += "
        + "mt6797-dvfsp-clock-state-test.o\n",
    )
    write_exact(makefile, text)
    write_exact(
        root / "drivers/soc/mediatek/mt6797-dvfsp-clock-state-test.c", TEST
    )


if __name__ == "__main__":
    main()
