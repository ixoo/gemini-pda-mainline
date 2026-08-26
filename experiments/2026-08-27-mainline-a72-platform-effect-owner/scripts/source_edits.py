#!/usr/bin/env python3
"""Apply deterministic MT6797 A72 platform-effect owner source edits."""

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
    config MTK_MT6797_A72_PLATFORM_EFFECTS
    \tbool "MediaTek MT6797 Cortex-A72 serialized platform effects"
    \tdepends on MTK_MT6797_A72_PLATFORM_STATE
    \tdefault n
    \thelp
    \t  Extend the exact platform-state source with one attempt-bound,
    \t  fail-closed owner for the CPU8 P27 reset/PWRAP prefix, its exact
    \t  pre-isolation inverse, external-isolation clear, and post-online
    \t  MP2 DCM toggle. The existing source mutex serializes snapshots and
    \t  effects over its single SPM, PWRAP, and MCUCFG resource ownership.

    \t  This option adds no caller, DA921x or SRAM-LDO operation, watchdog,
    \t  retained-memory update, PSCI call, CPU request, CPU_OFF, retry, or
    \t  device trigger. If unsure, say N.

    """)

TEST_KCONFIG = dedent("""\
    config MTK_MT6797_A72_PLATFORM_EFFECTS_KUNIT_TEST
    \tbool "KUnit tests for MT6797 A72 serialized platform effects"
    \tdepends on KUNIT=y
    \tdepends on MTK_MT6797_A72_PLATFORM_EFFECTS
    \tdefault n
    \thelp
    \t  Exercise exact success order, every P27, inverse, isolation, and DCM
    \t  refusal/readback boundary, foreign handles, and one-shot sealing with
    \t  an injected memory transport.

    \t  No MMIO, reset controller, delay, watchdog, retained RAM, regulator,
    \t  secure monitor, PSCI, or CPU operation is used. If unsure, say N.

    """)


def apply_production(root: Path) -> None:
    kconfig = root / "drivers/soc/mediatek/Kconfig"
    source = root / "drivers/soc/mediatek/mt6797-a72-platform-state.c"
    internal = root / "drivers/soc/mediatek/mt6797-a72-platform-state-internal.h"
    public = root / "include/linux/soc/mediatek/mt6797-a72-platform-state.h"

    replace_once(kconfig, "config MTK_MT6797_A72_TRANSITION_EXECUTOR\n",
                 PRODUCTION_KCONFIG +
                 "config MTK_MT6797_A72_TRANSITION_EXECUTOR\n")
    replace_once(
        public,
        "#if IS_ENABLED(CONFIG_MTK_MT6797_A72_PLATFORM_STATE)\n",
        template("platform_effect_public.h.inc") +
        "#if IS_ENABLED(CONFIG_MTK_MT6797_A72_PLATFORM_STATE)\n",
    )
    replace_once(
        internal,
        "struct mt6797_state_capture_ops {\n",
        template("platform_effect_internal.h.inc") +
        "struct mt6797_state_capture_ops {\n",
    )
    replace_once(source, "#include <linux/bitops.h>\n",
                 "#include <linux/bitops.h>\n#include <linux/delay.h>\n")
    replace_once(source, "#include <linux/module.h>\n",
                 "#include <linux/module.h>\n"
                 "#include <linux/mt6797-a72-provider.h>\n")
    replace_once(
        source,
        "\tstruct mutex lock; /* Serializes the two-sample transaction. */\n",
        "#if IS_ENABLED(CONFIG_MTK_MT6797_A72_PLATFORM_EFFECTS)\n"
        "\tstruct mt6797_a72_platform_effect_owner effect_owner;\n"
        "#endif\n"
        "\tstruct mutex lock; /* Serializes snapshots and platform effects. */\n",
    )
    replace_once(
        source,
        "static int mt6797_a72_platform_state_probe(struct platform_device *pdev)\n",
        "#if IS_ENABLED(CONFIG_MTK_MT6797_A72_PLATFORM_EFFECTS)\n" +
        template("platform_effect_source.c.inc") +
        "#endif\n\n"
        "static int mt6797_a72_platform_state_probe(struct platform_device *pdev)\n",
    )
    replace_once(
        source,
        "\tdev_info(dev, \"read-only capture source ready; no lifecycle caller\\n\");\n",
        "#if IS_ENABLED(CONFIG_MTK_MT6797_A72_PLATFORM_EFFECTS)\n"
        "\tdev_info(dev, \"platform source and effects ready; no caller\\n\");\n"
        "#else\n"
        "\tdev_info(dev, \"read-only capture source ready; no lifecycle caller\\n\");\n"
        "#endif\n",
    )


def apply_tests(root: Path) -> None:
    kconfig = root / "drivers/soc/mediatek/Kconfig"
    makefile = root / "drivers/soc/mediatek/Makefile"
    target = root / "drivers/soc/mediatek/mt6797-a72-platform-effect-test.c"

    replace_once(kconfig, "config MTK_MT6797_A72_TRANSITION_EXECUTOR\n",
                 TEST_KCONFIG +
                 "config MTK_MT6797_A72_TRANSITION_EXECUTOR\n")
    replace_once(
        makefile,
        "obj-$(CONFIG_MTK_MT6797_A72_PLATFORM_STATE_KUNIT_TEST) += "
        "mt6797-a72-platform-state-test.o\n",
        "obj-$(CONFIG_MTK_MT6797_A72_PLATFORM_STATE_KUNIT_TEST) += "
        "mt6797-a72-platform-state-test.o\n"
        "obj-$(CONFIG_MTK_MT6797_A72_PLATFORM_EFFECTS_KUNIT_TEST) += "
        "mt6797-a72-platform-effect-test.o\n",
    )
    if target.exists():
        raise SystemExit("platform-effect test source already exists")
    shutil.copyfile(TEMPLATES / "mt6797-a72-platform-effect-test.c", target)


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
