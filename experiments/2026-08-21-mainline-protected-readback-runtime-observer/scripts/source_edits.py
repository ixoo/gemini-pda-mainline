#!/usr/bin/env python3
"""Apply deterministic MT6797 protected-readback observer changes."""

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


OBSERVER_SOURCE = dedent(r"""
// SPDX-License-Identifier: GPL-2.0-only
/*
 * One-shot MT6797 protected-readback runtime observer.
 *
 * This candidate-only observer waits for both read-only transports, performs
 * one call to each, and publishes their complete raw records. It is not a
 * state owner and does not classify or authorize an A72 transition.
 */

#include <linux/device.h>
#include <linux/err.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/of_platform.h>
#include <linux/platform_device.h>

#include <linux/soc/mediatek/mt6797-bigidvfs-backend.h>
#include <linux/soc/mediatek/mt6797-dvfsp-clock-backend.h>

#define MT6797_READBACK_TAG "GEMINI_PROTECTED_READBACK_V1"

static struct platform_device *
mt6797_readback_get_backend(struct device *dev, const char *property)
{
	struct platform_device *backend;
	struct device_node *node;

	node = of_parse_phandle(dev->of_node, property, 0);
	if (!node)
		return ERR_PTR(-EINVAL);
	backend = of_find_device_by_node(node);
	of_node_put(node);
	if (!backend)
		return ERR_PTR(-EPROBE_DEFER);
	if (!device_is_bound(&backend->dev)) {
		put_device(&backend->dev);
		return ERR_PTR(-EPROBE_DEFER);
	}

	return backend;
}

static void
mt6797_readback_log_clock(struct device *dev, int ret,
			   const struct mt6797_dvfsp_clock_readback *record)
{
	dev_info(dev,
		 MT6797_READBACK_TAG
		 " clock ret=%d abi=%u generation=%llu"
		 " muxsel=0x%08x ckdiv=0x%08x"
		 " pll_ll=0x%08x,0x%08x,0x%08x"
		 " pll_l=0x%08x,0x%08x,0x%08x"
		 " pll_cci=0x%08x,0x%08x,0x%08x"
		 " cspm_swctrl=0x%08x,0x%08x,0x%08x"
		 " cspm_hwsta=0x%08x,0x%08x,0x%08x,0x%08x\n",
		 ret, record->abi,
		 (unsigned long long)record->sample_generation,
		 record->armplldiv_muxsel, record->armplldiv_ckdiv,
		 record->pll_ll[0], record->pll_ll[1], record->pll_ll[2],
		 record->pll_l[0], record->pll_l[1], record->pll_l[2],
		 record->pll_cci[0], record->pll_cci[1], record->pll_cci[2],
		 record->cspm_swctrl[0], record->cspm_swctrl[1],
		 record->cspm_swctrl[2], record->cspm_hwsta[0],
		 record->cspm_hwsta[1], record->cspm_hwsta[2],
		 record->cspm_hwsta[3]);
}

static void
mt6797_readback_log_bigidvfs(struct device *dev, int ret,
			      const struct mt6797_bigidvfs_readback *record)
{
	dev_info(dev,
		 MT6797_READBACK_TAG
		 " bigidvfs ret=%d abi=%u generation=%llu"
		 " pll_pcw=0x%08x pll_enable_posdiv=0x%08x"
		 " sram_selector=0x%08x control=0x%08x\n",
		 ret, record->abi,
		 (unsigned long long)record->sample_generation,
		 record->pll_pcw, record->pll_enable_posdiv,
		 record->sram_selector, record->control);
}

static int mt6797_readback_observer_probe(struct platform_device *pdev)
{
	struct mt6797_dvfsp_clock_readback clock = { };
	struct mt6797_bigidvfs_readback bigidvfs = { };
	struct platform_device *clock_backend;
	struct platform_device *bigidvfs_backend;
	struct device *dev = &pdev->dev;
	int clock_ret;
	int bigidvfs_ret;
	int ret;

	clock_backend = mt6797_readback_get_backend(
		dev, "mediatek,clock-backend");
	if (IS_ERR(clock_backend))
		return dev_err_probe(dev, PTR_ERR(clock_backend),
				     "clock backend unavailable\n");
	bigidvfs_backend = mt6797_readback_get_backend(
		dev, "mediatek,bigidvfs-backend");
	if (IS_ERR(bigidvfs_backend)) {
		ret = dev_err_probe(dev, PTR_ERR(bigidvfs_backend),
				    "BigiDVFS backend unavailable\n");
		goto put_clock;
	}

	clock_ret = mt6797_dvfsp_clock_backend_read(&clock_backend->dev,
						   &clock);
	bigidvfs_ret = mt6797_bigidvfs_backend_read(&bigidvfs_backend->dev,
						    &bigidvfs);
	mt6797_readback_log_clock(dev, clock_ret, &clock);
	mt6797_readback_log_bigidvfs(dev, bigidvfs_ret, &bigidvfs);
	dev_info(dev,
		 MT6797_READBACK_TAG
		 " state=complete attempts=1 clock_calls=1 bigidvfs_calls=1"
		 " cpu_requests=0 owner_registration=0\n");
	put_device(&bigidvfs_backend->dev);
	ret = 0;

put_clock:
	put_device(&clock_backend->dev);
	return ret;
}

static const struct of_device_id mt6797_readback_observer_of_match[] = {
	{ .compatible = "mediatek,mt6797-protected-readback-observer" },
	{ }
};
MODULE_DEVICE_TABLE(of, mt6797_readback_observer_of_match);

static struct platform_driver mt6797_readback_observer_driver = {
	.probe = mt6797_readback_observer_probe,
	.driver = {
		.name = "mt6797-protected-readback-observer",
		.of_match_table = mt6797_readback_observer_of_match,
		.suppress_bind_attrs = true,
	},
};
builtin_platform_driver(mt6797_readback_observer_driver);

MODULE_DESCRIPTION("MT6797 one-shot protected-readback observer");
MODULE_LICENSE("GPL");
""").lstrip("\n")


OBSERVER_BINDING = dedent(r"""
# SPDX-License-Identifier: (GPL-2.0-only OR BSD-2-Clause)
%YAML 1.2
---
$id: http://devicetree.org/schemas/soc/mediatek/mediatek,mt6797-protected-readback-observer.yaml#
$schema: http://devicetree.org/meta-schemas/core.yaml#

title: MediaTek MT6797 one-shot protected-readback observer

description: |
  This experiment-only observer calls the separately described protected clock
  and BigiDVFS read-only transports once after both have bound. It publishes
  raw records only and is not a state owner, clock or regulator provider, or
  CPU transition consumer.

maintainers:
  - Julien Etienne <julien.etienne@gmail.com>

properties:
  compatible:
    const: mediatek,mt6797-protected-readback-observer

  mediatek,clock-backend:
    $ref: /schemas/types.yaml#/definitions/phandle
    description: MT6797 protected clock readback transport

  mediatek,bigidvfs-backend:
    $ref: /schemas/types.yaml#/definitions/phandle
    description: MT6797 secure BigiDVFS readback transport

  status:
    enum: [ disabled, okay ]

required:
  - compatible
  - mediatek,clock-backend
  - mediatek,bigidvfs-backend

additionalProperties: false
""").lstrip("\n")


CANDIDATE_DTS = dedent(r"""
// SPDX-License-Identifier: GPL-2.0-only
/*
 * Copyright (c) 2026 Julien Etienne
 */

#include "mt6797-gemini-pda.dts"

/ {
	model = "Planet Computers Gemini PDA (protected readback observer)";

	protected-readback-observer {
		compatible = "mediatek,mt6797-protected-readback-observer";
		mediatek,clock-backend = <&dvfsp_clock_backend>;
		mediatek,bigidvfs-backend = <&dvfsp_bigidvfs_backend>;
		status = "okay";
	};
};

&dvfsp_clock_backend {
	status = "okay";
};

&dvfsp_bigidvfs_backend {
	status = "okay";
};
""").lstrip("\n")


def apply_observer(root: Path) -> None:
    source = root / "drivers/soc/mediatek/mt6797-protected-readback-observer.c"
    binding = root / (
        "Documentation/devicetree/bindings/soc/mediatek/"
        "mediatek,mt6797-protected-readback-observer.yaml"
    )
    if source.exists() or binding.exists():
        raise SystemExit("observer output already exists")
    source.parent.mkdir(parents=True, exist_ok=True)
    binding.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(OBSERVER_SOURCE, encoding="utf-8")
    binding.write_text(OBSERVER_BINDING, encoding="utf-8")

    kconfig = root / "drivers/soc/mediatek/Kconfig"
    observer_config = dedent(r"""
config MTK_MT6797_PROTECTED_READBACK_OBSERVER
	bool "MediaTek MT6797 one-shot protected readback observer"
	depends on MTK_MT6797_DVFSP_CLOCK_BACKEND
	depends on MTK_MT6797_DVFSP_BIGIDVFS_BACKEND
	help
	  Build the candidate-only observer that waits for both protected
	  readback transports, calls each exactly once, and logs every raw
	  field and return code. It exposes no trigger or retry endpoint.

	  This observer does not register a state owner, classify a recovered
	  state, or request a CPU, clock, regulator, or firmware transition.

""").lstrip("\n")
    anchor = "config MTK_MT6797_PROTECTED_READBACK_KUNIT_TEST\n"
    replace_once(kconfig, anchor, observer_config + anchor)

    makefile = root / "drivers/soc/mediatek/Makefile"
    anchor = (
        "obj-$(CONFIG_MTK_MT6797_PROTECTED_READBACK_KUNIT_TEST) += "
        "mt6797-protected-readback-test.o\n"
    )
    addition = (
        "obj-$(CONFIG_MTK_MT6797_PROTECTED_READBACK_OBSERVER) += "
        "mt6797-protected-readback-observer.o\n"
    )
    replace_once(makefile, anchor, addition + anchor)


def apply_dts(root: Path) -> None:
    dts = root / (
        "arch/arm64/boot/dts/mediatek/"
        "mt6797-gemini-pda-protected-readback.dts"
    )
    if dts.exists():
        raise SystemExit("candidate DTS already exists")
    dts.write_text(CANDIDATE_DTS, encoding="utf-8")

    makefile = root / "arch/arm64/boot/dts/mediatek/Makefile"
    anchor = "dtb-$(CONFIG_ARCH_MEDIATEK) += mt6797-gemini-pda.dtb\n"
    addition = (
        "dtb-$(CONFIG_ARCH_MEDIATEK) += "
        "mt6797-gemini-pda-protected-readback.dtb\n"
    )
    replace_once(makefile, anchor, anchor + addition)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--step", choices=("observer", "dts"), required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    if args.step == "observer":
        apply_observer(root)
    else:
        apply_dts(root)


if __name__ == "__main__":
    main()
