#!/usr/bin/env python3
"""Apply deterministic MT6797 infracfg reset production and KUnit edits."""

from __future__ import annotations

import argparse
from pathlib import Path
from textwrap import dedent


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one edit anchor, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def write_new(path: Path, content: str) -> None:
    if path.exists():
        raise SystemExit(f"refusing to overwrite existing path: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def descriptor_header() -> str:
    return dedent("""\
    /* SPDX-License-Identifier: GPL-2.0-only */
    #ifndef __DRV_CLK_MTK_CLK_MT6797_RESET_H
    #define __DRV_CLK_MTK_CLK_MT6797_RESET_H

    #include <dt-bindings/reset/mt6797-resets.h>

    #include "reset.h"

    /* Only reset paths confirmed by exact MT6797 sources are exposed. */
    static u16 infra_rst_ofs[] = {
    \tINFRA_RST0_SET_OFFSET,
    \tINFRA_RST2_SET_OFFSET,
    };

    static u16 infra_rst_idx_map[] = {
    \t[MT6797_INFRA_THERM_CTRL_RST] = 0 * RST_NR_PER_BANK,
    \t[MT6797_INFRA_PMIC_WRAP_RST] = 1 * RST_NR_PER_BANK,
    };

    static const struct mtk_clk_rst_desc infra_rst_desc = {
    \t.version = MTK_RST_SET_CLR,
    \t.rst_bank_ofs = infra_rst_ofs,
    \t.rst_bank_nr = ARRAY_SIZE(infra_rst_ofs),
    \t.rst_idx_map = infra_rst_idx_map,
    \t.rst_idx_map_nr = ARRAY_SIZE(infra_rst_idx_map),
    };

    #endif /* __DRV_CLK_MTK_CLK_MT6797_RESET_H */
    """)


def test_source() -> str:
    return dedent("""\
    // SPDX-License-Identifier: GPL-2.0-only
    #include <kunit/test.h>

    #include "clk-mt6797-reset.h"

    static int mt6797_resolve(unsigned int index, bool deassert,
    \t\t\t  unsigned int *reg, unsigned int *mask)
    {
    \tint id;

    \tid = mtk_reset_xlate_index(&infra_rst_desc, index);
    \tif (id < 0)
    \t\treturn id;

    \treturn mtk_reset_set_clr_reg(&infra_rst_desc, id, deassert,
    \t\t\t\t     reg, mask);
    }

    static void mt6797_reset_descriptor_contract(struct kunit *test)
    {
    \tKUNIT_EXPECT_EQ(test, infra_rst_desc.version, MTK_RST_SET_CLR);
    \tKUNIT_EXPECT_EQ(test, infra_rst_desc.rst_bank_nr, 2U);
    \tKUNIT_EXPECT_EQ(test, infra_rst_desc.rst_idx_map_nr, 2U);
    \tKUNIT_EXPECT_EQ(test, infra_rst_ofs[0], (u16)0x120);
    \tKUNIT_EXPECT_EQ(test, infra_rst_ofs[1], (u16)0x140);
    }

    static void mt6797_reset_thermal_transaction(struct kunit *test)
    {
    \tunsigned int index = MT6797_INFRA_THERM_CTRL_RST;
    \tunsigned int mask = 0, reg = 0;
    \tint ret;

    \tret = mt6797_resolve(index, false, &reg, &mask);
    \tKUNIT_ASSERT_EQ(test, ret, 0);
    \tKUNIT_EXPECT_EQ(test, reg, 0x120U);
    \tKUNIT_EXPECT_EQ(test, mask, BIT(0));
    \tret = mt6797_resolve(index, true, &reg, &mask);
    \tKUNIT_ASSERT_EQ(test, ret, 0);
    \tKUNIT_EXPECT_EQ(test, reg, 0x124U);
    \tKUNIT_EXPECT_EQ(test, mask, BIT(0));
    }

    static void mt6797_reset_pwrap_transaction(struct kunit *test)
    {
    \tunsigned int index = MT6797_INFRA_PMIC_WRAP_RST;
    \tunsigned int mask = 0, reg = 0;
    \tint ret;

    \tret = mt6797_resolve(index, false, &reg, &mask);
    \tKUNIT_ASSERT_EQ(test, ret, 0);
    \tKUNIT_EXPECT_EQ(test, reg, 0x140U);
    \tKUNIT_EXPECT_EQ(test, mask, BIT(0));
    \tret = mt6797_resolve(index, true, &reg, &mask);
    \tKUNIT_ASSERT_EQ(test, ret, 0);
    \tKUNIT_EXPECT_EQ(test, reg, 0x144U);
    \tKUNIT_EXPECT_EQ(test, mask, BIT(0));
    }

    static void mt6797_reset_unknown_public_id_rejected(struct kunit *test)
    {
    \tKUNIT_EXPECT_EQ(test, mtk_reset_xlate_index(&infra_rst_desc, 2),
    \t\t\t-EINVAL);
    }

    static void mt6797_reset_old_linear_id_rejected(struct kunit *test)
    {
    \tKUNIT_EXPECT_EQ(test, mtk_reset_xlate_index(&infra_rst_desc, 64),
    \t\t\t-EINVAL);
    }

    static void mt6797_reset_internal_bank_overflow_rejected(struct kunit *test)
    {
    \tunsigned long id = 2 * RST_NR_PER_BANK;
    \tunsigned int mask = 0, reg = 0;
    \tint ret;

    \tret = mtk_reset_set_clr_reg(&infra_rst_desc, id, false, &reg, &mask);
    \tKUNIT_EXPECT_EQ(test, ret, -EINVAL);
    }

    static struct kunit_case mt6797_infra_reset_cases[] = {
    \tKUNIT_CASE(mt6797_reset_descriptor_contract),
    \tKUNIT_CASE(mt6797_reset_thermal_transaction),
    \tKUNIT_CASE(mt6797_reset_pwrap_transaction),
    \tKUNIT_CASE(mt6797_reset_unknown_public_id_rejected),
    \tKUNIT_CASE(mt6797_reset_old_linear_id_rejected),
    \tKUNIT_CASE(mt6797_reset_internal_bank_overflow_rejected),
    \t{}
    };

    static struct kunit_suite mt6797_infra_reset_suite = {
    \t.name = "mt6797-infracfg-reset-translation",
    \t.test_cases = mt6797_infra_reset_cases,
    };

    kunit_test_suite(mt6797_infra_reset_suite);

    MODULE_LICENSE("GPL");
    """)


def edit_binding(root: Path) -> None:
    binding = root / "include/dt-bindings/reset/mt6797-resets.h"

    text = binding.read_text(encoding="utf-8")
    start = text.index("/* INFRACFG resets: INFRA_GLOBALCON_RST0 */")
    end = text.index("/* TOPRGU resets: WDT_SWSYSRST */")
    replacement = (
        "/* Source-proven infracfg reset inputs. */\n"
        "#define MT6797_INFRA_THERM_CTRL_RST\t0\n"
        "#define MT6797_INFRA_PMIC_WRAP_RST\t1\n\n"
    )
    binding.write_text(text[:start] + replacement + text[end:], encoding="utf-8")


def edit_production(root: Path) -> None:
    clock = root / "drivers/clk/mediatek"

    replace_once(
        clock / "reset.h",
        "#include <linux/reset-controller.h>\n#include <linux/types.h>\n",
        "#include <linux/bitops.h>\n#include <linux/errno.h>\n"
        "#include <linux/reset-controller.h>\n#include <linux/types.h>\n",
    )
    replace_once(
        clock / "reset.h",
        "struct mtk_clk_rst_data {\n"
        "\tstruct regmap *regmap;\n"
        "\tstruct reset_controller_dev rcdev;\n"
        "\tconst struct mtk_clk_rst_desc *desc;\n"
        "};\n\n",
        "struct mtk_clk_rst_data {\n"
        "\tstruct regmap *regmap;\n"
        "\tstruct reset_controller_dev rcdev;\n"
        "\tconst struct mtk_clk_rst_desc *desc;\n"
        "};\n\n"
        "static inline int\n"
        "mtk_reset_xlate_index(const struct mtk_clk_rst_desc *desc,\n"
        "\t\t      unsigned int index)\n"
        "{\n"
        "\tif (!desc->rst_idx_map || index >= desc->rst_idx_map_nr)\n"
        "\t\treturn -EINVAL;\n\n"
        "\treturn desc->rst_idx_map[index];\n"
        "}\n\n"
        "static inline int\n"
        "mtk_reset_set_clr_reg(const struct mtk_clk_rst_desc *desc,\n"
        "\t\t      unsigned long id, bool deassert,\n"
        "\t\t      unsigned int *reg, unsigned int *mask)\n"
        "{\n"
        "\tunsigned int bank = id / RST_NR_PER_BANK;\n\n"
        "\tif (bank >= desc->rst_bank_nr)\n"
        "\t\treturn -EINVAL;\n\n"
        "\t*reg = desc->rst_bank_ofs[bank] + (deassert ? 0x4 : 0);\n"
        "\t*mask = BIT(id % RST_NR_PER_BANK);\n\n"
        "\treturn 0;\n"
        "}\n\n",
    )
    replace_once(
        clock / "reset.c",
        "\tstruct mtk_clk_rst_data *data = to_mtk_clk_rst_data(rcdev);\n"
        "\tunsigned int deassert_ofs = deassert ? 0x4 : 0;\n\n"
        "\treturn regmap_write(data->regmap,\n"
        "\t\t\t    data->desc->rst_bank_ofs[id / RST_NR_PER_BANK] +\n"
        "\t\t\t    deassert_ofs,\n"
        "\t\t\t    BIT(id % RST_NR_PER_BANK));\n",
        "\tstruct mtk_clk_rst_data *data = to_mtk_clk_rst_data(rcdev);\n"
        "\tunsigned int mask, reg;\n"
        "\tint ret;\n\n"
        "\tret = mtk_reset_set_clr_reg(data->desc, id, deassert, &reg, &mask);\n"
        "\tif (ret)\n"
        "\t\treturn ret;\n\n"
        "\treturn regmap_write(data->regmap, reg, mask);\n",
    )
    replace_once(
        clock / "reset.c",
        "\tif (reset_spec->args[0] >= rcdev->nr_resets ||\n"
        "\t    reset_spec->args[0] >= data->desc->rst_idx_map_nr)\n"
        "\t\treturn -EINVAL;\n\n"
        "\treturn data->desc->rst_idx_map[reset_spec->args[0]];\n",
        "\tif (reset_spec->args[0] >= rcdev->nr_resets)\n"
        "\t\treturn -EINVAL;\n\n"
        "\treturn mtk_reset_xlate_index(data->desc, reset_spec->args[0]);\n",
    )
    replace_once(
        clock / "clk-mt6797.c",
        '#include "reset.h"\n',
        '#include "clk-mt6797-reset.h"\n',
    )
    replace_once(
        clock / "clk-mt6797.c",
        "static u16 infra_rst_ofs[] = {\n"
        "\t0x120,\n\t0x124,\n\t0x128,\n};\n\n"
        "static const struct mtk_clk_rst_desc infra_rst_desc = {\n"
        "\t.version = MTK_RST_SIMPLE,\n"
        "\t.rst_bank_ofs = infra_rst_ofs,\n"
        "\t.rst_bank_nr = ARRAY_SIZE(infra_rst_ofs),\n"
        "};\n\n",
        "",
    )
    write_new(clock / "clk-mt6797-reset.h", descriptor_header())

def edit_kunit(root: Path) -> None:
    clock = root / "drivers/clk/mediatek"
    write_new(clock / "clk-mt6797-reset-test.c", test_source())
    replace_once(
        clock / "Kconfig",
        "config COMMON_CLK_MT6797_CAMSYS\n",
        dedent("""\
        config COMMON_CLK_MT6797_RESET_KUNIT_TEST
        \ttristate "Test MT6797 infracfg reset translation" if !KUNIT_ALL_TESTS
        \tdepends on KUNIT
        \tdepends on COMMON_CLK_MT6797
        \tdefault KUNIT_ALL_TESTS
        \thelp
        \t  Test the hardware-free MT6797 infracfg reset index, register,
        \t  and mask translation. The test performs no MMIO, regmap,
        \t  clock, reset-controller registration, or platform operation.
        \t  It validates only pure descriptor arithmetic and bounds.

        config COMMON_CLK_MT6797_CAMSYS
        """),
    )
    replace_once(
        clock / "Makefile",
        "obj-$(CONFIG_COMMON_CLK_MT6797) += clk-mt6797.o\n",
        "obj-$(CONFIG_COMMON_CLK_MT6797) += clk-mt6797.o\n"
        "obj-$(CONFIG_COMMON_CLK_MT6797_RESET_KUNIT_TEST) += clk-mt6797-reset-test.o\n",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument(
        "--phase", choices=("binding", "production", "kunit"), required=True
    )
    args = parser.parse_args()
    if args.phase == "binding":
        edit_binding(args.source_root)
    elif args.phase == "production":
        edit_production(args.source_root)
    else:
        edit_kunit(args.source_root)


if __name__ == "__main__":
    main()
