#!/usr/bin/env python3
"""Apply deterministic MT6797 platform/provider/clock observer edits."""

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
config PSTORE_GEMINI_A72_PLATFORM_PROVIDER_CLOCK_LEDGER
	bool "Gemini A72 platform/provider/protected-clock retained ledger"
	depends on PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y
	depends on MTK_MT6797_A72_PLATFORM_PROVIDER_CLOCK_OBSERVER=y
	depends on !PSTORE_GEMINI_A72_PLATFORM_PROVIDER_SNAPSHOT_LEDGER
	depends on !PSTORE_GEMINI_A72_PLATFORM_SNAPSHOT_LEDGER
	depends on !PSTORE_GEMINI_A72_EARLY_INITCALL_LEDGER
	depends on !PSTORE_GEMINI_A72_GLOBAL_INITCALL_LEDGER
	depends on !PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER
	depends on !PSTORE_GEMINI_A72_PHYSICAL_SOURCE_PRECAPTURE_LEDGER
	depends on !PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_CONTROL
	depends on !PSTORE_GEMINI_PROTECTED_READBACK_PROBE_GATE_LEDGER
	depends on !PSTORE_GEMINI_CLOCK_BACKEND_ENTRY_LEDGER
	depends on !PSTORE_GEMINI_PROTECTED_READBACK_RAW_ENTRY_LEDGER
	depends on !PSTORE_GEMINI_PROTECTED_READBACK_FIRST_DMESG_WRITE_QUALIFICATION
	depends on !PSTORE_GEMINI_CLOCK_BACKEND_FIRST_DMESG_ENTRY_QUALIFICATION
	depends on !PSTORE_GEMINI_PROTECTED_CLOCK_FIRST_DMESG_CALL_QUALIFICATION
	default n
	help
	  Give the candidate-only three-source observer one retained record after
	  its platform and provider snapshots and immediately before its sole
	  protected-clock call, then one record only after that call returns.

	  Reuse the qualified signature-last, full-readback, two-write, no-clear,
	  and no-retry protocol. The protected-clock call retains its bounded clock
	  gate and CSPM power-on/semaphore writes. This mode adds no BigiDVFS,
	  provider action, publisher, owner mutation, or CPU request. If unsure,
	  say N.

''').lstrip("\n")
    replace_once(
        kconfig,
        "config PSTORE_GEMINI_A72_PLATFORM_PROVIDER_SNAPSHOT_LEDGER\n",
        mode + "config PSTORE_GEMINI_A72_PLATFORM_PROVIDER_SNAPSHOT_LEDGER\n",
    )
    # Keep the exclusion one-way. Kconfig rejects reciprocal negative
    # dependencies as a recursive dependency before configuration can start.
    replace_once(
        kconfig,
        "MTK_MT6797_A72_PLATFORM_PROVIDER_SNAPSHOT_OBSERVER=y || "
        "MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER=y ||",
        "MTK_MT6797_A72_PLATFORM_PROVIDER_SNAPSHOT_OBSERVER=y || "
        "MTK_MT6797_A72_PLATFORM_PROVIDER_CLOCK_OBSERVER=y || "
        "MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER=y ||",
    )

    ledger = root / "fs/pstore/gemini_protected_readback_ledger.c"
    replace_once(
        ledger,
        "\tdefined(CONFIG_PSTORE_GEMINI_A72_PLATFORM_PROVIDER_SNAPSHOT_LEDGER) || \\\n",
        "\tdefined(CONFIG_PSTORE_GEMINI_A72_PLATFORM_PROVIDER_CLOCK_LEDGER) || \\\n"
        "\tdefined(CONFIG_PSTORE_GEMINI_A72_PLATFORM_PROVIDER_SNAPSHOT_LEDGER) || \\\n",
    )
    records = dedent(r'''
#ifdef CONFIG_PSTORE_GEMINI_A72_PLATFORM_PROVIDER_CLOCK_LEDGER
static const char * const gemini_prb_records[] = {
	"====0.000000-D\n"
	"GEMINI_A72_PLATFORM_PROVIDER_CLOCK_SNAPSHOT_V1 token=GAPC-20260825-A "
	"checkpoint=before-clock slot=1 crc32=7a63713c\n",
	"====0.000000-D\n"
	"GEMINI_A72_PLATFORM_PROVIDER_CLOCK_SNAPSHOT_V1 token=GAPC-20260825-A "
	"checkpoint=after-clock slot=2 crc32=5773d4f6\n",
};
#elif defined(CONFIG_PSTORE_GEMINI_A72_PLATFORM_PROVIDER_SNAPSHOT_LEDGER)
''').lstrip("\n")
    replace_once(
        ledger,
        "#ifdef CONFIG_PSTORE_GEMINI_A72_PLATFORM_PROVIDER_SNAPSHOT_LEDGER\n",
        records,
    )
    raw_anchor = (
        "#if defined(CONFIG_PSTORE_GEMINI_A72_PLATFORM_PROVIDER_SNAPSHOT_LEDGER) || \\\n"
    )
    raw_replacement = (
        "#if defined(CONFIG_PSTORE_GEMINI_A72_PLATFORM_PROVIDER_CLOCK_LEDGER) || \\\n"
        "\tdefined(CONFIG_PSTORE_GEMINI_A72_PLATFORM_PROVIDER_SNAPSHOT_LEDGER) || \\\n"
    )
    text = ledger.read_text(encoding="utf-8")
    if text.count(raw_anchor) != 2:
        raise SystemExit("ledger: expected two platform/provider raw conditionals")
    ledger.write_text(text.replace(raw_anchor, raw_replacement), encoding="utf-8")


def apply_binding(root: Path, source_dir: Path) -> None:
    name = "mediatek,mt6797-a72-platform-provider-clock-observer.yaml"
    copy_source(
        source_dir,
        name,
        root / "Documentation/devicetree/bindings/soc/mediatek" / name,
    )


def apply_observer(root: Path, source_dir: Path) -> None:
    kconfig = root / "drivers/soc/mediatek/Kconfig"
    observer = dedent(r'''
config MTK_MT6797_A72_PLATFORM_PROVIDER_CLOCK_OBSERVER
	bool "MediaTek MT6797 A72 platform/provider/protected-clock observer"
	depends on ARM64_MT6797_A72_PROVIDER_OWNER
	depends on MTK_MT6797_A72_PLATFORM_STATE
	depends on MTK_MT6797_DVFSP_CLOCK_BACKEND
	default n
	help
	  Build the candidate-only observer that takes one stable platform snapshot,
	  one stable read-only DA921x provider snapshot, two retained checkpoints,
	  and exactly one bounded protected-clock snapshot with no caller retry.

	  The clock call uses one balanced clock-gate pair plus the existing CSPM
	  power-on/semaphore protocol. It adds no DA921x register-data write,
	  BigiDVFS or secure call, provider action, publisher, owner mutation, CPU
	  request, reset, or power action. If unsure, say N.

''').lstrip("\n")
    replace_once(
        kconfig,
        "config MTK_MT6797_A72_PLATFORM_PROVIDER_SNAPSHOT_OBSERVER\n",
        observer + "config MTK_MT6797_A72_PLATFORM_PROVIDER_SNAPSHOT_OBSERVER\n",
    )
    makefile = root / "drivers/soc/mediatek/Makefile"
    replace_once(
        makefile,
        "obj-$(CONFIG_MTK_MT6797_A72_PLATFORM_PROVIDER_SNAPSHOT_OBSERVER) += "
        "mt6797-a72-platform-provider-snapshot-observer.o\n",
        "obj-$(CONFIG_MTK_MT6797_A72_PLATFORM_PROVIDER_CLOCK_OBSERVER) += "
        "mt6797-a72-platform-provider-clock-observer.o\n"
        "obj-$(CONFIG_MTK_MT6797_A72_PLATFORM_PROVIDER_SNAPSHOT_OBSERVER) += "
        "mt6797-a72-platform-provider-snapshot-observer.o\n",
    )
    for name in (
        "mt6797-a72-platform-provider-clock-observer.c",
        "mt6797-a72-platform-provider-clock-observer-internal.h",
    ):
        copy_source(source_dir, name, root / "drivers/soc/mediatek" / name)


def apply_tests(root: Path, source_dir: Path) -> None:
    kconfig = root / "drivers/soc/mediatek/Kconfig"
    tests = dedent(r'''
config MTK_MT6797_A72_PLATFORM_PROVIDER_CLOCK_KUNIT_TEST
	bool "KUnit tests for MT6797 A72 platform/provider/clock observer"
	depends on KUNIT=y
	depends on MTK_MT6797_A72_PLATFORM_PROVIDER_CLOCK_OBSERVER
	default n
	help
	  Exercise exact source order, dependency refusal, every prefix failure,
	  terminal clock errors, terminal after-checkpoint failure, identity failure,
	  and all-zero pre-clock failure output with injected in-memory operations.

	  No MMIO, retained RAM, I2C, clock, SMC, provider registry, owner,
	  publisher, or CPU action occurs in these tests. If unsure, say N.

''').lstrip("\n")
    replace_once(
        kconfig,
        "config MTK_MT6797_A72_PLATFORM_PROVIDER_SNAPSHOT_OBSERVER\n",
        tests + "config MTK_MT6797_A72_PLATFORM_PROVIDER_SNAPSHOT_OBSERVER\n",
    )
    makefile = root / "drivers/soc/mediatek/Makefile"
    replace_once(
        makefile,
        "obj-$(CONFIG_MTK_MT6797_A72_PLATFORM_PROVIDER_CLOCK_OBSERVER) += "
        "mt6797-a72-platform-provider-clock-observer.o\n",
        "obj-$(CONFIG_MTK_MT6797_A72_PLATFORM_PROVIDER_CLOCK_OBSERVER) += "
        "mt6797-a72-platform-provider-clock-observer.o\n"
        "obj-$(CONFIG_MTK_MT6797_A72_PLATFORM_PROVIDER_CLOCK_KUNIT_TEST) += "
        "mt6797-a72-platform-provider-clock-observer-test.o\n",
    )
    name = "mt6797-a72-platform-provider-clock-observer-test.c"
    copy_source(source_dir, name, root / "drivers/soc/mediatek" / name)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument(
        "--phase", choices=("ledger", "binding", "observer", "tests"),
        required=True,
    )
    args = parser.parse_args()
    root = args.source_root.resolve()
    source_dir = Path(__file__).resolve().parents[1] / "source"
    actions = {
        "ledger": lambda: apply_ledger(root),
        "binding": lambda: apply_binding(root, source_dir),
        "observer": lambda: apply_observer(root, source_dir),
        "tests": lambda: apply_tests(root, source_dir),
    }
    actions[args.phase]()


if __name__ == "__main__":
    main()
