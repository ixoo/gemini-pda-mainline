#!/usr/bin/env python3
"""Add the disconnected A72 hotplug snapshot adapter and KUnit tests."""

from __future__ import annotations

import argparse
from pathlib import Path
from textwrap import dedent


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"{path}: expected one anchor: {old.splitlines()[0]}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def kernel_text(value: str) -> str:
    lines = []
    for line in dedent(value).lstrip("\n").splitlines(keepends=True):
        stripped = line.lstrip(" ")
        spaces = len(line) - len(stripped)
        lines.append("\t" * (spaces // 8) + " " * (spaces % 8) + stripped)
    return "".join(lines)


INTERNAL_HEADER = kernel_text(r"""
    /* SPDX-License-Identifier: GPL-2.0-only */
    #ifndef __MT6797_A72_HOTPLUG_SNAPSHOT_INTERNAL_H
    #define __MT6797_A72_HOTPLUG_SNAPSHOT_INTERNAL_H

    #include <linux/mt6797-a72-provider.h>
    #include <linux/soc/mediatek/mt6797-a72-platform-state.h>
    #include <linux/soc/mediatek/mt6797-bigidvfs-backend.h>
    #include <linux/soc/mediatek/mt6797-dvfsp-clock-backend.h>

    #include "mt6797-a72-hotplug-executor-internal.h"

    #define MT6797_A72_HOTPLUG_CLOCK_POWERON_WRITES 1U
    #define MT6797_A72_HOTPLUG_CLOCK_ACQUIRE_WRITES_MAX 200U
    #define MT6797_A72_HOTPLUG_CLOCK_RELEASE_WRITES_MAX 200U
    #define MT6797_A72_HOTPLUG_BIGIDVFS_STABLE_SAMPLES 2U
    #define MT6797_A72_HOTPLUG_BIGIDVFS_READS 8U

    struct device;

    struct mt6797_a72_hotplug_snapshot_ops {
            int (*platform)(struct device *dev,
                    struct mt6797_a72_platform_state *snapshot);
            int (*provider)(struct mt6797_a72_provider_snapshot *snapshot);
            int (*clock)(struct device *dev,
                    struct mt6797_dvfsp_clock_readback *snapshot);
            int (*bigidvfs)(struct device *dev,
                    struct mt6797_bigidvfs_readback *snapshot);
    };

    struct mt6797_a72_hotplug_snapshot_source {
            struct device *platform;
            struct device *clock;
            struct device *bigidvfs;
            const struct mt6797_a72_hotplug_snapshot_ops *ops;
    };

    struct mt6797_a72_hotplug_snapshot_trace {
            u32 platform_calls;
            u32 provider_calls;
            u32 clock_calls;
            u32 bigidvfs_calls;
            u32 protected_readback_checkpoints;
            u32 direct_state_calls;
            u32 physical_source_calls;
            u32 binding_retries;
            u32 clock_poweron_writes_max;
            u32 clock_acquire_writes_max;
            u32 clock_release_writes_max;
            u32 bigidvfs_stable_samples;
            u32 bigidvfs_reads;
            u32 bigidvfs_sram_set_calls;
            bool complete;
    };

    void mt6797_a72_hotplug_snapshot_source_init(
            struct mt6797_a72_hotplug_snapshot_source *source,
            struct device *platform, struct device *clock,
            struct device *bigidvfs);
    int mt6797_a72_hotplug_snapshot_capture(
            const struct mt6797_a72_hotplug_snapshot_source *source,
            struct mt6797_a72_hotplug_readback *readback,
            struct mt6797_a72_hotplug_snapshot_trace *trace);
    int mt6797_a72_hotplug_snapshot_device_capture(
            struct device *dev, struct mt6797_a72_hotplug_readback *readback,
            struct mt6797_a72_hotplug_snapshot_trace *trace);

    #endif /* __MT6797_A72_HOTPLUG_SNAPSHOT_INTERNAL_H */
    """)


SOURCE = kernel_text(r"""
    // SPDX-License-Identifier: GPL-2.0-only
    /* Disconnected physical snapshot adapter for MT6797 CPU9 hotplug. */

    #include <linux/bug.h>
    #include <linux/device.h>
    #include <linux/err.h>
    #include <linux/errno.h>
    #include <linux/module.h>
    #include <linux/mt6797-a72-provider.h>
    #include <linux/of.h>
    #include <linux/of_platform.h>
    #include <linux/platform_device.h>
    #include <linux/slab.h>
    #include <linux/string.h>

    #include <linux/soc/mediatek/mt6797-a72-platform-state.h>
    #include <linux/soc/mediatek/mt6797-bigidvfs-backend.h>
    #include <linux/soc/mediatek/mt6797-dvfsp-clock-backend.h>

    #include "mt6797-a72-hotplug-snapshot-internal.h"

    static int mt6797_hotplug_platform(
            struct device *dev, struct mt6797_a72_platform_state *snapshot)
    {
            return mt6797_a72_platform_state_snapshot(dev, snapshot);
    }

    static int mt6797_hotplug_provider(
            struct mt6797_a72_provider_snapshot *snapshot)
    {
            return mt6797_a72_provider_snapshot(snapshot);
    }

    static int mt6797_hotplug_clock(
            struct device *dev, struct mt6797_dvfsp_clock_readback *snapshot)
    {
            return mt6797_dvfsp_clock_backend_read(dev, snapshot);
    }

    static int mt6797_hotplug_bigidvfs(
            struct device *dev, struct mt6797_bigidvfs_readback *snapshot)
    {
            return mt6797_bigidvfs_backend_read(dev, snapshot);
    }

    static const struct mt6797_a72_hotplug_snapshot_ops mt6797_hotplug_ops = {
            .platform = mt6797_hotplug_platform,
            .provider = mt6797_hotplug_provider,
            .clock = mt6797_hotplug_clock,
            .bigidvfs = mt6797_hotplug_bigidvfs,
    };

    void mt6797_a72_hotplug_snapshot_source_init(
            struct mt6797_a72_hotplug_snapshot_source *source,
            struct device *platform, struct device *clock,
            struct device *bigidvfs)
    {
            if (!source)
                    return;
            memset(source, 0, sizeof(*source));
            source->platform = platform;
            source->clock = clock;
            source->bigidvfs = bigidvfs;
            source->ops = &mt6797_hotplug_ops;
    }

    static bool mt6797_hotplug_provider_valid(
            const struct mt6797_a72_provider_snapshot *provider)
    {
            return provider->abi == MT6797_A72_PROVIDER_STATE_ABI &&
                    provider->valid && !provider->reserved &&
                    provider->control_a <= 0xffU &&
                    provider->status_b <= 0xffU &&
                    provider->buckb_cont <= 0xffU &&
                    provider->vbuckb_a <= 0xffU &&
                    provider->vbuckb_b <= 0xffU;
    }

    static void mt6797_hotplug_map_clock(
            struct mt6797_a72_hotplug_readback *readback,
            const struct mt6797_dvfsp_clock_readback *clock)
    {
            unsigned int index = 0;
            unsigned int word;

            readback->clock[index++] = clock->armplldiv_muxsel;
            readback->clock[index++] = clock->armplldiv_ckdiv;
            for (word = 0; word < 3; word++)
                    readback->clock[index++] = clock->pll_ll[word];
            for (word = 0; word < 3; word++)
                    readback->clock[index++] = clock->pll_l[word];
            for (word = 0; word < 3; word++)
                    readback->clock[index++] = clock->pll_cci[word];
            for (word = 0; word < 3; word++)
                    readback->clock[index++] = clock->cspm_swctrl[word];
            for (word = 0; word < 4; word++)
                    readback->clock[index++] = clock->cspm_hwsta[word];
            WARN_ON_ONCE(index != MT6797_A72_HOTPLUG_CLOCK_VALUES);
    }

    static void mt6797_hotplug_map(
            struct mt6797_a72_hotplug_readback *readback,
            const struct mt6797_a72_platform_state *platform,
            const struct mt6797_a72_provider_snapshot *provider,
            const struct mt6797_dvfsp_clock_readback *clock,
            const struct mt6797_bigidvfs_readback *bigidvfs)
    {
            readback->spm_pwr_status = platform->spm_pwr_status;
            readback->spm_pwr_status_2nd = platform->spm_pwr_status_2nd;
            readback->spm_cpu_pwr_status = platform->spm_cpu_pwr_status;
            readback->spm_cpu_pwr_status_2nd = platform->spm_cpu_pwr_status_2nd;
            readback->spm_mp2_cpusys_pwr_con = platform->spm_mp2_cpusys_pwr_con;
            readback->spm_mp2_cpu0_pwr_con = platform->spm_mp2_cpu0_pwr_con;
            readback->spm_mp2_cpu1_pwr_con = platform->spm_mp2_cpu1_pwr_con;
            readback->spm_cpu_ext_buck_iso = platform->spm_cpu_ext_buck_iso;
            readback->mp2_sync_dcm = platform->mp2_sync_dcm;
            readback->cci_mp2_port_control = platform->cci_mp2_port_control;
            readback->cci_status_before = platform->cci_status_before;
            readback->cci_status_after = platform->cci_status_after;
            readback->provider[0] = provider->control_a;
            readback->provider[1] = provider->status_b;
            readback->provider[2] = provider->buckb_cont;
            readback->provider[3] = provider->vbuckb_a;
            readback->provider[4] = provider->vbuckb_b;
            mt6797_hotplug_map_clock(readback, clock);
            readback->bigidvfs[0] = bigidvfs->pll_pcw;
            readback->bigidvfs[1] = bigidvfs->pll_enable_posdiv;
            readback->bigidvfs[2] = bigidvfs->sram_selector;
            readback->bigidvfs[3] = bigidvfs->control;
            readback->valid = true;
    }

    int mt6797_a72_hotplug_snapshot_capture(
            const struct mt6797_a72_hotplug_snapshot_source *source,
            struct mt6797_a72_hotplug_readback *readback,
            struct mt6797_a72_hotplug_snapshot_trace *trace)
    {
            struct mt6797_a72_platform_state platform = { };
            struct mt6797_a72_provider_snapshot provider = { };
            struct mt6797_dvfsp_clock_readback clock = { };
            struct mt6797_bigidvfs_readback bigidvfs = { };
            const struct mt6797_a72_hotplug_snapshot_ops *ops;
            int ret;

            if (!readback || !trace)
                    return -EINVAL;
            memset(readback, 0, sizeof(*readback));
            memset(trace, 0, sizeof(*trace));
            if (!source || !source->platform || !source->clock ||
                !source->bigidvfs || !source->ops)
                    return -EINVAL;
            ops = source->ops;
            if (!ops->platform || !ops->provider || !ops->clock ||
                !ops->bigidvfs)
                    return -EINVAL;

            trace->platform_calls++;
            ret = ops->platform(source->platform, &platform);
            if (ret)
                    goto out_clear;
            if (!platform.valid) {
                    ret = -ENODATA;
                    goto out_clear;
            }
            trace->provider_calls++;
            ret = ops->provider(&provider);
            if (ret)
                    goto out_clear;
            if (!mt6797_hotplug_provider_valid(&provider)) {
                    ret = -EPROTO;
                    goto out_clear;
            }
            trace->clock_calls++;
            ret = ops->clock(source->clock, &clock);
            if (ret)
                    goto out_clear;
            if (clock.abi != MT6797_DVFSP_CLOCK_BACKEND_ABI ||
                !clock.sample_generation) {
                    ret = -EPROTO;
                    goto out_clear;
            }
            trace->bigidvfs_calls++;
            ret = ops->bigidvfs(source->bigidvfs, &bigidvfs);
            if (ret)
                    goto out_clear;
            if (bigidvfs.abi != MT6797_BIGIDVFS_BACKEND_ABI ||
                !bigidvfs.sample_generation) {
                    ret = -EPROTO;
                    goto out_clear;
            }

            mt6797_hotplug_map(readback, &platform, &provider, &clock,
                               &bigidvfs);
            trace->clock_poweron_writes_max =
                    MT6797_A72_HOTPLUG_CLOCK_POWERON_WRITES;
            trace->clock_acquire_writes_max =
                    MT6797_A72_HOTPLUG_CLOCK_ACQUIRE_WRITES_MAX;
            trace->clock_release_writes_max =
                    MT6797_A72_HOTPLUG_CLOCK_RELEASE_WRITES_MAX;
            trace->bigidvfs_stable_samples =
                    MT6797_A72_HOTPLUG_BIGIDVFS_STABLE_SAMPLES;
            trace->bigidvfs_reads = MT6797_A72_HOTPLUG_BIGIDVFS_READS;
            trace->complete = true;
            return 0;

    out_clear:
            memset(readback, 0, sizeof(*readback));
            return ret;
    }

    int mt6797_a72_hotplug_snapshot_device_capture(
            struct device *dev, struct mt6797_a72_hotplug_readback *readback,
            struct mt6797_a72_hotplug_snapshot_trace *trace)
    {
            struct mt6797_a72_hotplug_snapshot_source *source;

            if (!dev)
                    return -EINVAL;
            source = dev_get_drvdata(dev);
            if (!source)
                    return -ENODEV;
            return mt6797_a72_hotplug_snapshot_capture(source, readback, trace);
    }

    static struct device *mt6797_hotplug_get_device(
            struct device *dev, const char *property, const char *compatible)
    {
            struct platform_device *source;
            struct device_node *node;

            node = of_parse_phandle(dev->of_node, property, 0);
            if (!node)
                    return ERR_PTR(-EINVAL);
            if (!of_device_is_compatible(node, compatible)) {
                    of_node_put(node);
                    return ERR_PTR(-EINVAL);
            }
            source = of_find_device_by_node(node);
            of_node_put(node);
            if (!source)
                    return ERR_PTR(-EPROBE_DEFER);
            if (!device_is_bound(&source->dev)) {
                    put_device(&source->dev);
                    return ERR_PTR(-EPROBE_DEFER);
            }
            return &source->dev;
    }

    static void mt6797_hotplug_put_device(void *data)
    {
            put_device(data);
    }

    static int mt6797_hotplug_keep_device(struct device *owner,
                                           struct device *source)
    {
            return devm_add_action_or_reset(owner, mt6797_hotplug_put_device,
                                            source);
    }

    static int mt6797_a72_hotplug_snapshot_probe(struct platform_device *pdev)
    {
            struct mt6797_a72_hotplug_snapshot_source *source;
            struct device *dev = &pdev->dev;
            struct device *dependency;
            int ret;

            if (!mt6797_a72_provider_available())
                    return dev_err_probe(dev, -EPROBE_DEFER,
                                         "provider unavailable\n");
            source = devm_kzalloc(dev, sizeof(*source), GFP_KERNEL);
            if (!source)
                    return -ENOMEM;

            dependency = mt6797_hotplug_get_device(
                    dev, "mediatek,platform-state",
                    "mediatek,mt6797-a72-platform-state");
            if (IS_ERR(dependency))
                    return dev_err_probe(dev, PTR_ERR(dependency),
                                         "platform-state unavailable\n");
            ret = mt6797_hotplug_keep_device(dev, dependency);
            if (ret)
                    return ret;
            source->platform = dependency;

            dependency = mt6797_hotplug_get_device(
                    dev, "mediatek,clock-backend",
                    "mediatek,mt6797-dvfsp-clock-backend");
            if (IS_ERR(dependency))
                    return dev_err_probe(dev, PTR_ERR(dependency),
                                         "clock backend unavailable\n");
            ret = mt6797_hotplug_keep_device(dev, dependency);
            if (ret)
                    return ret;
            source->clock = dependency;

            dependency = mt6797_hotplug_get_device(
                    dev, "mediatek,bigidvfs-backend",
                    "mediatek,mt6797-bigidvfs-backend");
            if (IS_ERR(dependency))
                    return dev_err_probe(dev, PTR_ERR(dependency),
                                         "BigiDVFS backend unavailable\n");
            ret = mt6797_hotplug_keep_device(dev, dependency);
            if (ret)
                    return ret;
            source->bigidvfs = dependency;
            source->ops = &mt6797_hotplug_ops;
            platform_set_drvdata(pdev, source);

            dev_info(dev, "snapshot adapter ready; production caller absent\n");
            return 0;
    }

    static const struct of_device_id mt6797_a72_hotplug_snapshot_of_match[] = {
            { .compatible = "mediatek,mt6797-a72-hotplug-snapshot-adapter" },
            { }
    };
    MODULE_DEVICE_TABLE(of, mt6797_a72_hotplug_snapshot_of_match);

    static struct platform_driver mt6797_a72_hotplug_snapshot_driver = {
            .probe = mt6797_a72_hotplug_snapshot_probe,
            .driver = {
                    .name = "mt6797-a72-hotplug-snapshot",
                    .of_match_table = mt6797_a72_hotplug_snapshot_of_match,
                    .suppress_bind_attrs = true,
            },
    };
    builtin_platform_driver(mt6797_a72_hotplug_snapshot_driver);

    MODULE_DESCRIPTION("Disconnected MT6797 A72 hotplug snapshot adapter");
    MODULE_LICENSE("GPL");
    """)


TEST_SOURCE = kernel_text(r"""
    // SPDX-License-Identifier: GPL-2.0-only
    /* In-memory tests for the disconnected MT6797 hotplug snapshot adapter. */

    #include <kunit/test.h>
    #include <linux/errno.h>
    #include <linux/string.h>

    #include "mt6797-a72-hotplug-snapshot-internal.h"

    enum hotplug_snapshot_step {
            HOTPLUG_SNAPSHOT_PLATFORM = 1,
            HOTPLUG_SNAPSHOT_PROVIDER,
            HOTPLUG_SNAPSHOT_CLOCK,
            HOTPLUG_SNAPSHOT_BIGIDVFS,
    };

    struct hotplug_snapshot_test_state {
            struct mt6797_a72_platform_state platform;
            struct mt6797_a72_provider_snapshot provider;
            struct mt6797_dvfsp_clock_readback clock;
            struct mt6797_bigidvfs_readback bigidvfs;
            u32 order[4];
            u32 calls;
            u32 fail_step;
            u8 devices[3];
    };

    static struct hotplug_snapshot_test_state *hotplug_snapshot_state;

    static int hotplug_snapshot_platform(
            struct device *dev, struct mt6797_a72_platform_state *snapshot)
    {
            struct hotplug_snapshot_test_state *state = hotplug_snapshot_state;

            state->order[state->calls++] = HOTPLUG_SNAPSHOT_PLATFORM;
            if (state->fail_step == HOTPLUG_SNAPSHOT_PLATFORM)
                    return -EIO;
            *snapshot = state->platform;
            return 0;
    }

    static int hotplug_snapshot_provider(
            struct mt6797_a72_provider_snapshot *snapshot)
    {
            struct hotplug_snapshot_test_state *state = hotplug_snapshot_state;

            state->order[state->calls++] = HOTPLUG_SNAPSHOT_PROVIDER;
            if (state->fail_step == HOTPLUG_SNAPSHOT_PROVIDER)
                    return -EIO;
            *snapshot = state->provider;
            return 0;
    }

    static int hotplug_snapshot_clock(
            struct device *dev, struct mt6797_dvfsp_clock_readback *snapshot)
    {
            struct hotplug_snapshot_test_state *state = hotplug_snapshot_state;

            state->order[state->calls++] = HOTPLUG_SNAPSHOT_CLOCK;
            if (state->fail_step == HOTPLUG_SNAPSHOT_CLOCK)
                    return -EIO;
            *snapshot = state->clock;
            return 0;
    }

    static int hotplug_snapshot_bigidvfs(
            struct device *dev, struct mt6797_bigidvfs_readback *snapshot)
    {
            struct hotplug_snapshot_test_state *state = hotplug_snapshot_state;

            state->order[state->calls++] = HOTPLUG_SNAPSHOT_BIGIDVFS;
            if (state->fail_step == HOTPLUG_SNAPSHOT_BIGIDVFS)
                    return -EIO;
            *snapshot = state->bigidvfs;
            return 0;
    }

    static const struct mt6797_a72_hotplug_snapshot_ops hotplug_snapshot_ops = {
            .platform = hotplug_snapshot_platform,
            .provider = hotplug_snapshot_provider,
            .clock = hotplug_snapshot_clock,
            .bigidvfs = hotplug_snapshot_bigidvfs,
    };

    static void hotplug_snapshot_fill(struct hotplug_snapshot_test_state *state)
    {
            unsigned int index;

            memset(state, 0, sizeof(*state));
            state->platform.valid = true;
            state->platform.spm_pwr_status = 1;
            state->platform.spm_pwr_status_2nd = 2;
            state->platform.spm_cpu_pwr_status = BIT(7) | BIT(6);
            state->platform.spm_cpu_pwr_status_2nd = BIT(7) | BIT(6);
            state->platform.spm_mp2_cpusys_pwr_con = 5;
            state->platform.spm_mp2_cpu0_pwr_con = 6;
            state->platform.spm_mp2_cpu1_pwr_con = 7;
            state->platform.spm_cpu_ext_buck_iso = 8;
            state->platform.mp2_sync_dcm = 9;
            state->platform.cci_mp2_port_control = 10;
            state->platform.cci_status_before = 0;
            state->platform.cci_status_after = 0;
            state->provider.abi = MT6797_A72_PROVIDER_STATE_ABI;
            state->provider.valid = 1;
            state->provider.control_a = 0x11;
            state->provider.status_b = 0x12;
            state->provider.buckb_cont = 0x13;
            state->provider.vbuckb_a = 0x14;
            state->provider.vbuckb_b = 0x15;
            state->clock.abi = MT6797_DVFSP_CLOCK_BACKEND_ABI;
            state->clock.sample_generation = 1;
            state->clock.armplldiv_muxsel = 0x20;
            state->clock.armplldiv_ckdiv = 0x21;
            for (index = 0; index < 3; index++) {
                    state->clock.pll_ll[index] = 0x30 + index;
                    state->clock.pll_l[index] = 0x40 + index;
                    state->clock.pll_cci[index] = 0x50 + index;
                    state->clock.cspm_swctrl[index] = 0x60 + index;
            }
            for (index = 0; index < 4; index++)
                    state->clock.cspm_hwsta[index] = 0x70 + index;
            state->bigidvfs.abi = MT6797_BIGIDVFS_BACKEND_ABI;
            state->bigidvfs.sample_generation = 1;
            state->bigidvfs.pll_pcw = 0x80;
            state->bigidvfs.pll_enable_posdiv = 0x81;
            state->bigidvfs.sram_selector = 0x82;
            state->bigidvfs.control = 0x83;
    }

    static void hotplug_snapshot_source(
            struct mt6797_a72_hotplug_snapshot_source *source,
            struct hotplug_snapshot_test_state *state)
    {
            source->platform = (struct device *)&state->devices[0];
            source->clock = (struct device *)&state->devices[1];
            source->bigidvfs = (struct device *)&state->devices[2];
            source->ops = &hotplug_snapshot_ops;
            hotplug_snapshot_state = state;
    }

    static void hotplug_snapshot_success_test(struct kunit *test)
    {
            struct mt6797_a72_hotplug_snapshot_trace trace;
            struct mt6797_a72_hotplug_readback readback;
            struct mt6797_a72_hotplug_snapshot_source source;
            struct hotplug_snapshot_test_state *state;

            state = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
            KUNIT_ASSERT_NOT_NULL(test, state);
            hotplug_snapshot_fill(state);
            hotplug_snapshot_source(&source, state);
            KUNIT_ASSERT_EQ(test, mt6797_a72_hotplug_snapshot_capture(
                    &source, &readback, &trace), 0);
            KUNIT_EXPECT_TRUE(test, readback.valid);
            KUNIT_EXPECT_EQ(test, state->calls, 4U);
            KUNIT_EXPECT_MEMEQ(test, state->order,
                    ((u32[]){ 1, 2, 3, 4 }), sizeof(state->order));
            KUNIT_EXPECT_EQ(test, readback.provider[0], (u8)0x11);
            KUNIT_EXPECT_EQ(test, readback.provider[4], (u8)0x15);
            KUNIT_EXPECT_EQ(test, readback.clock[0], 0x20U);
            KUNIT_EXPECT_EQ(test, readback.clock[17], 0x73U);
            KUNIT_EXPECT_EQ(test, readback.bigidvfs[0], 0x80U);
            KUNIT_EXPECT_EQ(test, readback.bigidvfs[3], 0x83U);
            KUNIT_EXPECT_EQ(test, trace.platform_calls, 1U);
            KUNIT_EXPECT_EQ(test, trace.provider_calls, 1U);
            KUNIT_EXPECT_EQ(test, trace.clock_calls, 1U);
            KUNIT_EXPECT_EQ(test, trace.bigidvfs_calls, 1U);
            KUNIT_EXPECT_EQ(test, trace.protected_readback_checkpoints, 0U);
            KUNIT_EXPECT_EQ(test, trace.clock_poweron_writes_max, 1U);
            KUNIT_EXPECT_EQ(test, trace.clock_acquire_writes_max, 200U);
            KUNIT_EXPECT_EQ(test, trace.clock_release_writes_max, 200U);
            KUNIT_EXPECT_EQ(test, trace.bigidvfs_stable_samples, 2U);
            KUNIT_EXPECT_EQ(test, trace.bigidvfs_reads, 8U);
            KUNIT_EXPECT_EQ(test, trace.bigidvfs_sram_set_calls, 0U);
            KUNIT_EXPECT_TRUE(test, trace.complete);
    }

    static void hotplug_snapshot_generation_excluded_test(struct kunit *test)
    {
            struct mt6797_a72_hotplug_snapshot_trace trace;
            struct mt6797_a72_hotplug_readback first;
            struct mt6797_a72_hotplug_readback second;
            struct mt6797_a72_hotplug_snapshot_source source;
            struct hotplug_snapshot_test_state *state;

            state = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
            KUNIT_ASSERT_NOT_NULL(test, state);
            hotplug_snapshot_fill(state);
            hotplug_snapshot_source(&source, state);
            KUNIT_ASSERT_EQ(test, mt6797_a72_hotplug_snapshot_capture(
                    &source, &first, &trace), 0);
            state->clock.sample_generation = 99;
            state->bigidvfs.sample_generation = 101;
            state->calls = 0;
            KUNIT_ASSERT_EQ(test, mt6797_a72_hotplug_snapshot_capture(
                    &source, &second, &trace), 0);
            KUNIT_EXPECT_MEMEQ(test, &first, &second, sizeof(first));
    }

    static void hotplug_snapshot_component_failures_test(struct kunit *test)
    {
            struct mt6797_a72_hotplug_snapshot_trace trace;
            struct mt6797_a72_hotplug_readback readback;
            struct mt6797_a72_hotplug_readback zero = { };
            struct mt6797_a72_hotplug_snapshot_source source;
            struct hotplug_snapshot_test_state *state;
            u32 step;

            state = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
            KUNIT_ASSERT_NOT_NULL(test, state);
            for (step = 1; step <= 4; step++) {
                    hotplug_snapshot_fill(state);
                    state->fail_step = step;
                    hotplug_snapshot_source(&source, state);
                    memset(&readback, 0xa5, sizeof(readback));
                    KUNIT_EXPECT_EQ(test, mt6797_a72_hotplug_snapshot_capture(
                            &source, &readback, &trace), -EIO);
                    KUNIT_EXPECT_MEMEQ(test, &readback, &zero, sizeof(zero));
                    KUNIT_EXPECT_EQ(test, state->calls, step);
                    KUNIT_EXPECT_FALSE(test, trace.complete);
            }
    }

    static void hotplug_snapshot_source_guards_test(struct kunit *test)
    {
            struct mt6797_a72_hotplug_snapshot_trace trace;
            struct mt6797_a72_hotplug_readback readback;
            struct mt6797_a72_hotplug_snapshot_source source = { };
            struct hotplug_snapshot_test_state *state;

            state = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
            KUNIT_ASSERT_NOT_NULL(test, state);
            hotplug_snapshot_fill(state);
            mt6797_a72_hotplug_snapshot_source_init(NULL, NULL, NULL, NULL);
            KUNIT_EXPECT_EQ(test, mt6797_a72_hotplug_snapshot_capture(
                    NULL, &readback, &trace), -EINVAL);
            KUNIT_EXPECT_EQ(test, mt6797_a72_hotplug_snapshot_capture(
                    &source, &readback, &trace), -EINVAL);
            hotplug_snapshot_source(&source, state);
            source.ops = NULL;
            KUNIT_EXPECT_EQ(test, mt6797_a72_hotplug_snapshot_capture(
                    &source, &readback, &trace), -EINVAL);
    }

    static void hotplug_snapshot_shape_refusal_test(struct kunit *test)
    {
            struct mt6797_a72_hotplug_snapshot_trace trace;
            struct mt6797_a72_hotplug_readback readback;
            struct mt6797_a72_hotplug_readback zero = { };
            struct mt6797_a72_hotplug_snapshot_source source;
            struct hotplug_snapshot_test_state *state;

            state = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
            KUNIT_ASSERT_NOT_NULL(test, state);
            hotplug_snapshot_fill(state);
            hotplug_snapshot_source(&source, state);
            state->platform.valid = false;
            KUNIT_EXPECT_EQ(test, mt6797_a72_hotplug_snapshot_capture(
                    &source, &readback, &trace), -ENODATA);
            hotplug_snapshot_fill(state);
            state->provider.valid = 0;
            KUNIT_EXPECT_EQ(test, mt6797_a72_hotplug_snapshot_capture(
                    &source, &readback, &trace), -EPROTO);
            hotplug_snapshot_fill(state);
            state->clock.sample_generation = 0;
            KUNIT_EXPECT_EQ(test, mt6797_a72_hotplug_snapshot_capture(
                    &source, &readback, &trace), -EPROTO);
            hotplug_snapshot_fill(state);
            state->bigidvfs.abi++;
            KUNIT_EXPECT_EQ(test, mt6797_a72_hotplug_snapshot_capture(
                    &source, &readback, &trace), -EPROTO);
            KUNIT_EXPECT_MEMEQ(test, &readback, &zero, sizeof(zero));
    }

    static void hotplug_snapshot_provider_width_test(struct kunit *test)
    {
            struct mt6797_a72_hotplug_snapshot_trace trace;
            struct mt6797_a72_hotplug_readback readback;
            struct mt6797_a72_hotplug_snapshot_source source;
            struct hotplug_snapshot_test_state *state;

            state = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
            KUNIT_ASSERT_NOT_NULL(test, state);
            hotplug_snapshot_fill(state);
            hotplug_snapshot_source(&source, state);
            state->provider.vbuckb_b = 0x100;
            KUNIT_EXPECT_EQ(test, mt6797_a72_hotplug_snapshot_capture(
                    &source, &readback, &trace), -EPROTO);
            KUNIT_EXPECT_FALSE(test, readback.valid);
            KUNIT_EXPECT_EQ(test, trace.clock_calls, 0U);
            KUNIT_EXPECT_EQ(test, trace.bigidvfs_calls, 0U);
    }

    static struct kunit_case hotplug_snapshot_cases[] = {
            KUNIT_CASE(hotplug_snapshot_success_test),
            KUNIT_CASE(hotplug_snapshot_generation_excluded_test),
            KUNIT_CASE(hotplug_snapshot_component_failures_test),
            KUNIT_CASE(hotplug_snapshot_source_guards_test),
            KUNIT_CASE(hotplug_snapshot_shape_refusal_test),
            KUNIT_CASE(hotplug_snapshot_provider_width_test),
            { }
    };

    static struct kunit_suite hotplug_snapshot_suite = {
            .name = "mt6797-a72-hotplug-snapshot",
            .test_cases = hotplug_snapshot_cases,
    };

    kunit_test_suite(hotplug_snapshot_suite);

    MODULE_DESCRIPTION("MT6797 A72 hotplug snapshot adapter KUnit tests");
    MODULE_LICENSE("GPL");
    """)


KCONFIG_ANCHOR = """config MTK_MMSYS
"""

KCONFIG_BLOCK = """config MTK_MT6797_A72_HOTPLUG_SNAPSHOT
\tbool \"MediaTek MT6797 CPU9 hotplug snapshot adapter\"
\tdepends on MTK_MT6797_A72_HOTPLUG_EXECUTOR
\tdepends on MTK_MT6797_A72_PLATFORM_STATE
\tdepends on MTK_MT6797_DVFSP_CLOCK_BACKEND
\tdepends on MTK_MT6797_DVFSP_BIGIDVFS_BACKEND
\tdepends on ARM64_MT6797_A72_PROVIDER_OWNER
\tdefault n
\thelp
\t  Build a disconnected adapter that takes one stable platform sample,
\t  provider snapshot, bounded protected-clock sample, and stable BigiDVFS
\t  sample, then maps only equality-relevant values into the CPU9 hotplug
\t  executor readback. Three supplier device references live until unbind.

\t  The adapter does not use the protected-readback ledger, bind a hotplug
\t  callback, issue a CPU request, or select a Device Tree node. The clock
\t  backend retains its documented bounded transport writes. If unsure, say N.

config MTK_MT6797_A72_HOTPLUG_SNAPSHOT_KUNIT_TEST
\tbool \"KUnit tests for the MT6797 CPU9 hotplug snapshot adapter\"
\tdepends on KUNIT=y
\tdepends on MTK_MT6797_A72_HOTPLUG_SNAPSHOT
\tdefault n
\thelp
\t  Exercise exact component order, mapping, generation exclusion, call
\t  budgets, failure clearing, and malformed snapshots with injected memory
\t  operations only. No device, MMIO, I2C, SMC, retained-memory, CPU,
\t  watchdog, or network action occurs.

"""


MAKEFILE_ANCHOR = (
    "obj-$(CONFIG_MTK_MT6797_A72_HOTPLUG_EXECUTOR_KUNIT_TEST) += "
    "mt6797-a72-hotplug-executor-test.o\n"
)
MAKEFILE_BLOCK = (
    MAKEFILE_ANCHOR
    + "obj-$(CONFIG_MTK_MT6797_A72_HOTPLUG_SNAPSHOT) += "
    "mt6797-a72-hotplug-snapshot.o\n"
    + "obj-$(CONFIG_MTK_MT6797_A72_HOTPLUG_SNAPSHOT_KUNIT_TEST) += "
    "mt6797-a72-hotplug-snapshot-test.o\n"
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    mediatek = root / "drivers/soc/mediatek"
    replace_once(
        mediatek / "Kconfig",
        KCONFIG_ANCHOR,
        KCONFIG_BLOCK + KCONFIG_ANCHOR,
    )
    replace_once(mediatek / "Makefile", MAKEFILE_ANCHOR, MAKEFILE_BLOCK)
    additions = {
        "mt6797-a72-hotplug-snapshot-internal.h": INTERNAL_HEADER,
        "mt6797-a72-hotplug-snapshot.c": SOURCE,
        "mt6797-a72-hotplug-snapshot-test.c": TEST_SOURCE,
    }
    for name, text in additions.items():
        path = mediatek / name
        if path.exists():
            raise SystemExit(f"refusing to overwrite: {path}")
        path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
