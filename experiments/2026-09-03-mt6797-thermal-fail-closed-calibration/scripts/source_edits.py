#!/usr/bin/env python3
"""Apply deterministic MT6797 thermal calibration production and KUnit edits."""

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


def policy_header() -> str:
    return dedent("""\
    /* SPDX-License-Identifier: GPL-2.0-only */
    #ifndef __MTK_AUXADC_THERMAL_INTERNAL_H
    #define __MTK_AUXADC_THERMAL_INTERNAL_H

    #include <linux/errno.h>
    #include <linux/types.h>

    static inline int
    mtk_thermal_calibration_status(bool required, int ret)
    {
    \tif (!ret || (!required && ret != -EPROBE_DEFER))
    \t\treturn 0;

    \treturn ret;
    }

    static inline bool
    mtk_thermal_calibration_length_valid(bool required, size_t len)
    {
    \tconst size_t expected = 3 * sizeof(u32);

    \treturn required ? len == expected : len >= expected;
    }

    #endif /* __MTK_AUXADC_THERMAL_INTERNAL_H */
    """)


def kunit_source() -> str:
    return dedent("""\
    // SPDX-License-Identifier: GPL-2.0-only
    #include <kunit/test.h>

    #include "auxadc_thermal_internal.h"

    static void mtk_thermal_optional_success(struct kunit *test)
    {
    \tKUNIT_EXPECT_EQ(test, mtk_thermal_calibration_status(false, 0), 0);
    }

    static void mtk_thermal_required_success(struct kunit *test)
    {
    \tKUNIT_EXPECT_EQ(test, mtk_thermal_calibration_status(true, 0), 0);
    }

    static void mtk_thermal_optional_missing_falls_back(struct kunit *test)
    {
    \tKUNIT_EXPECT_EQ(test,
    \t\t\tmtk_thermal_calibration_status(false, -ENOENT), 0);
    }

    static void mtk_thermal_required_missing_fails(struct kunit *test)
    {
    \tKUNIT_EXPECT_EQ(test,
    \t\t\tmtk_thermal_calibration_status(true, -ENOENT), -ENOENT);
    }

    static void mtk_thermal_optional_invalid_falls_back(struct kunit *test)
    {
    \tKUNIT_EXPECT_EQ(test,
    \t\t\tmtk_thermal_calibration_status(false, -EINVAL), 0);
    }

    static void mtk_thermal_required_invalid_fails(struct kunit *test)
    {
    \tKUNIT_EXPECT_EQ(test,
    \t\t\tmtk_thermal_calibration_status(true, -EINVAL), -EINVAL);
    }

    static void mtk_thermal_defer_always_propagates(struct kunit *test)
    {
    \tKUNIT_EXPECT_EQ(test,
    \t\t\tmtk_thermal_calibration_status(false, -EPROBE_DEFER),
    \t\t\t-EPROBE_DEFER);
    \tKUNIT_EXPECT_EQ(test,
    \t\t\tmtk_thermal_calibration_status(true, -EPROBE_DEFER),
    \t\t\t-EPROBE_DEFER);
    }

    static void mtk_thermal_optional_length_preserves_minimum(struct kunit *test)
    {
    \tKUNIT_EXPECT_FALSE(test,
    \t\tmtk_thermal_calibration_length_valid(false, 2 * sizeof(u32)));
    \tKUNIT_EXPECT_TRUE(test,
    \t\tmtk_thermal_calibration_length_valid(false, 3 * sizeof(u32)));
    \tKUNIT_EXPECT_TRUE(test,
    \t\tmtk_thermal_calibration_length_valid(false, 4 * sizeof(u32)));
    }

    static void mtk_thermal_required_length_is_exact(struct kunit *test)
    {
    \tKUNIT_EXPECT_FALSE(test,
    \t\tmtk_thermal_calibration_length_valid(true, 2 * sizeof(u32)));
    \tKUNIT_EXPECT_TRUE(test,
    \t\tmtk_thermal_calibration_length_valid(true, 3 * sizeof(u32)));
    \tKUNIT_EXPECT_FALSE(test,
    \t\tmtk_thermal_calibration_length_valid(true, 4 * sizeof(u32)));
    }

    static struct kunit_case mtk_thermal_calibration_cases[] = {
    \tKUNIT_CASE(mtk_thermal_optional_success),
    \tKUNIT_CASE(mtk_thermal_required_success),
    \tKUNIT_CASE(mtk_thermal_optional_missing_falls_back),
    \tKUNIT_CASE(mtk_thermal_required_missing_fails),
    \tKUNIT_CASE(mtk_thermal_optional_invalid_falls_back),
    \tKUNIT_CASE(mtk_thermal_required_invalid_fails),
    \tKUNIT_CASE(mtk_thermal_defer_always_propagates),
    \tKUNIT_CASE(mtk_thermal_optional_length_preserves_minimum),
    \tKUNIT_CASE(mtk_thermal_required_length_is_exact),
    \t{}
    };

    static struct kunit_suite mtk_thermal_calibration_suite = {
    \t.name = "mtk-thermal-calibration-policy",
    \t.test_cases = mtk_thermal_calibration_cases,
    };

    kunit_test_suite(mtk_thermal_calibration_suite);

    MODULE_LICENSE("GPL");
    """)


def edit_production(root: Path) -> None:
    thermal = root / "drivers/thermal/mediatek"
    driver = thermal / "auxadc_thermal.c"
    write_new(thermal / "auxadc_thermal_internal.h", policy_header())
    replace_once(
        driver,
        '#include <linux/soc/mediatek/mt6797-eem-readback.h>\n\n'
        '#include "../thermal_hwmon.h"\n',
        '#include <linux/soc/mediatek/mt6797-eem-readback.h>\n\n'
        '#include "auxadc_thermal_internal.h"\n'
        '#include "../thermal_hwmon.h"\n',
    )
    replace_once(
        driver,
        "\tbool need_switch_bank;\n",
        "\tbool need_switch_bank;\n\tbool requires_calibration;\n",
    )
    replace_once(
        driver,
        "\t.need_switch_bank = true,\n\t.bank_data = {\n",
        "\t.need_switch_bank = true,\n\t.requires_calibration = true,\n"
        "\t.bank_data = {\n",
    )
    replace_once(
        driver,
        "\tcell = nvmem_cell_get(dev, \"calibration-data\");\n"
        "\tif (IS_ERR(cell)) {\n"
        "\t\tif (PTR_ERR(cell) == -EPROBE_DEFER)\n"
        "\t\t\treturn PTR_ERR(cell);\n"
        "\t\treturn 0;\n"
        "\t}\n",
        "\tcell = nvmem_cell_get(dev, \"calibration-data\");\n"
        "\tif (IS_ERR(cell))\n"
        "\t\treturn mtk_thermal_calibration_status(\n"
        "\t\t\tmt->conf->requires_calibration, PTR_ERR(cell));\n",
    )
    replace_once(
        driver,
        "\tif (len < 3 * sizeof(u32)) {\n",
        "\tif (!mtk_thermal_calibration_length_valid(\n"
        "\t\t    mt->conf->requires_calibration, len)) {\n",
    )
    replace_once(
        driver,
        "\tif (ret) {\n"
        "\t\tdev_info(dev, \"Device not calibrated, using default calibration values\\n\");\n"
        "\t\tret = 0;\n"
        "\t}\n",
        "\tif (ret) {\n"
        "\t\tret = mtk_thermal_calibration_status(\n"
        "\t\t\tmt->conf->requires_calibration, ret);\n"
        "\t\tif (!ret)\n"
        "\t\t\tdev_info(dev, \"Device not calibrated, using default calibration values\\n\");\n"
        "\t}\n",
    )


def edit_kunit(root: Path) -> None:
    thermal = root / "drivers/thermal/mediatek"
    kconfig = thermal / "Kconfig"
    makefile = thermal / "Makefile"
    write_new(thermal / "auxadc_thermal_test.c", kunit_source())
    replace_once(
        kconfig,
        "config MTK_LVTS_THERMAL\n",
        dedent("""\
        config MTK_SOC_THERMAL_KUNIT_TEST
        \ttristate "Test MediaTek AUXADC thermal calibration policy" if !KUNIT_ALL_TESTS
        \tdepends on KUNIT
        \tdepends on MTK_SOC_THERMAL
        \tdefault KUNIT_ALL_TESTS
        \thelp
        \t  Test the hardware-free calibration requirement policy used by
        \t  the MediaTek AUXADC thermal driver. The test performs no MMIO,
        \t  clock, reset, NVMEM, or platform-device operation.

        config MTK_LVTS_THERMAL
        """),
    )
    replace_once(
        makefile,
        "obj-$(CONFIG_MTK_SOC_THERMAL)\t+= auxadc_thermal.o\n",
        "obj-$(CONFIG_MTK_SOC_THERMAL)\t+= auxadc_thermal.o\n"
        "obj-$(CONFIG_MTK_SOC_THERMAL_KUNIT_TEST) += auxadc_thermal_test.o\n",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--phase", choices=("production", "kunit"), required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    if args.phase == "production":
        edit_production(root)
    else:
        edit_kunit(root)


if __name__ == "__main__":
    main()
