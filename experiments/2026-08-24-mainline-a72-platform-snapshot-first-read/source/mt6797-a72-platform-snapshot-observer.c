// SPDX-License-Identifier: GPL-2.0-only
/* Candidate-only MT6797 A72 platform-snapshot observer. */

#include <linux/device.h>
#include <linux/err.h>
#include <linux/errno.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/of_platform.h>
#include <linux/platform_device.h>
#include <linux/pstore_ram.h>
#include <linux/string.h>

#include <linux/soc/mediatek/mt6797-a72-platform-state.h>

#include "mt6797-a72-platform-snapshot-observer-internal.h"

#define MT6797_A72_PLATFORM_SNAPSHOT_TAG "GEMINI_A72_PLATFORM_SNAPSHOT_V1"

static bool mt6797_platform_snapshot_checkpoint(void *context,
						unsigned int checkpoint)
{
	return gemini_protected_readback_ledger_checkpoint(checkpoint);
}

static int mt6797_platform_snapshot_read(void *context, struct device *dev,
					 struct mt6797_a72_platform_state *snapshot)
{
	return mt6797_a72_platform_state_snapshot(dev, snapshot);
}

static const struct mt6797_a72_platform_snapshot_observer_ops
mt6797_a72_platform_snapshot_ops = {
	.checkpoint = mt6797_platform_snapshot_checkpoint,
	.snapshot = mt6797_platform_snapshot_read,
};

int mt6797_platform_snapshot_capture(struct device *platform,
				     const struct mt6797_a72_platform_snapshot_observer_ops *ops,
				     void *context,
				     struct mt6797_a72_platform_state *snapshot)
{
	int ret;

	if (!snapshot)
		return -EINVAL;
	memset(snapshot, 0, sizeof(*snapshot));
	if (!platform || !ops || !ops->checkpoint || !ops->snapshot)
		return -EINVAL;
	if (!ops->checkpoint(context, 0))
		return -EIO;

	ret = ops->snapshot(context, platform, snapshot);
	if (ret)
		goto out_clear;
	if (!snapshot->valid) {
		ret = -ENODATA;
		goto out_clear;
	}
	if (!ops->checkpoint(context, 1)) {
		ret = -EIO;
		goto out_clear;
	}

	return 0;

out_clear:
	memset(snapshot, 0, sizeof(*snapshot));
	return ret;
}

static struct device *
mt6797_a72_platform_snapshot_get_device(struct device *dev)
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

static void mt6797_a72_platform_snapshot_log(struct device *dev,
					     const struct mt6797_a72_platform_state *snapshot)
{
	dev_info(dev,
		 MT6797_A72_PLATFORM_SNAPSHOT_TAG
		 " valid=%u spm=%08x/%08x/%08x/%08x"
		 " mp2=%08x/%08x/%08x iso=%08x dcm=%08x"
		 " cci=%08x/%08x/%08x pwrap=%u\n",
		 snapshot->valid, snapshot->spm_pwr_status,
		 snapshot->spm_pwr_status_2nd,
		 snapshot->spm_cpu_pwr_status,
		 snapshot->spm_cpu_pwr_status_2nd,
		 snapshot->spm_mp2_cpusys_pwr_con,
		 snapshot->spm_mp2_cpu0_pwr_con,
		 snapshot->spm_mp2_cpu1_pwr_con,
		 snapshot->spm_cpu_ext_buck_iso, snapshot->mp2_sync_dcm,
		 snapshot->cci_mp2_port_control, snapshot->cci_status_before,
		 snapshot->cci_status_after, snapshot->pwrap_reset_asserted);
	dev_info(dev,
		 MT6797_A72_PLATFORM_SNAPSHOT_TAG
		 " state=complete platform_calls=1 stable_samples=2"
		 " register_observations=26 retained_writes=2 retries=0"
		 " provider_snapshots=0 protected_clock_reads=0"
		 " bigidvfs_reads=0 secure_calls=0 publisher_calls=0"
		 " owner_mutations=0 cpu_requests=0\n");
}

static int mt6797_a72_platform_snapshot_probe(struct platform_device *pdev)
{
	struct mt6797_a72_platform_state snapshot;
	struct device *platform;
	struct device *dev = &pdev->dev;
	int ret;

	platform = mt6797_a72_platform_snapshot_get_device(dev);
	if (IS_ERR(platform))
		return dev_err_probe(dev, PTR_ERR(platform),
				     "platform-state source unavailable\n");

	ret = mt6797_platform_snapshot_capture(platform,
					       &mt6797_a72_platform_snapshot_ops,
					       NULL, &snapshot);
	if (ret)
		dev_err_probe(dev, ret, "platform snapshot failed\n");
	else
		mt6797_a72_platform_snapshot_log(dev, &snapshot);
	put_device(platform);

	return ret;
}

static const struct of_device_id mt6797_a72_platform_snapshot_of_match[] = {
	{ .compatible = "mediatek,mt6797-a72-platform-snapshot-observer" },
	{ }
};
MODULE_DEVICE_TABLE(of, mt6797_a72_platform_snapshot_of_match);

static struct platform_driver mt6797_a72_platform_snapshot_driver = {
	.probe = mt6797_a72_platform_snapshot_probe,
	.driver = {
		.name = "mt6797-a72-platform-snapshot-observer",
		.of_match_table = mt6797_a72_platform_snapshot_of_match,
		.suppress_bind_attrs = true,
	},
};
builtin_platform_driver(mt6797_a72_platform_snapshot_driver);

MODULE_DESCRIPTION("MT6797 A72 candidate-only platform-snapshot observer");
MODULE_LICENSE("GPL");
