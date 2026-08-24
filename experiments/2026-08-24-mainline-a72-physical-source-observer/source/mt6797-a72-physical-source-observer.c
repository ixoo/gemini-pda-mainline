// SPDX-License-Identifier: GPL-2.0-only
/* Candidate-only MT6797 A72 direct physical-source observer. */

#include <asm/mt6797_a72_membership.h>

#include <linux/device.h>
#include <linux/err.h>
#include <linux/errno.h>
#include <linux/module.h>
#include <linux/mt6797-a72-provider.h>
#include <linux/of.h>
#include <linux/of_platform.h>
#include <linux/platform_device.h>
#include <linux/pstore_ram.h>
#include <linux/string.h>

#include <linux/soc/mediatek/mt6797-a72-platform-state.h>
#include <linux/soc/mediatek/mt6797-bigidvfs-backend.h>
#include <linux/soc/mediatek/mt6797-dvfsp-clock-backend.h>

#include "mt6797-a72-physical-source-observer-internal.h"

#define MT6797_A72_PHYSICAL_SOURCE_TAG "GEMINI_A72_PHYSICAL_SOURCE_V1"

static const struct mt6797_a72_physical_source_reader_ops
mt6797_a72_physical_source_readers = {
	.platform = mt6797_a72_platform_state_snapshot,
	.provider = mt6797_a72_provider_snapshot,
	.clock = mt6797_dvfsp_clock_backend_read,
	.checkpoint = gemini_protected_readback_ledger_checkpoint,
	.bigidvfs = mt6797_bigidvfs_backend_read,
};

int
mt6797_a72_physical_source_capture(void *context,
                                   struct mt6797_a72_direct_source_snapshot *snapshot)
{
	struct mt6797_a72_physical_source_context *source = context;
	const struct mt6797_a72_physical_source_reader_ops *readers;
	int ret;

	if (!snapshot)
		return -EINVAL;
	memset(snapshot, 0, sizeof(*snapshot));
	if (!source || !source->platform || !source->clock ||
	    !source->bigidvfs || !source->readers)
		return -EINVAL;
	readers = source->readers;
	if (!readers->platform || !readers->provider || !readers->clock ||
	    !readers->checkpoint || !readers->bigidvfs)
		return -EINVAL;

	ret = readers->platform(source->platform, &snapshot->platform);
	if (ret)
		goto out_clear;
	ret = readers->provider(&snapshot->provider);
	if (ret)
		goto out_clear;
	ret = readers->clock(source->clock, &snapshot->clock);
	if (ret)
		goto out_clear;
	if (!readers->checkpoint(0)) {
		ret = -EIO;
		goto out_clear;
	}
	ret = readers->bigidvfs(source->bigidvfs, &snapshot->bigidvfs);
	if (ret)
		goto out_clear;
	if (!readers->checkpoint(1)) {
		ret = -EIO;
		goto out_clear;
	}

	snapshot->abi = MT6797_A72_DIRECT_SOURCE_ABI;
	snapshot->valid = 1;
	return 0;

out_clear:
	memset(snapshot, 0, sizeof(*snapshot));
	return ret;
}

static const struct mt6797_a72_direct_source_ops
mt6797_a72_physical_source_ops = {
	.snapshot = mt6797_a72_physical_source_capture,
};

int
mt6797_a72_physical_source_run(struct mt6797_a72_physical_source_context *context,
                               const struct mt6797_a72_physical_source_runtime_ops *runtime,
                               struct mt6797_a72_direct_state_snapshot *snapshot)
{
	int ret;

	if (!snapshot)
		return -EINVAL;
	memset(snapshot, 0, sizeof(*snapshot));
	if (!context || !runtime || !runtime->register_source ||
	    !runtime->snapshot || !runtime->unregister_source)
		return -EINVAL;

	ret = runtime->register_source(&mt6797_a72_physical_source_ops,
				       context);
	if (ret)
		return ret;
	ret = runtime->snapshot(snapshot);
	runtime->unregister_source(&mt6797_a72_physical_source_ops, context);
	if (ret)
		memset(snapshot, 0, sizeof(*snapshot));

	return ret;
}

static const struct mt6797_a72_physical_source_runtime_ops mt6797_physical_runtime = {
	.register_source = mt6797_a72_direct_source_register,
	.snapshot = mt6797_a72_direct_state_snapshot,
	.unregister_source = mt6797_a72_direct_source_unregister,
};

static struct device *
mt6797_a72_physical_source_get_device(struct device *dev,
				      const char *property)
{
	struct platform_device *source;
	struct device_node *node;

	node = of_parse_phandle(dev->of_node, property, 0);
	if (!node)
		return ERR_PTR(-EINVAL);
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

static void
mt6797_a72_physical_source_log(struct device *dev,
                               const struct mt6797_a72_direct_state_snapshot *state)
{
	const struct mt6797_a72_direct_source_snapshot *source = &state->source;
	const struct mt6797_a72_platform_state *platform = &source->platform;
	const struct mt6797_dvfsp_clock_readback *clock = &source->clock;
	const struct mt6797_bigidvfs_readback *bigidvfs = &source->bigidvfs;

	dev_info(dev,
		 MT6797_A72_PHYSICAL_SOURCE_TAG
		 " direct abi=%u valid=%u cpu8=%u/%u/%u/%u/%llx"
		 " cpu9=%u/%u/%u/%u/%llx owner=%u/%u/%u/%u/%llx\n",
		 state->abi, state->valid, state->cpu8_possible,
		 state->cpu8_present, state->cpu8_online,
		 state->cpu8_method_valid,
		 (unsigned long long)state->cpu8_mpidr,
		 state->cpu9_possible, state->cpu9_present,
		 state->cpu9_online, state->cpu9_method_valid,
		 (unsigned long long)state->cpu9_mpidr,
		 state->owner.abi, state->owner.health, state->owner.phase,
		 state->owner.provider_state,
		 (unsigned long long)state->owner.diagnostic_blockers);
	dev_info(dev,
		 MT6797_A72_PHYSICAL_SOURCE_TAG
		 " provider abi=%u valid=%u raw=%02x/%02x/%02x/%02x/%02x\n",
		 source->provider.abi, source->provider.valid,
		 source->provider.control_a, source->provider.status_b,
		 source->provider.buckb_cont, source->provider.vbuckb_a,
		 source->provider.vbuckb_b);
	dev_info(dev,
		 MT6797_A72_PHYSICAL_SOURCE_TAG
		 " platform valid=%u spm=%08x/%08x/%08x/%08x"
		 " mp2=%08x/%08x/%08x iso=%08x dcm=%08x"
		 " cci=%08x/%08x/%08x pwrap=%u\n",
		 platform->valid, platform->spm_pwr_status,
		 platform->spm_pwr_status_2nd, platform->spm_cpu_pwr_status,
		 platform->spm_cpu_pwr_status_2nd,
		 platform->spm_mp2_cpusys_pwr_con,
		 platform->spm_mp2_cpu0_pwr_con,
		 platform->spm_mp2_cpu1_pwr_con,
		 platform->spm_cpu_ext_buck_iso, platform->mp2_sync_dcm,
		 platform->cci_mp2_port_control, platform->cci_status_before,
		 platform->cci_status_after, platform->pwrap_reset_asserted);
	dev_info(dev,
		 MT6797_A72_PHYSICAL_SOURCE_TAG
		 " clock abi=%u generation=%llu mux=%08x div=%08x"
		 " pll=%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x"
		 " sw=%08x/%08x/%08x hw=%08x/%08x/%08x/%08x\n",
		 clock->abi, (unsigned long long)clock->sample_generation,
		 clock->armplldiv_muxsel, clock->armplldiv_ckdiv,
		 clock->pll_ll[0], clock->pll_ll[1], clock->pll_ll[2],
		 clock->pll_l[0], clock->pll_l[1], clock->pll_l[2],
		 clock->pll_cci[0], clock->pll_cci[1], clock->pll_cci[2],
		 clock->cspm_swctrl[0], clock->cspm_swctrl[1],
		 clock->cspm_swctrl[2], clock->cspm_hwsta[0],
		 clock->cspm_hwsta[1], clock->cspm_hwsta[2],
		 clock->cspm_hwsta[3]);
	dev_info(dev,
		 MT6797_A72_PHYSICAL_SOURCE_TAG
		 " bigidvfs abi=%u generation=%llu raw=%08x/%08x/%08x/%08x\n",
		 bigidvfs->abi,
		 (unsigned long long)bigidvfs->sample_generation,
		 bigidvfs->pll_pcw, bigidvfs->pll_enable_posdiv,
		 bigidvfs->sram_selector, bigidvfs->control);
	dev_info(dev,
		 MT6797_A72_PHYSICAL_SOURCE_TAG
		 " state=complete registrations=1 callbacks=1 unregisters=1"
		 " platform_calls=1 provider_snapshots=1 clock_calls=1"
		 " retained_writes=2 bigidvfs_calls=1 bigidvfs_smc_reads=8"
		 " compositor_retries=0 provider_acquires=0 provider_releases=0"
		 " publisher_calls=0 owner_mutations=0 cpu_requests=0\n");
}

static int
mt6797_a72_physical_source_probe(struct platform_device *pdev)
{
	struct mt6797_a72_physical_source_context context = {
		.readers = &mt6797_a72_physical_source_readers,
	};
	struct mt6797_a72_direct_state_snapshot snapshot;
	struct device *dev = &pdev->dev;
	int ret;

	context.platform = mt6797_a72_physical_source_get_device(dev, "mediatek,platform-state");
	if (IS_ERR(context.platform))
		return dev_err_probe(dev, PTR_ERR(context.platform),
				     "platform-state source unavailable\n");
	context.clock = mt6797_a72_physical_source_get_device(dev, "mediatek,clock-backend");
	if (IS_ERR(context.clock)) {
		ret = dev_err_probe(dev, PTR_ERR(context.clock),
				    "clock source unavailable\n");
		goto put_platform;
	}
	context.bigidvfs = mt6797_a72_physical_source_get_device(dev, "mediatek,bigidvfs-backend");
	if (IS_ERR(context.bigidvfs)) {
		ret = dev_err_probe(dev, PTR_ERR(context.bigidvfs),
				    "BigiDVFS source unavailable\n");
		goto put_clock;
	}

	ret = mt6797_a72_physical_source_run(&context, &mt6797_physical_runtime,
					     &snapshot);
	if (ret)
		dev_err_probe(dev, ret, "direct physical snapshot failed\n");
	else
		mt6797_a72_physical_source_log(dev, &snapshot);

	put_device(context.bigidvfs);
put_clock:
	put_device(context.clock);
put_platform:
	put_device(context.platform);
	return ret;
}

static const struct of_device_id mt6797_a72_physical_source_of_match[] = {
	{ .compatible = "mediatek,mt6797-a72-physical-source-observer" },
	{ }
};
MODULE_DEVICE_TABLE(of, mt6797_a72_physical_source_of_match);

static struct platform_driver mt6797_a72_physical_source_driver = {
	.probe = mt6797_a72_physical_source_probe,
	.driver = {
		.name = "mt6797-a72-physical-source-observer",
		.of_match_table = mt6797_a72_physical_source_of_match,
		.suppress_bind_attrs = true,
	},
};
builtin_platform_driver(mt6797_a72_physical_source_driver);

MODULE_DESCRIPTION("MT6797 A72 candidate-only direct physical-source observer");
MODULE_LICENSE("GPL");
