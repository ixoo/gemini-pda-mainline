// SPDX-License-Identifier: GPL-2.0-only
/*
 * Read-only MediaTek MT6797 Cortex-A72 platform-state source
 *
 * Copyright (c) 2026 Julien Etienne
 */

#include <linux/bitops.h>
#include <linux/device.h>
#include <linux/io.h>
#include <linux/mfd/syscon.h>
#include <linux/module.h>
#include <linux/mutex.h>
#include <linux/of.h>
#include <linux/platform_device.h>
#include <linux/regmap.h>
#include <linux/reset.h>
#include <linux/soc/mediatek/mt6797-a72-platform-state.h>

#define MT6797_SPM_PWR_STATUS			0x180
#define MT6797_SPM_PWR_STATUS_2ND		0x184
#define MT6797_SPM_CPU_PWR_STATUS		0x188
#define MT6797_SPM_CPU_PWR_STATUS_2ND		0x18c
#define MT6797_SPM_MP2_CPUSYS_PWR_CON		0x218
#define MT6797_SPM_MP2_CPU0_PWR_CON		0x240
#define MT6797_SPM_MP2_CPU1_PWR_CON		0x244
#define MT6797_SPM_CPU_EXT_BUCK_ISO		0x290

#define MT6797_MCUCFG_MP2_SYNC_DCM		0x274
#define MT6797_MCUCFG_MP2_SYNC_DCM_MASK		GENMASK(6, 0)

#define MT6797_CCI_STATUS			0x000c
#define MT6797_CCI_CHANGE_PENDING		BIT(0)
#define MT6797_CCI_MP2_PORT_CONTROL		0x6000
#define MT6797_CCI_MP2_REQUEST_MASK		GENMASK(1, 0)

struct mt6797_a72_platform_state_source {
	struct regmap *spm;
	struct reset_control *pwrap_reset;
	void __iomem *mcucfg;
	void __iomem *cci;
	struct mutex lock; /* Serializes the two-sample transaction. */
};

static int mt6797_state_read_spm(struct mt6797_a72_platform_state_source *source,
				  struct mt6797_a72_platform_state *sample)
{
	int ret;

	ret = regmap_read(source->spm, MT6797_SPM_PWR_STATUS,
			  &sample->spm_pwr_status);
	if (ret)
		return ret;
	ret = regmap_read(source->spm, MT6797_SPM_PWR_STATUS_2ND,
			  &sample->spm_pwr_status_2nd);
	if (ret)
		return ret;
	ret = regmap_read(source->spm, MT6797_SPM_CPU_PWR_STATUS,
			  &sample->spm_cpu_pwr_status);
	if (ret)
		return ret;
	ret = regmap_read(source->spm, MT6797_SPM_CPU_PWR_STATUS_2ND,
			  &sample->spm_cpu_pwr_status_2nd);
	if (ret)
		return ret;
	ret = regmap_read(source->spm, MT6797_SPM_MP2_CPUSYS_PWR_CON,
			  &sample->spm_mp2_cpusys_pwr_con);
	if (ret)
		return ret;
	ret = regmap_read(source->spm, MT6797_SPM_MP2_CPU0_PWR_CON,
			  &sample->spm_mp2_cpu0_pwr_con);
	if (ret)
		return ret;
	ret = regmap_read(source->spm, MT6797_SPM_MP2_CPU1_PWR_CON,
			  &sample->spm_mp2_cpu1_pwr_con);
	if (ret)
		return ret;
	ret = regmap_read(source->spm, MT6797_SPM_CPU_EXT_BUCK_ISO,
			  &sample->spm_cpu_ext_buck_iso);
	if (ret)
		return ret;

	return 0;
}

static int mt6797_state_read_once(struct mt6797_a72_platform_state_source *source,
				   struct mt6797_a72_platform_state *sample)
{
	int reset_state;
	int ret;

	*sample = (struct mt6797_a72_platform_state){};
	ret = mt6797_state_read_spm(source, sample);
	if (ret)
		return ret;

	reset_state = reset_control_status(source->pwrap_reset);
	if (reset_state < 0)
		return reset_state;
	sample->pwrap_reset_asserted = reset_state;

	sample->mp2_sync_dcm = readl(source->mcucfg +
				       MT6797_MCUCFG_MP2_SYNC_DCM);
	sample->cci_status_before = readl(source->cci + MT6797_CCI_STATUS);
	sample->cci_mp2_port_control = readl(source->cci +
					      MT6797_CCI_MP2_PORT_CONTROL);
	sample->cci_status_after = readl(source->cci + MT6797_CCI_STATUS);

	return 0;
}

static bool mt6797_state_moved(const struct mt6797_a72_platform_state *first,
			       const struct mt6797_a72_platform_state *second)
{
	return first->spm_cpu_pwr_status != second->spm_cpu_pwr_status ||
		first->spm_cpu_pwr_status_2nd !=
			second->spm_cpu_pwr_status_2nd ||
		first->spm_mp2_cpusys_pwr_con !=
			second->spm_mp2_cpusys_pwr_con ||
		first->spm_mp2_cpu0_pwr_con != second->spm_mp2_cpu0_pwr_con ||
		first->spm_mp2_cpu1_pwr_con != second->spm_mp2_cpu1_pwr_con ||
		first->spm_cpu_ext_buck_iso != second->spm_cpu_ext_buck_iso ||
		((first->mp2_sync_dcm ^ second->mp2_sync_dcm) &
		 MT6797_MCUCFG_MP2_SYNC_DCM_MASK) ||
		((first->cci_mp2_port_control ^
		  second->cci_mp2_port_control) & MT6797_CCI_MP2_REQUEST_MASK) ||
		first->pwrap_reset_asserted != second->pwrap_reset_asserted;
}

static bool mt6797_state_cci_busy(const struct mt6797_a72_platform_state *sample)
{
	return (sample->cci_status_before | sample->cci_status_after) &
		MT6797_CCI_CHANGE_PENDING;
}

int mt6797_a72_platform_state_snapshot(struct device *dev,
				       struct mt6797_a72_platform_state *snapshot)
{
	struct mt6797_a72_platform_state_source *source;
	struct mt6797_a72_platform_state first;
	struct mt6797_a72_platform_state second;
	int ret;

	if (!snapshot)
		return -EINVAL;
	*snapshot = (struct mt6797_a72_platform_state){};
	if (!dev)
		return -EINVAL;

	source = dev_get_drvdata(dev);
	if (!source)
		return -ENODEV;

	mutex_lock(&source->lock);
	ret = mt6797_state_read_once(source, &first);
	if (ret)
		goto out;
	ret = mt6797_state_read_once(source, &second);
	if (ret)
		goto out;
	if (mt6797_state_cci_busy(&first) ||
	    mt6797_state_cci_busy(&second)) {
		ret = -EBUSY;
		goto out;
	}
	if (mt6797_state_moved(&first, &second)) {
		ret = -EAGAIN;
		goto out;
	}

	*snapshot = second;
	snapshot->valid = true;
out:
	mutex_unlock(&source->lock);
	return ret;
}
EXPORT_SYMBOL_GPL(mt6797_a72_platform_state_snapshot);

static int mt6797_a72_platform_state_probe(struct platform_device *pdev)
{
	struct mt6797_a72_platform_state_source *source;
	struct device *dev = &pdev->dev;

	source = devm_kzalloc(dev, sizeof(*source), GFP_KERNEL);
	if (!source)
		return -ENOMEM;

	source->spm = syscon_regmap_lookup_by_phandle(dev->of_node, "mediatek,spm");
	if (IS_ERR(source->spm))
		return dev_err_probe(dev, PTR_ERR(source->spm),
				     "failed to get SPM syscon\n");

	source->pwrap_reset = devm_reset_control_get_exclusive(dev, "pwrap");
	if (IS_ERR(source->pwrap_reset))
		return dev_err_probe(dev, PTR_ERR(source->pwrap_reset),
				     "failed to get PWRAP reset\n");

	source->mcucfg = devm_platform_ioremap_resource_byname(pdev, "mcucfg");
	if (IS_ERR(source->mcucfg))
		return PTR_ERR(source->mcucfg);
	source->cci = devm_platform_ioremap_resource_byname(pdev, "cci");
	if (IS_ERR(source->cci))
		return PTR_ERR(source->cci);

	mutex_init(&source->lock);
	platform_set_drvdata(pdev, source);
	dev_info(dev, "read-only capture source ready; no lifecycle caller\n");

	return 0;
}

static const struct of_device_id mt6797_a72_platform_state_of_match[] = {
	{ .compatible = "mediatek,mt6797-a72-platform-state" },
	{ }
};
MODULE_DEVICE_TABLE(of, mt6797_a72_platform_state_of_match);

static struct platform_driver mt6797_a72_platform_state_driver = {
	.probe = mt6797_a72_platform_state_probe,
	.driver = {
		.name = "mt6797-a72-platform-state",
		.of_match_table = mt6797_a72_platform_state_of_match,
		.suppress_bind_attrs = true,
	},
};
builtin_platform_driver(mt6797_a72_platform_state_driver);

MODULE_DESCRIPTION("MediaTek MT6797 Cortex-A72 platform-state source");
MODULE_LICENSE("GPL");
