#!/usr/bin/env python3
"""Apply deterministic MT6797 thermal-stage ledger source edits."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one edit anchor, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def copy_template(templates: Path, root: Path, relative: str) -> None:
    source = templates / relative
    target = root / relative
    if target.exists():
        raise SystemExit(f"refusing to overwrite existing source: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def add_core(root: Path, templates: Path) -> None:
    kconfig = root / "fs/pstore/Kconfig"
    makefile = root / "fs/pstore/Makefile"
    replace_once(
        kconfig,
        "config PSTORE_GEMINI_A72_HOTPLUG_LEDGER\n",
        "config PSTORE_GEMINI_MT6797_THERMAL_LEDGER\n"
        '\tbool "Gemini MT6797 thermal-stage record-5 ledger"\n'
        "\tdepends on PSTORE_RAM=y\n"
        "\tdepends on MTK_SOC_THERMAL=y\n"
        "\tselect CRC32\n"
        "\tdefault n\n"
        "\thelp\n"
        "\t  Add an empty-only, alternating two-copy CRC ledger in exact\n"
        "\t  Gemini ramoops dmesg record 5. It records at most 96 bounded\n"
        "\t  thermal-probe operation boundaries and seals on a terminal.\n\n"
        "\t  The owner never clears, repairs, resumes, reopens, or retries a\n"
        "\t  nonempty lane. It adds no CPU request, frequency policy, load,\n"
        "\t  thermal trip, cooling action, storage write, or boot policy.\n\n"
        "config PSTORE_GEMINI_A72_HOTPLUG_LEDGER\n",
    )
    replace_once(
        makefile,
        "obj-$(CONFIG_PSTORE_GEMINI_A72_HOTPLUG_LEDGER) += gemini_a72_hotplug_ledger.o\n",
        "obj-$(CONFIG_PSTORE_GEMINI_MT6797_THERMAL_LEDGER) += gemini_mt6797_thermal_ledger.o\n"
        "obj-$(CONFIG_PSTORE_GEMINI_A72_HOTPLUG_LEDGER) += gemini_a72_hotplug_ledger.o\n",
    )
    for relative in (
        "include/linux/gemini_mt6797_thermal_ledger.h",
        "fs/pstore/gemini_mt6797_thermal_ledger_internal.h",
        "fs/pstore/gemini_mt6797_thermal_ledger.c",
    ):
        copy_template(templates, root, relative)


def add_tests(root: Path, templates: Path) -> None:
    kconfig = root / "fs/pstore/Kconfig"
    makefile = root / "fs/pstore/Makefile"
    replace_once(
        kconfig,
        "config PSTORE_GEMINI_A72_HOTPLUG_LEDGER\n",
        "config PSTORE_GEMINI_MT6797_THERMAL_LEDGER_KUNIT_TEST\n"
        '\tbool "KUnit tests for the Gemini MT6797 thermal-stage ledger"\n'
        "\tdepends on KUNIT=y\n"
        "\tdepends on PSTORE_GEMINI_MT6797_THERMAL_LEDGER=y\n"
        "\tdefault n\n"
        "\thelp\n"
        "\t  Test exact empty ownership, alternating CRC copies, bounds,\n"
        "\t  readback, terminal sealing, and refusal paths with an injected\n"
        "\t  word array. The tests perform no retained-RAM, MMIO, thermal,\n"
        "\t  reset, clock, storage, network, CPU, or device action.\n\n"
        "config PSTORE_GEMINI_A72_HOTPLUG_LEDGER\n",
    )
    replace_once(
        makefile,
        "obj-$(CONFIG_PSTORE_GEMINI_MT6797_THERMAL_LEDGER) += gemini_mt6797_thermal_ledger.o\n",
        "obj-$(CONFIG_PSTORE_GEMINI_MT6797_THERMAL_LEDGER) += gemini_mt6797_thermal_ledger.o\n"
        "obj-$(CONFIG_PSTORE_GEMINI_MT6797_THERMAL_LEDGER_KUNIT_TEST) += gemini_mt6797_thermal_ledger_test.o\n",
    )
    copy_template(
        templates, root, "fs/pstore/gemini_mt6797_thermal_ledger_test.c"
    )


OLD_EXECUTE = r'''static inline int
mtk_thermal_transaction_execute(void *context,
				const struct mtk_thermal_transaction_ops *ops,
				struct mtk_thermal_transaction_state *state,
				unsigned int banks)
{
	unsigned int bank;
	int ret;

	if (!context || !mtk_thermal_transaction_ops_valid(ops) ||
	    !mtk_thermal_transaction_state_is_closed(state) || !banks)
		return -EINVAL;

	ret = ops->enable_auxadc_clock(context);
	if (ret)
		goto fail;
	state->auxadc_clock_enabled = true;

	ret = ops->enable_thermal_clock(context);
	if (ret)
		goto fail;
	state->thermal_clock_enabled = true;

	ret = ops->reset_thermal(context);
	if (ret)
		goto fail;
	state->reset_deasserted = true;

	state->apmixed_configured = true;
	ret = ops->configure_apmixed(context);
	if (ret)
		goto fail;

	ret = ops->wait_for_idle(context);
	if (ret)
		goto fail;

	state->banks_touched = true;
	ops->pause_disable_banks(context);
	state->channel_touched = true;
	ret = ops->clear_auxadc_channel(context);
	if (ret)
		goto fail;

	for (bank = 0; bank < banks; bank++) {
		ret = ops->prepare_bank(context, bank);
		if (ret)
			goto fail;
	}

	ret = ops->commit_auxadc_channel(context);
	if (ret)
		goto fail;

	for (bank = 0; bank < banks; bank++) {
		ret = ops->enable_bank(context, bank);
		if (ret)
			goto fail;
	}

	for (bank = 0; bank < banks; bank++) {
		ret = ops->release_bank(context, bank);
		if (ret)
			goto fail;
	}

	for (bank = 0; bank < banks; bank++) {
		ret = ops->first_sample(context, bank);
		if (ret)
			goto fail;
	}

	state->ready = true;

	return 0;

fail:
	mtk_thermal_transaction_close(context, ops, state);
	return ret;
}
'''


NEW_EXECUTE = r'''static inline int
mtk_thermal_transaction_trace(void *context,
			      const struct mtk_thermal_transaction_ops *ops,
			      u32 operation, u32 phase, u32 index, int result)
{
	int trace_ret;

	if (!ops->trace)
		return result;
	trace_ret = ops->trace(context, operation, phase, index, result);

	return result ? result : trace_ret;
}

static inline int
mtk_thermal_transaction_execute(void *context,
				const struct mtk_thermal_transaction_ops *ops,
				struct mtk_thermal_transaction_state *state,
				unsigned int banks)
{
	const u32 none = GEMINI_MT6797_THERMAL_LEDGER_INDEX_NONE;
	unsigned int bank;
	int ret;

	if (!context || !mtk_thermal_transaction_ops_valid(ops) ||
	    !mtk_thermal_transaction_state_is_closed(state) || !banks)
		return -EINVAL;

	ret = mtk_thermal_transaction_trace(
		context, ops, GEMINI_MT6797_THERMAL_AUXADC_CLOCK_ENABLE,
		GEMINI_MT6797_THERMAL_LEDGER_BEFORE, none, 0);
	if (ret)
		goto fail;
	ret = ops->enable_auxadc_clock(context);
	if (!ret)
		state->auxadc_clock_enabled = true;
	ret = mtk_thermal_transaction_trace(
		context, ops, GEMINI_MT6797_THERMAL_AUXADC_CLOCK_ENABLE,
		GEMINI_MT6797_THERMAL_LEDGER_AFTER, none, ret);
	if (ret)
		goto fail;

	ret = mtk_thermal_transaction_trace(
		context, ops, GEMINI_MT6797_THERMAL_CLOCK_ENABLE,
		GEMINI_MT6797_THERMAL_LEDGER_BEFORE, none, 0);
	if (ret)
		goto fail;
	ret = ops->enable_thermal_clock(context);
	if (!ret)
		state->thermal_clock_enabled = true;
	ret = mtk_thermal_transaction_trace(
		context, ops, GEMINI_MT6797_THERMAL_CLOCK_ENABLE,
		GEMINI_MT6797_THERMAL_LEDGER_AFTER, none, ret);
	if (ret)
		goto fail;

	ret = mtk_thermal_transaction_trace(
		context, ops, GEMINI_MT6797_THERMAL_RESET,
		GEMINI_MT6797_THERMAL_LEDGER_BEFORE, none, 0);
	if (ret)
		goto fail;
	ret = ops->reset_thermal(context);
	if (!ret)
		state->reset_deasserted = true;
	ret = mtk_thermal_transaction_trace(
		context, ops, GEMINI_MT6797_THERMAL_RESET,
		GEMINI_MT6797_THERMAL_LEDGER_AFTER, none, ret);
	if (ret)
		goto fail;

	ret = mtk_thermal_transaction_trace(
		context, ops, GEMINI_MT6797_THERMAL_APMIXED,
		GEMINI_MT6797_THERMAL_LEDGER_BEFORE, none, 0);
	if (ret)
		goto fail;
	state->apmixed_configured = true;
	ret = ops->configure_apmixed(context);
	ret = mtk_thermal_transaction_trace(
		context, ops, GEMINI_MT6797_THERMAL_APMIXED,
		GEMINI_MT6797_THERMAL_LEDGER_AFTER, none, ret);
	if (ret)
		goto fail;

	ret = mtk_thermal_transaction_trace(
		context, ops, GEMINI_MT6797_THERMAL_GLOBAL_IDLE,
		GEMINI_MT6797_THERMAL_LEDGER_BEFORE, none, 0);
	if (ret)
		goto fail;
	ret = ops->wait_for_idle(context);
	ret = mtk_thermal_transaction_trace(
		context, ops, GEMINI_MT6797_THERMAL_GLOBAL_IDLE,
		GEMINI_MT6797_THERMAL_LEDGER_AFTER, none, ret);
	if (ret)
		goto fail;

	ret = mtk_thermal_transaction_trace(
		context, ops, GEMINI_MT6797_THERMAL_PAUSE_BANKS,
		GEMINI_MT6797_THERMAL_LEDGER_BEFORE, none, 0);
	if (ret)
		goto fail;
	state->banks_touched = true;
	ops->pause_disable_banks(context);
	ret = mtk_thermal_transaction_trace(
		context, ops, GEMINI_MT6797_THERMAL_PAUSE_BANKS,
		GEMINI_MT6797_THERMAL_LEDGER_AFTER, none, 0);
	if (ret)
		goto fail;

	ret = mtk_thermal_transaction_trace(
		context, ops, GEMINI_MT6797_THERMAL_CLEAR_CHANNEL,
		GEMINI_MT6797_THERMAL_LEDGER_BEFORE, none, 0);
	if (ret)
		goto fail;
	state->channel_touched = true;
	ret = ops->clear_auxadc_channel(context);
	ret = mtk_thermal_transaction_trace(
		context, ops, GEMINI_MT6797_THERMAL_CLEAR_CHANNEL,
		GEMINI_MT6797_THERMAL_LEDGER_AFTER, none, ret);
	if (ret)
		goto fail;

	for (bank = 0; bank < banks; bank++) {
		ret = mtk_thermal_transaction_trace(
			context, ops, GEMINI_MT6797_THERMAL_PREPARE_BANK,
			GEMINI_MT6797_THERMAL_LEDGER_BEFORE, bank, 0);
		if (ret)
			goto fail;
		ret = ops->prepare_bank(context, bank);
		ret = mtk_thermal_transaction_trace(
			context, ops, GEMINI_MT6797_THERMAL_PREPARE_BANK,
			GEMINI_MT6797_THERMAL_LEDGER_AFTER, bank, ret);
		if (ret)
			goto fail;
	}

	ret = mtk_thermal_transaction_trace(
		context, ops, GEMINI_MT6797_THERMAL_COMMIT_CHANNEL,
		GEMINI_MT6797_THERMAL_LEDGER_BEFORE, none, 0);
	if (ret)
		goto fail;
	ret = ops->commit_auxadc_channel(context);
	ret = mtk_thermal_transaction_trace(
		context, ops, GEMINI_MT6797_THERMAL_COMMIT_CHANNEL,
		GEMINI_MT6797_THERMAL_LEDGER_AFTER, none, ret);
	if (ret)
		goto fail;

	for (bank = 0; bank < banks; bank++) {
		ret = mtk_thermal_transaction_trace(
			context, ops, GEMINI_MT6797_THERMAL_ENABLE_BANK,
			GEMINI_MT6797_THERMAL_LEDGER_BEFORE, bank, 0);
		if (ret)
			goto fail;
		ret = ops->enable_bank(context, bank);
		ret = mtk_thermal_transaction_trace(
			context, ops, GEMINI_MT6797_THERMAL_ENABLE_BANK,
			GEMINI_MT6797_THERMAL_LEDGER_AFTER, bank, ret);
		if (ret)
			goto fail;
	}

	for (bank = 0; bank < banks; bank++) {
		ret = mtk_thermal_transaction_trace(
			context, ops, GEMINI_MT6797_THERMAL_RELEASE_BANK,
			GEMINI_MT6797_THERMAL_LEDGER_BEFORE, bank, 0);
		if (ret)
			goto fail;
		ret = ops->release_bank(context, bank);
		ret = mtk_thermal_transaction_trace(
			context, ops, GEMINI_MT6797_THERMAL_RELEASE_BANK,
			GEMINI_MT6797_THERMAL_LEDGER_AFTER, bank, ret);
		if (ret)
			goto fail;
	}

	for (bank = 0; bank < banks; bank++) {
		ret = mtk_thermal_transaction_trace(
			context, ops, GEMINI_MT6797_THERMAL_FIRST_SAMPLE,
			GEMINI_MT6797_THERMAL_LEDGER_BEFORE, bank, 0);
		if (ret)
			goto fail;
		ret = ops->first_sample(context, bank);
		ret = mtk_thermal_transaction_trace(
			context, ops, GEMINI_MT6797_THERMAL_FIRST_SAMPLE,
			GEMINI_MT6797_THERMAL_LEDGER_AFTER, bank, ret);
		if (ret)
			goto fail;
	}

	state->ready = true;

	return 0;

fail:
	mtk_thermal_transaction_close(context, ops, state);
	return ret;
}
'''


OLD_PROBE = r'''static int mtk_thermal_probe(struct platform_device *pdev)
{
	const struct mtk_thermal_transaction_ops *ops;
	struct device_node *np = pdev->dev.of_node;
	struct thermal_zone_device *tzdev;
	struct mtk_thermal *mt;
	int ctrl_id, i, ret;

	mt = devm_kzalloc(&pdev->dev, sizeof(*mt), GFP_KERNEL);
	if (!mt)
		return -ENOMEM;

	mt->conf = of_device_get_match_data(&pdev->dev);
	if (!mt->conf)
		return -EINVAL;
	ops = &mt6797_thermal_transaction_ops;

	ret = mtk_thermal_get_calibration_data(&pdev->dev, mt);
	if (ret)
		return ret;

	mt->thermal_base = devm_platform_get_and_ioremap_resource(pdev, 0, NULL);
	if (IS_ERR(mt->thermal_base))
		return PTR_ERR(mt->thermal_base);

	mutex_init(&mt->lock);
	mt->dev = &pdev->dev;
	platform_set_drvdata(pdev, mt);
	for (i = 0; i < mt->conf->num_banks; i++) {
		mt->banks[i].id = i;
		mt->banks[i].mt = mt;
	}

	ret = mtk_thermal_map_phandle(&pdev->dev, np, "mediatek,auxadc",
				      &mt->auxadc_base,
				      &mt->auxadc_phys_base);
	if (ret) {
		dev_err(&pdev->dev, "cannot map AUXADC: %d\n", ret);
		return ret;
	}

	ret = mtk_thermal_map_phandle(&pdev->dev, np, "mediatek,apmixedsys",
				      &mt->apmixed_base,
				      &mt->apmixed_phys_base);
	if (ret) {
		dev_err(&pdev->dev, "cannot map APMIXEDSYS: %d\n", ret);
		return ret;
	}

	if (mt->conf->version == MTK_THERMAL_V4) {
		mt->rst = devm_reset_control_get_exclusive(&pdev->dev, NULL);
		if (IS_ERR(mt->rst))
			return dev_err_probe(&pdev->dev, PTR_ERR(mt->rst),
					     "cannot acquire thermal reset\n");

		mt->clk_auxadc = devm_clk_get(&pdev->dev, "auxadc");
		if (IS_ERR(mt->clk_auxadc))
			return dev_err_probe(&pdev->dev,
					     PTR_ERR(mt->clk_auxadc),
					     "cannot acquire AUXADC clock\n");

		mt->clk_peri_therm = devm_clk_get(&pdev->dev, "therm");
		if (IS_ERR(mt->clk_peri_therm))
			return dev_err_probe(&pdev->dev,
					     PTR_ERR(mt->clk_peri_therm),
					     "cannot acquire thermal clock\n");

		mt->raw_to_mcelsius = raw_to_mcelsius_v4;
		ret = mtk_thermal_transaction_execute(mt, ops, &mt->transaction,
						      mt->conf->num_banks);
		if (ret)
			return dev_err_probe(&pdev->dev, ret,
					     "MT6797 transaction failed\n");
	} else {
		ret = device_reset_optional(&pdev->dev);
		if (ret)
			return ret;

		mt->clk_auxadc = devm_clk_get_enabled(&pdev->dev, "auxadc");
		if (IS_ERR(mt->clk_auxadc))
			return dev_err_probe(&pdev->dev,
					     PTR_ERR(mt->clk_auxadc),
					     "cannot enable AUXADC clock\n");

		mt->clk_peri_therm = devm_clk_get_enabled(&pdev->dev, "therm");
		if (IS_ERR(mt->clk_peri_therm))
			return dev_err_probe(&pdev->dev,
					     PTR_ERR(mt->clk_peri_therm),
					     "cannot enable thermal clock\n");

		mtk_thermal_turn_on_buffer(mt, mt->apmixed_base);
		if (mt->conf->version != MTK_THERMAL_V1)
			mtk_thermal_release_periodic_ts(mt, mt->auxadc_base);

		if (mt->conf->version == MTK_THERMAL_V1)
			mt->raw_to_mcelsius = raw_to_mcelsius_v1;
		else if (mt->conf->version == MTK_THERMAL_V2)
			mt->raw_to_mcelsius = raw_to_mcelsius_v2;
		else
			mt->raw_to_mcelsius = raw_to_mcelsius_v3;

		for (ctrl_id = 0; ctrl_id < mt->conf->num_controller;
		     ctrl_id++)
			for (i = 0; i < mt->conf->num_banks; i++)
				mtk_thermal_init_bank(mt, i,
						      mt->apmixed_phys_base,
						      mt->auxadc_phys_base,
						      ctrl_id);
	}

	tzdev = devm_thermal_of_zone_register(&pdev->dev, 0, mt,
					      &mtk_thermal_ops);
	if (IS_ERR(tzdev)) {
		ret = PTR_ERR(tzdev);
		if (mt->conf->version == MTK_THERMAL_V4)
			mtk_thermal_transaction_close(mt, ops, &mt->transaction);
		return ret;
	}

	ret = devm_thermal_add_hwmon_sysfs(&pdev->dev, tzdev);
	if (ret)
		dev_warn(&pdev->dev, "error in thermal_add_hwmon_sysfs\n");

	return 0;
}
'''


NEW_PROBE = r'''static int mt6797_thermal_probe_trace(u32 operation, u32 phase,
				       int result, u32 terminal)
{
	int trace_ret;

	trace_ret = gemini_mt6797_thermal_ledger_checkpoint(
		operation, phase, GEMINI_MT6797_THERMAL_LEDGER_INDEX_NONE,
		result, terminal);

	return result ? result : trace_ret;
}

static int mtk_thermal_probe(struct platform_device *pdev)
{
	const struct mtk_thermal_transaction_ops *ops;
	struct device_node *np = pdev->dev.of_node;
	struct thermal_zone_device *tzdev;
	struct mtk_thermal *mt;
	bool is_v4;
	bool traced;
	int ctrl_id, i, ret;

	mt = devm_kzalloc(&pdev->dev, sizeof(*mt), GFP_KERNEL);
	if (!mt)
		return -ENOMEM;

	mt->conf = of_device_get_match_data(&pdev->dev);
	if (!mt->conf)
		return -EINVAL;
	ops = &mt6797_thermal_transaction_ops;
	is_v4 = mt->conf->version == MTK_THERMAL_V4;
	traced = IS_ENABLED(CONFIG_PSTORE_GEMINI_MT6797_THERMAL_LEDGER) &&
		is_v4;
	if (traced) {
		ret = gemini_mt6797_thermal_ledger_begin();
		if (ret)
			return ret;
		ret = mt6797_thermal_probe_trace(
			GEMINI_MT6797_THERMAL_PROBE,
			GEMINI_MT6797_THERMAL_LEDGER_AFTER, 0, 0);
		if (ret)
			return ret;
		ret = mt6797_thermal_probe_trace(
			GEMINI_MT6797_THERMAL_CALIBRATION,
			GEMINI_MT6797_THERMAL_LEDGER_BEFORE, 0, 0);
		if (ret)
			return ret;
	}

	ret = mtk_thermal_get_calibration_data(&pdev->dev, mt);
	if (traced)
		ret = mt6797_thermal_probe_trace(
			GEMINI_MT6797_THERMAL_CALIBRATION,
			GEMINI_MT6797_THERMAL_LEDGER_AFTER, ret, 0);
	if (ret)
		goto fail_calibration;

	if (traced) {
		ret = mt6797_thermal_probe_trace(
			GEMINI_MT6797_THERMAL_RESOURCE,
			GEMINI_MT6797_THERMAL_LEDGER_BEFORE, 0, 0);
		if (ret)
			goto fail_resource;
	}
	mt->thermal_base = devm_platform_get_and_ioremap_resource(pdev, 0, NULL);
	ret = IS_ERR(mt->thermal_base) ? PTR_ERR(mt->thermal_base) : 0;
	if (traced)
		ret = mt6797_thermal_probe_trace(
			GEMINI_MT6797_THERMAL_RESOURCE,
			GEMINI_MT6797_THERMAL_LEDGER_AFTER, ret, 0);
	if (ret)
		goto fail_resource;

	mutex_init(&mt->lock);
	mt->dev = &pdev->dev;
	platform_set_drvdata(pdev, mt);
	for (i = 0; i < mt->conf->num_banks; i++) {
		mt->banks[i].id = i;
		mt->banks[i].mt = mt;
	}

	if (traced) {
		ret = mt6797_thermal_probe_trace(
			GEMINI_MT6797_THERMAL_AUXADC_MAP,
			GEMINI_MT6797_THERMAL_LEDGER_BEFORE, 0, 0);
		if (ret)
			goto fail_auxadc_map;
	}
	ret = mtk_thermal_map_phandle(&pdev->dev, np, "mediatek,auxadc",
				      &mt->auxadc_base,
				      &mt->auxadc_phys_base);
	if (traced)
		ret = mt6797_thermal_probe_trace(
			GEMINI_MT6797_THERMAL_AUXADC_MAP,
			GEMINI_MT6797_THERMAL_LEDGER_AFTER, ret, 0);
	if (ret) {
		dev_err(&pdev->dev, "cannot map AUXADC: %d\n", ret);
		goto fail_auxadc_map;
	}

	if (traced) {
		ret = mt6797_thermal_probe_trace(
			GEMINI_MT6797_THERMAL_APMIXED_MAP,
			GEMINI_MT6797_THERMAL_LEDGER_BEFORE, 0, 0);
		if (ret)
			goto fail_apmixed_map;
	}
	ret = mtk_thermal_map_phandle(&pdev->dev, np, "mediatek,apmixedsys",
				      &mt->apmixed_base,
				      &mt->apmixed_phys_base);
	if (traced)
		ret = mt6797_thermal_probe_trace(
			GEMINI_MT6797_THERMAL_APMIXED_MAP,
			GEMINI_MT6797_THERMAL_LEDGER_AFTER, ret, 0);
	if (ret) {
		dev_err(&pdev->dev, "cannot map APMIXEDSYS: %d\n", ret);
		goto fail_apmixed_map;
	}

	if (is_v4) {
		ret = mt6797_thermal_probe_trace(
			GEMINI_MT6797_THERMAL_RESET_ACQUIRE,
			GEMINI_MT6797_THERMAL_LEDGER_BEFORE, 0, 0);
		if (ret)
			goto fail_reset_acquire;
		mt->rst = devm_reset_control_get_exclusive(&pdev->dev, NULL);
		ret = IS_ERR(mt->rst) ? PTR_ERR(mt->rst) : 0;
		ret = mt6797_thermal_probe_trace(
			GEMINI_MT6797_THERMAL_RESET_ACQUIRE,
			GEMINI_MT6797_THERMAL_LEDGER_AFTER, ret, 0);
		if (ret) {
			ret = dev_err_probe(&pdev->dev, ret,
					    "cannot acquire thermal reset\n");
			goto fail_reset_acquire;
		}

		ret = mt6797_thermal_probe_trace(
			GEMINI_MT6797_THERMAL_AUXADC_CLOCK_ACQUIRE,
			GEMINI_MT6797_THERMAL_LEDGER_BEFORE, 0, 0);
		if (ret)
			goto fail_auxadc_clock_acquire;
		mt->clk_auxadc = devm_clk_get(&pdev->dev, "auxadc");
		ret = IS_ERR(mt->clk_auxadc) ? PTR_ERR(mt->clk_auxadc) : 0;
		ret = mt6797_thermal_probe_trace(
			GEMINI_MT6797_THERMAL_AUXADC_CLOCK_ACQUIRE,
			GEMINI_MT6797_THERMAL_LEDGER_AFTER, ret, 0);
		if (ret) {
			ret = dev_err_probe(&pdev->dev, ret,
					    "cannot acquire AUXADC clock\n");
			goto fail_auxadc_clock_acquire;
		}

		ret = mt6797_thermal_probe_trace(
			GEMINI_MT6797_THERMAL_CLOCK_ACQUIRE,
			GEMINI_MT6797_THERMAL_LEDGER_BEFORE, 0, 0);
		if (ret)
			goto fail_thermal_clock_acquire;
		mt->clk_peri_therm = devm_clk_get(&pdev->dev, "therm");
		ret = IS_ERR(mt->clk_peri_therm) ?
			PTR_ERR(mt->clk_peri_therm) : 0;
		ret = mt6797_thermal_probe_trace(
			GEMINI_MT6797_THERMAL_CLOCK_ACQUIRE,
			GEMINI_MT6797_THERMAL_LEDGER_AFTER, ret, 0);
		if (ret) {
			ret = dev_err_probe(&pdev->dev, ret,
					    "cannot acquire thermal clock\n");
			goto fail_thermal_clock_acquire;
		}

		mt->raw_to_mcelsius = raw_to_mcelsius_v4;
		ret = mt6797_thermal_probe_trace(
			GEMINI_MT6797_THERMAL_TRANSACTION,
			GEMINI_MT6797_THERMAL_LEDGER_BEFORE, 0, 0);
		if (ret)
			goto fail_transaction;
		ret = mtk_thermal_transaction_execute(mt, ops, &mt->transaction,
						      mt->conf->num_banks);
		ret = mt6797_thermal_probe_trace(
			GEMINI_MT6797_THERMAL_TRANSACTION,
			GEMINI_MT6797_THERMAL_LEDGER_AFTER, ret, 0);
		if (ret) {
			ret = dev_err_probe(&pdev->dev, ret,
					    "MT6797 transaction failed\n");
			goto fail_transaction;
		}
	} else {
		ret = device_reset_optional(&pdev->dev);
		if (ret)
			return ret;

		mt->clk_auxadc = devm_clk_get_enabled(&pdev->dev, "auxadc");
		if (IS_ERR(mt->clk_auxadc))
			return dev_err_probe(&pdev->dev,
					     PTR_ERR(mt->clk_auxadc),
					     "cannot enable AUXADC clock\n");

		mt->clk_peri_therm = devm_clk_get_enabled(&pdev->dev, "therm");
		if (IS_ERR(mt->clk_peri_therm))
			return dev_err_probe(&pdev->dev,
					     PTR_ERR(mt->clk_peri_therm),
					     "cannot enable thermal clock\n");

		mtk_thermal_turn_on_buffer(mt, mt->apmixed_base);
		if (mt->conf->version != MTK_THERMAL_V1)
			mtk_thermal_release_periodic_ts(mt, mt->auxadc_base);

		if (mt->conf->version == MTK_THERMAL_V1)
			mt->raw_to_mcelsius = raw_to_mcelsius_v1;
		else if (mt->conf->version == MTK_THERMAL_V2)
			mt->raw_to_mcelsius = raw_to_mcelsius_v2;
		else
			mt->raw_to_mcelsius = raw_to_mcelsius_v3;

		for (ctrl_id = 0; ctrl_id < mt->conf->num_controller;
		     ctrl_id++)
			for (i = 0; i < mt->conf->num_banks; i++)
				mtk_thermal_init_bank(mt, i,
						      mt->apmixed_phys_base,
						      mt->auxadc_phys_base,
						      ctrl_id);
	}

	if (traced) {
		ret = mt6797_thermal_probe_trace(
			GEMINI_MT6797_THERMAL_ZONE_REGISTER,
			GEMINI_MT6797_THERMAL_LEDGER_BEFORE, 0, 0);
		if (ret)
			goto fail_zone;
	}
	tzdev = devm_thermal_of_zone_register(&pdev->dev, 0, mt,
					      &mtk_thermal_ops);
	ret = IS_ERR(tzdev) ? PTR_ERR(tzdev) : 0;
	if (traced)
		ret = mt6797_thermal_probe_trace(
			GEMINI_MT6797_THERMAL_ZONE_REGISTER,
			GEMINI_MT6797_THERMAL_LEDGER_AFTER, ret, 0);
	if (ret)
		goto fail_zone;

	ret = devm_thermal_add_hwmon_sysfs(&pdev->dev, tzdev);
	if (ret)
		dev_warn(&pdev->dev, "error in thermal_add_hwmon_sysfs\n");

	if (traced) {
		ret = mt6797_thermal_probe_trace(
			GEMINI_MT6797_THERMAL_PROBE_COMPLETE,
			GEMINI_MT6797_THERMAL_LEDGER_TERMINAL, 0,
			GEMINI_MT6797_THERMAL_LEDGER_SUCCESS);
		if (ret) {
			mtk_thermal_transaction_close(mt, ops, &mt->transaction);
			return ret;
		}
	}

	return 0;

fail_zone:
	if (traced)
		mt6797_thermal_probe_trace(
			GEMINI_MT6797_THERMAL_ZONE_REGISTER,
			GEMINI_MT6797_THERMAL_LEDGER_TERMINAL, ret,
			GEMINI_MT6797_THERMAL_LEDGER_FAILURE);
	if (is_v4)
		mtk_thermal_transaction_close(mt, ops, &mt->transaction);
	return ret;
fail_transaction:
	mt6797_thermal_probe_trace(
		GEMINI_MT6797_THERMAL_TRANSACTION,
		GEMINI_MT6797_THERMAL_LEDGER_TERMINAL, ret,
		GEMINI_MT6797_THERMAL_LEDGER_FAILURE);
	return ret;
fail_thermal_clock_acquire:
	mt6797_thermal_probe_trace(
		GEMINI_MT6797_THERMAL_CLOCK_ACQUIRE,
		GEMINI_MT6797_THERMAL_LEDGER_TERMINAL, ret,
		GEMINI_MT6797_THERMAL_LEDGER_FAILURE);
	return ret;
fail_auxadc_clock_acquire:
	mt6797_thermal_probe_trace(
		GEMINI_MT6797_THERMAL_AUXADC_CLOCK_ACQUIRE,
		GEMINI_MT6797_THERMAL_LEDGER_TERMINAL, ret,
		GEMINI_MT6797_THERMAL_LEDGER_FAILURE);
	return ret;
fail_reset_acquire:
	mt6797_thermal_probe_trace(
		GEMINI_MT6797_THERMAL_RESET_ACQUIRE,
		GEMINI_MT6797_THERMAL_LEDGER_TERMINAL, ret,
		GEMINI_MT6797_THERMAL_LEDGER_FAILURE);
	return ret;
fail_apmixed_map:
	if (traced)
		mt6797_thermal_probe_trace(
			GEMINI_MT6797_THERMAL_APMIXED_MAP,
			GEMINI_MT6797_THERMAL_LEDGER_TERMINAL, ret,
			GEMINI_MT6797_THERMAL_LEDGER_FAILURE);
	return ret;
fail_auxadc_map:
	if (traced)
		mt6797_thermal_probe_trace(
			GEMINI_MT6797_THERMAL_AUXADC_MAP,
			GEMINI_MT6797_THERMAL_LEDGER_TERMINAL, ret,
			GEMINI_MT6797_THERMAL_LEDGER_FAILURE);
	return ret;
fail_resource:
	if (traced)
		mt6797_thermal_probe_trace(
			GEMINI_MT6797_THERMAL_RESOURCE,
			GEMINI_MT6797_THERMAL_LEDGER_TERMINAL, ret,
			GEMINI_MT6797_THERMAL_LEDGER_FAILURE);
	return ret;
fail_calibration:
	if (traced)
		mt6797_thermal_probe_trace(
			GEMINI_MT6797_THERMAL_CALIBRATION,
			GEMINI_MT6797_THERMAL_LEDGER_TERMINAL, ret,
			GEMINI_MT6797_THERMAL_LEDGER_FAILURE);
	return ret;
}
'''


def instrument_transaction(root: Path) -> None:
    header = root / "drivers/thermal/mediatek/auxadc_thermal_internal.h"
    source = root / "drivers/thermal/mediatek/auxadc_thermal.c"
    test = root / "drivers/thermal/mediatek/mt6797_auxadc_transaction_test.c"

    replace_once(
        header,
        "#include <linux/errno.h>\n#include <linux/types.h>\n",
        "#include <linux/errno.h>\n"
        "#include <linux/gemini_mt6797_thermal_ledger.h>\n"
        "#include <linux/types.h>\n",
    )
    replace_once(
        header,
        "\tint (*first_sample)(void *context, unsigned int bank);\n};\n",
        "\tint (*first_sample)(void *context, unsigned int bank);\n"
        "\tint (*trace)(void *context, u32 operation, u32 phase, u32 index,\n"
        "\t\t     int result);\n};\n",
    )
    replace_once(header, OLD_EXECUTE, NEW_EXECUTE)

    replace_once(
        source,
        "static const struct mtk_thermal_transaction_ops\n"
        "mt6797_thermal_transaction_ops = {\n",
        "#ifdef CONFIG_PSTORE_GEMINI_MT6797_THERMAL_LEDGER\n"
        "static int mt6797_thermal_trace(void *context, u32 operation,\n"
        "\t\t\t\tu32 phase, u32 index, int result)\n"
        "{\n"
        "\t(void)context;\n\n"
        "\treturn gemini_mt6797_thermal_ledger_checkpoint(\n"
        "\t\toperation, phase, index, result, 0);\n"
        "}\n"
        "#endif\n\n"
        "static const struct mtk_thermal_transaction_ops\n"
        "mt6797_thermal_transaction_ops = {\n",
    )
    replace_once(
        source,
        "\t.first_sample = mt6797_thermal_first_sample,\n};\n",
        "\t.first_sample = mt6797_thermal_first_sample,\n"
        "#ifdef CONFIG_PSTORE_GEMINI_MT6797_THERMAL_LEDGER\n"
        "\t.trace = mt6797_thermal_trace,\n"
        "#endif\n"
        "};\n",
    )
    replace_once(source, OLD_PROBE, NEW_PROBE)

    replace_once(
        test,
        "struct mt6797_test_context {\n"
        "\tstruct mt6797_test_event events[64];\n"
        "\tunsigned int event_count;\n"
        "\tint fallible_count;\n"
        "\tint fail_at;\n"
        "};\n",
        "struct mt6797_test_trace_event {\n"
        "\tu32 operation;\n"
        "\tu32 phase;\n"
        "\tu32 index;\n"
        "\tint result;\n"
        "};\n\n"
        "struct mt6797_test_context {\n"
        "\tstruct mt6797_test_event events[64];\n"
        "\tstruct mt6797_test_trace_event trace_events[64];\n"
        "\tunsigned int event_count;\n"
        "\tunsigned int trace_count;\n"
        "\tint fallible_count;\n"
        "\tint fail_at;\n"
        "\tint trace_fail_at;\n"
        "};\n",
    )
    replace_once(
        test,
        "static const struct mtk_thermal_transaction_ops mt6797_test_ops = {\n",
        "static int mt6797_test_trace(void *data, u32 operation, u32 phase,\n"
        "\t\t\t      u32 index, int result)\n"
        "{\n"
        "\tstruct mt6797_test_context *context = data;\n"
        "\tunsigned int ordinal = context->trace_count++;\n\n"
        "\tcontext->trace_events[ordinal].operation = operation;\n"
        "\tcontext->trace_events[ordinal].phase = phase;\n"
        "\tcontext->trace_events[ordinal].index = index;\n"
        "\tcontext->trace_events[ordinal].result = result;\n\n"
        "\treturn ordinal == context->trace_fail_at ? -ECANCELED : 0;\n"
        "}\n\n"
        "static const struct mtk_thermal_transaction_ops mt6797_test_ops = {\n",
    )
    trace_tests = r'''static void
mt6797_test_expect_trace(struct kunit *test,
			  const struct mt6797_test_context *context,
			  unsigned int ordinal, u32 operation, u32 phase,
			  u32 index, int result)
{
	KUNIT_ASSERT_LT(test, ordinal, context->trace_count);
	KUNIT_EXPECT_EQ(test, context->trace_events[ordinal].operation,
			operation);
	KUNIT_EXPECT_EQ(test, context->trace_events[ordinal].phase, phase);
	KUNIT_EXPECT_EQ(test, context->trace_events[ordinal].index, index);
	KUNIT_EXPECT_EQ(test, context->trace_events[ordinal].result, result);
}

static void
mt6797_test_expect_trace_pair(struct kunit *test,
			       const struct mt6797_test_context *context,
			       unsigned int *ordinal, u32 operation, u32 index)
{
	mt6797_test_expect_trace(
		test, context, (*ordinal)++, operation,
		GEMINI_MT6797_THERMAL_LEDGER_BEFORE, index, 0);
	mt6797_test_expect_trace(
		test, context, (*ordinal)++, operation,
		GEMINI_MT6797_THERMAL_LEDGER_AFTER, index, 0);
}

static void mt6797_transaction_trace_success_order(struct kunit *test)
{
	struct mtk_thermal_transaction_ops ops = mt6797_test_ops;
	struct mtk_thermal_transaction_state state = {};
	struct mt6797_test_context context = {
		.fail_at = -1,
		.trace_fail_at = -1,
	};
	const u32 none = GEMINI_MT6797_THERMAL_LEDGER_INDEX_NONE;
	unsigned int ordinal = 0;
	unsigned int bank;
	int ret;

	ops.trace = mt6797_test_trace;
	ret = mtk_thermal_transaction_execute(&context, &ops, &state,
					      MT6797_TEST_BANKS);
	KUNIT_ASSERT_EQ(test, ret, 0);

	mt6797_test_expect_trace_pair(test, &context, &ordinal,
		GEMINI_MT6797_THERMAL_AUXADC_CLOCK_ENABLE, none);
	mt6797_test_expect_trace_pair(test, &context, &ordinal,
		GEMINI_MT6797_THERMAL_CLOCK_ENABLE, none);
	mt6797_test_expect_trace_pair(test, &context, &ordinal,
		GEMINI_MT6797_THERMAL_RESET, none);
	mt6797_test_expect_trace_pair(test, &context, &ordinal,
		GEMINI_MT6797_THERMAL_APMIXED, none);
	mt6797_test_expect_trace_pair(test, &context, &ordinal,
		GEMINI_MT6797_THERMAL_GLOBAL_IDLE, none);
	mt6797_test_expect_trace_pair(test, &context, &ordinal,
		GEMINI_MT6797_THERMAL_PAUSE_BANKS, none);
	mt6797_test_expect_trace_pair(test, &context, &ordinal,
		GEMINI_MT6797_THERMAL_CLEAR_CHANNEL, none);
	for (bank = 0; bank < MT6797_TEST_BANKS; bank++)
		mt6797_test_expect_trace_pair(test, &context, &ordinal,
			GEMINI_MT6797_THERMAL_PREPARE_BANK, bank);
	mt6797_test_expect_trace_pair(test, &context, &ordinal,
		GEMINI_MT6797_THERMAL_COMMIT_CHANNEL, none);
	for (bank = 0; bank < MT6797_TEST_BANKS; bank++)
		mt6797_test_expect_trace_pair(test, &context, &ordinal,
			GEMINI_MT6797_THERMAL_ENABLE_BANK, bank);
	for (bank = 0; bank < MT6797_TEST_BANKS; bank++)
		mt6797_test_expect_trace_pair(test, &context, &ordinal,
			GEMINI_MT6797_THERMAL_RELEASE_BANK, bank);
	for (bank = 0; bank < MT6797_TEST_BANKS; bank++)
		mt6797_test_expect_trace_pair(test, &context, &ordinal,
			GEMINI_MT6797_THERMAL_FIRST_SAMPLE, bank);
	KUNIT_EXPECT_EQ(test, context.trace_count, ordinal);
	KUNIT_EXPECT_EQ(test, ordinal, 64U);
}

static void mt6797_transaction_trace_records_failure(struct kunit *test)
{
	struct mtk_thermal_transaction_ops ops = mt6797_test_ops;
	struct mtk_thermal_transaction_state state = {};
	struct mt6797_test_context context = {
		.fail_at = 4,
		.trace_fail_at = -1,
	};
	int ret;

	ops.trace = mt6797_test_trace;
	ret = mtk_thermal_transaction_execute(&context, &ops, &state,
					      MT6797_TEST_BANKS);
	KUNIT_ASSERT_EQ(test, ret, -EIO);
	KUNIT_EXPECT_EQ(test, context.trace_count, 10U);
	mt6797_test_expect_trace(
		test, &context, 9, GEMINI_MT6797_THERMAL_GLOBAL_IDLE,
		GEMINI_MT6797_THERMAL_LEDGER_AFTER,
		GEMINI_MT6797_THERMAL_LEDGER_INDEX_NONE, -EIO);
	KUNIT_EXPECT_TRUE(test, mtk_thermal_transaction_state_is_closed(&state));
}

static void mt6797_transaction_trace_fails_before_effect(struct kunit *test)
{
	struct mtk_thermal_transaction_ops ops = mt6797_test_ops;
	struct mtk_thermal_transaction_state state = {};
	struct mt6797_test_context context = {
		.fail_at = -1,
		.trace_fail_at = 2,
	};
	int ret;

	ops.trace = mt6797_test_trace;
	ret = mtk_thermal_transaction_execute(&context, &ops, &state,
					      MT6797_TEST_BANKS);
	KUNIT_ASSERT_EQ(test, ret, -ECANCELED);
	KUNIT_EXPECT_EQ(test, context.trace_count, 3U);
	KUNIT_EXPECT_EQ(test, context.event_count, 2U);
	mt6797_test_expect_event(test, &context, 0,
				  MT6797_TEST_AUXADC_CLOCK_ON, -1);
	mt6797_test_expect_event(test, &context, 1,
				  MT6797_TEST_AUXADC_CLOCK_OFF, -1);
	mt6797_test_expect_trace(
		test, &context, 2, GEMINI_MT6797_THERMAL_CLOCK_ENABLE,
		GEMINI_MT6797_THERMAL_LEDGER_BEFORE,
		GEMINI_MT6797_THERMAL_LEDGER_INDEX_NONE, 0);
	KUNIT_EXPECT_TRUE(test, mtk_thermal_transaction_state_is_closed(&state));
}

'''
    replace_once(
        test,
        "static struct kunit_case mt6797_thermal_transaction_cases[] = {\n",
        trace_tests
        + "static struct kunit_case mt6797_thermal_transaction_cases[] = {\n",
    )
    replace_once(
        test,
        "\tKUNIT_CASE(mt6797_transaction_first_sample_gate),\n",
        "\tKUNIT_CASE(mt6797_transaction_first_sample_gate),\n"
        "\tKUNIT_CASE(mt6797_transaction_trace_success_order),\n"
        "\tKUNIT_CASE(mt6797_transaction_trace_records_failure),\n"
        "\tKUNIT_CASE(mt6797_transaction_trace_fails_before_effect),\n",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--templates", type=Path, required=True)
    parser.add_argument(
        "--phase", choices=("core", "tests", "instrumentation"), required=True
    )
    args = parser.parse_args()
    if args.phase == "core":
        add_core(args.source_root, args.templates)
    elif args.phase == "tests":
        add_tests(args.source_root, args.templates)
    else:
        instrument_transaction(args.source_root)


if __name__ == "__main__":
    main()
