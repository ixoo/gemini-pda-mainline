#!/usr/bin/env python3
"""Require unsafe parent-proof source mutations to fail validation."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


SCRIPT_DIR = Path(__file__).resolve().parent
VALIDATOR = SCRIPT_DIR / "validate_parent_proof_source.py"
FILES = (
    "arch/arm64/include/asm/mt6797_a72_membership.h",
    "arch/arm64/kernel/mt6797_a72_membership.c",
    "arch/arm64/kernel/mt6797_a72_membership_test.c",
    "include/linux/soc/mediatek/mt6797-a72-binder.h",
    "drivers/soc/mediatek/mt6797-a72-binder-internal.h",
    "drivers/soc/mediatek/mt6797-a72-binder.c",
    "drivers/soc/mediatek/mt6797-a72-binder-test.c",
    "arch/arm64/kernel/mt6797_psci.c",
)


def run(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "--source-root", str(root),
         "--require-binder"],
        check=False, capture_output=True, text=True,
    )


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise ValueError(f"mutation anchor changed: {old}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    source = args.source_root.resolve()
    positive = run(source)
    if positive.returncode:
        sys.stderr.write(positive.stderr)
        return 1

    mutations = (
        ("relax-owner-phase", "arch/arm64/kernel/mt6797_a72_membership.c",
         "a72_owner.phase == MT6797_A72_PHASE_IDLE",
         "a72_owner.phase != MT6797_A72_PHASE_FAULT"),
        ("relax-hotplug-phase", "arch/arm64/kernel/mt6797_a72_membership.c",
         "a72_owner.hotplug_phase == MT6797_A72_HOTPLUG_IDLE",
         "a72_owner.hotplug_phase != MT6797_A72_HOTPLUG_FAULT"),
        ("drop-member", "arch/arm64/kernel/mt6797_a72_membership.c",
         "a72_owner.members == (BIT(0) | BIT(1))",
         "a72_owner.members == BIT(0)"),
        ("allow-hotplug-retired", "arch/arm64/kernel/mt6797_a72_membership.c",
         "!a72_owner.hotplug_retired_mask",
         "a72_owner.hotplug_retired_mask != ~0U"),
        ("allow-owner-active", "arch/arm64/kernel/mt6797_a72_membership.c",
         "!a72_owner.active.valid && !a72_owner.hotplug_active.valid",
         "!a72_owner.hotplug_active.valid"),
        ("allow-controller", "arch/arm64/kernel/mt6797_a72_membership.c",
         "!a72_owner.controller && !a72_owner.controller_cookie",
         "!a72_owner.controller_cookie"),
        ("drop-transition-lock", "arch/arm64/kernel/mt6797_a72_membership.c",
         "\tmemset(proof, 0, sizeof(*proof));\n"
         "\tmutex_lock(&a72_transition_lock);\n"
         "\traw_spin_lock_irqsave(&a72_state_lock, flags);\n",
         "\tmemset(proof, 0, sizeof(*proof));\n"
         "\traw_spin_lock_irqsave(&a72_state_lock, flags);\n"),
        ("substitute-cpu8", "arch/arm64/kernel/mt6797_a72_membership.c",
         "proof->cpu8 = a72_owner.retired[0].identity",
         "proof->cpu8 = a72_owner.retired[1].identity"),
        ("narrow-online-mask",
         "include/linux/soc/mediatek/mt6797-a72-binder.h",
         "#define MT6797_A72_BINDER_PARENT_ONLINE_MASK GENMASK(9, 0)",
         "#define MT6797_A72_BINDER_PARENT_ONLINE_MASK GENMASK(8, 0)"),
        ("extend-age", "include/linux/soc/mediatek/mt6797-a72-binder.h",
         "#define MT6797_A72_BINDER_PARENT_MAX_AGE_MS 5000U",
         "#define MT6797_A72_BINDER_PARENT_MAX_AGE_MS 6000U"),
        ("drop-boot-claim", "drivers/soc/mediatek/mt6797-a72-binder.c",
         "atomic_read(&binder->boot_claimed) != 1",
         "atomic_read(&binder->boot_claimed) > 1"),
        ("relax-terminal", "drivers/soc/mediatek/mt6797-a72-binder.c",
         "result->terminal != MT6797_A72_TRANSITION_CPU8_ONLINE_PROOF",
         "result->terminal == MT6797_A72_TRANSITION_TERMINAL_NONE"),
        ("wrong-online-count", "drivers/soc/mediatek/mt6797-a72-binder.c",
         "online_count != 10", "online_count != 9"),
        ("drop-watchdog-validation", "drivers/soc/mediatek/mt6797-a72-binder.c",
         "ret = binder->backend->watchdog_validate(",
         "ret = binder->backend->watchdog_takeover("),
        ("invert-age", "drivers/soc/mediatek/mt6797-a72-binder.c",
         "observed_ns - binder->watchdog_takeover_ns >\n"
         "\t    MT6797_A72_BINDER_PARENT_MAX_AGE_MS * 1000000ULL",
         "observed_ns - binder->watchdog_takeover_ns <\n"
         "\t    MT6797_A72_BINDER_PARENT_MAX_AGE_MS * 1000000ULL"),
        ("drop-publish-lock", "drivers/soc/mediatek/mt6797-a72-binder.c",
         "\tif (!proof)\n\t\treturn -EINVAL;\n"
         "\tmemset(proof, 0, sizeof(*proof));\n"
         "\tmutex_lock(&mt6797_a72_binder_publish_lock);\n"
         "\tbinder = mt6797_a72_binder_ready();\n",
         "\tif (!proof)\n\t\treturn -EINVAL;\n"
         "\tmemset(proof, 0, sizeof(*proof));\n"
         "\tbinder = mt6797_a72_binder_ready();\n"),
        ("add-physical-effect", "drivers/soc/mediatek/mt6797-a72-binder.c",
         "\tmemset(proof, 0, sizeof(*proof));\n"
         "\tif (!mt6797_a72_binder_backend_valid(binder->backend))",
         "\tmemset(proof, 0, sizeof(*proof));\n"
         "\tcpu_down(9);\n"
         "\tif (!mt6797_a72_binder_backend_valid(binder->backend))"),
        ("bind-psci", "arch/arm64/kernel/mt6797_psci.c",
         "static bool mt6797_psci_cpu_can_disable(unsigned int cpu)\n{\n",
         "static bool mt6797_psci_cpu_can_disable(unsigned int cpu)\n{\n"
         "\tmt6797_a72_binder_parent_proof(NULL);\n"),
        ("open-cpu-disable", "arch/arm64/kernel/mt6797_psci.c",
         "static bool mt6797_psci_cpu_can_disable(unsigned int cpu)\n"
         "{\n\treturn false;\n}",
         "static bool mt6797_psci_cpu_can_disable(unsigned int cpu)\n"
         "{\n\treturn cpu == 9;\n}"),
        ("drop-binder-test", "drivers/soc/mediatek/mt6797-a72-binder-test.c",
         "\tKUNIT_CASE(mt6797_binder_parent_proof_test),\n", ""),
    )

    for name, relative, old, new in mutations:
        with tempfile.TemporaryDirectory(
            prefix="gemini-parent-proof-mutation-"
        ) as temp_name:
            root = Path(temp_name)
            for item in FILES:
                target = root / item
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source / item, target)
            try:
                replace_once(root / relative, old, new)
            except ValueError as exc:
                print(f"mutation={name} setup=fail reason={exc}",
                      file=sys.stderr)
                return 1
            result = run(root)
            if result.returncode == 0:
                print(f"mutation={name} result=unexpected-pass",
                      file=sys.stderr)
                return 1

    print(f"parent_proof_source_mutations={len(mutations)}")
    print("parent_proof_source_mutations=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
