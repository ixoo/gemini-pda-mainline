#!/usr/bin/env python3
"""Apply deterministic MT6797 A72 physical-source observer edits."""

from __future__ import annotations

import argparse
import shutil
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


def copy_source(source_dir: Path, name: str, destination: Path) -> None:
    source = source_dir / name
    if not source.is_file() or source.is_symlink():
        raise SystemExit(f"unsafe source template: {source}")
    if destination.exists():
        raise SystemExit(f"destination already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def apply_ledger(root: Path) -> None:
    kconfig = root / "fs/pstore/Kconfig"
    mode = dedent(r'''
config PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER
	bool "Gemini A72 physical-source retained ledger"
	depends on PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y
	depends on MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER=y
	depends on !PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_CONTROL
	depends on !PSTORE_GEMINI_PROTECTED_READBACK_PROBE_GATE_LEDGER
	depends on !PSTORE_GEMINI_CLOCK_BACKEND_ENTRY_LEDGER
	depends on !PSTORE_GEMINI_PROTECTED_READBACK_RAW_ENTRY_LEDGER
	depends on !PSTORE_GEMINI_PROTECTED_READBACK_FIRST_DMESG_WRITE_QUALIFICATION
	depends on !PSTORE_GEMINI_CLOCK_BACKEND_FIRST_DMESG_ENTRY_QUALIFICATION
	depends on !PSTORE_GEMINI_PROTECTED_CLOCK_FIRST_DMESG_CALL_QUALIFICATION
	default n
	help
	  Give the candidate-only direct physical-source callback consecutive
	  retained records 1 and 2 immediately before and after its one BigiDVFS
	  read. Require both raw headers to be all ones before the first write.

	  Reuse the qualified payload, start, size, signature-last, barrier, full
	  readback, no-overwrite, no-clear, and no-retry protocol. This mode makes
	  at most two short retained-RAM writes and adds no storage, firmware write,
	  provider transaction, owner mutation, CPU request, reset, or power action.
	  If unsure, say N.

''').lstrip("\n")
    replace_once(
        kconfig,
        "config PSTORE_GEMINI_PROTECTED_READBACK_LEDGER\n",
        mode + "config PSTORE_GEMINI_PROTECTED_READBACK_LEDGER\n",
    )
    replace_once(
        kconfig,
        "\tdepends on MTK_MT6797_PROTECTED_READBACK_OBSERVER=y || "
        "MTK_MT6797_DVFSP_CLOCK_BACKEND=y || "
        "PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_CONTROL=y\n",
        "\tdepends on MTK_MT6797_PROTECTED_READBACK_OBSERVER=y || "
        "MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER=y || "
        "MTK_MT6797_DVFSP_CLOCK_BACKEND=y || "
        "PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_CONTROL=y\n",
    )

    ledger = root / "fs/pstore/gemini_protected_readback_ledger.c"
    replace_once(
        ledger,
        "\tdefined(CONFIG_PSTORE_GEMINI_PROTECTED_CLOCK_FIRST_DMESG_CALL_QUALIFICATION)\n"
        "#define GEMINI_PRB_LEDGER_BASE\t\tGEMINI_PRB_RESERVE_BASE\n",
        "\tdefined(CONFIG_PSTORE_GEMINI_PROTECTED_CLOCK_FIRST_DMESG_CALL_QUALIFICATION) || \\\n"
        "\tdefined(CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER)\n"
        "#define GEMINI_PRB_LEDGER_BASE\t\tGEMINI_PRB_RESERVE_BASE\n",
    )
    records = dedent(r'''
#ifdef CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER
static const char * const gemini_prb_records[] = {
	"====0.000000-D\n"
	"GEMINI_A72_PHYSICAL_SOURCE_V1 token=GPSQ-20260824-A "
	"checkpoint=before-bigidvfs slot=1 crc32=47eaad49\n",
	"====0.000000-D\n"
	"GEMINI_A72_PHYSICAL_SOURCE_V1 token=GPSQ-20260824-A "
	"checkpoint=after-bigidvfs slot=2 crc32=d03ca6dc\n",
};
#elif defined(CONFIG_PSTORE_GEMINI_PROTECTED_CLOCK_FIRST_DMESG_CALL_QUALIFICATION)
''').lstrip("\n")
    replace_once(
        ledger,
        "#ifdef CONFIG_PSTORE_GEMINI_PROTECTED_CLOCK_FIRST_DMESG_CALL_QUALIFICATION\n",
        records,
    )
    raw_anchor = (
        "#if defined(CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_RAW_ENTRY_LEDGER) || \\\n"
        "\tdefined(CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_RAW_WRITE_QUALIFICATION) || \\\n"
    )
    raw_replacement = (
        "#if defined(CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER) || \\\n"
        "\tdefined(CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_RAW_ENTRY_LEDGER) || \\\n"
        "\tdefined(CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_RAW_WRITE_QUALIFICATION) || \\\n"
    )
    text = ledger.read_text(encoding="utf-8")
    if text.count(raw_anchor) != 2:
        raise SystemExit("ledger: expected two raw signature conditionals")
    ledger.write_text(text.replace(raw_anchor, raw_replacement), encoding="utf-8")


def apply_observer(root: Path, source_dir: Path) -> None:
    kconfig = root / "drivers/soc/mediatek/Kconfig"
    observer = dedent(r'''
config MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER
	bool "MediaTek MT6797 A72 direct physical-source observer"
	depends on ARM64_MT6797_A72_DIRECT_STATE_COMPOSITOR
	depends on MTK_MT6797_A72_PLATFORM_STATE
	depends on MTK_MT6797_DVFSP_CLOCK_BACKEND
	depends on MTK_MT6797_DVFSP_BIGIDVFS_BACKEND
	default n
	help
	  Build the candidate-only one-shot source that retains bound platform,
	  clock, and BigiDVFS device references, temporarily registers one direct
	  callback, and asks the public A72 compositor for one all-or-zero record.

	  The callback reads platform, DA921x, and clock state, writes one retained
	  checkpoint, makes exactly one two-sample BigiDVFS read, and writes one
	  final checkpoint. It adds no publisher, provider transaction, owner
	  mutation, CPU request, retry, storage, reset, or power action.
	  If unsure, say N.

''').lstrip("\n")
    replace_once(
        kconfig,
        "config MTK_MT6797_PROTECTED_READBACK_OBSERVER\n",
        observer + "config MTK_MT6797_PROTECTED_READBACK_OBSERVER\n",
    )
    makefile = root / "drivers/soc/mediatek/Makefile"
    replace_once(
        makefile,
        "obj-$(CONFIG_MTK_MT6797_PROTECTED_READBACK_OBSERVER) += "
        "mt6797-protected-readback-observer.o\n",
        "obj-$(CONFIG_MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER) += "
        "mt6797-a72-physical-source-observer.o\n"
        "obj-$(CONFIG_MTK_MT6797_PROTECTED_READBACK_OBSERVER) += "
        "mt6797-protected-readback-observer.o\n",
    )
    for name in (
        "mt6797-a72-physical-source-observer.c",
        "mt6797-a72-physical-source-observer-internal.h",
    ):
        copy_source(source_dir, name, root / "drivers/soc/mediatek" / name)


def apply_binding(root: Path, source_dir: Path) -> None:
    name = "mediatek,mt6797-a72-physical-source-observer.yaml"
    copy_source(
        source_dir,
        name,
        root / "Documentation/devicetree/bindings/soc/mediatek" / name,
    )


def apply_dts(root: Path, source_dir: Path) -> None:
    makefile = root / "arch/arm64/boot/dts/mediatek/Makefile"
    replace_once(
        makefile,
        "dtb-$(CONFIG_ARCH_MEDIATEK) += mt6797-gemini-pda-protected-readback.dtb\n",
        "dtb-$(CONFIG_ARCH_MEDIATEK) += "
        "mt6797-gemini-pda-protected-readback.dtb\n"
        "dtb-$(CONFIG_ARCH_MEDIATEK) += "
        "mt6797-gemini-pda-a72-physical-source.dtb\n",
    )
    name = "mt6797-gemini-pda-a72-physical-source.dts"
    copy_source(source_dir, name, root / "arch/arm64/boot/dts/mediatek" / name)


def apply_tests(root: Path, source_dir: Path) -> None:
    kconfig = root / "drivers/soc/mediatek/Kconfig"
    tests = dedent(r'''
config MTK_MT6797_A72_PHYSICAL_SOURCE_KUNIT_TEST
	bool "KUnit tests for MT6797 A72 direct physical-source observer"
	depends on KUNIT=y
	depends on MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER
	default n
	help
	  Exercise the exact six-stage callback order, every component failure,
	  all-zero output, and register/snapshot/unregister lifetime with injected
	  in-memory operations. No MMIO, I2C, retained RAM, SMC, owner mutation,
	  publisher, or CPU operation is performed.

''').lstrip("\n")
    replace_once(
        kconfig,
        "config MTK_MT6797_PROTECTED_READBACK_OBSERVER\n",
        tests + "config MTK_MT6797_PROTECTED_READBACK_OBSERVER\n",
    )
    makefile = root / "drivers/soc/mediatek/Makefile"
    replace_once(
        makefile,
        "obj-$(CONFIG_MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER) += "
        "mt6797-a72-physical-source-observer.o\n",
        "obj-$(CONFIG_MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER) += "
        "mt6797-a72-physical-source-observer.o\n"
        "obj-$(CONFIG_MTK_MT6797_A72_PHYSICAL_SOURCE_KUNIT_TEST) += "
        "mt6797-a72-physical-source-observer-test.o\n",
    )
    name = "mt6797-a72-physical-source-observer-test.c"
    copy_source(source_dir, name, root / "drivers/soc/mediatek" / name)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument(
        "--phase",
        choices=("ledger", "observer", "binding", "dts", "tests"),
        required=True,
    )
    args = parser.parse_args()
    root = args.source_root.resolve()
    source_dir = Path(__file__).resolve().parents[1] / "source"

    actions = {
        "ledger": lambda: apply_ledger(root),
        "observer": lambda: apply_observer(root, source_dir),
        "binding": lambda: apply_binding(root, source_dir),
        "dts": lambda: apply_dts(root, source_dir),
        "tests": lambda: apply_tests(root, source_dir),
    }
    actions[args.phase]()


if __name__ == "__main__":
    main()
