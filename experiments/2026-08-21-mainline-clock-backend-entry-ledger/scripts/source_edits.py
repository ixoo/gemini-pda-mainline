#!/usr/bin/env python3
"""Apply the deterministic clock-backend init/probe ledger discriminator."""

from __future__ import annotations

import argparse
from pathlib import Path
from textwrap import dedent


MODE = "CONFIG_PSTORE_GEMINI_CLOCK_BACKEND_ENTRY_LEDGER"
PROBE_GATE = "CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_PROBE_GATE_LEDGER"


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        first = old.splitlines()[0] if old.splitlines() else "<empty>"
        raise SystemExit(
            f"{path}: expected one anchor beginning {first!r}, found {count}"
        )
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def apply(root: Path) -> None:
    ledger = root / "fs/pstore/gemini_protected_readback_ledger.c"
    old_records = dedent(r'''
#ifdef CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_PROBE_GATE_LEDGER
static const char * const gemini_prb_records[] = {
	"====0.000000-D\n"
	"GEMINI_PROTECTED_READBACK_LEDGER_V2 token=GPRB-20260821-B "
	"checkpoint=probe-enter slot=173 crc32=06a9b43b\n",
	"====0.000000-D\n"
	"GEMINI_PROTECTED_READBACK_LEDGER_V2 token=GPRB-20260821-B "
	"checkpoint=gate-passed slot=174 crc32=41e86ca4\n",
};
#else
static const char * const gemini_prb_records[] = {
	"====0.000000-D\n"
	"GEMINI_PROTECTED_READBACK_LEDGER_V1 token=GPRB-20260821-A "
	"checkpoint=before-clock slot=173 crc32=08f2fe56\n",
	"====0.000000-D\n"
	"GEMINI_PROTECTED_READBACK_LEDGER_V1 token=GPRB-20260821-A "
	"checkpoint=after-clock slot=174 crc32=e477a18e\n",
};
#endif
''').lstrip("\n")
    new_records = dedent(r'''
#ifdef CONFIG_PSTORE_GEMINI_CLOCK_BACKEND_ENTRY_LEDGER
static const char * const gemini_prb_records[] = {
	"====0.000000-D\n"
	"GEMINI_CLOCK_BACKEND_ENTRY_LEDGER_V1 token=GCBE-20260821-A "
	"checkpoint=driver-init slot=173 crc32=cda5d04d\n",
	"====0.000000-D\n"
	"GEMINI_CLOCK_BACKEND_ENTRY_LEDGER_V1 token=GCBE-20260821-A "
	"checkpoint=probe-enter slot=174 crc32=a3662888\n",
};
#elif defined(CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_PROBE_GATE_LEDGER)
static const char * const gemini_prb_records[] = {
	"====0.000000-D\n"
	"GEMINI_PROTECTED_READBACK_LEDGER_V2 token=GPRB-20260821-B "
	"checkpoint=probe-enter slot=173 crc32=06a9b43b\n",
	"====0.000000-D\n"
	"GEMINI_PROTECTED_READBACK_LEDGER_V2 token=GPRB-20260821-B "
	"checkpoint=gate-passed slot=174 crc32=41e86ca4\n",
};
#else
static const char * const gemini_prb_records[] = {
	"====0.000000-D\n"
	"GEMINI_PROTECTED_READBACK_LEDGER_V1 token=GPRB-20260821-A "
	"checkpoint=before-clock slot=173 crc32=08f2fe56\n",
	"====0.000000-D\n"
	"GEMINI_PROTECTED_READBACK_LEDGER_V1 token=GPRB-20260821-A "
	"checkpoint=after-clock slot=174 crc32=e477a18e\n",
};
#endif
''').lstrip("\n")
    replace_once(ledger, old_records, new_records)

    replace_once(
        ledger,
        f"#ifdef {PROBE_GATE}\nstatic bool gemini_prb_minimal_dt(void)\n",
        f"#if defined({PROBE_GATE}) || defined({MODE})\n"
        "static bool gemini_prb_minimal_dt(void)\n",
    )

    old_gate = (
        f"#ifdef {PROBE_GATE}\n"
        "\tif (checkpoint == 0) {\n"
        "\t\tif (!gemini_prb_minimal_dt())\n"
        "\t\t\treturn false;\n"
        "\t} else if (!gemini_prb_exact_dt()) {\n"
        "\t\treturn false;\n"
        "\t}\n"
        "#else\n"
        "\tif (!gemini_prb_exact_dt())\n"
        "\t\treturn false;\n"
        "#endif\n"
    )
    new_gate = (
        f"#ifdef {MODE}\n"
        "\tif (!gemini_prb_minimal_dt())\n"
        "\t\treturn false;\n"
        f"#elif defined({PROBE_GATE})\n"
        "\tif (checkpoint == 0) {\n"
        "\t\tif (!gemini_prb_minimal_dt())\n"
        "\t\t\treturn false;\n"
        "\t} else if (!gemini_prb_exact_dt()) {\n"
        "\t\treturn false;\n"
        "\t}\n"
        "#else\n"
        "\tif (!gemini_prb_exact_dt())\n"
        "\t\treturn false;\n"
        "#endif\n"
    )
    replace_once(ledger, old_gate, new_gate)

    kconfig = root / "fs/pstore/Kconfig"
    mode_config = dedent(r'''
config PSTORE_GEMINI_CLOCK_BACKEND_ENTRY_LEDGER
	bool "Gemini clock-backend init/probe entry ledger"
	depends on PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y
	depends on MTK_MT6797_DVFSP_CLOCK_BACKEND=y
	depends on !PSTORE_GEMINI_PROTECTED_READBACK_PROBE_GATE_LEDGER
	default n
	help
	  Move the isolated retained records before clock-backend platform-driver
	  registration and to the first clock-backend probe operation. The mode
	  is intended for a derivative DT that enables only that read-free probe;
	  it does not instantiate the observer or BigiDVFS backend and makes no
	  protected call.

	  Both records retain the exact Gemini reservation and empty-prefix gates,
	  the existing payload-before-metadata writer, complete readback, two-write
	  ceiling, and no-clear/no-retry policy. The historical call-ledger and
	  probe/gate modes are unchanged when this mode is disabled.

''').lstrip("\n")
    replace_once(
        kconfig,
        "config PSTORE_GEMINI_POST_RAMOOPS_CHECKPOINT\n",
        mode_config + "config PSTORE_GEMINI_POST_RAMOOPS_CHECKPOINT\n",
    )

    backend = root / "drivers/soc/mediatek/mt6797-dvfsp-clock-backend.c"
    replace_once(
        backend,
        "#include <linux/io.h>\n#include <linux/module.h>\n",
        "#include <linux/io.h>\n#include <linux/module.h>\n"
        "#include <linux/pstore_ram.h>\n",
    )
    replace_once(
        backend,
        "\tint ret;\n\n\tbackend = devm_kzalloc(&pdev->dev, sizeof(*backend), GFP_KERNEL);\n",
        "\tint ret;\n\n"
        f"#ifdef {MODE}\n"
        "\tif (!gemini_protected_readback_ledger_checkpoint(1))\n"
        "\t\treturn dev_err_probe(&pdev->dev, -EIO,\n"
        "\t\t\t\t     \"probe-enter ledger checkpoint failed\\n\");\n"
        "#endif\n\n"
        "\tbackend = devm_kzalloc(&pdev->dev, sizeof(*backend), GFP_KERNEL);\n",
    )
    replace_once(
        backend,
        "module_platform_driver(mt6797_dvfsp_clock_backend_driver);\n",
        f"#ifdef {MODE}\n"
        "static int __init mt6797_dvfsp_clock_backend_driver_init(void)\n"
        "{\n"
        "\tif (!gemini_protected_readback_ledger_checkpoint(0))\n"
        "\t\treturn -EIO;\n\n"
        "\treturn platform_driver_register(\n"
        "\t\t&mt6797_dvfsp_clock_backend_driver);\n"
        "}\n"
        "module_init(mt6797_dvfsp_clock_backend_driver_init);\n\n"
        "static void __exit mt6797_dvfsp_clock_backend_driver_exit(void)\n"
        "{\n"
        "\tplatform_driver_unregister(&mt6797_dvfsp_clock_backend_driver);\n"
        "}\n"
        "module_exit(mt6797_dvfsp_clock_backend_driver_exit);\n"
        "#else\n"
        "module_platform_driver(mt6797_dvfsp_clock_backend_driver);\n"
        "#endif\n",
    )

    dts_makefile = root / "arch/arm64/boot/dts/mediatek/Makefile"
    replace_once(
        dts_makefile,
        "dtb-$(CONFIG_ARCH_MEDIATEK) += mt6797-gemini-pda.dtb\n",
        "dtb-$(CONFIG_ARCH_MEDIATEK) += mt6797-gemini-pda.dtb\n"
        "dtb-$(CONFIG_ARCH_MEDIATEK) += mt6797-gemini-pda-clock-backend-entry.dtb\n",
    )
    candidate_dts = root / (
        "arch/arm64/boot/dts/mediatek/mt6797-gemini-pda-clock-backend-entry.dts"
    )
    if candidate_dts.exists():
        raise SystemExit(f"refusing to overwrite {candidate_dts}")
    candidate_dts.write_text(
        dedent(r'''
        // SPDX-License-Identifier: GPL-2.0-only
        /*
         * Copyright (c) 2026 Julien Etienne
         */

        #include "mt6797-gemini-pda.dts"

        / {
	        model = "Planet Computers Gemini PDA (clock backend entry ledger)";
        };

        &dvfsp_clock_backend {
	        status = "okay";
        };
        ''').lstrip("\n"),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    apply(args.source_root.resolve())


if __name__ == "__main__":
    main()
