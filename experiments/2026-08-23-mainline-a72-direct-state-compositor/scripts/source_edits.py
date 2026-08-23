#!/usr/bin/env python3
"""Apply deterministic closed A72 direct-state compositor edits."""

from __future__ import annotations

import argparse
from pathlib import Path
from textwrap import dedent


SCRIPT_DIR = Path(__file__).resolve().parent
SOURCE_DIR = SCRIPT_DIR.parent / "source"


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        first = old.splitlines()[0] if old.splitlines() else "<empty>"
        raise SystemExit(
            f"{path}: expected one anchor beginning {first!r}, found {count}"
        )
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def core(root: Path) -> None:
    direct_header = root / "include/linux/mt6797-a72-direct-state.h"
    if direct_header.exists():
        raise SystemExit(f"refusing to overwrite {direct_header}")
    direct_header.parent.mkdir(parents=True, exist_ok=True)
    direct_header.write_bytes(
        (SOURCE_DIR / "mt6797-a72-direct-state.h").read_bytes()
    )

    membership_header = root / "arch/arm64/include/asm/mt6797_a72_membership.h"
    replace_once(
        membership_header,
        "#include <linux/mt6797-a72-provider.h>\n",
        "#include <linux/mt6797-a72-provider.h>\n"
        "#include <linux/mt6797-a72-direct-state.h>\n",
    )
    header_definition = (
        SOURCE_DIR / "mt6797_a72_direct_state_membership.h.inc"
    ).read_text(encoding="utf-8").rstrip() + "\n\n"
    replace_once(
        membership_header,
        "enum mt6797_a72_a34_reset_provenance {\n",
        header_definition + "enum mt6797_a72_a34_reset_provenance {\n",
    )

    membership = root / "arch/arm64/kernel/mt6797_a72_membership.c"
    replace_once(
        membership,
        "#include <linux/cpumask.h>\n",
        "#include <linux/cpumask.h>\n#include <linux/cpu.h>\n",
    )
    core_definition = (
        SOURCE_DIR / "mt6797_a72_direct_state_membership.c.inc"
    ).read_text(encoding="utf-8").rstrip() + "\n\n"
    owner_anchor = dedent(r'''
static struct mt6797_a72_owner_state a72_owner = {
	.diagnostic_blockers = MT6797_A72_BLOCK_MASK,
	.health = MT6797_A72_OWNER_CLOSED,
	.phase = MT6797_A72_PHASE_UNINITIALIZED,
	.provider_state = MT6797_A72_PROVIDER_NONE,
};

''').lstrip("\n")
    replace_once(membership, owner_anchor, owner_anchor + core_definition)

    platforms = root / "arch/arm64/Kconfig.platforms"
    config = dedent(r'''
config ARM64_MT6797_A72_DIRECT_STATE_COMPOSITOR
	bool "Compose closed MT6797 A72 direct physical state"
	depends on HOTPLUG_CPU
	depends on ARM64_MT6797_A72_P24_TRANSACTION_OWNER_MODEL
	default n
	help
	  Add a single default-off composition boundary under the CPU-hotplug
	  read lock and the A72 transition owner. It accepts only one complete
	  injected physical source while CPU8 and CPU9 are possible, present,
	  and offline and the owner remains pristine CLOSED / UNINITIALIZED.

	  This option supplies no physical reader, owner opener, A34 decision,
	  hardware operation, CPU_ON, or CPU_OFF. If unsure, say N.

''').lstrip("\n")
    replace_once(
        platforms,
        "config ARM64_MT6797_A72_A34_ELIGIBILITY_EVALUATOR\n",
        config + "config ARM64_MT6797_A72_A34_ELIGIBILITY_EVALUATOR\n",
    )


def tests(root: Path) -> None:
    test_path = root / "arch/arm64/kernel/mt6797_a72_direct_state_test.c"
    if test_path.exists():
        raise SystemExit(f"refusing to overwrite {test_path}")
    test_path.write_bytes(
        (SOURCE_DIR / "mt6797_a72_direct_state_test.c").read_bytes()
    )

    kconfig = root / "arch/arm64/Kconfig"
    config = dedent(r'''
config ARM64_MT6797_A72_DIRECT_STATE_KUNIT_TEST
	bool "KUnit tests for the closed MT6797 A72 direct-state compositor"
	depends on KUNIT=y
	depends on HOTPLUG_CPU
	depends on ARM64_MT6797_A72_P30_PROTOCOL_MODEL
	select ARM64_MT6797_A72_P24_TRANSACTION_OWNER_MODEL
	select ARM64_MT6797_A72_P24_ADMISSION_HOOKS
	select ARM64_MT6797_A72_P24_OWNER_TEST_SEED
	select ARM64_MT6797_A72_DIRECT_STATE_COMPOSITOR
	help
	  Exercise the injected direct-state source registry, exact topology and
	  record validation, zero-on-error contract, lock-owned lifecycle checks,
	  and byte-identical CLOSED owner preservation. No physical reader or CPU
	  operation is connected.

''').lstrip("\n")
    replace_once(
        kconfig,
        "config ARM64_MT6797_A72_PROVIDER_OWNER\n",
        config + "config ARM64_MT6797_A72_PROVIDER_OWNER\n",
    )

    makefile = root / "arch/arm64/kernel/Makefile"
    anchor = (
        "obj-$(CONFIG_ARM64_MT6797_A72_A34_ELIGIBILITY_KUNIT_TEST) "
        "+= mt6797_a72_a34_evaluator_test.o\n"
    )
    replace_once(
        makefile,
        anchor,
        anchor
        + "obj-$(CONFIG_ARM64_MT6797_A72_DIRECT_STATE_KUNIT_TEST) "
        "+= mt6797_a72_direct_state_test.o\n",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--phase", choices=("core", "tests"), required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    if args.phase == "core":
        core(root)
    else:
        tests(root)


if __name__ == "__main__":
    main()
