#!/usr/bin/env python3
"""Apply deterministic MT6797 thermal transaction production and KUnit edits."""

from __future__ import annotations

import argparse
from pathlib import Path
from textwrap import dedent


THERMAL_C = Path("drivers/thermal/mediatek/auxadc_thermal.c")
INTERNAL_H = Path("drivers/thermal/mediatek/auxadc_thermal_internal.h")
KCONFIG = Path("drivers/thermal/mediatek/Kconfig")
MAKEFILE = Path("drivers/thermal/mediatek/Makefile")
TEST_C = Path("drivers/thermal/mediatek/mt6797_auxadc_transaction_test.c")


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one edit anchor, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def replace_region(path: Path, start: str, end: str, replacement: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(start) != 1 or text.count(end) != 1:
        raise SystemExit(f"{path}: region anchors are not unique")
    first = text.index(start)
    last = text.index(end, first)
    path.write_text(text[:first] + replacement + text[last:], encoding="utf-8")


def write_new(path: Path, content: str) -> None:
    if path.exists():
        raise SystemExit(f"refusing to overwrite existing path: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def transaction_header() -> str:
    return dedent("""\

    struct mtk_thermal_transaction_state {
    \tbool auxadc_clock_enabled;
    \tbool thermal_clock_enabled;
    \tbool reset_deasserted;
    \tbool apmixed_configured;
    \tbool banks_touched;
    \tbool channel_touched;
    \tbool ready;
    };

    struct mtk_thermal_transaction_ops {
    \tint (*enable_auxadc_clock)(void *context);
    \tvoid (*disable_auxadc_clock)(void *context);
    \tint (*enable_thermal_clock)(void *context);
    \tvoid (*disable_thermal_clock)(void *context);
    \tint (*reset_thermal)(void *context);
    \tvoid (*assert_thermal_reset)(void *context);
    \tint (*configure_apmixed)(void *context);
    \tvoid (*restore_apmixed)(void *context);
    \tint (*wait_for_idle)(void *context);
    \tvoid (*pause_disable_banks)(void *context);
    \tint (*clear_auxadc_channel)(void *context);
    \tvoid (*disable_auxadc_channel)(void *context);
    \tint (*prepare_bank)(void *context, unsigned int bank);
    \tint (*commit_auxadc_channel)(void *context);
    \tint (*enable_bank)(void *context, unsigned int bank);
    \tint (*release_bank)(void *context, unsigned int bank);
    \tint (*first_sample)(void *context, unsigned int bank);
    };

    static inline bool
    mtk_thermal_transaction_state_is_closed(
    \tconst struct mtk_thermal_transaction_state *state)
    {
    \treturn state && !state->auxadc_clock_enabled &&
    \t\t!state->thermal_clock_enabled && !state->reset_deasserted &&
    \t\t!state->apmixed_configured && !state->banks_touched &&
    \t\t!state->channel_touched && !state->ready;
    }

    static inline u32 mtk_thermal_mt6797_apmixed_value(u32 value)
    {
    \treturn value & ~GENMASK(5, 4);
    }

    static inline bool mtk_thermal_mt6797_ahb_idle(u32 value)
    {
    \treturn !(value >> 16);
    }

    static inline bool mtk_thermal_mt6797_auxadc_idle(u32 value)
    {
    \treturn !(value & BIT(0));
    }

    static inline bool
    mtk_thermal_mt6797_first_sample_valid(u32 raw, int temperature)
    {
    \treturn (raw & GENMASK(11, 0)) && temperature >= -20000 &&
    \t\ttemperature <= 150000;
    }

    static inline void
    mtk_thermal_transaction_close(
    \tvoid *context, const struct mtk_thermal_transaction_ops *ops,
    \tstruct mtk_thermal_transaction_state *state)
    {
    \tif (!context || !ops || !state)
    \t\treturn;

    \tif (state->banks_touched)
    \t\tops->pause_disable_banks(context);
    \tif (state->channel_touched)
    \t\tops->disable_auxadc_channel(context);
    \tif (state->apmixed_configured)
    \t\tops->restore_apmixed(context);
    \tif (state->reset_deasserted)
    \t\tops->assert_thermal_reset(context);
    \tif (state->thermal_clock_enabled)
    \t\tops->disable_thermal_clock(context);
    \tif (state->auxadc_clock_enabled)
    \t\tops->disable_auxadc_clock(context);

    \tstate->auxadc_clock_enabled = false;
    \tstate->thermal_clock_enabled = false;
    \tstate->reset_deasserted = false;
    \tstate->apmixed_configured = false;
    \tstate->banks_touched = false;
    \tstate->channel_touched = false;
    \tstate->ready = false;
    }

    static inline bool
    mtk_thermal_transaction_ops_valid(
    \tconst struct mtk_thermal_transaction_ops *ops)
    {
    \treturn ops && ops->enable_auxadc_clock &&
    \t\tops->disable_auxadc_clock && ops->enable_thermal_clock &&
    \t\tops->disable_thermal_clock && ops->reset_thermal &&
    \t\tops->assert_thermal_reset && ops->configure_apmixed &&
    \t\tops->restore_apmixed && ops->wait_for_idle &&
    \t\tops->pause_disable_banks && ops->clear_auxadc_channel &&
    \t\tops->disable_auxadc_channel && ops->prepare_bank &&
    \t\tops->commit_auxadc_channel && ops->enable_bank &&
    \t\tops->release_bank && ops->first_sample;
    }

    static inline int
    mtk_thermal_transaction_execute(
    \tvoid *context, const struct mtk_thermal_transaction_ops *ops,
    \tstruct mtk_thermal_transaction_state *state, unsigned int banks)
    {
    \tunsigned int bank;
    \tint ret;

    \tif (!context || !mtk_thermal_transaction_ops_valid(ops) ||
    \t    !mtk_thermal_transaction_state_is_closed(state) || !banks)
    \t\treturn -EINVAL;

    \tret = ops->enable_auxadc_clock(context);
    \tif (ret)
    \t\tgoto fail;
    \tstate->auxadc_clock_enabled = true;

    \tret = ops->enable_thermal_clock(context);
    \tif (ret)
    \t\tgoto fail;
    \tstate->thermal_clock_enabled = true;

    \tret = ops->reset_thermal(context);
    \tif (ret)
    \t\tgoto fail;
    \tstate->reset_deasserted = true;

    \tstate->apmixed_configured = true;
    \tret = ops->configure_apmixed(context);
    \tif (ret)
    \t\tgoto fail;

    \tret = ops->wait_for_idle(context);
    \tif (ret)
    \t\tgoto fail;

    \tstate->banks_touched = true;
    \tops->pause_disable_banks(context);
    \tstate->channel_touched = true;
    \tret = ops->clear_auxadc_channel(context);
    \tif (ret)
    \t\tgoto fail;

    \tfor (bank = 0; bank < banks; bank++) {
    \t\tret = ops->prepare_bank(context, bank);
    \t\tif (ret)
    \t\t\tgoto fail;
    \t}

    \tret = ops->commit_auxadc_channel(context);
    \tif (ret)
    \t\tgoto fail;

    \tfor (bank = 0; bank < banks; bank++) {
    \t\tret = ops->enable_bank(context, bank);
    \t\tif (ret)
    \t\t\tgoto fail;
    \t}

    \tfor (bank = 0; bank < banks; bank++) {
    \t\tret = ops->release_bank(context, bank);
    \t\tif (ret)
    \t\t\tgoto fail;
    \t}

    \tfor (bank = 0; bank < banks; bank++) {
    \t\tret = ops->first_sample(context, bank);
    \t\tif (ret)
    \t\t\tgoto fail;
    \t}

    \tstate->ready = true;

    \treturn 0;

    fail:
    \tmtk_thermal_transaction_close(context, ops, state);
    \treturn ret;
    }
    """)


def production_helpers() -> str:
    return dedent("""\
    static int mt6797_thermal_enable_auxadc_clock(void *context)
    {
    \tstruct mtk_thermal *mt = context;

    \treturn clk_prepare_enable(mt->clk_auxadc);
    }

    static void mt6797_thermal_disable_auxadc_clock(void *context)
    {
    \tstruct mtk_thermal *mt = context;

    \tclk_disable_unprepare(mt->clk_auxadc);
    }

    static int mt6797_thermal_enable_thermal_clock(void *context)
    {
    \tstruct mtk_thermal *mt = context;

    \treturn clk_prepare_enable(mt->clk_peri_therm);
    }

    static void mt6797_thermal_disable_thermal_clock(void *context)
    {
    \tstruct mtk_thermal *mt = context;

    \tclk_disable_unprepare(mt->clk_peri_therm);
    }

    static int mt6797_thermal_reset(void *context)
    {
    \tstruct mtk_thermal *mt = context;

    \treturn reset_control_reset(mt->rst);
    }

    static void mt6797_thermal_assert_reset(void *context)
    {
    \tstruct mtk_thermal *mt = context;

    \treset_control_assert(mt->rst);
    }

    static int mt6797_thermal_configure_apmixed(void *context)
    {
    \tstruct mtk_thermal *mt = context;
    \tu32 expected, value;

    \tmt->apmixed_buffer_saved = readl(mt->apmixed_base +
    \t\t\t\t\t     APMIXED_SYS_TS_CON1);
    \texpected = mtk_thermal_mt6797_apmixed_value(
    \t\tmt->apmixed_buffer_saved);
    \twritel(expected, mt->apmixed_base + APMIXED_SYS_TS_CON1);
    \tudelay(200);
    \tvalue = readl(mt->apmixed_base + APMIXED_SYS_TS_CON1);

    \treturn value == expected ? 0 : -EIO;
    }

    static void mt6797_thermal_restore_apmixed(void *context)
    {
    \tstruct mtk_thermal *mt = context;

    \twritel(mt->apmixed_buffer_saved,
    \t       mt->apmixed_base + APMIXED_SYS_TS_CON1);
    }

    static int mt6797_thermal_wait_for_idle(void *context)
    {
    \tstruct mtk_thermal *mt = context;
    \tu32 value;
    \tint ret;

    \tret = readl_poll_timeout(mt->thermal_base + MT6797_THERMAL_AHB_STATUS,
    \t\t\t\t value, mtk_thermal_mt6797_ahb_idle(value),
    \t\t\t\t 2, 100);
    \tif (ret)
    \t\treturn ret;

    \treturn readl_poll_timeout(mt->auxadc_base + AUXADC_CON2_V, value,
    \t\t\t\t  mtk_thermal_mt6797_auxadc_idle(value),
    \t\t\t\t  1000, 30000);
    }

    static void mt6797_thermal_pause_disable_banks(void *context)
    {
    \tstruct mtk_thermal *mt = context;
    \tunsigned int bank;

    \tfor (bank = 0; bank < mt->conf->num_banks; bank++) {
    \t\tstruct mtk_thermal_bank *selected = &mt->banks[bank];
    \t\tu32 value;

    \t\tmtk_thermal_get_bank(selected);
    \t\tvalue = readl(mt->thermal_base + TEMP_MSRCTL1);
    \t\twritel(value | MT6797_PERIODIC_PAUSE_MASK,
    \t\t       mt->thermal_base + TEMP_MSRCTL1);
    \t\twritel(0, mt->thermal_base + TEMP_MONCTL0);
    \t\tmtk_thermal_put_bank(selected);
    \t}
    }

    static void mt6797_thermal_disable_auxadc_channel(void *context)
    {
    \tstruct mtk_thermal *mt = context;
    \tu32 value;

    \tvalue = readl(mt->auxadc_base + AUXADC_CON0_V);
    \twritel(value & ~BIT(mt->conf->auxadc_channel),
    \t       mt->auxadc_base + AUXADC_CON0_V);
    \twritel(BIT(mt->conf->auxadc_channel),
    \t       mt->auxadc_base + AUXADC_CON1_CLR_V);
    }

    static int mt6797_thermal_clear_auxadc_channel(void *context)
    {
    \tmt6797_thermal_disable_auxadc_channel(context);

    \treturn 0;
    }

    static int mt6797_thermal_prepare_bank(void *context, unsigned int num)
    {
    \tstruct mtk_thermal *mt = context;
    \tstruct mtk_thermal_bank *bank = &mt->banks[num];
    \tconst struct mtk_thermal_data *conf = mt->conf;
    \tvoid __iomem *controller_base = mt->thermal_base +
    \t\tconf->controller_offset[0];
    \tunsigned int i;

    \tmtk_thermal_get_bank(bank);
    \twritel(TEMP_MONCTL1_PERIOD_UNIT(12),
    \t       controller_base + TEMP_MONCTL1);
    \twritel(TEMP_MONCTL2_FILTER_INTERVAL(1) |
    \t       TEMP_MONCTL2_SENSOR_INTERVAL(429),
    \t       controller_base + TEMP_MONCTL2);
    \twritel(TEMP_AHBPOLL_ADC_POLL_INTERVAL(conf->temp_ahbpoll),
    \t       controller_base + TEMP_AHBPOLL);
    \twritel(conf->temp_msrctl0, controller_base + TEMP_MSRCTL0);
    \twritel(0, controller_base + TEMP_MONIDET0);
    \twritel(0, controller_base + TEMP_MONIDET1);
    \twritel(BIT(conf->auxadc_channel), controller_base + TEMP_ADCMUX);
    \twritel(mt->auxadc_phys_base + AUXADC_CON1_CLR_V,
    \t       controller_base + TEMP_ADCMUXADDR);
    \twritel(mt->apmixed_phys_base + APMIXED_SYS_TS_CON1,
    \t       controller_base + TEMP_PNPMUXADDR);
    \twritel(BIT(conf->auxadc_channel), controller_base + TEMP_ADCEN);
    \twritel(mt->auxadc_phys_base + AUXADC_CON1_SET_V,
    \t       controller_base + TEMP_ADCENADDR);
    \twritel(mt->auxadc_phys_base + AUXADC_DATA(conf->auxadc_channel),
    \t       controller_base + TEMP_ADCVALIDADDR);
    \twritel(mt->auxadc_phys_base + AUXADC_DATA(conf->auxadc_channel),
    \t       controller_base + TEMP_ADCVOLTADDR);
    \twritel(0, controller_base + TEMP_RDCTRL);
    \twritel(conf->temp_adcvalidmask,
    \t       controller_base + TEMP_ADCVALIDMASK);
    \twritel(0, controller_base + TEMP_ADCVOLTAGESHIFT);
    \twritel(TEMP_ADCWRITECTRL_ADC_MUX_WRITE,
    \t       controller_base + TEMP_ADCWRITECTRL);

    \tfor (i = 0; i < conf->bank_data[num].num_sensors; i++)
    \t\twritel(conf->sensor_mux_values[
    \t\t\tconf->bank_data[num].sensors[i]],
    \t\t       controller_base + conf->adcpnp[i]);

    \twritel(TEMP_ADCWRITECTRL_ADC_PNP_WRITE |
    \t       TEMP_ADCWRITECTRL_ADC_MUX_WRITE,
    \t       controller_base + TEMP_ADCWRITECTRL);
    \tmtk_thermal_put_bank(bank);

    \treturn 0;
    }

    static int mt6797_thermal_commit_auxadc_channel(void *context)
    {
    \tstruct mtk_thermal *mt = context;

    \twritel(BIT(mt->conf->auxadc_channel),
    \t       mt->auxadc_base + AUXADC_CON1_SET_V);

    \treturn 0;
    }

    static int mt6797_thermal_enable_bank(void *context, unsigned int num)
    {
    \tstruct mtk_thermal *mt = context;
    \tstruct mtk_thermal_bank *bank = &mt->banks[num];

    \tmtk_thermal_get_bank(bank);
    \twritel(GENMASK(mt->conf->bank_data[num].num_sensors - 1, 0),
    \t       mt->thermal_base + TEMP_MONCTL0);
    \tmtk_thermal_put_bank(bank);

    \treturn 0;
    }

    static int mt6797_thermal_release_bank(void *context, unsigned int num)
    {
    \tstruct mtk_thermal *mt = context;
    \tstruct mtk_thermal_bank *bank = &mt->banks[num];
    \tu32 value;

    \tmtk_thermal_get_bank(bank);
    \tvalue = readl(mt->thermal_base + TEMP_MSRCTL1);
    \twritel(value & ~MT6797_PERIODIC_PAUSE_MASK,
    \t       mt->thermal_base + TEMP_MSRCTL1);
    \tmtk_thermal_put_bank(bank);

    \treturn 0;
    }

    static int mt6797_thermal_first_sample(void *context, unsigned int num)
    {
    \tstruct mtk_thermal *mt = context;
    \tconst struct thermal_bank_cfg *bank_conf =
    \t\t&mt->conf->bank_data[num];
    \tstruct mtk_thermal_bank *bank = &mt->banks[num];
    \tunsigned int attempt, sensor;

    \tfor (attempt = 0; attempt < MT6797_FIRST_SAMPLE_ATTEMPTS;
    \t     attempt++) {
    \t\tbool valid = true;

    \t\tmtk_thermal_get_bank(bank);
    \t\tfor (sensor = 0; sensor < bank_conf->num_sensors; sensor++) {
    \t\t\tu32 raw = readl(mt->thermal_base + mt->conf->msr[sensor]);
    \t\t\tint temperature = mt->raw_to_mcelsius(
    \t\t\t\tmt, bank_conf->sensors[sensor], raw);

    \t\t\tif (!mtk_thermal_mt6797_first_sample_valid(
    \t\t\t\traw, temperature)) {
    \t\t\t\tvalid = false;
    \t\t\t\tbreak;
    \t\t\t}
    \t\t}
    \t\tmtk_thermal_put_bank(bank);
    \t\tif (valid)
    \t\t\treturn 0;
    \t\tusleep_range(1000, 1500);
    \t}

    \tdev_err(mt->dev, "bank %u has no valid first thermal sample\n", num);

    \treturn -ETIMEDOUT;
    }

    static const struct mtk_thermal_transaction_ops
    mt6797_thermal_transaction_ops = {
    \t.enable_auxadc_clock = mt6797_thermal_enable_auxadc_clock,
    \t.disable_auxadc_clock = mt6797_thermal_disable_auxadc_clock,
    \t.enable_thermal_clock = mt6797_thermal_enable_thermal_clock,
    \t.disable_thermal_clock = mt6797_thermal_disable_thermal_clock,
    \t.reset_thermal = mt6797_thermal_reset,
    \t.assert_thermal_reset = mt6797_thermal_assert_reset,
    \t.configure_apmixed = mt6797_thermal_configure_apmixed,
    \t.restore_apmixed = mt6797_thermal_restore_apmixed,
    \t.wait_for_idle = mt6797_thermal_wait_for_idle,
    \t.pause_disable_banks = mt6797_thermal_pause_disable_banks,
    \t.clear_auxadc_channel = mt6797_thermal_clear_auxadc_channel,
    \t.disable_auxadc_channel = mt6797_thermal_disable_auxadc_channel,
    \t.prepare_bank = mt6797_thermal_prepare_bank,
    \t.commit_auxadc_channel = mt6797_thermal_commit_auxadc_channel,
    \t.enable_bank = mt6797_thermal_enable_bank,
    \t.release_bank = mt6797_thermal_release_bank,
    \t.first_sample = mt6797_thermal_first_sample,
    };

    static void mtk_thermal_iounmap(void *base)
    {
    \tiounmap(base);
    }

    static int mtk_thermal_map_phandle(struct device *dev,
    \t\t\t\t     struct device_node *owner,
    \t\t\t\t     const char *property,
    \t\t\t\t     void __iomem **base, u64 *phys)
    {
    \tstruct device_node *node;
    \tint ret;

    \tnode = of_parse_phandle(owner, property, 0);
    \tif (!node)
    \t\treturn -ENODEV;

    \t*phys = of_get_phys_base(node);
    \tif (*phys == OF_BAD_ADDR) {
    \t\tof_node_put(node);
    \t\treturn -EINVAL;
    \t}

    \t*base = of_iomap(node, 0);
    \tof_node_put(node);
    \tif (!*base)
    \t\treturn -ENOMEM;

    \tret = devm_add_action_or_reset(dev, mtk_thermal_iounmap, *base);
    \tif (ret)
    \t\treturn ret;

    \treturn 0;
    }

    """)


def probe_source() -> str:
    return dedent("""\
    static int mtk_thermal_probe(struct platform_device *pdev)
    {
    \tstruct device_node *np = pdev->dev.of_node;
    \tstruct thermal_zone_device *tzdev;
    \tstruct mtk_thermal *mt;
    \tint ctrl_id, i, ret;

    \tmt = devm_kzalloc(&pdev->dev, sizeof(*mt), GFP_KERNEL);
    \tif (!mt)
    \t\treturn -ENOMEM;

    \tmt->conf = of_device_get_match_data(&pdev->dev);
    \tif (!mt->conf)
    \t\treturn -EINVAL;

    \tret = mtk_thermal_get_calibration_data(&pdev->dev, mt);
    \tif (ret)
    \t\treturn ret;

    \tmt->thermal_base = devm_platform_get_and_ioremap_resource(
    \t\tpdev, 0, NULL);
    \tif (IS_ERR(mt->thermal_base))
    \t\treturn PTR_ERR(mt->thermal_base);

    \tmutex_init(&mt->lock);
    \tmt->dev = &pdev->dev;
    \tplatform_set_drvdata(pdev, mt);
    \tfor (i = 0; i < mt->conf->num_banks; i++) {
    \t\tmt->banks[i].id = i;
    \t\tmt->banks[i].mt = mt;
    \t}

    \tret = mtk_thermal_map_phandle(&pdev->dev, np, "mediatek,auxadc",
    \t\t\t\t      &mt->auxadc_base,
    \t\t\t\t      &mt->auxadc_phys_base);
    \tif (ret) {
    \t\tdev_err(&pdev->dev, "cannot map AUXADC: %d\n", ret);
    \t\treturn ret;
    \t}

    \tret = mtk_thermal_map_phandle(&pdev->dev, np,
    \t\t\t\t      "mediatek,apmixedsys",
    \t\t\t\t      &mt->apmixed_base,
    \t\t\t\t      &mt->apmixed_phys_base);
    \tif (ret) {
    \t\tdev_err(&pdev->dev, "cannot map APMIXEDSYS: %d\n", ret);
    \t\treturn ret;
    \t}

    \tif (mt->conf->version == MTK_THERMAL_V4) {
    \t\tmt->rst = devm_reset_control_get_exclusive(&pdev->dev, NULL);
    \t\tif (IS_ERR(mt->rst))
    \t\t\treturn dev_err_probe(&pdev->dev, PTR_ERR(mt->rst),
    \t\t\t\t\t     "cannot acquire thermal reset\n");

    \t\tmt->clk_auxadc = devm_clk_get(&pdev->dev, "auxadc");
    \t\tif (IS_ERR(mt->clk_auxadc))
    \t\t\treturn dev_err_probe(&pdev->dev,
    \t\t\t\t\t     PTR_ERR(mt->clk_auxadc),
    \t\t\t\t\t     "cannot acquire AUXADC clock\n");

    \t\tmt->clk_peri_therm = devm_clk_get(&pdev->dev, "therm");
    \t\tif (IS_ERR(mt->clk_peri_therm))
    \t\t\treturn dev_err_probe(&pdev->dev,
    \t\t\t\t\t     PTR_ERR(mt->clk_peri_therm),
    \t\t\t\t\t     "cannot acquire thermal clock\n");

    \t\tmt->raw_to_mcelsius = raw_to_mcelsius_v4;
    \t\tret = mtk_thermal_transaction_execute(
    \t\t\tmt, &mt6797_thermal_transaction_ops,
    \t\t\t&mt->transaction, mt->conf->num_banks);
    \t\tif (ret)
    \t\t\treturn dev_err_probe(&pdev->dev, ret,
    \t\t\t\t\t     "MT6797 transaction failed\n");
    \t} else {
    \t\tret = device_reset_optional(&pdev->dev);
    \t\tif (ret)
    \t\t\treturn ret;

    \t\tmt->clk_auxadc = devm_clk_get_enabled(&pdev->dev, "auxadc");
    \t\tif (IS_ERR(mt->clk_auxadc))
    \t\t\treturn dev_err_probe(&pdev->dev,
    \t\t\t\t\t     PTR_ERR(mt->clk_auxadc),
    \t\t\t\t\t     "cannot enable AUXADC clock\n");

    \t\tmt->clk_peri_therm = devm_clk_get_enabled(&pdev->dev, "therm");
    \t\tif (IS_ERR(mt->clk_peri_therm))
    \t\t\treturn dev_err_probe(&pdev->dev,
    \t\t\t\t\t     PTR_ERR(mt->clk_peri_therm),
    \t\t\t\t\t     "cannot enable thermal clock\n");

    \t\tmtk_thermal_turn_on_buffer(mt, mt->apmixed_base);
    \t\tif (mt->conf->version != MTK_THERMAL_V1)
    \t\t\tmtk_thermal_release_periodic_ts(mt,
    \t\t\t\t\t\tmt->auxadc_base);

    \t\tif (mt->conf->version == MTK_THERMAL_V1)
    \t\t\tmt->raw_to_mcelsius = raw_to_mcelsius_v1;
    \t\telse if (mt->conf->version == MTK_THERMAL_V2)
    \t\t\tmt->raw_to_mcelsius = raw_to_mcelsius_v2;
    \t\telse
    \t\t\tmt->raw_to_mcelsius = raw_to_mcelsius_v3;

    \t\tfor (ctrl_id = 0; ctrl_id < mt->conf->num_controller;
    \t\t     ctrl_id++)
    \t\t\tfor (i = 0; i < mt->conf->num_banks; i++)
    \t\t\t\tmtk_thermal_init_bank(
    \t\t\t\t\tmt, i, mt->apmixed_phys_base,
    \t\t\t\t\tmt->auxadc_phys_base, ctrl_id);
    \t}

    \ttzdev = devm_thermal_of_zone_register(&pdev->dev, 0, mt,
    \t\t\t\t\t      &mtk_thermal_ops);
    \tif (IS_ERR(tzdev)) {
    \t\tret = PTR_ERR(tzdev);
    \t\tif (mt->conf->version == MTK_THERMAL_V4)
    \t\t\tmtk_thermal_transaction_close(
    \t\t\t\tmt, &mt6797_thermal_transaction_ops,
    \t\t\t\t&mt->transaction);
    \t\treturn ret;
    \t}

    \tret = devm_thermal_add_hwmon_sysfs(&pdev->dev, tzdev);
    \tif (ret)
    \t\tdev_warn(&pdev->dev, "error in thermal_add_hwmon_sysfs\n");

    \treturn 0;
    }

    static void mtk_thermal_remove(struct platform_device *pdev)
    {
    \tstruct mtk_thermal *mt = platform_get_drvdata(pdev);

    \tif (mt && mt->conf->version == MTK_THERMAL_V4)
    \t\tmtk_thermal_transaction_close(
    \t\t\tmt, &mt6797_thermal_transaction_ops, &mt->transaction);

    }

    """)


def test_source() -> str:
    return dedent("""\
    // SPDX-License-Identifier: GPL-2.0-only
    #include <kunit/test.h>

    #include "auxadc_thermal_internal.h"

    #define MT6797_TEST_BANKS 6
    #define MT6797_TEST_FALLIBLE_CALLS 31

    enum mt6797_test_operation {
    \tMT6797_TEST_AUXADC_CLOCK_ON,
    \tMT6797_TEST_AUXADC_CLOCK_OFF,
    \tMT6797_TEST_THERMAL_CLOCK_ON,
    \tMT6797_TEST_THERMAL_CLOCK_OFF,
    \tMT6797_TEST_RESET,
    \tMT6797_TEST_ASSERT_RESET,
    \tMT6797_TEST_APMIXED,
    \tMT6797_TEST_RESTORE_APMIXED,
    \tMT6797_TEST_IDLE,
    \tMT6797_TEST_PAUSE_DISABLE,
    \tMT6797_TEST_CLEAR_CHANNEL,
    \tMT6797_TEST_DISABLE_CHANNEL,
    \tMT6797_TEST_PREPARE_BANK,
    \tMT6797_TEST_COMMIT_CHANNEL,
    \tMT6797_TEST_ENABLE_BANK,
    \tMT6797_TEST_RELEASE_BANK,
    \tMT6797_TEST_FIRST_SAMPLE,
    };

    struct mt6797_test_event {
    \tenum mt6797_test_operation operation;
    \tint bank;
    };

    struct mt6797_test_context {
    \tstruct mt6797_test_event events[64];
    \tunsigned int event_count;
    \tint fallible_count;
    \tint fail_at;
    };

    static void mt6797_test_record(struct mt6797_test_context *context,
    \t\t\t\t enum mt6797_test_operation operation,
    \t\t\t\t int bank)
    {
    \tcontext->events[context->event_count].operation = operation;
    \tcontext->events[context->event_count].bank = bank;
    \tcontext->event_count++;
    }

    static int mt6797_test_fallible(
    \tstruct mt6797_test_context *context,
    \tenum mt6797_test_operation operation, int bank)
    {
    \tint ordinal = context->fallible_count++;

    \tmt6797_test_record(context, operation, bank);
    \treturn ordinal == context->fail_at ? -EIO : 0;
    }

    #define MT6797_TEST_SIMPLE_INT(name, operation) \\
    \tstatic int name(void *data) \\
    \t{ \\
    \t\treturn mt6797_test_fallible(data, operation, -1); \\
    \t}

    #define MT6797_TEST_SIMPLE_VOID(name, operation) \\
    \tstatic void name(void *data) \\
    \t{ \\
    \t\tmt6797_test_record(data, operation, -1); \\
    \t}

    MT6797_TEST_SIMPLE_INT(mt6797_test_auxadc_on,
    \t\t\t MT6797_TEST_AUXADC_CLOCK_ON)
    MT6797_TEST_SIMPLE_VOID(mt6797_test_auxadc_off,
    \t\t\t  MT6797_TEST_AUXADC_CLOCK_OFF)
    MT6797_TEST_SIMPLE_INT(mt6797_test_thermal_on,
    \t\t\t MT6797_TEST_THERMAL_CLOCK_ON)
    MT6797_TEST_SIMPLE_VOID(mt6797_test_thermal_off,
    \t\t\t  MT6797_TEST_THERMAL_CLOCK_OFF)
    MT6797_TEST_SIMPLE_INT(mt6797_test_reset, MT6797_TEST_RESET)
    MT6797_TEST_SIMPLE_VOID(mt6797_test_assert_reset,
    \t\t\t  MT6797_TEST_ASSERT_RESET)
    MT6797_TEST_SIMPLE_INT(mt6797_test_apmixed, MT6797_TEST_APMIXED)
    MT6797_TEST_SIMPLE_VOID(mt6797_test_restore_apmixed,
    \t\t\t  MT6797_TEST_RESTORE_APMIXED)
    MT6797_TEST_SIMPLE_INT(mt6797_test_idle, MT6797_TEST_IDLE)
    MT6797_TEST_SIMPLE_VOID(mt6797_test_pause_disable,
    \t\t\t  MT6797_TEST_PAUSE_DISABLE)
    MT6797_TEST_SIMPLE_INT(mt6797_test_clear_channel,
    \t\t\t MT6797_TEST_CLEAR_CHANNEL)
    MT6797_TEST_SIMPLE_VOID(mt6797_test_disable_channel,
    \t\t\t  MT6797_TEST_DISABLE_CHANNEL)
    MT6797_TEST_SIMPLE_INT(mt6797_test_commit_channel,
    \t\t\t MT6797_TEST_COMMIT_CHANNEL)

    #define MT6797_TEST_BANK_INT(name, operation) \\
    \tstatic int name(void *data, unsigned int bank) \\
    \t{ \\
    \t\treturn mt6797_test_fallible(data, operation, bank); \\
    \t}

    MT6797_TEST_BANK_INT(mt6797_test_prepare_bank, MT6797_TEST_PREPARE_BANK)
    MT6797_TEST_BANK_INT(mt6797_test_enable_bank, MT6797_TEST_ENABLE_BANK)
    MT6797_TEST_BANK_INT(mt6797_test_release_bank, MT6797_TEST_RELEASE_BANK)
    MT6797_TEST_BANK_INT(mt6797_test_first_sample, MT6797_TEST_FIRST_SAMPLE)

    static const struct mtk_thermal_transaction_ops mt6797_test_ops = {
    \t.enable_auxadc_clock = mt6797_test_auxadc_on,
    \t.disable_auxadc_clock = mt6797_test_auxadc_off,
    \t.enable_thermal_clock = mt6797_test_thermal_on,
    \t.disable_thermal_clock = mt6797_test_thermal_off,
    \t.reset_thermal = mt6797_test_reset,
    \t.assert_thermal_reset = mt6797_test_assert_reset,
    \t.configure_apmixed = mt6797_test_apmixed,
    \t.restore_apmixed = mt6797_test_restore_apmixed,
    \t.wait_for_idle = mt6797_test_idle,
    \t.pause_disable_banks = mt6797_test_pause_disable,
    \t.clear_auxadc_channel = mt6797_test_clear_channel,
    \t.disable_auxadc_channel = mt6797_test_disable_channel,
    \t.prepare_bank = mt6797_test_prepare_bank,
    \t.commit_auxadc_channel = mt6797_test_commit_channel,
    \t.enable_bank = mt6797_test_enable_bank,
    \t.release_bank = mt6797_test_release_bank,
    \t.first_sample = mt6797_test_first_sample,
    };

    static void mt6797_test_expect_event(
    \tstruct kunit *test, const struct mt6797_test_context *context,
    \tunsigned int ordinal, enum mt6797_test_operation operation, int bank)
    {
    \tKUNIT_ASSERT_LT(test, ordinal, context->event_count);
    \tKUNIT_EXPECT_EQ(test, context->events[ordinal].operation, operation);
    \tKUNIT_EXPECT_EQ(test, context->events[ordinal].bank, bank);
    }

    static void mt6797_transaction_success_order(struct kunit *test)
    {
    \tstruct mtk_thermal_transaction_state state = {};
    \tstruct mt6797_test_context context = { .fail_at = -1 };
    \tunsigned int ordinal = 0;
    \tunsigned int bank;
    \tint ret;

    \tret = mtk_thermal_transaction_execute(
    \t\t&context, &mt6797_test_ops, &state, MT6797_TEST_BANKS);
    \tKUNIT_ASSERT_EQ(test, ret, 0);
    \tKUNIT_ASSERT_TRUE(test, state.ready);

    \tmt6797_test_expect_event(test, &context, ordinal++,
    \t\tMT6797_TEST_AUXADC_CLOCK_ON, -1);
    \tmt6797_test_expect_event(test, &context, ordinal++,
    \t\tMT6797_TEST_THERMAL_CLOCK_ON, -1);
    \tmt6797_test_expect_event(test, &context, ordinal++,
    \t\tMT6797_TEST_RESET, -1);
    \tmt6797_test_expect_event(test, &context, ordinal++,
    \t\tMT6797_TEST_APMIXED, -1);
    \tmt6797_test_expect_event(test, &context, ordinal++,
    \t\tMT6797_TEST_IDLE, -1);
    \tmt6797_test_expect_event(test, &context, ordinal++,
    \t\tMT6797_TEST_PAUSE_DISABLE, -1);
    \tmt6797_test_expect_event(test, &context, ordinal++,
    \t\tMT6797_TEST_CLEAR_CHANNEL, -1);
    \tfor (bank = 0; bank < MT6797_TEST_BANKS; bank++)
    \t\tmt6797_test_expect_event(test, &context, ordinal++,
    \t\t\tMT6797_TEST_PREPARE_BANK, bank);
    \tmt6797_test_expect_event(test, &context, ordinal++,
    \t\tMT6797_TEST_COMMIT_CHANNEL, -1);
    \tfor (bank = 0; bank < MT6797_TEST_BANKS; bank++)
    \t\tmt6797_test_expect_event(test, &context, ordinal++,
    \t\t\tMT6797_TEST_ENABLE_BANK, bank);
    \tfor (bank = 0; bank < MT6797_TEST_BANKS; bank++)
    \t\tmt6797_test_expect_event(test, &context, ordinal++,
    \t\t\tMT6797_TEST_RELEASE_BANK, bank);
    \tfor (bank = 0; bank < MT6797_TEST_BANKS; bank++)
    \t\tmt6797_test_expect_event(test, &context, ordinal++,
    \t\t\tMT6797_TEST_FIRST_SAMPLE, bank);
    \tKUNIT_EXPECT_EQ(test, context.event_count, ordinal);

    \tmtk_thermal_transaction_close(
    \t\t&context, &mt6797_test_ops, &state);
    \tmt6797_test_expect_event(test, &context, ordinal++,
    \t\tMT6797_TEST_PAUSE_DISABLE, -1);
    \tmt6797_test_expect_event(test, &context, ordinal++,
    \t\tMT6797_TEST_DISABLE_CHANNEL, -1);
    \tmt6797_test_expect_event(test, &context, ordinal++,
    \t\tMT6797_TEST_RESTORE_APMIXED, -1);
    \tmt6797_test_expect_event(test, &context, ordinal++,
    \t\tMT6797_TEST_ASSERT_RESET, -1);
    \tmt6797_test_expect_event(test, &context, ordinal++,
    \t\tMT6797_TEST_THERMAL_CLOCK_OFF, -1);
    \tmt6797_test_expect_event(test, &context, ordinal++,
    \t\tMT6797_TEST_AUXADC_CLOCK_OFF, -1);
    \tKUNIT_EXPECT_EQ(test, context.event_count, ordinal);
    \tKUNIT_EXPECT_TRUE(test,
    \t\tmtk_thermal_transaction_state_is_closed(&state));
    }

    static void mt6797_transaction_all_failures_close(struct kunit *test)
    {
    \tint fail_at;

    \tfor (fail_at = 0; fail_at < MT6797_TEST_FALLIBLE_CALLS;
    \t     fail_at++) {
    \t\tstruct mtk_thermal_transaction_state state = {};
    \t\tstruct mt6797_test_context context = { .fail_at = fail_at };
    \t\tint ret;

    \t\tret = mtk_thermal_transaction_execute(
    \t\t\t&context, &mt6797_test_ops, &state,
    \t\t\tMT6797_TEST_BANKS);
    \t\tKUNIT_EXPECT_EQ_MSG(test, ret, -EIO, "failure %d", fail_at);
    \t\tKUNIT_EXPECT_TRUE_MSG(
    \t\t\ttest, mtk_thermal_transaction_state_is_closed(&state),
    \t\t\t"failure %d left transaction open", fail_at);
    \t}
    }

    static void mt6797_transaction_rejects_invalid_start(struct kunit *test)
    {
    \tstruct mtk_thermal_transaction_state state = {};
    \tstruct mt6797_test_context context = { .fail_at = -1 };

    \tKUNIT_EXPECT_EQ(test,
    \t\tmtk_thermal_transaction_execute(
    \t\t\t&context, &mt6797_test_ops, &state, 0),
    \t\t-EINVAL);
    \tstate.ready = true;
    \tKUNIT_EXPECT_EQ(test,
    \t\tmtk_thermal_transaction_execute(
    \t\t\t&context, &mt6797_test_ops, &state,
    \t\t\tMT6797_TEST_BANKS),
    \t\t-EINVAL);
    }

    static void mt6797_transaction_apmixed_mask(struct kunit *test)
    {
    \tu32 original = 0xa5a5a5f5;
    \tu32 expected = original & ~GENMASK(5, 4);

    \tKUNIT_EXPECT_EQ(test,
    \t\tmtk_thermal_mt6797_apmixed_value(original), expected);
    \tKUNIT_EXPECT_EQ(test, expected & GENMASK(5, 4), 0U);
    \tKUNIT_EXPECT_EQ(test, expected & ~GENMASK(5, 4),
    \t\toriginal & ~GENMASK(5, 4));
    }

    static void mt6797_transaction_idle_predicates(struct kunit *test)
    {
    \tKUNIT_EXPECT_TRUE(test, mtk_thermal_mt6797_ahb_idle(0x0000ffff));
    \tKUNIT_EXPECT_FALSE(test, mtk_thermal_mt6797_ahb_idle(0x00010000));
    \tKUNIT_EXPECT_TRUE(test, mtk_thermal_mt6797_auxadc_idle(0x2));
    \tKUNIT_EXPECT_FALSE(test, mtk_thermal_mt6797_auxadc_idle(0x1));
    }

    static void mt6797_transaction_first_sample_gate(struct kunit *test)
    {
    \tKUNIT_EXPECT_FALSE(test,
    \t\tmtk_thermal_mt6797_first_sample_valid(0, 25000));
    \tKUNIT_EXPECT_FALSE(test,
    \t\tmtk_thermal_mt6797_first_sample_valid(1, -20001));
    \tKUNIT_EXPECT_FALSE(test,
    \t\tmtk_thermal_mt6797_first_sample_valid(1, 150001));
    \tKUNIT_EXPECT_TRUE(test,
    \t\tmtk_thermal_mt6797_first_sample_valid(1, -20000));
    \tKUNIT_EXPECT_TRUE(test,
    \t\tmtk_thermal_mt6797_first_sample_valid(0xfff, 150000));
    }

    static struct kunit_case mt6797_thermal_transaction_cases[] = {
    \tKUNIT_CASE(mt6797_transaction_success_order),
    \tKUNIT_CASE(mt6797_transaction_all_failures_close),
    \tKUNIT_CASE(mt6797_transaction_rejects_invalid_start),
    \tKUNIT_CASE(mt6797_transaction_apmixed_mask),
    \tKUNIT_CASE(mt6797_transaction_idle_predicates),
    \tKUNIT_CASE(mt6797_transaction_first_sample_gate),
    \t{}
    };

    static struct kunit_suite mt6797_thermal_transaction_suite = {
    \t.name = "mt6797-thermal-transaction",
    \t.test_cases = mt6797_thermal_transaction_cases,
    };

    kunit_test_suite(mt6797_thermal_transaction_suite);

    MODULE_LICENSE("GPL");
    """)


def edit_production(root: Path) -> None:
    thermal = root / THERMAL_C
    internal = root / INTERNAL_H

    replace_once(
        thermal,
        "#include <linux/io.h>\n",
        "#include <linux/io.h>\n#include <linux/iopoll.h>\n",
    )
    replace_once(
        thermal,
        "#define AUXADC_CON1_SET_V\t0x008\n",
        "#define AUXADC_CON0_V\t\t0x000\n"
        "#define AUXADC_CON1_SET_V\t0x008\n",
    )
    replace_once(
        thermal,
        "#define PTPCORESEL\t\t0x400\n",
        "#define PTPCORESEL\t\t0x400\n"
        "#define MT6797_THERMAL_AHB_STATUS\t0x418\n"
        "#define MT6797_PERIODIC_PAUSE_MASK\t0x10e\n"
        "#define MT6797_FIRST_SAMPLE_ATTEMPTS\t100\n",
    )
    replace_once(
        thermal,
        "\tstruct clk *clk_auxadc;\n"
        "\t/* lock: for getting and putting banks */\n",
        "\tstruct clk *clk_auxadc;\n"
        "\tstruct reset_control *rst;\n"
        "\tvoid __iomem *auxadc_base;\n"
        "\tvoid __iomem *apmixed_base;\n"
        "\tu64 auxadc_phys_base;\n"
        "\tu64 apmixed_phys_base;\n"
        "\tu32 apmixed_buffer_saved;\n"
        "\tstruct mtk_thermal_transaction_state transaction;\n"
        "\t/* lock: for getting and putting banks */\n",
    )
    replace_once(
        thermal,
        "\t.apmixed_buffer_ctl_mask = GENMASK(31, 6) | BIT(3),\n"
        "\t.apmixed_buffer_ctl_set = BIT(0),\n"
        "\t.temp_ahbpoll = 0x30d,\n",
        "\t.apmixed_buffer_ctl_mask = (u32)~GENMASK(5, 4),\n"
        "\t.apmixed_buffer_ctl_set = 0,\n"
        "\t.temp_ahbpoll = 0x30d,\n",
    )
    replace_once(
        thermal,
        "\tif (raw == 0)\n\t\treturn 0;\n\n\traw &= 0xfff;\n"
        "\tgain = 10000 + ((s64)(mt->adc_ge - 512) * 10000) / 4096;\n",
        "\tif (!(raw & GENMASK(11, 0)))\n"
        "\t\treturn THERMAL_TEMP_INVALID;\n\n"
        "\traw &= 0xfff;\n"
        "\tgain = 10000 + ((s64)(mt->adc_ge - 512) * 10000) / 4096;\n",
    )
    replace_once(
        internal,
        "#include <linux/errno.h>\n#include <linux/types.h>\n",
        "#include <linux/bitops.h>\n#include <linux/errno.h>\n"
        "#include <linux/types.h>\n",
    )
    replace_once(
        internal,
        "\n#endif /* __MTK_AUXADC_THERMAL_INTERNAL_H */\n",
        transaction_header()
        + "\n#endif /* __MTK_AUXADC_THERMAL_INTERNAL_H */\n",
    )
    replace_once(
        thermal,
        "static int mtk_thermal_extract_efuse_v1(struct mtk_thermal *mt, u32 *buf)\n",
        production_helpers()
        + "static int mtk_thermal_extract_efuse_v1(struct mtk_thermal *mt, u32 *buf)\n",
    )
    replace_region(
        thermal,
        "static int mtk_thermal_probe(struct platform_device *pdev)\n",
        "static struct platform_driver mtk_thermal_driver = {\n",
        probe_source(),
    )
    replace_once(
        thermal,
        "static struct platform_driver mtk_thermal_driver = {\n"
        "\t.probe = mtk_thermal_probe,\n",
        "static struct platform_driver mtk_thermal_driver = {\n"
        "\t.probe = mtk_thermal_probe,\n"
        "\t.remove = mtk_thermal_remove,\n",
    )


def edit_kunit(root: Path) -> None:
    write_new(root / TEST_C, test_source())
    replace_once(
        root / KCONFIG,
        "config MTK_LVTS_THERMAL\n",
        dedent("""\
        config MTK_SOC_THERMAL_TRANSACTION_KUNIT_TEST
        \ttristate "Test MT6797 thermal transaction" if !KUNIT_ALL_TESTS
        \tdepends on KUNIT
        \tdefault KUNIT_ALL_TESTS
        \thelp
        \t  Test the hardware-free ordering, failure unwind, APMIXED mask,
        \t  idle predicates, and first-sample gate used by the disabled-node
        \t  MT6797 thermal transaction. The test performs no MMIO, clock,
        \t  reset, DT, NVMEM, platform-device, or thermal-zone operation.

        config MTK_LVTS_THERMAL
        """),
    )
    replace_once(
        root / MAKEFILE,
        "obj-$(CONFIG_MTK_SOC_THERMAL_KUNIT_TEST) += auxadc_thermal_test.o\n",
        "obj-$(CONFIG_MTK_SOC_THERMAL_KUNIT_TEST) += auxadc_thermal_test.o\n"
        "obj-$(CONFIG_MTK_SOC_THERMAL_TRANSACTION_KUNIT_TEST) += mt6797_auxadc_transaction_test.o\n",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--phase", choices=("production", "kunit"), required=True)
    args = parser.parse_args()
    if args.phase == "production":
        edit_production(args.source_root)
    else:
        edit_kunit(args.source_root)


if __name__ == "__main__":
    main()
