#!/usr/bin/env python3
"""Apply deterministic protected-readback transport and KUnit changes."""

from __future__ import annotations

import argparse
from pathlib import Path
from textwrap import dedent


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        first = old.splitlines()[0] if old.splitlines() else "<empty>"
        raise SystemExit(
            f"{path}: expected one anchor beginning {first!r}, found {count}"
        )
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


CLOCK_INTERNAL_HEADER = dedent(r"""
/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef __MT6797_PROTECTED_READBACK_INTERNAL_H
#define __MT6797_PROTECTED_READBACK_INTERNAL_H

#include <linux/types.h>

#include <linux/soc/mediatek/mt6797-dvfsp-clock-backend.h>

enum mt6797_dvfsp_clock_window {
	MT6797_DVFSP_CLOCK_WINDOW_MCUMIXED,
	MT6797_DVFSP_CLOCK_WINDOW_CSPM,
};

struct mt6797_dvfsp_clock_transport_ops {
	void (*write)(void *context, u32 window, u32 offset, u32 value);
	u32 (*read)(void *context, u32 window, u32 offset);
	void (*delay_us)(void *context, unsigned int usec);
	void (*settle_ns)(void *context, unsigned int nsec);
};

int mt6797_clock_snapshot(const struct mt6797_dvfsp_clock_transport_ops *ops,
			  void *context,
			  struct mt6797_dvfsp_clock_readback *readback);

#endif /* __MT6797_PROTECTED_READBACK_INTERNAL_H */
""").lstrip("\n")


CLOCK_SOURCE = dedent(r"""
// SPDX-License-Identifier: GPL-2.0-only
/*
 * Disabled-only MT6797 MCUMIXED/DVFSP clock-window readback transport.
 *
 * The CPU PLL and divider window is shared by Linux, SPM, and ATF. Keep the
 * semaphore protocol here separate from the eventual calibrated state owner:
 * this file can read raw words, but cannot make OPP or voltage decisions.
 */

#include <linux/bitops.h>
#include <linux/clk.h>
#include <linux/delay.h>
#include <linux/device.h>
#include <linux/io.h>
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/mutex.h>
#include <linux/of.h>
#include <linux/platform_device.h>
#include <linux/spinlock.h>
#include <linux/string.h>

#include <linux/soc/mediatek/mt6797-dvfsp-clock-backend.h>

#include "mt6797-protected-readback-internal.h"

#define MT6797_DVFSP_CSPM_POWERON_EN		0x000
#define MT6797_DVFSP_SEMAPHORE			0x440
#define MT6797_DVFSP_SEMAPHORE_REQUEST		1
#define MT6797_DVFSP_SEMAPHORE_HELD		BIT(0)
#define MT6797_DVFSP_SEMAPHORE_POLL_US		10
#define MT6797_DVFSP_SEMAPHORE_RETRIES		200
#define MT6797_DVFSP_SEMAPHORE_SETTLE_NS	200
#define MT6797_DVFSP_CSPM_POWERON_VALUE		0x0b160001

#define MT6797_ARMPLL_LL			0x200
#define MT6797_ARMPLL_L			0x210
#define MT6797_ARMPLL_CCI			0x220
#define MT6797_ARMPLL_WORDS			3
#define MT6797_ARMPLLDIV_MUXSEL			0x270
#define MT6797_ARMPLLDIV_CKDIV			0x274

/* Vendor mt_cpufreq_hybrid.c maps these CSPM words to live DVFS state. */
static const u32 mt6797_dvfsp_cspm_swctrl_offset[3] = {
	0x608, 0x60c, 0x610,
};
static const u32 mt6797_dvfsp_cspm_hwsta_offset[4] = {
	0x614, 0x618, 0x61c, 0x620,
};

struct mt6797_dvfsp_clock_backend {
	void __iomem *mcumixed;
	void __iomem *cspm;
	struct clk *i2c_clk;
	struct mutex operation_lock;
	spinlock_t semaphore_lock;
	bool faulted;
	u64 sample_generation;
};

static void mt6797_clock_write(void *context, u32 window, u32 offset,
			       u32 value)
{
	struct mt6797_dvfsp_clock_backend *backend = context;
	void __iomem *base = backend->cspm;

	if (window == MT6797_DVFSP_CLOCK_WINDOW_MCUMIXED)
		base = backend->mcumixed;
	writel(value, base + offset);
}

static u32 mt6797_clock_read(void *context, u32 window, u32 offset)
{
	struct mt6797_dvfsp_clock_backend *backend = context;
	void __iomem *base = backend->cspm;

	if (window == MT6797_DVFSP_CLOCK_WINDOW_MCUMIXED)
		base = backend->mcumixed;
	return readl(base + offset);
}

static void mt6797_clock_delay_us(void *context, unsigned int usec)
{
	udelay(usec);
}

static void mt6797_clock_settle_ns(void *context, unsigned int nsec)
{
	ndelay(nsec);
}

static const struct mt6797_dvfsp_clock_transport_ops
mt6797_clock_ops = {
	.write = mt6797_clock_write,
	.read = mt6797_clock_read,
	.delay_us = mt6797_clock_delay_us,
	.settle_ns = mt6797_clock_settle_ns,
};

static int
mt6797_clock_acquire(const struct mt6797_dvfsp_clock_transport_ops *ops,
		     void *context)
{
	const u32 cspm = MT6797_DVFSP_CLOCK_WINDOW_CSPM;
	unsigned int i;

	for (i = 0; i < MT6797_DVFSP_SEMAPHORE_RETRIES; i++) {
		ops->write(context, cspm,
			   MT6797_DVFSP_SEMAPHORE,
			   MT6797_DVFSP_SEMAPHORE_REQUEST);
		if (ops->read(context, cspm,
			      MT6797_DVFSP_SEMAPHORE) &
		    MT6797_DVFSP_SEMAPHORE_HELD)
			return 0;
		ops->delay_us(context, MT6797_DVFSP_SEMAPHORE_POLL_US);
	}

	return -ETIMEDOUT;
}

static int
mt6797_clock_release(const struct mt6797_dvfsp_clock_transport_ops *ops,
		     void *context)
{
	const u32 cspm = MT6797_DVFSP_CLOCK_WINDOW_CSPM;
	unsigned int i;
	u32 semaphore;

	for (i = 0; i < MT6797_DVFSP_SEMAPHORE_RETRIES; i++) {
		ops->write(context, cspm,
			   MT6797_DVFSP_SEMAPHORE,
			   MT6797_DVFSP_SEMAPHORE_REQUEST);
		semaphore = ops->read(context, cspm,
				      MT6797_DVFSP_SEMAPHORE);
		if (!(semaphore & MT6797_DVFSP_SEMAPHORE_HELD))
			return 0;
		ops->delay_us(context, MT6797_DVFSP_SEMAPHORE_POLL_US);
	}

	return -ETIMEDOUT;
}

int mt6797_clock_snapshot(const struct mt6797_dvfsp_clock_transport_ops *ops,
			  void *context,
			  struct mt6797_dvfsp_clock_readback *readback)
{
	struct mt6797_dvfsp_clock_readback observed = { };
	const u32 cspm = MT6797_DVFSP_CLOCK_WINDOW_CSPM;
	const u32 mcumixed = MT6797_DVFSP_CLOCK_WINDOW_MCUMIXED;
	unsigned int i;
	int ret;

	if (!readback)
		return -EINVAL;
	memset(readback, 0, sizeof(*readback));
	if (!ops || !ops->write || !ops->read || !ops->delay_us ||
	    !ops->settle_ns)
		return -EINVAL;

	ops->write(context, cspm,
		   MT6797_DVFSP_CSPM_POWERON_EN,
		   MT6797_DVFSP_CSPM_POWERON_VALUE);
	ops->read(context, cspm,
		  MT6797_DVFSP_CSPM_POWERON_EN);

	ret = mt6797_clock_acquire(ops, context);
	if (ret)
		return ret;

	/* The recovered owner requires this boundary before MCUMIXED access. */
	ops->settle_ns(context, MT6797_DVFSP_SEMAPHORE_SETTLE_NS);
	observed.armplldiv_muxsel = ops->read(context, mcumixed,
					      MT6797_ARMPLLDIV_MUXSEL);
	observed.armplldiv_ckdiv = ops->read(context, mcumixed,
					     MT6797_ARMPLLDIV_CKDIV);
	for (i = 0; i < MT6797_ARMPLL_WORDS; i++) {
		observed.pll_ll[i] = ops->read(context, mcumixed,
			MT6797_ARMPLL_LL + i * sizeof(u32));
		observed.pll_l[i] = ops->read(context, mcumixed,
			MT6797_ARMPLL_L + i * sizeof(u32));
		observed.pll_cci[i] = ops->read(context, mcumixed,
			MT6797_ARMPLL_CCI + i * sizeof(u32));
	}

	for (i = 0; i < ARRAY_SIZE(mt6797_dvfsp_cspm_swctrl_offset); i++)
		observed.cspm_swctrl[i] = ops->read(context, cspm,
			mt6797_dvfsp_cspm_swctrl_offset[i]);
	for (i = 0; i < ARRAY_SIZE(mt6797_dvfsp_cspm_hwsta_offset); i++)
		observed.cspm_hwsta[i] = ops->read(context, cspm,
			mt6797_dvfsp_cspm_hwsta_offset[i]);

	ret = mt6797_clock_release(ops, context);
	if (ret)
		return ret;

	*readback = observed;
	return 0;
}

static void
mt6797_dvfsp_clock_mark_fault(struct mt6797_dvfsp_clock_backend *backend)
{
	backend->faulted = true;
}

int mt6797_dvfsp_clock_backend_read(struct device *dev,
				    struct mt6797_dvfsp_clock_readback *readback)
{
	struct mt6797_dvfsp_clock_readback observed = { };
	struct mt6797_dvfsp_clock_backend *backend;
	unsigned long flags;
	int ret;

	if (!readback)
		return -EINVAL;
	memset(readback, 0, sizeof(*readback));
	if (!dev)
		return -EINVAL;

	backend = dev_get_drvdata(dev);
	if (!backend)
		return -ENODEV;

	mutex_lock(&backend->operation_lock);
	if (backend->faulted) {
		ret = -EIO;
		goto out_unlock;
	}

	ret = clk_prepare_enable(backend->i2c_clk);
	if (ret)
		goto out_unlock;

	local_irq_save(flags);
	spin_lock(&backend->semaphore_lock);
	ret = mt6797_clock_snapshot(&mt6797_clock_ops, backend, &observed);
	if (ret) {
		mt6797_dvfsp_clock_mark_fault(backend);
		goto out_spin;
	}

	if (++backend->sample_generation == 0)
		backend->sample_generation = 1;
	observed.abi = MT6797_DVFSP_CLOCK_BACKEND_ABI;
	observed.sample_generation = backend->sample_generation;
	*readback = observed;

out_spin:
	spin_unlock(&backend->semaphore_lock);
	local_irq_restore(flags);
	clk_disable_unprepare(backend->i2c_clk);

out_unlock:
	mutex_unlock(&backend->operation_lock);
	return ret;
}
EXPORT_SYMBOL_GPL(mt6797_dvfsp_clock_backend_read);

static int mt6797_dvfsp_clock_backend_probe(struct platform_device *pdev)
{
	struct mt6797_dvfsp_clock_backend *backend;
	int ret;

	backend = devm_kzalloc(&pdev->dev, sizeof(*backend), GFP_KERNEL);
	if (!backend)
		return -ENOMEM;

	backend->mcumixed = devm_platform_ioremap_resource_byname(pdev, "mcumixed");
	if (IS_ERR(backend->mcumixed))
		return PTR_ERR(backend->mcumixed);

	backend->cspm = devm_platform_ioremap_resource_byname(pdev, "cspm");
	if (IS_ERR(backend->cspm))
		return PTR_ERR(backend->cspm);

	backend->i2c_clk = devm_clk_get(&pdev->dev, "i2c");
	if (IS_ERR(backend->i2c_clk))
		return PTR_ERR(backend->i2c_clk);

	mutex_init(&backend->operation_lock);
	spin_lock_init(&backend->semaphore_lock);
	platform_set_drvdata(pdev, backend);
	dev_info(&pdev->dev,
		 "protected clock readback transport ready; owner unregistered\n");

	ret = 0;
	return ret;
}

static const struct of_device_id mt6797_dvfsp_clock_backend_of_match[] = {
	{ .compatible = "mediatek,mt6797-dvfsp-clock-backend" },
	{ }
};
MODULE_DEVICE_TABLE(of, mt6797_dvfsp_clock_backend_of_match);

static struct platform_driver mt6797_dvfsp_clock_backend_driver = {
	.probe = mt6797_dvfsp_clock_backend_probe,
	.driver = {
		.name = "mt6797-dvfsp-clock-backend",
		.of_match_table = mt6797_dvfsp_clock_backend_of_match,
	},
};
module_platform_driver(mt6797_dvfsp_clock_backend_driver);

MODULE_DESCRIPTION("MT6797 protected CPU clock readback transport");
MODULE_LICENSE("GPL");
""").lstrip("\n")


BIGIDVFS_HEADER_EXTENSION = dedent(r"""

#include <linux/soc/mediatek/mt6797-bigidvfs-backend.h>

struct mt6797_bigidvfs_transport_ops {
	int (*read)(void *context, u32 address, u32 *value);
};

int
mt6797_bigidvfs_snapshot(const struct mt6797_bigidvfs_transport_ops *ops,
			 void *context,
			 struct mt6797_bigidvfs_readback *readback);
""").lstrip("\n")


BIGIDVFS_SOURCE = dedent(r"""
// SPDX-License-Identifier: GPL-2.0-only
/*
 * Disabled-only MT6797 BigiDVFS secure-register readback transport.
 *
 * The retained firmware audit proves only REG_READ (0xc200035f) for this
 * boundary. Keep the exact whitelist and raw sample separate from the future
 * calibrated state owner; advertised getter FIDs are not assumed present.
 */

#include <linux/arm-smccc.h>
#include <linux/device.h>
#include <linux/errno.h>
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/mutex.h>
#include <linux/of.h>
#include <linux/platform_device.h>
#include <linux/slab.h>
#include <linux/string.h>

#include <linux/soc/mediatek/mt6797-bigidvfs-backend.h>

#include "mt6797-protected-readback-internal.h"

struct mt6797_bigidvfs_backend {
	struct mutex operation_lock;
	bool faulted;
	u64 sample_generation;
};

struct mt6797_bigidvfs_raw_sample {
	u32 word[4];
};

static const u32 mt6797_bigidvfs_addresses[] = {
	MT6797_BIGIDVFS_PLL_PCW,
	MT6797_BIGIDVFS_PLL_ENABLE_POSDIV,
	MT6797_BIGIDVFS_SRAM_SELECTOR,
	MT6797_BIGIDVFS_CONTROL,
};

static bool mt6797_bigidvfs_address_allowed(u32 address)
{
	switch (address) {
	case MT6797_BIGIDVFS_PLL_PCW:
	case MT6797_BIGIDVFS_PLL_ENABLE_POSDIV:
	case MT6797_BIGIDVFS_SRAM_SELECTOR:
	case MT6797_BIGIDVFS_CONTROL:
		return true;
	default:
		return false;
	}
}

static int mt6797_bigidvfs_secure_read(void *context, u32 address, u32 *value)
{
	struct arm_smccc_res result;

	if (!value || !mt6797_bigidvfs_address_allowed(address))
		return -EINVAL;

	arm_smccc_smc(MT6797_BIGIDVFS_FID_READ, address, 0, 0, 0, 0, 0, 0,
		      &result);
	/* REG_READ returns a zero-extended raw word; reject all error forms. */
	if (result.a0 >> 32)
		return -EIO;

	*value = (u32)result.a0;
	return 0;
}

static const struct mt6797_bigidvfs_transport_ops bigidvfs_ops = {
	.read = mt6797_bigidvfs_secure_read,
};

static int
mt6797_bigidvfs_read_sample(const struct mt6797_bigidvfs_transport_ops *ops,
			    void *context,
			    struct mt6797_bigidvfs_raw_sample *sample)
{
	unsigned int i;
	int ret;

	for (i = 0; i < ARRAY_SIZE(mt6797_bigidvfs_addresses); i++) {
		ret = ops->read(context, mt6797_bigidvfs_addresses[i],
				&sample->word[i]);
		if (ret)
			return ret;
	}

	return 0;
}

int
mt6797_bigidvfs_snapshot(const struct mt6797_bigidvfs_transport_ops *ops,
			 void *context,
			 struct mt6797_bigidvfs_readback *readback)
{
	struct mt6797_bigidvfs_raw_sample first = { };
	struct mt6797_bigidvfs_raw_sample second = { };
	struct mt6797_bigidvfs_readback observed = { };
	int ret;

	if (!readback)
		return -EINVAL;
	memset(readback, 0, sizeof(*readback));
	if (!ops || !ops->read)
		return -EINVAL;

	ret = mt6797_bigidvfs_read_sample(ops, context, &first);
	if (ret)
		return ret;
	ret = mt6797_bigidvfs_read_sample(ops, context, &second);
	if (ret)
		return ret;
	if (memcmp(&first, &second, sizeof(first)))
		return -EAGAIN;

	observed.pll_pcw = second.word[0];
	observed.pll_enable_posdiv = second.word[1];
	observed.sram_selector = second.word[2];
	observed.control = second.word[3];
	*readback = observed;
	return 0;
}

static void
mt6797_bigidvfs_mark_fault(struct mt6797_bigidvfs_backend *backend)
{
	backend->faulted = true;
}

int mt6797_bigidvfs_backend_read(struct device *dev,
				 struct mt6797_bigidvfs_readback *readback)
{
	struct mt6797_bigidvfs_readback observed = { };
	struct mt6797_bigidvfs_backend *backend;
	int ret;

	if (!readback)
		return -EINVAL;
	memset(readback, 0, sizeof(*readback));
	if (!dev)
		return -EINVAL;

	backend = dev_get_drvdata(dev);
	if (!backend)
		return -ENODEV;

	mutex_lock(&backend->operation_lock);
	if (backend->faulted) {
		ret = -EIO;
		goto out_unlock;
	}

	ret = mt6797_bigidvfs_snapshot(&bigidvfs_ops, backend, &observed);
	if (ret) {
		if (ret != -EAGAIN)
			mt6797_bigidvfs_mark_fault(backend);
		goto out_unlock;
	}

	if (++backend->sample_generation == 0)
		backend->sample_generation = 1;
	observed.abi = MT6797_BIGIDVFS_BACKEND_ABI;
	observed.sample_generation = backend->sample_generation;
	*readback = observed;

out_unlock:
	mutex_unlock(&backend->operation_lock);
	return ret;
}
EXPORT_SYMBOL_GPL(mt6797_bigidvfs_backend_read);

static int mt6797_bigidvfs_backend_probe(struct platform_device *pdev)
{
	struct mt6797_bigidvfs_backend *backend;
	const char *method;

	if (!pdev->dev.of_node ||
	    of_property_read_string(pdev->dev.of_node, "method", &method) ||
	    strcmp(method, "smc"))
		return -EINVAL;

	backend = devm_kzalloc(&pdev->dev, sizeof(*backend), GFP_KERNEL);
	if (!backend)
		return -ENOMEM;

	mutex_init(&backend->operation_lock);
	platform_set_drvdata(pdev, backend);
	dev_info(&pdev->dev,
		 "secure readback transport ready; owner unregistered\n");

	return 0;
}

static const struct of_device_id mt6797_bigidvfs_backend_of_match[] = {
	{ .compatible = "mediatek,mt6797-bigidvfs-backend" },
	{ }
};
MODULE_DEVICE_TABLE(of, mt6797_bigidvfs_backend_of_match);

static struct platform_driver mt6797_bigidvfs_backend_driver = {
	.probe = mt6797_bigidvfs_backend_probe,
	.driver = {
		.name = "mt6797-bigidvfs-backend",
		.of_match_table = mt6797_bigidvfs_backend_of_match,
	},
};
module_platform_driver(mt6797_bigidvfs_backend_driver);

MODULE_DESCRIPTION("Disabled MT6797 BigiDVFS secure readback transport");
MODULE_LICENSE("GPL");
""").lstrip("\n")


TEST_SOURCE = dedent(r"""
// SPDX-License-Identifier: GPL-2.0-only
#include <kunit/test.h>
#include <linux/errno.h>
#include <linux/kernel.h>
#include <linux/string.h>

#include "mt6797-protected-readback-internal.h"

#define MT6797_CLOCK_TEST_EVENTS		700
#define MT6797_CLOCK_TEST_SEMAPHORE	0x440
#define MT6797_CLOCK_TEST_MUXSEL		0x270
#define MT6797_CLOCK_TEST_SETTLE_NS	200
#define MT6797_CLOCK_TEST_DATA_READS	18

enum mt6797_clock_test_event_kind {
	MT6797_CLOCK_TEST_WRITE,
	MT6797_CLOCK_TEST_READ,
	MT6797_CLOCK_TEST_DELAY_US,
	MT6797_CLOCK_TEST_SETTLE_NS,
};

struct mt6797_clock_test_event {
	enum mt6797_clock_test_event_kind kind;
	u32 window;
	u32 offset;
	u32 value;
};

struct mt6797_clock_test_state {
	struct mt6797_clock_test_event events[MT6797_CLOCK_TEST_EVENTS];
	unsigned int event_count;
	unsigned int semaphore_reads;
	bool acquire_timeout;
	bool release_timeout;
};

struct mt6797_bigidvfs_test_state {
	u32 addresses[8];
	unsigned int calls;
	unsigned int fault_call;
	bool unstable;
};

static void mt6797_clock_test_record(struct mt6797_clock_test_state *state,
				     enum mt6797_clock_test_event_kind kind,
				     u32 window, u32 offset, u32 value)
{
	struct mt6797_clock_test_event *event;

	if (state->event_count >= ARRAY_SIZE(state->events))
		return;
	event = &state->events[state->event_count++];
	event->kind = kind;
	event->window = window;
	event->offset = offset;
	event->value = value;
}

static void mt6797_clock_test_write(void *context, u32 window, u32 offset,
				    u32 value)
{
	mt6797_clock_test_record(context, MT6797_CLOCK_TEST_WRITE, window,
				 offset, value);
}

static u32 mt6797_clock_test_read(void *context, u32 window, u32 offset)
{
	struct mt6797_clock_test_state *state = context;
	u32 value = ((u32)window << 28) | offset;

	if (window == MT6797_DVFSP_CLOCK_WINDOW_CSPM &&
	    offset == MT6797_CLOCK_TEST_SEMAPHORE) {
		state->semaphore_reads++;
		if (state->acquire_timeout ||
		    (state->release_timeout && state->semaphore_reads > 1))
			value = state->release_timeout ? 1 : 0;
		else
			value = state->semaphore_reads == 1 ? 1 : 0;
	}
	mt6797_clock_test_record(state, MT6797_CLOCK_TEST_READ, window,
				 offset, value);
	return value;
}

static void mt6797_clock_test_delay(void *context, unsigned int usec)
{
	mt6797_clock_test_record(context, MT6797_CLOCK_TEST_DELAY_US,
				 MT6797_DVFSP_CLOCK_WINDOW_CSPM, 0, usec);
}

static void mt6797_clock_test_settle(void *context, unsigned int nsec)
{
	mt6797_clock_test_record(context, MT6797_CLOCK_TEST_SETTLE_NS,
				 MT6797_DVFSP_CLOCK_WINDOW_MCUMIXED, 0,
				 nsec);
}

static const struct mt6797_dvfsp_clock_transport_ops mt6797_clock_test_ops = {
	.write = mt6797_clock_test_write,
	.read = mt6797_clock_test_read,
	.delay_us = mt6797_clock_test_delay,
	.settle_ns = mt6797_clock_test_settle,
};

static int mt6797_bigidvfs_test_read(void *context, u32 address, u32 *value)
{
	struct mt6797_bigidvfs_test_state *state = context;

	state->addresses[state->calls] = address;
	state->calls++;
	if (state->calls == state->fault_call)
		return -EIO;
	*value = address ^ 0x55aa55aa;
	if (state->unstable && state->calls == 5)
		*value ^= 1;
	return 0;
}

static const struct mt6797_bigidvfs_transport_ops big_test_ops = {
	.read = mt6797_bigidvfs_test_read,
};

static void
mt6797_expect_clock_zero(struct kunit *test,
			 const struct mt6797_dvfsp_clock_readback *readback)
{
	struct mt6797_dvfsp_clock_readback zero = { };

	KUNIT_EXPECT_EQ(test, memcmp(readback, &zero, sizeof(*readback)), 0);
}

static void
mt6797_expect_bigidvfs_zero(struct kunit *test,
			    const struct mt6797_bigidvfs_readback *readback)
{
	struct mt6797_bigidvfs_readback zero = { };

	KUNIT_EXPECT_EQ(test, memcmp(readback, &zero, sizeof(*readback)), 0);
}

static void mt6797_clock_snapshot_order_test(struct kunit *test)
{
	struct mt6797_dvfsp_clock_readback readback;
	struct mt6797_clock_test_state *state;
	unsigned int release_index;
	int ret;

	state = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
	KUNIT_ASSERT_NOT_NULL(test, state);
	memset(&readback, 0xa5, sizeof(readback));
	ret = mt6797_clock_snapshot(&mt6797_clock_test_ops, state, &readback);
	KUNIT_ASSERT_EQ(test, ret, 0);
	KUNIT_ASSERT_EQ(test, state->event_count, 25U);
	KUNIT_EXPECT_EQ(test, state->events[2].kind,
			MT6797_CLOCK_TEST_WRITE);
	KUNIT_EXPECT_EQ(test, state->events[2].offset,
			MT6797_CLOCK_TEST_SEMAPHORE);
	KUNIT_EXPECT_EQ(test, state->events[3].kind,
			MT6797_CLOCK_TEST_READ);
	KUNIT_EXPECT_EQ(test, state->events[4].kind,
			MT6797_CLOCK_TEST_SETTLE_NS);
	KUNIT_EXPECT_EQ(test, state->events[4].value,
			MT6797_CLOCK_TEST_SETTLE_NS);
	KUNIT_EXPECT_EQ(test, state->events[5].kind,
			MT6797_CLOCK_TEST_READ);
	KUNIT_EXPECT_EQ(test, state->events[5].window,
			MT6797_DVFSP_CLOCK_WINDOW_MCUMIXED);
	KUNIT_EXPECT_EQ(test, state->events[5].offset,
			MT6797_CLOCK_TEST_MUXSEL);
	release_index = 5 + MT6797_CLOCK_TEST_DATA_READS;
	KUNIT_EXPECT_EQ(test, state->events[release_index].kind,
			MT6797_CLOCK_TEST_WRITE);
	KUNIT_EXPECT_EQ(test, state->events[release_index].offset,
			MT6797_CLOCK_TEST_SEMAPHORE);
	KUNIT_EXPECT_EQ(test, readback.armplldiv_muxsel,
			MT6797_CLOCK_TEST_MUXSEL);
	KUNIT_EXPECT_EQ(test, readback.abi, 0U);
	KUNIT_EXPECT_EQ(test, readback.sample_generation, 0ULL);
}

static void mt6797_clock_acquire_timeout_test(struct kunit *test)
{
	struct mt6797_dvfsp_clock_readback readback;
	struct mt6797_clock_test_state *state;
	int ret;

	state = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
	KUNIT_ASSERT_NOT_NULL(test, state);
	state->acquire_timeout = true;
	memset(&readback, 0xa5, sizeof(readback));
	ret = mt6797_clock_snapshot(&mt6797_clock_test_ops, state, &readback);
	KUNIT_EXPECT_EQ(test, ret, -ETIMEDOUT);
	KUNIT_EXPECT_EQ(test, state->semaphore_reads, 200U);
	KUNIT_EXPECT_EQ(test, state->event_count, 602U);
	mt6797_expect_clock_zero(test, &readback);
}

static void mt6797_clock_release_timeout_test(struct kunit *test)
{
	struct mt6797_dvfsp_clock_readback readback;
	struct mt6797_clock_test_state *state;
	int ret;

	state = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
	KUNIT_ASSERT_NOT_NULL(test, state);
	state->release_timeout = true;
	memset(&readback, 0xa5, sizeof(readback));
	ret = mt6797_clock_snapshot(&mt6797_clock_test_ops, state, &readback);
	KUNIT_EXPECT_EQ(test, ret, -ETIMEDOUT);
	KUNIT_EXPECT_EQ(test, state->semaphore_reads, 201U);
	KUNIT_EXPECT_EQ(test, state->event_count, 623U);
	mt6797_expect_clock_zero(test, &readback);
}

static void mt6797_bigidvfs_snapshot_order_test(struct kunit *test)
{
	static const u32 expected[] = {
		MT6797_BIGIDVFS_PLL_PCW,
		MT6797_BIGIDVFS_PLL_ENABLE_POSDIV,
		MT6797_BIGIDVFS_SRAM_SELECTOR,
		MT6797_BIGIDVFS_CONTROL,
		MT6797_BIGIDVFS_PLL_PCW,
		MT6797_BIGIDVFS_PLL_ENABLE_POSDIV,
		MT6797_BIGIDVFS_SRAM_SELECTOR,
		MT6797_BIGIDVFS_CONTROL,
	};
	struct mt6797_bigidvfs_readback readback;
	struct mt6797_bigidvfs_test_state state = { };
	int ret;

	memset(&readback, 0xa5, sizeof(readback));
	ret = mt6797_bigidvfs_snapshot(&big_test_ops, &state, &readback);
	KUNIT_ASSERT_EQ(test, ret, 0);
	KUNIT_EXPECT_EQ(test, state.calls, 8U);
	KUNIT_EXPECT_EQ(test, memcmp(state.addresses, expected,
				     sizeof(expected)), 0);
	KUNIT_EXPECT_EQ(test, readback.pll_pcw,
			MT6797_BIGIDVFS_PLL_PCW ^ 0x55aa55aa);
	KUNIT_EXPECT_EQ(test, readback.abi, 0U);
	KUNIT_EXPECT_EQ(test, readback.sample_generation, 0ULL);
}

static void mt6797_bigidvfs_faults_test(struct kunit *test)
{
	struct mt6797_bigidvfs_readback readback;
	struct mt6797_bigidvfs_test_state state;
	unsigned int fault;
	int ret;

	for (fault = 1; fault <= 8; fault++) {
		memset(&state, 0, sizeof(state));
		state.fault_call = fault;
		memset(&readback, 0xa5, sizeof(readback));
		ret = mt6797_bigidvfs_snapshot(&big_test_ops, &state, &readback);
		KUNIT_EXPECT_EQ(test, ret, -EIO);
		KUNIT_EXPECT_EQ(test, state.calls, fault);
		mt6797_expect_bigidvfs_zero(test, &readback);
	}
}

static void mt6797_bigidvfs_unstable_test(struct kunit *test)
{
	struct mt6797_bigidvfs_readback readback;
	struct mt6797_bigidvfs_test_state state = {
		.unstable = true,
	};
	int ret;

	memset(&readback, 0xa5, sizeof(readback));
	ret = mt6797_bigidvfs_snapshot(&big_test_ops, &state, &readback);
	KUNIT_EXPECT_EQ(test, ret, -EAGAIN);
	KUNIT_EXPECT_EQ(test, state.calls, 8U);
	mt6797_expect_bigidvfs_zero(test, &readback);
}

static struct kunit_case mt6797_protected_readback_cases[] = {
	KUNIT_CASE(mt6797_clock_snapshot_order_test),
	KUNIT_CASE(mt6797_clock_acquire_timeout_test),
	KUNIT_CASE(mt6797_clock_release_timeout_test),
	KUNIT_CASE(mt6797_bigidvfs_snapshot_order_test),
	KUNIT_CASE(mt6797_bigidvfs_faults_test),
	KUNIT_CASE(mt6797_bigidvfs_unstable_test),
	{ }
};

static struct kunit_suite mt6797_protected_readback_suite = {
	.name = "mt6797-protected-readback",
	.test_cases = mt6797_protected_readback_cases,
};

kunit_test_suite(mt6797_protected_readback_suite);

MODULE_LICENSE("GPL");
""").lstrip("\n")


def apply_clock(root: Path) -> None:
    (root / "drivers/soc/mediatek/mt6797-protected-readback-internal.h").write_text(
        CLOCK_INTERNAL_HEADER, encoding="utf-8"
    )
    (root / "drivers/soc/mediatek/mt6797-dvfsp-clock-backend.c").write_text(
        CLOCK_SOURCE, encoding="utf-8"
    )


def apply_bigidvfs(root: Path) -> None:
    header = root / "drivers/soc/mediatek/mt6797-protected-readback-internal.h"
    replace_once(
        header,
        "\n#endif /* __MT6797_PROTECTED_READBACK_INTERNAL_H */\n",
        BIGIDVFS_HEADER_EXTENSION
        + "\n#endif /* __MT6797_PROTECTED_READBACK_INTERNAL_H */\n",
    )
    (root / "drivers/soc/mediatek/mt6797-bigidvfs-backend.c").write_text(
        BIGIDVFS_SOURCE, encoding="utf-8"
    )


def apply_tests(root: Path) -> None:
    kconfig = root / "drivers/soc/mediatek/Kconfig"
    makefile = root / "drivers/soc/mediatek/Makefile"
    replace_once(
        kconfig,
        dedent("""\
        config MTK_RAM_CONSOLE_PARSER
        """),
        dedent("""\
        config MTK_MT6797_PROTECTED_READBACK_KUNIT_TEST
        \tbool "KUnit tests for MT6797 protected readback transports"
        \tdepends on KUNIT=y
        \tdepends on MTK_MT6797_DVFSP_CLOCK_BACKEND
        \tdepends on MTK_MT6797_DVFSP_BIGIDVFS_BACKEND
        \thelp
        \t  Exercise the protocol-exact clock ordering and two-sample secure
        \t  readback rules with in-memory transports. It covers acquisition
        \t  and release timeouts, every secure-read fault, and instability.
        \t  No MMIO, secure call, state-owner registration, or CPU operation
        \t  is performed.

        config MTK_RAM_CONSOLE_PARSER
        """),
    )
    replace_once(
        makefile,
        "obj-$(CONFIG_MTK_MT6797_DVFSP_BIGIDVFS_BACKEND) += mt6797-bigidvfs-backend.o\n",
        "obj-$(CONFIG_MTK_MT6797_DVFSP_BIGIDVFS_BACKEND) += mt6797-bigidvfs-backend.o\n"
        "obj-$(CONFIG_MTK_MT6797_PROTECTED_READBACK_KUNIT_TEST) += "
        "mt6797-protected-readback-test.o\n",
    )
    (root / "drivers/soc/mediatek/mt6797-protected-readback-test.c").write_text(
        TEST_SOURCE, encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--step", choices=("clock", "bigidvfs", "tests"), required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()

    if args.step == "clock":
        apply_clock(root)
    elif args.step == "bigidvfs":
        apply_bigidvfs(root)
    else:
        apply_tests(root)


if __name__ == "__main__":
    main()
