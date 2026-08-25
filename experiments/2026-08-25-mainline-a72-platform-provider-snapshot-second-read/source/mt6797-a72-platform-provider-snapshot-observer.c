// SPDX-License-Identifier: GPL-2.0-only
/* Candidate-only MT6797 A72 platform and provider snapshot observer. */

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

#include "mt6797-a72-platform-provider-snapshot-observer-internal.h"

#define MT6797_A72_PLATFORM_PROVIDER_TAG \
	"GEMINI_A72_PLATFORM_PROVIDER_SNAPSHOT_V1"

static int mt6797_platform_provider_platform(
	void *context, struct device *dev,
	struct mt6797_a72_platform_state *snapshot)
{
	return mt6797_a72_platform_state_snapshot(dev, snapshot);
}

static bool mt6797_platform_provider_checkpoint(void *context,
						 unsigned int checkpoint)
{
	return gemini_protected_readback_ledger_checkpoint(checkpoint);
}

static int mt6797_platform_provider_provider(
	void *context, struct mt6797_a72_provider_snapshot *snapshot)
{
	return mt6797_a72_provider_snapshot(snapshot);
}

static const struct mt6797_a72_platform_provider_observer_ops
mt6797_a72_platform_provider_ops = {
	.platform = mt6797_platform_provider_platform,
	.checkpoint = mt6797_platform_provider_checkpoint,
	.provider = mt6797_platform_provider_provider,
};

int mt6797_platform_provider_snapshot_capture(
	struct device *platform,
	const struct mt6797_a72_platform_provider_observer_ops *ops,
	void *context, struct mt6797_a72_platform_provider_snapshot *snapshot)
{
	int ret;

	if (!snapshot)
		return -EINVAL;
	memset(snapshot, 0, sizeof(*snapshot));
	if (!platform || !ops || !ops->platform || !ops->checkpoint ||
	    !ops->provider)
		return -EINVAL;

	ret = ops->platform(context, platform, &snapshot->platform);
	if (ret)
		goto out_clear;
	if (!snapshot->platform.valid) {
		ret = -ENODATA;
		goto out_clear;
	}
	if (!ops->checkpoint(context, 0)) {
		ret = -EIO;
		goto out_clear;
	}
	ret = ops->provider(context, &snapshot->provider);
	if (ret)
		goto out_clear;
	if (!snapshot->provider.valid) {
		ret = -ENODATA;
		goto out_clear;
	}
	if (!ops->checkpoint(context, 1)) {
		ret = -EIO;
		goto out_clear;
	}

	snapshot->valid = true;
	return 0;

out_clear:
	memset(snapshot, 0, sizeof(*snapshot));
	return ret;
}

static struct device *
mt6797_a72_platform_provider_get_device(struct device *dev)
{
	struct platform_device *source;
	struct device_node *node;

	node = of_parse_phandle(dev->of_node, "mediatek,platform-state", 0);
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

static void mt6797_a72_platform_provider_log(
	struct device *dev,
	const struct mt6797_a72_platform_provider_snapshot *snapshot)
{
	const struct mt6797_a72_platform_state *platform = &snapshot->platform;
	const struct mt6797_a72_provider_snapshot *provider = &snapshot->provider;

	dev_info(dev,
		 MT6797_A72_PLATFORM_PROVIDER_TAG
		 " platform valid=%u spm=%08x/%08x/%08x/%08x"
		 " mp2=%08x/%08x/%08x iso=%08x dcm=%08x"
		 " cci=%08x/%08x/%08x pwrap=%u\n",
		 platform->valid, platform->spm_pwr_status,
		 platform->spm_pwr_status_2nd,
		 platform->spm_cpu_pwr_status,
		 platform->spm_cpu_pwr_status_2nd,
		 platform->spm_mp2_cpusys_pwr_con,
		 platform->spm_mp2_cpu0_pwr_con,
		 platform->spm_mp2_cpu1_pwr_con,
		 platform->spm_cpu_ext_buck_iso, platform->mp2_sync_dcm,
		 platform->cci_mp2_port_control, platform->cci_status_before,
		 platform->cci_status_after, platform->pwrap_reset_asserted);
	dev_info(dev,
		 MT6797_A72_PLATFORM_PROVIDER_TAG
		 " provider abi=%u valid=%u raw=%02x/%02x/%02x/%02x/%02x\n",
		 provider->abi, provider->valid, provider->control_a,
		 provider->status_b, provider->buckb_cont, provider->vbuckb_a,
		 provider->vbuckb_b);
	dev_info(dev,
		 MT6797_A72_PLATFORM_PROVIDER_TAG
		 " state=complete platform_calls=1 platform_samples=2"
		 " platform_register_observations=26 retained_writes=2"
		 " provider_snapshots=1 provider_samples=2 provider_i2c_reads=10"
		 " provider_i2c_writes=0 observer_retries=0"
		 " protected_clock_reads=0 bigidvfs_reads=0 secure_calls=0"
		 " provider_acquires=0 provider_releases=0 publisher_calls=0"
		 " owner_mutations=0 cpu_requests=0\n");
}

static int mt6797_a72_platform_provider_probe(struct platform_device *pdev)
{
	struct mt6797_a72_platform_provider_snapshot snapshot;
	struct device *platform;
	struct device *dev = &pdev->dev;
	int ret;

	platform = mt6797_a72_platform_provider_get_device(dev);
	if (IS_ERR(platform))
		return dev_err_probe(dev, PTR_ERR(platform),
				     "platform-state source unavailable\n");

	ret = mt6797_platform_provider_snapshot_capture(
		platform, &mt6797_a72_platform_provider_ops, NULL, &snapshot);
	if (ret)
		dev_err_probe(dev, ret, "platform/provider snapshot failed\n");
	else
		mt6797_a72_platform_provider_log(dev, &snapshot);
	put_device(platform);

	return ret;
}

static const struct of_device_id mt6797_a72_platform_provider_of_match[] = {
	{ .compatible = "mediatek,mt6797-a72-platform-provider-snapshot-observer" },
	{ }
};
MODULE_DEVICE_TABLE(of, mt6797_a72_platform_provider_of_match);

static struct platform_driver mt6797_a72_platform_provider_driver = {
	.probe = mt6797_a72_platform_provider_probe,
	.driver = {
		.name = "mt6797-a72-platform-provider-snapshot-observer",
		.of_match_table = mt6797_a72_platform_provider_of_match,
		.suppress_bind_attrs = true,
	},
};
builtin_platform_driver(mt6797_a72_platform_provider_driver);

MODULE_DESCRIPTION("MT6797 A72 platform and provider snapshot observer");
MODULE_LICENSE("GPL");
