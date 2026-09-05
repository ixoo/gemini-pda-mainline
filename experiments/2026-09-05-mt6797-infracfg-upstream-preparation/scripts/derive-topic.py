#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Derive review-only upstream edits from exact inputs, on Buildbox only."""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
CLK = 'drivers/clk/mediatek/'
BINDING = 'include/dt-bindings/reset/mt6797-resets.h'
SCHEMA = 'Documentation/devicetree/bindings/clock/mediatek,infracfg.yaml'
DTS = 'arch/arm64/boot/dts/mediatek/mt6797.dtsi'
PHASES = ('bounds', 'bounds-test', 'binding', 'provider', 'provider-test', 'dts')

BOUNDS = '''/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef __DRV_CLK_MTK_RESET_INTERNAL_H
#define __DRV_CLK_MTK_RESET_INTERNAL_H

#include <linux/bitops.h>
#include <linux/errno.h>

#include "reset.h"

static inline int
mtk_reset_xlate_index(const struct mtk_clk_rst_desc *desc, unsigned int index)
{
	if (!desc->rst_idx_map || index >= desc->rst_idx_map_nr)
		return -EINVAL;

	return desc->rst_idx_map[index];
}

static inline int
mtk_reset_set_clr_reg(const struct mtk_clk_rst_desc *desc,
		      unsigned long id, bool deassert,
		      unsigned int *reg, unsigned int *mask)
{
	unsigned long bank = id / RST_NR_PER_BANK;

	if (!desc->rst_bank_ofs || bank >= desc->rst_bank_nr)
		return -EINVAL;

	*reg = desc->rst_bank_ofs[bank] + (deassert ? 0x4 : 0);
	*mask = BIT(id % RST_NR_PER_BANK);

	return 0;
}

#endif /* __DRV_CLK_MTK_RESET_INTERNAL_H */
'''

HEADER = '''/* SPDX-License-Identifier: (GPL-2.0-only OR BSD-2-Clause) */
#ifndef _DT_BINDINGS_RESET_MT6797_H
#define _DT_BINDINGS_RESET_MT6797_H

#define MT6797_INFRA_THERM_CTRL_RST	0
#define MT6797_INFRA_PMIC_WRAP_RST	1

#endif /* _DT_BINDINGS_RESET_MT6797_H */
'''

DESCRIPTOR = '''/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef __DRV_CLK_MTK_MT6797_RESET_H
#define __DRV_CLK_MTK_MT6797_RESET_H

#include <dt-bindings/reset/mt6797-resets.h>
#include <linux/kernel.h>

#include "reset.h"

static u16 infra_rst_ofs[] = {
	INFRA_RST0_SET_OFFSET,
	INFRA_RST2_SET_OFFSET,
};

static u16 infra_rst_idx_map[] = {
	[MT6797_INFRA_THERM_CTRL_RST] = 0 * RST_NR_PER_BANK,
	[MT6797_INFRA_PMIC_WRAP_RST] = 1 * RST_NR_PER_BANK,
};

static const struct mtk_clk_rst_desc infra_rst_desc = {
	.version = MTK_RST_SET_CLR,
	.rst_bank_ofs = infra_rst_ofs,
	.rst_bank_nr = ARRAY_SIZE(infra_rst_ofs),
	.rst_idx_map = infra_rst_idx_map,
	.rst_idx_map_nr = ARRAY_SIZE(infra_rst_idx_map),
};

#endif /* __DRV_CLK_MTK_MT6797_RESET_H */
'''

GENERIC_TEST = '''// SPDX-License-Identifier: GPL-2.0-only
#include <kunit/test.h>
#include <linux/limits.h>
#include <linux/module.h>

#include "reset-internal.h"

static u16 test_offsets[] = { 0x120, 0x140 };
static u16 test_map[] = { 0, 32, 64 };

static const struct mtk_clk_rst_desc test_desc = {
	.rst_bank_ofs = test_offsets,
	.rst_bank_nr = ARRAY_SIZE(test_offsets),
	.rst_idx_map = test_map,
	.rst_idx_map_nr = ARRAY_SIZE(test_map),
};

static void mtk_reset_map_bounds(struct kunit *test)
{
	struct mtk_clk_rst_desc desc = test_desc;

	KUNIT_EXPECT_EQ(test, mtk_reset_xlate_index(&desc, 0), 0);
	KUNIT_EXPECT_EQ(test, mtk_reset_xlate_index(&desc, 1), 32);
	KUNIT_EXPECT_EQ(test, mtk_reset_xlate_index(&desc, 3), -EINVAL);
	KUNIT_EXPECT_EQ(test, mtk_reset_xlate_index(&desc, UINT_MAX), -EINVAL);
	desc.rst_idx_map = NULL;
	KUNIT_EXPECT_EQ(test, mtk_reset_xlate_index(&desc, 0), -EINVAL);
}

static void mtk_reset_register_pairs(struct kunit *test)
{
	unsigned int reg = 0, mask = 0;

	KUNIT_ASSERT_EQ(test, mtk_reset_set_clr_reg(&test_desc, 0, false,
						 &reg, &mask), 0);
	KUNIT_EXPECT_EQ(test, reg, 0x120U);
	KUNIT_EXPECT_EQ(test, mask, BIT(0));
	KUNIT_ASSERT_EQ(test, mtk_reset_set_clr_reg(&test_desc, 63, true,
						 &reg, &mask), 0);
	KUNIT_EXPECT_EQ(test, reg, 0x144U);
	KUNIT_EXPECT_EQ(test, mask, BIT(31));
}

static void expect_no_address(struct kunit *test,
			      const struct mtk_clk_rst_desc *desc,
			      unsigned long id)
{
	unsigned int reg = 0xfeed, mask = 0xbeef;

	KUNIT_EXPECT_EQ(test, mtk_reset_set_clr_reg(desc, id, false,
						 &reg, &mask), -EINVAL);
	KUNIT_EXPECT_EQ(test, reg, 0xfeedU);
	KUNIT_EXPECT_EQ(test, mask, 0xbeefU);
}

static void mtk_reset_invalid_bank(struct kunit *test)
{
	int id = mtk_reset_xlate_index(&test_desc, 2);

	KUNIT_ASSERT_EQ(test, id, 64);
	expect_no_address(test, &test_desc, id);
	expect_no_address(test, &test_desc, ULONG_MAX);
	/* Also catches a bank narrowed to zero on a 64-bit build. */
	if (BITS_PER_LONG > 32)
		expect_no_address(test, &test_desc, (unsigned long)(1ULL << 37));
}

static void mtk_reset_missing_banks(struct kunit *test)
{
	struct mtk_clk_rst_desc desc = test_desc;

	desc.rst_bank_nr = 0;
	expect_no_address(test, &desc, 0);
	desc = test_desc;
	desc.rst_bank_ofs = NULL;
	expect_no_address(test, &desc, 0);
}

static struct kunit_case mtk_reset_cases[] = {
	KUNIT_CASE(mtk_reset_map_bounds),
	KUNIT_CASE(mtk_reset_register_pairs),
	KUNIT_CASE(mtk_reset_invalid_bank),
	KUNIT_CASE(mtk_reset_missing_banks),
	{}
};

static struct kunit_suite mtk_reset_suite = {
	.name = "mtk-reset-bounds",
	.test_cases = mtk_reset_cases,
};

kunit_test_suite(mtk_reset_suite);

MODULE_LICENSE("GPL");
'''

SOC_TEST = '''// SPDX-License-Identifier: GPL-2.0-only
#include <kunit/test.h>
#include <linux/module.h>

#include "clk-mt6797-reset.h"
#include "reset-internal.h"

static void mt6797_reset_descriptor(struct kunit *test)
{
	KUNIT_EXPECT_EQ(test, infra_rst_desc.version, MTK_RST_SET_CLR);
	KUNIT_EXPECT_EQ(test, infra_rst_desc.rst_bank_nr, 2U);
	KUNIT_EXPECT_EQ(test, infra_rst_desc.rst_idx_map_nr, 2U);
	KUNIT_EXPECT_EQ(test, infra_rst_ofs[0], (u16)0x120);
	KUNIT_EXPECT_EQ(test, infra_rst_ofs[1], (u16)0x140);
}

static void expect_pair(struct kunit *test, unsigned int index,
			unsigned int expected_reg)
{
	unsigned int reg = 0, mask = 0;
	int id = mtk_reset_xlate_index(&infra_rst_desc, index);

	KUNIT_ASSERT_GE(test, id, 0);
	KUNIT_ASSERT_EQ(test, mtk_reset_set_clr_reg(&infra_rst_desc, id, false,
						 &reg, &mask), 0);
	KUNIT_EXPECT_EQ(test, reg, expected_reg);
	KUNIT_EXPECT_EQ(test, mask, BIT(0));
	KUNIT_ASSERT_EQ(test, mtk_reset_set_clr_reg(&infra_rst_desc, id, true,
						 &reg, &mask), 0);
	KUNIT_EXPECT_EQ(test, reg, expected_reg + 4);
	KUNIT_EXPECT_EQ(test, mask, BIT(0));
}

static void mt6797_reset_thermal(struct kunit *test)
{
	expect_pair(test, MT6797_INFRA_THERM_CTRL_RST, 0x120);
}

static void mt6797_reset_pwrap(struct kunit *test)
{
	expect_pair(test, MT6797_INFRA_PMIC_WRAP_RST, 0x140);
}

static void mt6797_reset_unexposed(struct kunit *test)
{
	KUNIT_EXPECT_EQ(test, mtk_reset_xlate_index(&infra_rst_desc, 2), -EINVAL);
	KUNIT_EXPECT_EQ(test, mtk_reset_xlate_index(&infra_rst_desc, 64), -EINVAL);
}

static struct kunit_case mt6797_reset_cases[] = {
	KUNIT_CASE(mt6797_reset_descriptor),
	KUNIT_CASE(mt6797_reset_thermal),
	KUNIT_CASE(mt6797_reset_pwrap),
	KUNIT_CASE(mt6797_reset_unexposed),
	{}
};

static struct kunit_suite mt6797_reset_suite = {
	.name = "mt6797-infracfg-reset",
	.test_cases = mt6797_reset_cases,
};

kunit_test_suite(mt6797_reset_suite);

MODULE_LICENSE("GPL");
'''


def replace(text, old, new):
    if text.count(old) != 1:
        raise ValueError('source anchor absent or ambiguous')
    return text.replace(old, new, 1)


def phase_edits(files, phase):
    """Pure transformation; caller pins and validates the complete input inventory."""
    out = dict(files)

    def change(path, old, new):
        out[path] = replace(out[path], old, new)

    def create(path, content):
        if path in out:
            raise ValueError('new source path already exists: ' + path)
        out[path] = content

    if phase == 'bounds':
        create(CLK + 'reset-internal.h', BOUNDS)
        change(CLK + 'reset.c', '#include "reset.h"', '#include "reset-internal.h"')
        change(CLK + 'reset.c', '''	unsigned int deassert_ofs = deassert ? 0x4 : 0;

	return regmap_write(data->regmap,
			    data->desc->rst_bank_ofs[id / RST_NR_PER_BANK] +
			    deassert_ofs,
			    BIT(id % RST_NR_PER_BANK));''', '''	unsigned int reg, mask;
	int ret;

	ret = mtk_reset_set_clr_reg(data->desc, id, deassert, &reg, &mask);
	if (ret)
		return ret;

	return regmap_write(data->regmap, reg, mask);''')
        change(CLK + 'reset.c', '''	if (reset_spec->args[0] >= rcdev->nr_resets ||
	    reset_spec->args[0] >= data->desc->rst_idx_map_nr)''',
               '\tif (reset_spec->args[0] >= rcdev->nr_resets)')
        change(CLK + 'reset.c', '\treturn data->desc->rst_idx_map[reset_spec->args[0]];',
               '\treturn mtk_reset_xlate_index(data->desc, reset_spec->args[0]);')
    elif phase == 'bounds-test':
        create(CLK + 'reset-test.c', GENERIC_TEST)
        change(CLK + 'Kconfig', 'config COMMON_CLK_MEDIATEK_FHCTL\n', '''config COMMON_CLK_MEDIATEK_RESET_KUNIT_TEST
	tristate "Test MediaTek reset bounds" if !KUNIT_ALL_TESTS
	depends on KUNIT
	default KUNIT_ALL_TESTS
	help
	  Test reset index and SET/CLEAR register translation without
	  registering a reset controller or accessing hardware.

config COMMON_CLK_MEDIATEK_FHCTL
''')
        change(CLK + 'Makefile', '\nobj-$(CONFIG_COMMON_CLK_MEDIATEK_FHCTL)',
               '\nobj-$(CONFIG_COMMON_CLK_MEDIATEK_RESET_KUNIT_TEST) += reset-test.o\nobj-$(CONFIG_COMMON_CLK_MEDIATEK_FHCTL)')
    elif phase == 'binding':
        create(BINDING, HEADER)
        change(SCHEMA, '          - mediatek,mt6795-infracfg\n          - mediatek,mt7622-infracfg',
               '          - mediatek,mt6795-infracfg\n          - mediatek,mt6797-infracfg\n          - mediatek,mt7622-infracfg')
    elif phase == 'provider':
        create(CLK + 'clk-mt6797-reset.h', DESCRIPTOR)
        change(CLK + 'clk-mt6797.c', '#include "clk-pll.h"',
               '#include "clk-pll.h"\n#include "clk-mt6797-reset.h"')
        change(CLK + 'clk-mt6797.c', '''static int mtk_infrasys_init(struct platform_device *pdev)
{
	int i;
	struct device_node *node = pdev->dev.of_node;

''', '''static int mtk_infrasys_init(struct platform_device *pdev)
{
	struct device_node *node = pdev->dev.of_node;
	int i, ret;

	ret = mtk_register_reset_controller_with_dev(&pdev->dev, &infra_rst_desc);
	if (ret)
		return ret;

''')
    elif phase == 'provider-test':
        create(CLK + 'clk-mt6797-reset-test.c', SOC_TEST)
        change(CLK + 'Kconfig', 'config COMMON_CLK_MT6797_MMSYS\n', '''config COMMON_CLK_MT6797_RESET_KUNIT_TEST
	tristate "Test MT6797 infracfg reset mapping" if !KUNIT_ALL_TESTS
	depends on KUNIT
	default KUNIT_ALL_TESTS
	help
	  Test the two supported MT6797 reset lines and the rejected
	  public indices. This test does not access hardware.

config COMMON_CLK_MT6797_MMSYS
''')
        change(CLK + 'Makefile', 'obj-$(CONFIG_COMMON_CLK_MT6797) += clk-mt6797.o\n',
               'obj-$(CONFIG_COMMON_CLK_MT6797) += clk-mt6797.o\nobj-$(CONFIG_COMMON_CLK_MT6797_RESET_KUNIT_TEST) += clk-mt6797-reset-test.o\n')
    elif phase == 'dts':
        change(DTS, '''compatible = "mediatek,mt6797-infracfg", "syscon";
		reg = <0 0x10001000 0 0x1000>;
		#clock-cells = <1>;
	};''', '''compatible = "mediatek,mt6797-infracfg", "syscon";
		reg = <0 0x10001000 0 0x1000>;
		#clock-cells = <1>;
		#reset-cells = <1>;
	};''')
    else:
        raise ValueError('unknown phase')
    return out


def expected_stages(fetcher):
    manifest = json.loads((HERE.parent / 'derivation-inputs.json').read_text())
    files = {}
    for entry in manifest['remote']:
        source = fetcher(entry)
        data = source.encode('utf-8')
        if len(data) != entry['bytes'] or hashlib.sha256(data).hexdigest() != entry['sha256']:
            raise ValueError('pinned derivation input mismatch: ' + entry['path'])
        files[entry['path']] = source
    stages = [files]
    for phase in PHASES:
        stages.append(phase_edits(stages[-1], phase))
    return stages


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--phase', choices=PHASES, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    if not str(root).startswith('/workspace/gemini-pda/tmp/infracfg-topic.'):
        raise ValueError('only an isolated Buildbox scratch checkout is allowed')
    manifest = json.loads((HERE.parent / 'derivation-inputs.json').read_text())
    # Reconstruct every expected intermediate from immutable Git parent bytes.
    import subprocess
    def original(entry):
        data = subprocess.check_output(['git', '-C', str(root), 'show',
                                        manifest['upstream_commit'] + ':' + entry['path']])
        if len(data) != entry['bytes'] or hashlib.sha256(data).hexdigest() != entry['sha256']:
            raise ValueError('pinned parent changed: ' + entry['path'])
        return data.decode('utf-8')
    stages = expected_stages(original)
    new_paths = sorted(set(stages[-1]) - set(stages[0]))
    existing = subprocess.check_output(['git', '-C', str(root), 'ls-tree', '-r',
                                       '--name-only', manifest['upstream_commit'],
                                       '--', *new_paths], text=True)
    if existing:
        raise ValueError('new path already exists in upstream Git tree')
    index = PHASES.index(args.phase)
    before, after = stages[index:index + 2]
    # Check the entire derivation inventory before any edit, including future paths.
    for name in stages[-1]:
        path = root / name
        if path.is_symlink() or (name in before and
                                (not path.is_file() or path.read_text() != before[name])):
            raise ValueError('intermediate source mismatch: ' + name)
        if name not in before and path.exists():
            raise ValueError('unexpected existing path: ' + name)
    for name, content in after.items():
        if before.get(name) != content:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)


if __name__ == '__main__':
    main()
