#!/usr/bin/env python3
"""Apply the deterministic Gemini probe/gate retained-ledger mode."""

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


def apply(root: Path) -> None:
    ledger = root / "fs/pstore/gemini_protected_readback_ledger.c"
    old_records = dedent(r'''
static const char * const gemini_prb_records[] = {
	"====0.000000-D\n"
	"GEMINI_PROTECTED_READBACK_LEDGER_V1 token=GPRB-20260821-A "
	"checkpoint=before-clock slot=173 crc32=08f2fe56\n",
	"====0.000000-D\n"
	"GEMINI_PROTECTED_READBACK_LEDGER_V1 token=GPRB-20260821-A "
	"checkpoint=after-clock slot=174 crc32=e477a18e\n",
};
''').lstrip("\n")
    new_records = dedent(r'''
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
    replace_once(ledger, old_records, new_records)

    exact_dt = dedent(r'''
static bool gemini_prb_exact_dt(void)
{
	struct device_node *node;
	struct resource resource;
	const char *model;
	u32 value;
	bool exact = false;

	if (!of_machine_is_compatible("planet,gemini-pda") ||
	    of_property_read_string(of_root, "model", &model) ||
	    strcmp(model, "MT6797X"))
		return false;

	node = of_find_node_by_path("/reserved-memory/ramoops@44410000");
	if (!node)
		return false;
	if (!of_device_is_compatible(node, "ramoops") ||
	    of_address_to_resource(node, 0, &resource) ||
	    resource.start != GEMINI_PRB_RESERVE_BASE ||
	    resource_size(&resource) != GEMINI_PRB_RESERVE_SIZE ||
	    !of_property_read_bool(node, "no-map"))
		goto out;

	if (of_property_read_u32(node, "record-size", &value) ||
	    value != 0x1000)
		goto out;
	if (of_property_read_u32(node, "console-size", &value) ||
	    value != 0x10000)
		goto out;
	if (of_property_read_u32(node, "ftrace-size", &value) ||
	    value != 0x1000)
		goto out;
	if (of_property_read_u32(node, "pmsg-size", &value) ||
	    value != 0x20000)
		goto out;
	if (of_property_read_u32(node, "mem-type", &value) || value)
		goto out;
	exact = true;
out:
	of_node_put(node);
	return exact;
}
''').lstrip("\n")
    minimal_and_exact = dedent(r'''
#ifdef CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_PROBE_GATE_LEDGER
static bool gemini_prb_minimal_dt(void)
{
	struct device_node *node;
	struct resource resource;
	bool exact = false;

	if (!of_machine_is_compatible("planet,gemini-pda"))
		return false;

	node = of_find_node_by_path("/reserved-memory/ramoops@44410000");
	if (!node)
		return false;
	if (of_device_is_compatible(node, "ramoops") &&
	    !of_address_to_resource(node, 0, &resource) &&
	    resource.start == GEMINI_PRB_RESERVE_BASE &&
	    resource_size(&resource) == GEMINI_PRB_RESERVE_SIZE &&
	    of_property_read_bool(node, "no-map"))
		exact = true;
	of_node_put(node);

	return exact;
}
#endif

''').lstrip("\n") + exact_dt
    replace_once(ledger, exact_dt, minimal_and_exact)

    old_gate = (
        "\tif (checkpoint > 1 || (checkpoint == 0 && gemini_prb_armed) ||\n"
        "\t    (checkpoint == 1 && !gemini_prb_armed) || !gemini_prb_exact_dt())\n"
        "\t\treturn false;\n"
    )
    new_gate = (
        "\tif (checkpoint > 1 || (checkpoint == 0 && gemini_prb_armed) ||\n"
        "\t    (checkpoint == 1 && !gemini_prb_armed))\n"
        "\t\treturn false;\n"
        "#ifdef CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_PROBE_GATE_LEDGER\n"
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
    mode = dedent(r'''
config PSTORE_GEMINI_PROTECTED_READBACK_PROBE_GATE_LEDGER
	bool "Gemini protected-readback probe/gate ledger mode"
	depends on PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y
	default n
	help
	  Move the isolated protected-readback ledger's two retained records to
	  observer probe entry and the final exact gate immediately before the
	  first protected read. The entry record requires only the exact Gemini
	  compatibility, ramoops reservation, no-map property, and empty slots;
	  the second retains the complete model, DT, prefix, and readback gates.

	  This experiment-only mode adds no retained write, protected read, retry,
	  owner, CPU, storage, firmware-write, reset, or power operation. The base
	  call-ledger behavior is unchanged when this mode is disabled.

''').lstrip("\n")
    replace_once(
        kconfig,
        "config PSTORE_GEMINI_POST_RAMOOPS_CHECKPOINT\n",
        mode + "config PSTORE_GEMINI_POST_RAMOOPS_CHECKPOINT\n",
    )

    observer = root / (
        "drivers/soc/mediatek/mt6797-protected-readback-observer.c"
    )
    replace_once(
        observer,
        "\tint ret;\n\n\tclock_backend = mt6797_readback_get_backend(dev,\n",
        "\tint ret;\n\n"
        "#ifdef CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_PROBE_GATE_LEDGER\n"
        "\tif (!gemini_protected_readback_ledger_checkpoint(0))\n"
        "\t\treturn dev_err_probe(dev, -EIO,\n"
        "\t\t\t\t     \"probe-enter ledger checkpoint failed\\n\");\n"
        "#endif\n\n"
        "\tclock_backend = mt6797_readback_get_backend(dev,\n",
    )

    old_calls = (
        "\tif (!gemini_protected_readback_ledger_checkpoint(0)) {\n"
        "\t\tret = dev_err_probe(dev, -EIO,\n"
        "\t\t\t\t    \"before-clock ledger checkpoint failed\\n\");\n"
        "\t\tgoto put_bigidvfs;\n"
        "\t}\n"
        "\tclock_ret = mt6797_dvfsp_clock_backend_read(&clock_backend->dev,\n"
        "\t\t\t\t\t\t    &clock);\n"
        "\tif (!gemini_protected_readback_ledger_checkpoint(1)) {\n"
        "\t\tret = dev_err_probe(dev, -EIO,\n"
        "\t\t\t\t    \"after-clock ledger checkpoint failed\\n\");\n"
        "\t\tgoto put_bigidvfs;\n"
        "\t}\n"
    )
    new_calls = (
        "#ifdef CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_PROBE_GATE_LEDGER\n"
        "\tif (!gemini_protected_readback_ledger_checkpoint(1)) {\n"
        "\t\tret = dev_err_probe(dev, -EIO,\n"
        "\t\t\t\t    \"gate-passed ledger checkpoint failed\\n\");\n"
        "\t\tgoto put_bigidvfs;\n"
        "\t}\n"
        "#else\n"
        "\tif (!gemini_protected_readback_ledger_checkpoint(0)) {\n"
        "\t\tret = dev_err_probe(dev, -EIO,\n"
        "\t\t\t\t    \"before-clock ledger checkpoint failed\\n\");\n"
        "\t\tgoto put_bigidvfs;\n"
        "\t}\n"
        "#endif\n"
        "\tclock_ret = mt6797_dvfsp_clock_backend_read(&clock_backend->dev,\n"
        "\t\t\t\t\t\t    &clock);\n"
        "#ifndef CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_PROBE_GATE_LEDGER\n"
        "\tif (!gemini_protected_readback_ledger_checkpoint(1)) {\n"
        "\t\tret = dev_err_probe(dev, -EIO,\n"
        "\t\t\t\t    \"after-clock ledger checkpoint failed\\n\");\n"
        "\t\tgoto put_bigidvfs;\n"
        "\t}\n"
        "#endif\n"
    )
    replace_once(observer, old_calls, new_calls)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    apply(args.source_root.resolve())


if __name__ == "__main__":
    main()
