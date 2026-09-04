#!/usr/bin/env python3
"""Apply deterministic bounded MT6797 A72 frequency-observer edits."""

from __future__ import annotations

import argparse
from pathlib import Path


OBSERVER_HEADER = r'''/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef __MT6797_A72_FREQUENCY_OBSERVER_INTERNAL_H
#define __MT6797_A72_FREQUENCY_OBSERVER_INTERNAL_H

#include <linux/mutex.h>
#include <linux/types.h>

#include <linux/soc/mediatek/mt6797-dvfsp-clock-state.h>

#define MT6797_A72_FREQUENCY_OBSERVER_ABI 1U
#define MT6797_A72_FREQUENCY_OBSERVER_MAX_ATTEMPTS 3U

struct device;
struct mt6797_a72_hotplug_snapshot_source;

struct mt6797_a72_frequency_observer_controller {
	/* Serialize the attempt budget and its paired transport calls. */
	struct mutex lock;
	u32 attempts;
};

struct mt6797_a72_frequency_observation {
	u32 abi;
	u32 attempt;
	u64 clock_sample_generation;
	u64 big_sample_generation;
	u32 armplldiv_muxsel;
	u32 armplldiv_ckdiv;
	u32 big_pll_pcw;
	u32 big_pll_enable_posdiv;
	struct mt6797_dvfsp_clock_state state;
};

struct mt6797_a72_frequency_observer_trace {
	u32 attempt;
	u32 attempts_remaining;
	u32 clock_calls;
	u32 bigidvfs_calls;
	u32 clock_poweron_writes_max;
	u32 clock_acquire_writes_max;
	u32 clock_release_writes_max;
	u32 bigidvfs_stable_samples;
	u32 bigidvfs_reads;
	u32 bigidvfs_sram_set_calls;
	bool complete;
};

#if IS_ENABLED(CONFIG_MTK_MT6797_A72_FREQUENCY_OBSERVER)
void mt6797_a72_frequency_observer_init(
	struct mt6797_a72_frequency_observer_controller *controller);
int mt6797_a72_frequency_observer_sample(
	struct mt6797_a72_frequency_observer_controller *controller,
	const struct mt6797_a72_hotplug_snapshot_source *source,
	struct mt6797_a72_frequency_observation *observation,
	struct mt6797_a72_frequency_observer_trace *trace);
int mt6797_a72_frequency_observer_register(struct device *dev);
#else
static inline void mt6797_a72_frequency_observer_init(
	struct mt6797_a72_frequency_observer_controller *controller)
{
}

static inline int mt6797_a72_frequency_observer_register(struct device *dev)
{
	return 0;
}
#endif

#endif /* __MT6797_A72_FREQUENCY_OBSERVER_INTERNAL_H */
'''


OBSERVER_SOURCE = r'''// SPDX-License-Identifier: GPL-2.0-only
/* Three-sample read-only MT6797 A72 frequency observation boundary. */

#include <linux/device.h>
#include <linux/errno.h>
#include <linux/module.h>
#include <linux/string.h>
#include <linux/sysfs.h>

#include "mt6797-a72-frequency-observer-internal.h"
#include "mt6797-a72-hotplug-snapshot-internal.h"

void mt6797_a72_frequency_observer_init(
	struct mt6797_a72_frequency_observer_controller *controller)
{
	if (!controller)
		return;
	mutex_init(&controller->lock);
	controller->attempts = 0;
}

static int mt6797_a72_frequency_observer_capture(
	const struct mt6797_a72_hotplug_snapshot_source *source,
	struct mt6797_a72_frequency_observation *observation,
	struct mt6797_a72_frequency_observer_trace *trace)
{
	struct mt6797_dvfsp_clock_readback clock = { };
	struct mt6797_bigidvfs_readback big = { };
	int ret;

	trace->clock_calls++;
	ret = source->ops->clock(source->clock, &clock);
	if (ret)
		return ret;
	if (clock.abi != MT6797_DVFSP_CLOCK_BACKEND_ABI || clock.reserved ||
	    !clock.sample_generation)
		return -EPROTO;

	trace->bigidvfs_calls++;
	ret = source->ops->bigidvfs(source->bigidvfs, &big);
	if (ret)
		return ret;
	if (big.abi != MT6797_BIGIDVFS_BACKEND_ABI || big.reserved ||
	    !big.sample_generation)
		return -EPROTO;

	ret = mt6797_dvfsp_clock_state_decode(
		&clock, &big, &observation->state);
	if (ret)
		return ret;

	observation->abi = MT6797_A72_FREQUENCY_OBSERVER_ABI;
	observation->clock_sample_generation = clock.sample_generation;
	observation->big_sample_generation = big.sample_generation;
	observation->armplldiv_muxsel = clock.armplldiv_muxsel;
	observation->armplldiv_ckdiv = clock.armplldiv_ckdiv;
	observation->big_pll_pcw = big.pll_pcw;
	observation->big_pll_enable_posdiv = big.pll_enable_posdiv;
	trace->complete = true;
	return 0;
}

int mt6797_a72_frequency_observer_sample(
	struct mt6797_a72_frequency_observer_controller *controller,
	const struct mt6797_a72_hotplug_snapshot_source *source,
	struct mt6797_a72_frequency_observation *observation,
	struct mt6797_a72_frequency_observer_trace *trace)
{
	int ret;

	if (!observation || !trace)
		return -EINVAL;
	memset(observation, 0, sizeof(*observation));
	memset(trace, 0, sizeof(*trace));
	if (!controller || !source || !source->clock || !source->bigidvfs ||
	    !source->ops || !source->ops->clock || !source->ops->bigidvfs)
		return -EINVAL;

	mutex_lock(&controller->lock);
	if (controller->attempts >=
	    MT6797_A72_FREQUENCY_OBSERVER_MAX_ATTEMPTS) {
		trace->attempt = controller->attempts;
		ret = -ENOSPC;
		goto out_unlock;
	}

	controller->attempts++;
	trace->attempt = controller->attempts;
	trace->attempts_remaining =
		MT6797_A72_FREQUENCY_OBSERVER_MAX_ATTEMPTS -
		controller->attempts;
	trace->clock_poweron_writes_max =
		MT6797_A72_HOTPLUG_CLOCK_POWERON_WRITES;
	trace->clock_acquire_writes_max =
		MT6797_A72_HOTPLUG_CLOCK_ACQUIRE_WRITES_MAX;
	trace->clock_release_writes_max =
		MT6797_A72_HOTPLUG_CLOCK_RELEASE_WRITES_MAX;
	trace->bigidvfs_stable_samples =
		MT6797_A72_HOTPLUG_BIGIDVFS_STABLE_SAMPLES;
	trace->bigidvfs_reads = MT6797_A72_HOTPLUG_BIGIDVFS_READS;

	ret = mt6797_a72_frequency_observer_capture(source, observation, trace);
	if (ret)
		memset(observation, 0, sizeof(*observation));
	else
		observation->attempt = trace->attempt;

out_unlock:
	mutex_unlock(&controller->lock);
	return ret;
}

static ssize_t a72_frequency_observation_show(
	struct device *dev, struct device_attribute *attr, char *buf)
{
	struct mt6797_a72_hotplug_snapshot_source *source =
		dev_get_drvdata(dev);
	struct mt6797_a72_frequency_observer_trace trace;
	struct mt6797_a72_frequency_observation observation;
	const struct mt6797_dvfsp_clock_state_cluster *big;
	ssize_t count = 0;
	int ret;

	if (!source)
		return -ENODEV;
	ret = mt6797_a72_frequency_observer_sample(
		&source->frequency_observer, source, &observation, &trace);
	if (ret) {
		dev_info(dev,
			 "GEMINI_A72_FREQUENCY_OBSERVATION_V1 attempt=%u/3 ret=%d\n",
			 trace.attempt, ret);
		return ret;
	}

	big = &observation.state.cluster[
		MT6797_DVFSP_CLOCK_STATE_CLUSTER_B];
	count += sysfs_emit_at(buf, count,
		"abi=%u attempt=%u max_attempts=%u remaining=%u ",
		observation.abi, observation.attempt,
		MT6797_A72_FREQUENCY_OBSERVER_MAX_ATTEMPTS,
		trace.attempts_remaining);
	count += sysfs_emit_at(buf, count,
		"clock_generation=%llu big_generation=%llu ",
		(unsigned long long)observation.clock_sample_generation,
		(unsigned long long)observation.big_sample_generation);
	count += sysfs_emit_at(buf, count,
		"armplldiv_muxsel=0x%08x armplldiv_ckdiv=0x%08x ",
		observation.armplldiv_muxsel, observation.armplldiv_ckdiv);
	count += sysfs_emit_at(buf, count,
		"big_pll_pcw=0x%08x big_pll_enable_posdiv=0x%08x ",
		observation.big_pll_pcw, observation.big_pll_enable_posdiv);
	count += sysfs_emit_at(buf, count,
		"b_pcw=0x%08x b_posdiv=%u b_mux=%u b_divider=%u ",
		big->pll_pcw, big->posdiv, big->mux_selector,
		big->divider_selector);
	count += sysfs_emit_at(buf, count,
		"ll_khz=%u l_khz=%u b_khz=%u cci_khz=%u\n",
		observation.state.cluster[
			MT6797_DVFSP_CLOCK_STATE_CLUSTER_LL].frequency_khz,
		observation.state.cluster[
			MT6797_DVFSP_CLOCK_STATE_CLUSTER_L].frequency_khz,
		big->frequency_khz,
		observation.state.cluster[
			MT6797_DVFSP_CLOCK_STATE_CLUSTER_CCI].frequency_khz);
	dev_info(dev, "GEMINI_A72_FREQUENCY_OBSERVATION_V1 %s", buf);
	return count;
}
static DEVICE_ATTR_RO(a72_frequency_observation);

static struct attribute *mt6797_a72_frequency_observer_attrs[] = {
	&dev_attr_a72_frequency_observation.attr,
	NULL,
};

static const struct attribute_group mt6797_a72_frequency_observer_group = {
	.attrs = mt6797_a72_frequency_observer_attrs,
};

int mt6797_a72_frequency_observer_register(struct device *dev)
{
	if (!dev)
		return -EINVAL;
	return devm_device_add_group(dev,
				     &mt6797_a72_frequency_observer_group);
}

MODULE_DESCRIPTION("Bounded read-only MT6797 A72 frequency observer");
MODULE_LICENSE("GPL");
'''


OBSERVER_TEST = r'''// SPDX-License-Identifier: GPL-2.0-only
/* In-memory tests for the bounded MT6797 A72 frequency observer. */

#include <kunit/test.h>
#include <linux/errno.h>
#include <linux/string.h>

#include "mt6797-a72-frequency-observer-internal.h"
#include "mt6797-a72-hotplug-snapshot-internal.h"

struct frequency_observer_test_state {
	struct mt6797_dvfsp_clock_readback clock;
	struct mt6797_bigidvfs_readback big;
	u32 clock_calls;
	u32 big_calls;
	int clock_error;
	int big_error;
	u8 devices[2];
};

static struct frequency_observer_test_state *frequency_observer_state;

static int frequency_observer_clock(
	struct device *dev, struct mt6797_dvfsp_clock_readback *clock)
{
	struct frequency_observer_test_state *state = frequency_observer_state;

	state->clock_calls++;
	if (state->clock_error)
		return state->clock_error;
	*clock = state->clock;
	return 0;
}

static int frequency_observer_big(
	struct device *dev, struct mt6797_bigidvfs_readback *big)
{
	struct frequency_observer_test_state *state = frequency_observer_state;

	state->big_calls++;
	if (state->big_error)
		return state->big_error;
	*big = state->big;
	return 0;
}

static const struct mt6797_a72_hotplug_snapshot_ops frequency_observer_ops = {
	.clock = frequency_observer_clock,
	.bigidvfs = frequency_observer_big,
};

static void frequency_observer_fill(
	struct frequency_observer_test_state *state,
	struct mt6797_a72_hotplug_snapshot_source *source,
	struct mt6797_a72_frequency_observer_controller *controller)
{
	memset(state, 0, sizeof(*state));
	state->clock = (struct mt6797_dvfsp_clock_readback) {
		.abi = MT6797_DVFSP_CLOCK_BACKEND_ABI,
		.sample_generation = 11,
		.armplldiv_muxsel = 0x55,
		.armplldiv_ckdiv = 0x42108,
		.pll_ll = { 0, 0xc1114000, 0 },
		.pll_l = { 0, 0x400c4000, 0 },
		.pll_cci = { 0, 0xc10c1d89, 0 },
	};
	state->big = (struct mt6797_bigidvfs_readback) {
		.abi = MT6797_BIGIDVFS_BACKEND_ABI,
		.sample_generation = 13,
		.pll_pcw = 0xc1130000,
		.pll_enable_posdiv = 0x07001000,
	};
	memset(source, 0, sizeof(*source));
	source->clock = (struct device *)&state->devices[0];
	source->bigidvfs = (struct device *)&state->devices[1];
	source->ops = &frequency_observer_ops;
	mt6797_a72_frequency_observer_init(controller);
	frequency_observer_state = state;
}

static void frequency_observer_live_values_test(struct kunit *test)
{
	struct mt6797_a72_frequency_observer_controller controller;
	struct mt6797_a72_frequency_observer_trace trace;
	struct mt6797_a72_frequency_observation observation;
	struct mt6797_a72_hotplug_snapshot_source source;
	struct frequency_observer_test_state *state;

	state = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
	KUNIT_ASSERT_NOT_NULL(test, state);
	frequency_observer_fill(state, &source, &controller);
	KUNIT_ASSERT_EQ(test, mt6797_a72_frequency_observer_sample(
		&controller, &source, &observation, &trace), 0);
	KUNIT_EXPECT_EQ(test, observation.abi, 1U);
	KUNIT_EXPECT_EQ(test, observation.attempt, 1U);
	KUNIT_EXPECT_EQ(test, observation.clock_sample_generation, 11ULL);
	KUNIT_EXPECT_EQ(test, observation.big_sample_generation, 13ULL);
	KUNIT_EXPECT_EQ(test, observation.big_pll_pcw, 0xc1130000U);
	KUNIT_EXPECT_EQ(test, observation.big_pll_enable_posdiv, 0x07001000U);
	KUNIT_EXPECT_EQ(test, observation.state.cluster[
		MT6797_DVFSP_CLOCK_STATE_CLUSTER_LL].frequency_khz, 897000U);
	KUNIT_EXPECT_EQ(test, observation.state.cluster[
		MT6797_DVFSP_CLOCK_STATE_CLUSTER_L].frequency_khz, 1274000U);
	KUNIT_EXPECT_EQ(test, observation.state.cluster[
		MT6797_DVFSP_CLOCK_STATE_CLUSTER_B].frequency_khz, 845000U);
	KUNIT_EXPECT_EQ(test, observation.state.cluster[
		MT6797_DVFSP_CLOCK_STATE_CLUSTER_CCI].frequency_khz, 629500U);
	KUNIT_EXPECT_EQ(test, trace.clock_calls, 1U);
	KUNIT_EXPECT_EQ(test, trace.bigidvfs_calls, 1U);
	KUNIT_EXPECT_EQ(test, trace.clock_poweron_writes_max, 1U);
	KUNIT_EXPECT_EQ(test, trace.clock_acquire_writes_max, 200U);
	KUNIT_EXPECT_EQ(test, trace.clock_release_writes_max, 200U);
	KUNIT_EXPECT_EQ(test, trace.bigidvfs_stable_samples, 2U);
	KUNIT_EXPECT_EQ(test, trace.bigidvfs_reads, 8U);
	KUNIT_EXPECT_EQ(test, trace.bigidvfs_sram_set_calls, 0U);
	KUNIT_EXPECT_EQ(test, trace.attempts_remaining, 2U);
	KUNIT_EXPECT_TRUE(test, trace.complete);
}

static void frequency_observer_budget_test(struct kunit *test)
{
	struct mt6797_a72_frequency_observer_controller controller;
	struct mt6797_a72_frequency_observer_trace trace;
	struct mt6797_a72_frequency_observation observation;
	struct mt6797_a72_hotplug_snapshot_source source;
	struct frequency_observer_test_state *state;
	u32 attempt;

	state = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
	KUNIT_ASSERT_NOT_NULL(test, state);
	frequency_observer_fill(state, &source, &controller);
	for (attempt = 1; attempt <= 3; attempt++) {
		KUNIT_ASSERT_EQ(test, mt6797_a72_frequency_observer_sample(
			&controller, &source, &observation, &trace), 0);
		KUNIT_EXPECT_EQ(test, observation.attempt, attempt);
		KUNIT_EXPECT_EQ(test, trace.attempts_remaining, 3U - attempt);
	}
	KUNIT_EXPECT_EQ(test, mt6797_a72_frequency_observer_sample(
		&controller, &source, &observation, &trace), -ENOSPC);
	KUNIT_EXPECT_EQ(test, state->clock_calls, 3U);
	KUNIT_EXPECT_EQ(test, state->big_calls, 3U);
	KUNIT_EXPECT_EQ(test, trace.clock_calls, 0U);
	KUNIT_EXPECT_EQ(test, trace.bigidvfs_calls, 0U);
	KUNIT_EXPECT_EQ(test, trace.attempt, 3U);
	KUNIT_EXPECT_FALSE(test, trace.complete);
}

static void frequency_observer_failure_consumes_attempt_test(
	struct kunit *test)
{
	struct mt6797_a72_frequency_observer_controller controller;
	struct mt6797_a72_frequency_observer_trace trace;
	struct mt6797_a72_frequency_observation observation;
	struct mt6797_a72_frequency_observation zero = { };
	struct mt6797_a72_hotplug_snapshot_source source;
	struct frequency_observer_test_state *state;

	state = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
	KUNIT_ASSERT_NOT_NULL(test, state);
	frequency_observer_fill(state, &source, &controller);
	state->clock_error = -EIO;
	KUNIT_EXPECT_EQ(test, mt6797_a72_frequency_observer_sample(
		&controller, &source, &observation, &trace), -EIO);
	KUNIT_EXPECT_MEMEQ(test, &observation, &zero, sizeof(zero));
	KUNIT_EXPECT_EQ(test, trace.attempt, 1U);
	state->clock_error = 0;
	KUNIT_EXPECT_EQ(test, mt6797_a72_frequency_observer_sample(
		&controller, &source, &observation, &trace), 0);
	KUNIT_EXPECT_EQ(test, mt6797_a72_frequency_observer_sample(
		&controller, &source, &observation, &trace), 0);
	KUNIT_EXPECT_EQ(test, mt6797_a72_frequency_observer_sample(
		&controller, &source, &observation, &trace), -ENOSPC);
	KUNIT_EXPECT_EQ(test, state->clock_calls, 3U);
	KUNIT_EXPECT_EQ(test, state->big_calls, 2U);
}

static void frequency_observer_shape_refusal_test(struct kunit *test)
{
	struct mt6797_a72_frequency_observer_controller controller;
	struct mt6797_a72_frequency_observer_trace trace;
	struct mt6797_a72_frequency_observation observation;
	struct mt6797_a72_frequency_observation zero = { };
	struct mt6797_a72_hotplug_snapshot_source source;
	struct frequency_observer_test_state *state;

	state = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
	KUNIT_ASSERT_NOT_NULL(test, state);
	frequency_observer_fill(state, &source, &controller);
	state->clock.sample_generation = 0;
	KUNIT_EXPECT_EQ(test, mt6797_a72_frequency_observer_sample(
		&controller, &source, &observation, &trace), -EPROTO);
	KUNIT_EXPECT_EQ(test, state->clock_calls, 1U);
	KUNIT_EXPECT_EQ(test, state->big_calls, 0U);
	KUNIT_EXPECT_MEMEQ(test, &observation, &zero, sizeof(zero));
}

static void frequency_observer_source_guards_test(struct kunit *test)
{
	struct mt6797_a72_frequency_observer_controller controller;
	struct mt6797_a72_frequency_observer_trace trace;
	struct mt6797_a72_frequency_observation observation;
	struct mt6797_a72_hotplug_snapshot_source source = { };

	mt6797_a72_frequency_observer_init(&controller);
	KUNIT_EXPECT_EQ(test, mt6797_a72_frequency_observer_sample(
		NULL, &source, &observation, &trace), -EINVAL);
	KUNIT_EXPECT_EQ(test, mt6797_a72_frequency_observer_sample(
		&controller, NULL, &observation, &trace), -EINVAL);
	KUNIT_EXPECT_EQ(test, mt6797_a72_frequency_observer_sample(
		&controller, &source, &observation, &trace), -EINVAL);
	KUNIT_EXPECT_EQ(test, controller.attempts, 0U);
}

static struct kunit_case frequency_observer_cases[] = {
	KUNIT_CASE(frequency_observer_live_values_test),
	KUNIT_CASE(frequency_observer_budget_test),
	KUNIT_CASE(frequency_observer_failure_consumes_attempt_test),
	KUNIT_CASE(frequency_observer_shape_refusal_test),
	KUNIT_CASE(frequency_observer_source_guards_test),
	{ }
};

static struct kunit_suite frequency_observer_suite = {
	.name = "mt6797-a72-frequency-observer",
	.test_cases = frequency_observer_cases,
};

kunit_test_suite(frequency_observer_suite);

MODULE_DESCRIPTION("MT6797 A72 bounded frequency observer KUnit tests");
MODULE_LICENSE("GPL");
'''


PRODUCTION_KCONFIG = r'''
config MTK_MT6797_A72_FREQUENCY_OBSERVER
	bool "MediaTek MT6797 bounded A72 frequency observer"
	depends on MTK_MT6797_A72_HOTPLUG_SNAPSHOT
	depends on MTK_MT6797_DVFSP_STATE_DECODERS
	default n
	help
	  Add one read-only attribute to the existing snapshot adapter. At most
	  three reads per boot take bounded protected-clock and stable BigiDVFS
	  samples, then publish raw register values and decoded cluster rates.

	  The observer does not request a CPU, change voltage or frequency, select
	  a policy, write retained memory, or add a Device Tree node. The protected
	  clock transport retains its documented bounded semaphore writes.
'''


TEST_KCONFIG = r'''
config MTK_MT6797_A72_FREQUENCY_OBSERVER_KUNIT_TEST
	bool "KUnit tests for the bounded MT6797 A72 frequency observer"
	depends on KUNIT=y
	depends on MTK_MT6797_A72_FREQUENCY_OBSERVER
	default n
	help
	  Exercise live-value composition, the three-attempt cap, failure budget,
	  malformed samples, and source guards with injected memory records only.
	  No device, MMIO, I2C, SMC, CPU, watchdog, or network action occurs.
	  The production sysfs interface and hardware transports are not invoked.
'''


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    if text.count(old) != 1:
        raise SystemExit(f"expected one anchor in {path}: {old!r}")
    path.write_text(text.replace(old, new, 1))


def production(root: Path) -> None:
    soc = root / "drivers/soc/mediatek"
    kconfig = soc / "Kconfig"
    makefile = soc / "Makefile"
    snapshot = soc / "mt6797-a72-hotplug-snapshot.c"
    internal = soc / "mt6797-a72-hotplug-snapshot-internal.h"

    replace_once(
        kconfig,
        "config MTK_MT6797_A72_RESTORE_EXECUTOR\n",
        PRODUCTION_KCONFIG + "\nconfig MTK_MT6797_A72_RESTORE_EXECUTOR\n",
    )
    replace_once(
        makefile,
        "obj-$(CONFIG_MTK_MT6797_A72_HOTPLUG_SNAPSHOT) += mt6797-a72-hotplug-snapshot.o\n",
        "obj-$(CONFIG_MTK_MT6797_A72_HOTPLUG_SNAPSHOT) += mt6797-a72-hotplug-snapshot.o\n"
        "obj-$(CONFIG_MTK_MT6797_A72_FREQUENCY_OBSERVER) += mt6797-a72-frequency-observer.o\n",
    )
    replace_once(
        internal,
        '#include "mt6797-a72-hotplug-executor-internal.h"\n',
        '#include "mt6797-a72-frequency-observer-internal.h"\n'
        '#include "mt6797-a72-hotplug-executor-internal.h"\n',
    )
    replace_once(
        internal,
        "\tconst struct mt6797_a72_hotplug_snapshot_ops *ops;\n};\n",
        "\tconst struct mt6797_a72_hotplug_snapshot_ops *ops;\n"
        "\tstruct mt6797_a72_frequency_observer_controller frequency_observer;\n"
        "};\n",
    )
    replace_once(
        snapshot,
        "\tsource->ops = &mt6797_hotplug_ops;\n}\n",
        "\tsource->ops = &mt6797_hotplug_ops;\n"
        "\tmt6797_a72_frequency_observer_init(&source->frequency_observer);\n"
        "}\n",
    )
    replace_once(
        snapshot,
        "\tsource->ops = &mt6797_hotplug_ops;\n\tplatform_set_drvdata(pdev, source);\n\n"
        "\tdev_info(dev, \"snapshot adapter ready; production caller absent\\n\");\n",
        "\tsource->ops = &mt6797_hotplug_ops;\n"
        "\tmt6797_a72_frequency_observer_init(&source->frequency_observer);\n"
        "\tplatform_set_drvdata(pdev, source);\n"
        "\tret = mt6797_a72_frequency_observer_register(dev);\n"
        "\tif (ret)\n\t\treturn ret;\n\n"
        "\tdev_info(dev, \"snapshot adapter ready; production caller absent\\n\");\n",
    )
    (soc / "mt6797-a72-frequency-observer-internal.h").write_text(
        OBSERVER_HEADER
    )
    (soc / "mt6797-a72-frequency-observer.c").write_text(OBSERVER_SOURCE)


def tests(root: Path) -> None:
    soc = root / "drivers/soc/mediatek"
    replace_once(
        soc / "Kconfig",
        "config MTK_MT6797_A72_RESTORE_EXECUTOR\n",
        TEST_KCONFIG + "\nconfig MTK_MT6797_A72_RESTORE_EXECUTOR\n",
    )
    replace_once(
        soc / "Makefile",
        "obj-$(CONFIG_MTK_MT6797_A72_FREQUENCY_OBSERVER) += mt6797-a72-frequency-observer.o\n",
        "obj-$(CONFIG_MTK_MT6797_A72_FREQUENCY_OBSERVER) += mt6797-a72-frequency-observer.o\n"
        "obj-$(CONFIG_MTK_MT6797_A72_FREQUENCY_OBSERVER_KUNIT_TEST) += mt6797-a72-frequency-observer-test.o\n",
    )
    (soc / "mt6797-a72-frequency-observer-test.c").write_text(OBSERVER_TEST)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--phase", required=True, choices=("production", "tests"))
    args = parser.parse_args()
    root = args.source_root.resolve()
    if args.phase == "production":
        production(root)
    else:
        tests(root)


if __name__ == "__main__":
    main()
