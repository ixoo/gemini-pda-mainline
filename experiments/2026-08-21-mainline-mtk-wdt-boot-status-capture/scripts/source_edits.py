#!/usr/bin/env python3
"""Apply deterministic MediaTek watchdog boot-status capture changes."""

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


def write_new(path: Path, source: Path) -> None:
    if path.exists():
        raise SystemExit(f"refusing to overwrite existing path: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


def apply(root: Path, experiment: Path) -> None:
    kconfig = root / "drivers/watchdog/Kconfig"
    driver = root / "drivers/watchdog/mtk_wdt.c"

    replace_once(
        kconfig,
        "config DIGICOLOR_WATCHDOG\n",
        dedent("""\
        config MEDIATEK_WATCHDOG_BOOT_STATUS_CAPTURE
        \tbool "Capture raw MediaTek watchdog boot status"
        \tdepends on MEDIATEK_WATCHDOG=y
        \thelp
        \t  Capture the complete raw boot-status word once, before watchdog
        \t  initialization, on MediaTek variants with an audited status
        \t  register. Expose only an immutable typed snapshot; this option
        \t  does not classify reset provenance.

        config MEDIATEK_WATCHDOG_BOOT_STATUS_KUNIT_TEST
        \tbool "KUnit tests for MediaTek watchdog boot-status capture"
        \tdepends on KUNIT=y
        \tdepends on MEDIATEK_WATCHDOG=y
        \tselect MEDIATEK_WATCHDOG_BOOT_STATUS_CAPTURE
        \thelp
        \t  Test invalid, exact, every-bit, and immutable snapshot behavior
        \t  without MMIO or watchdog operations. The suite has no production
        \t  hook and does not interpret the raw status as reset provenance.

        \t  If unsure, say N.

        config DIGICOLOR_WATCHDOG
        """),
    )

    replace_once(
        driver,
        "#include <linux/moduleparam.h>\n",
        "#include <linux/moduleparam.h>\n#include <linux/mtk_wdt.h>\n",
    )
    replace_once(
        driver,
        "#include <linux/interrupt.h>\n",
        dedent("""\
        #include <linux/interrupt.h>

        #if IS_ENABLED(CONFIG_MEDIATEK_WATCHDOG_BOOT_STATUS_KUNIT_TEST)
        #include <kunit/test.h>
        #endif
        """),
    )
    replace_once(
        driver,
        "#define WDT_RST\t\t\t0x08\n",
        "#define WDT_RST\t\t\t0x08\n#define WDT_STATUS\t\t0x0c\n",
    )
    replace_once(
        driver,
        "\tbool use_auto_restart;\n};\n\nstruct mtk_wdt_data {\n",
        dedent("""\
        \tbool use_auto_restart;
        #ifdef CONFIG_MEDIATEK_WATCHDOG_BOOT_STATUS_CAPTURE
        \tstruct mtk_wdt_boot_status boot_status;
        #endif
        };

        struct mtk_wdt_data {
        """),
    )
    replace_once(
        driver,
        "\tbool use_auto_restart;\n\tunsigned int restart_priority;\n};\n",
        "\tbool use_auto_restart;\n\tbool has_boot_status;\n"
        "\tunsigned int restart_priority;\n};\n",
    )
    replace_once(
        driver,
        "static const struct mtk_wdt_data mt6797_data = {\n"
        "\t.toprgu_sw_rst_num = MT6797_TOPRGU_SW_RST_NUM,\n",
        "static const struct mtk_wdt_data mt6797_data = {\n"
        "\t.toprgu_sw_rst_num = MT6797_TOPRGU_SW_RST_NUM,\n"
        "\t.has_boot_status = true,\n",
    )
    replace_once(
        driver,
        "/**\n * toprgu_reset_sw_en_unlocked() - enable/disable software control for reset bit\n",
        dedent("""\
        #ifdef CONFIG_MEDIATEK_WATCHDOG_BOOT_STATUS_CAPTURE
        static void
        mtk_wdt_capture_boot_status(struct mtk_wdt_boot_status *status, u32 raw)
        {
        \tif (READ_ONCE(status->valid))
        \t\treturn;

        \tWRITE_ONCE(status->raw, raw);
        \t/* Publish the complete raw word before marking it valid. */
        \tsmp_store_release(&status->valid, true);
        }

        static int
        mtk_wdt_copy_boot_status(const struct mtk_wdt_boot_status *status,
        \t\t\t struct mtk_wdt_boot_status *snapshot)
        {
        \tif (!snapshot)
        \t\treturn -EINVAL;

        \t*snapshot = (struct mtk_wdt_boot_status){};
        \t/* Pair with capture so a valid snapshot observes the raw word. */
        \tif (!smp_load_acquire(&status->valid))
        \t\treturn -ENODATA;

        \tsnapshot->raw = READ_ONCE(status->raw);
        \tsnapshot->valid = true;
        \treturn 0;
        }

        int mtk_wdt_boot_status_snapshot(struct device *dev,
        \t\t\t\t struct mtk_wdt_boot_status *snapshot)
        {
        \tstruct mtk_wdt_dev *mtk_wdt;

        \tif (!snapshot)
        \t\treturn -EINVAL;
        \t*snapshot = (struct mtk_wdt_boot_status){};
        \tif (!dev)
        \t\treturn -EINVAL;

        \tmtk_wdt = dev_get_drvdata(dev);
        \tif (!mtk_wdt)
        \t\treturn -ENODEV;

        \treturn mtk_wdt_copy_boot_status(&mtk_wdt->boot_status, snapshot);
        }
        EXPORT_SYMBOL_GPL(mtk_wdt_boot_status_snapshot);
        #endif

        /**
         * toprgu_reset_sw_en_unlocked() - enable/disable software control for reset bit
        """),
    )
    replace_once(
        driver,
        "\tmtk_wdt->wdt_base = devm_platform_ioremap_resource(pdev, 0);\n"
        "\tif (IS_ERR(mtk_wdt->wdt_base))\n"
        "\t\treturn PTR_ERR(mtk_wdt->wdt_base);\n\n"
        "\tirq = platform_get_irq_optional(pdev, 0);\n",
        dedent("""\
        \tmtk_wdt->wdt_base = devm_platform_ioremap_resource(pdev, 0);
        \tif (IS_ERR(mtk_wdt->wdt_base))
        \t\treturn PTR_ERR(mtk_wdt->wdt_base);

        #ifdef CONFIG_MEDIATEK_WATCHDOG_BOOT_STATUS_CAPTURE
        \tif (wdt_data && wdt_data->has_boot_status)
        \t\tmtk_wdt_capture_boot_status(&mtk_wdt->boot_status,
        \t\t\t\t\t    readl(mtk_wdt->wdt_base + WDT_STATUS));
        #endif

        \tirq = platform_get_irq_optional(pdev, 0);
        """),
    )
    replace_once(
        driver,
        "module_platform_driver(mtk_wdt_driver);\n",
        dedent("""\
        module_platform_driver(mtk_wdt_driver);

        #if IS_ENABLED(CONFIG_MEDIATEK_WATCHDOG_BOOT_STATUS_KUNIT_TEST)
        static void mtk_wdt_boot_status_invalid_test(struct kunit *test)
        {
        \tstruct mtk_wdt_boot_status snapshot = {
        \t\t.raw = U32_MAX,
        \t\t.valid = true,
        \t};
        \tstruct mtk_wdt_boot_status stored = {};

        \tKUNIT_EXPECT_EQ(test, -ENODATA,
        \t\t\tmtk_wdt_copy_boot_status(&stored, &snapshot));
        \tKUNIT_EXPECT_EQ(test, 0U, snapshot.raw);
        \tKUNIT_EXPECT_FALSE(test, snapshot.valid);
        }

        static void mtk_wdt_boot_status_exact_test(struct kunit *test)
        {
        \tstruct mtk_wdt_boot_status snapshot = {};
        \tstruct mtk_wdt_boot_status stored = {};

        \tmtk_wdt_capture_boot_status(&stored, 0xa5c33ca5);
        \tKUNIT_ASSERT_EQ(test, 0,
        \t\t\tmtk_wdt_copy_boot_status(&stored, &snapshot));
        \tKUNIT_EXPECT_EQ(test, 0xa5c33ca5U, snapshot.raw);
        \tKUNIT_EXPECT_TRUE(test, snapshot.valid);
        }

        static void mtk_wdt_boot_status_every_bit_test(struct kunit *test)
        {
        \tunsigned int bit;

        \tfor (bit = 0; bit < 32; bit++) {
        \t\tstruct mtk_wdt_boot_status snapshot = {};
        \t\tstruct mtk_wdt_boot_status stored = {};

        \t\tmtk_wdt_capture_boot_status(&stored, BIT(bit));
        \t\tKUNIT_ASSERT_EQ(test, 0,
        \t\t\t\tmtk_wdt_copy_boot_status(&stored, &snapshot));
        \t\tKUNIT_EXPECT_EQ(test, BIT(bit), snapshot.raw);
        \t\tKUNIT_EXPECT_TRUE(test, snapshot.valid);
        \t}
        }

        static void mtk_wdt_boot_status_immutable_test(struct kunit *test)
        {
        \tstruct mtk_wdt_boot_status snapshot = {};
        \tstruct mtk_wdt_boot_status stored = {};

        \tmtk_wdt_capture_boot_status(&stored, 0x13579bdf);
        \tmtk_wdt_capture_boot_status(&stored, 0xeca86420);
        \tKUNIT_ASSERT_EQ(test, 0,
        \t\t\tmtk_wdt_copy_boot_status(&stored, &snapshot));
        \tKUNIT_EXPECT_EQ(test, 0x13579bdfU, snapshot.raw);
        \tKUNIT_EXPECT_TRUE(test, snapshot.valid);
        }

        static struct kunit_case mtk_wdt_boot_status_cases[] = {
        \tKUNIT_CASE(mtk_wdt_boot_status_invalid_test),
        \tKUNIT_CASE(mtk_wdt_boot_status_exact_test),
        \tKUNIT_CASE(mtk_wdt_boot_status_every_bit_test),
        \tKUNIT_CASE(mtk_wdt_boot_status_immutable_test),
        \t{}
        };

        static struct kunit_suite mtk_wdt_boot_status_suite = {
        \t.name = "mtk-wdt-boot-status",
        \t.test_cases = mtk_wdt_boot_status_cases,
        };

        kunit_test_suite(mtk_wdt_boot_status_suite);
        #endif
        """),
    )

    write_new(root / "include/linux/mtk_wdt.h", experiment / "source/mtk_wdt.h")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    if not (root / "drivers/watchdog/mtk_wdt.c").is_file():
        raise SystemExit("unexpected source root")
    apply(root, Path(__file__).resolve().parents[1])


if __name__ == "__main__":
    main()
