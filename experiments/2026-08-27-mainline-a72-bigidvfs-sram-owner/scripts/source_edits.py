#!/usr/bin/env python3
"""Apply deterministic MT6797 A72 BigiDVFS SRAM-owner source edits."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
from textwrap import dedent


SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATES = SCRIPT_DIR.parent / "templates"


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"{path}: expected one anchor: {old.splitlines()[0]}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def template(name: str) -> str:
    return (TEMPLATES / name).read_text(encoding="utf-8")


PRODUCTION_KCONFIG = dedent("""\
    config MTK_MT6797_A72_BIGIDVFS_SRAM_OWNER
    \tbool "MediaTek MT6797 Cortex-A72 BigiDVFS SRAM-LDO owner"
    \tdepends on MTK_MT6797_DVFSP_BIGIDVFS_BACKEND
    \tdefault n
    \thelp
    \t  Extend the exact BigiDVFS backend with one serialized, attempt-bound,
    \t  one-shot CPU8 SRAM-LDO request. The owner accepts only the fixed 1.1 V
    \t  service, waits 240 microseconds, and requires two stable selector and
    \t  calibration samples through the existing secure read transport.

    \t  This option adds no production caller, generic voltage interface,
    \t  inverse, retry, CPU request, regulator action, retained write, device
    \t  trigger, or boot policy. Every post-call failure seals the owner and
    \t  latches the backend fault. If unsure, say N.

    """)

TEST_KCONFIG = dedent("""\
    config MTK_MT6797_A72_BIGIDVFS_SRAM_OWNER_KUNIT_TEST
    \tbool "KUnit tests for MT6797 A72 BigiDVFS SRAM-LDO owner"
    \tdepends on KUNIT=y
    \tdepends on MTK_MT6797_A72_BIGIDVFS_SRAM_OWNER
    \tdefault n
    \thelp
    \t  Exercise the exact service, settle, stable selector/calibration,
    \t  one-shot, prerequisite, and every injected failure boundary with an
    \t  in-memory transport.

    \t  No SMCCC, physical delay, MMIO, regulator, watchdog, retained RAM,
    \t  PSCI, or CPU operation is used. If unsure, say N.

    """)


def apply_production(root: Path) -> None:
    kconfig = root / "drivers/soc/mediatek/Kconfig"
    source = root / "drivers/soc/mediatek/mt6797-bigidvfs-backend.c"
    public = root / "include/linux/soc/mediatek/mt6797-bigidvfs-backend.h"
    internal = root / "drivers/soc/mediatek/mt6797-bigidvfs-sram-internal.h"

    replace_once(
        kconfig,
        "config MTK_MT6797_A72_PLATFORM_PROVIDER_CLOCK_OBSERVER\n",
        PRODUCTION_KCONFIG +
        "config MTK_MT6797_A72_PLATFORM_PROVIDER_CLOCK_OBSERVER\n",
    )
    replace_once(
        public,
        "#include <linux/types.h>\n",
        "#include <linux/bitops.h>\n"
        "#include <linux/errno.h>\n"
        "#include <linux/kconfig.h>\n"
        "#include <linux/types.h>\n",
    )
    replace_once(
        public,
        "int mt6797_bigidvfs_backend_read(\n",
        template("bigidvfs_sram_public.h.inc") +
        "int mt6797_bigidvfs_backend_read(\n",
    )
    if internal.exists():
        raise SystemExit("BigiDVFS SRAM internal header already exists")
    shutil.copyfile(TEMPLATES / "bigidvfs_sram_internal.h", internal)
    replace_once(source, "#include <linux/device.h>\n",
                 "#include <linux/delay.h>\n#include <linux/device.h>\n")
    replace_once(
        source,
        '#include "mt6797-protected-readback-internal.h"\n',
        '#include "mt6797-bigidvfs-sram-internal.h"\n'
        '#include "mt6797-protected-readback-internal.h"\n',
    )
    replace_once(
        source,
        "\tu64 sample_generation;\n};\n",
        "\tu64 sample_generation;\n"
        "#if IS_ENABLED(CONFIG_MTK_MT6797_A72_BIGIDVFS_SRAM_OWNER)\n"
        "\tstruct mt6797_bigidvfs_sram_owner sram_owner;\n"
        "#endif\n"
        "};\n",
    )
    replace_once(
        source,
        "\tcase MT6797_BIGIDVFS_SRAM_SELECTOR:\n"
        "\tcase MT6797_BIGIDVFS_CONTROL:\n",
        "\tcase MT6797_BIGIDVFS_SRAM_SELECTOR:\n"
        "#if IS_ENABLED(CONFIG_MTK_MT6797_A72_BIGIDVFS_SRAM_OWNER)\n"
        "\tcase MT6797_BIGIDVFS_SRAM_CALIBRATION:\n"
        "#endif\n"
        "\tcase MT6797_BIGIDVFS_CONTROL:\n",
    )
    replace_once(
        source,
        "static void\nmt6797_bigidvfs_mark_fault",
        "#if IS_ENABLED(CONFIG_MTK_MT6797_A72_BIGIDVFS_SRAM_OWNER)\n" +
        template("bigidvfs_sram_source.c.inc") +
        "#endif\n\n"
        "static void\nmt6797_bigidvfs_mark_fault",
    )
    replace_once(
        source,
        "static int mt6797_bigidvfs_backend_probe(struct platform_device *pdev)\n",
        "#if IS_ENABLED(CONFIG_MTK_MT6797_A72_BIGIDVFS_SRAM_OWNER)\n" +
        template("bigidvfs_sram_adapter.c.inc") +
        "#endif\n"
        "static int mt6797_bigidvfs_backend_probe(struct platform_device *pdev)\n",
    )
    replace_once(
        source,
        "\tdev_info(&pdev->dev,\n"
        "\t\t \"secure readback transport ready; owner unregistered\\n\");\n",
        "#if IS_ENABLED(CONFIG_MTK_MT6797_A72_BIGIDVFS_SRAM_OWNER)\n"
        "\tdev_info(&pdev->dev,\n"
        "\t\t \"secure readback and one-shot SRAM owner ready; no caller\\n\");\n"
        "#else\n"
        "\tdev_info(&pdev->dev,\n"
        "\t\t \"secure readback transport ready; owner unregistered\\n\");\n"
        "#endif\n",
    )


def apply_tests(root: Path) -> None:
    kconfig = root / "drivers/soc/mediatek/Kconfig"
    makefile = root / "drivers/soc/mediatek/Makefile"
    target = root / "drivers/soc/mediatek/mt6797-bigidvfs-sram-owner-test.c"

    replace_once(
        kconfig,
        "config MTK_MT6797_A72_PLATFORM_PROVIDER_CLOCK_OBSERVER\n",
        TEST_KCONFIG +
        "config MTK_MT6797_A72_PLATFORM_PROVIDER_CLOCK_OBSERVER\n",
    )
    replace_once(
        makefile,
        "obj-$(CONFIG_MTK_MT6797_DVFSP_BIGIDVFS_BACKEND) += "
        "mt6797-bigidvfs-backend.o\n",
        "obj-$(CONFIG_MTK_MT6797_DVFSP_BIGIDVFS_BACKEND) += "
        "mt6797-bigidvfs-backend.o\n"
        "obj-$(CONFIG_MTK_MT6797_A72_BIGIDVFS_SRAM_OWNER_KUNIT_TEST) += "
        "mt6797-bigidvfs-sram-owner-test.o\n",
    )
    if target.exists():
        raise SystemExit("BigiDVFS SRAM-owner test source already exists")
    shutil.copyfile(TEMPLATES / "mt6797-bigidvfs-sram-owner-test.c", target)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--phase", choices=("production", "tests"),
                        required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    if args.phase == "production":
        apply_production(root)
    else:
        apply_tests(root)


if __name__ == "__main__":
    main()
