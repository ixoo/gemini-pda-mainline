#!/usr/bin/env python3
"""Require unsafe CPU9 hotplug-owner mutations to fail closed."""

from __future__ import annotations

import argparse
import pathlib
import shutil
import subprocess
import sys
import tempfile


FILES = (
    "arch/arm64/include/asm/mt6797_a72_membership.h",
    "arch/arm64/kernel/mt6797_a72_membership.c",
    "arch/arm64/kernel/mt6797_a72_membership_test.c",
    "arch/arm64/kernel/mt6797_psci.c",
)


def replace_once(path: pathlib.Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise RuntimeError(f"mutation anchor changed: {old}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def validate(validator: pathlib.Path,
             root: pathlib.Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(validator), "--source-root", str(root),
         "--require-tests"],
        check=False, capture_output=True, text=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=pathlib.Path, required=True)
    args = parser.parse_args()
    source = args.source_root.resolve()
    validator = pathlib.Path(__file__).resolve().parent / \
        "validate_owner_source.py"
    mutations = (
        ("restore-attempt-removed", FILES[0],
         "#define MT6797_A72_ATTEMPT_CPU9_RESTORE BIT(4)",
         "#define MT6797_A72_ATTEMPT_CPU9_RESTORE 0"),
        ("hotplug-not-opened", FILES[1],
         "a72_owner.hotplug_phase = MT6797_A72_HOTPLUG_IDLE;",
         "a72_owner.hotplug_phase = MT6797_A72_HOTPLUG_NONE;"),
        ("down-target-cpu8", FILES[1],
         "if (cpu != 9 || target != CPUHP_OFFLINE)",
         "if (cpu != 8 || target != CPUHP_OFFLINE)"),
        ("down-parent-unchecked", FILES[1],
         "!mt6797_a72_cpu9_retired_parent_valid_locked(BIT(0) |\n"
         "\t\t\t\t\t\t\t    BIT(1)) ||",
         "false ||"),
        ("down-attempt-not-consumed", FILES[1],
         "a72_owner.attempts_consumed |=\n"
         "\t\t\tMT6797_A72_ATTEMPT_CPU9_OFF;",
         "a72_owner.attempts_consumed &=\n"
         "\t\t\t~MT6797_A72_ATTEMPT_CPU9_OFF;"),
        ("frozen-down-allowed", FILES[1],
         "if (!tasks_frozen && target == CPUHP_OFFLINE &&",
         "if (target == CPUHP_OFFLINE &&"),
        ("cpu-off-budget-rearmed", FILES[1],
         "a72_owner.hotplug_active.budgets.cpu_off =\n"
         "\t\t\tMT6797_A72_BUDGET_CONSUMED;",
         "a72_owner.hotplug_active.budgets.cpu_off =\n"
         "\t\t\tMT6797_A72_BUDGET_AVAILABLE;"),
        ("affinity-budget-rearmed", FILES[1],
         "a72_owner.hotplug_active.budgets.affinity =\n"
         "\t\t\tMT6797_A72_BUDGET_CONSUMED;",
         "a72_owner.hotplug_active.budgets.affinity =\n"
         "\t\t\tMT6797_A72_BUDGET_AVAILABLE;"),
        ("retained-peer-unproven", FILES[1],
         "proof->cpu8_responsive == 1",
         "proof->cpu8_responsive <= 1"),
        ("down-membership-not-committed", FILES[1],
         "a72_owner.hotplug_active.completed = 1;\n"
         "\t\ta72_owner.members = BIT(0);\n"
         "\t\t*transaction = a72_owner.hotplug_active;",
         "a72_owner.hotplug_active.completed = 1;\n"
         "\t\ta72_owner.members = BIT(0) | BIT(1);\n"
         "\t\t*transaction = a72_owner.hotplug_active;"),
        ("precommit-made-fatal", FILES[1],
         "mt6797_a72_hotplug_retire_locked(0,\n"
         "\t\t\t\t\t\t  MT6797_A72_HOTPLUG_REJECTED);",
         "mt6797_a72_hotplug_fault_locked(error);"),
        ("postcommit-made-reversible", FILES[1],
         "case MT6797_A72_HOTPLUG_OFF_PROVEN:\n"
         "\t\t\tmt6797_a72_hotplug_fault_locked(error);",
         "case MT6797_A72_HOTPLUG_OFF_PROVEN:\n"
         "\t\t\tmt6797_a72_hotplug_retire_locked(\n"
         "\t\t\t\t0, MT6797_A72_HOTPLUG_REJECTED);"),
        ("restore-parent-unlinked", FILES[1],
         "minted.identity.parent_generation =\n"
         "\t\t\t\tparent->identity.generation;",
         "minted.identity.parent_generation = 0;"),
        ("restore-reuses-up-attempt", FILES[1],
         "~MT6797_A72_ATTEMPT_CPU9_RESTORE;",
         "~MT6797_A72_ATTEMPT_CPU9_UP;"),
        ("restore-reserved-identity-accepted", FILES[1],
         "\t} else if (!a72_owner.next_generation || !a72_owner.next_cookie ||\n"
         "\t\t   a72_owner.next_generation == ~0ULL ||\n"
         "\t\t   a72_owner.next_cookie == ~0ULL) {\n"
         "\t\tret = -EPROTO;\n"
         "\t} else {\n"
         "\t\tparent = &a72_owner.hotplug_retired[0];",
         "\t} else {\n"
         "\t\tparent = &a72_owner.hotplug_retired[0];"),
        ("restore-cpu-on-rearmed", FILES[1],
         "a72_owner.hotplug_active.budgets.cpu_on =\n"
         "\t\t\tMT6797_A72_BUDGET_CONSUMED;",
         "a72_owner.hotplug_active.budgets.cpu_on =\n"
         "\t\t\tMT6797_A72_BUDGET_AVAILABLE;"),
        ("restore-membership-not-committed", FILES[1],
         "a72_owner.members = BIT(0) | BIT(1);\n"
         "\t\t*transaction = a72_owner.hotplug_active;",
         "a72_owner.members = BIT(0);\n"
         "\t\t*transaction = a72_owner.hotplug_active;"),
        ("restore-failure-reversible", FILES[1],
         "mt6797_a72_hotplug_fault_locked(error);\n"
         "\t\t*transaction = a72_owner.hotplug_active;\n"
         "\t\tret = 0;\n"
         "\t}\n"
         "\traw_spin_unlock_irqrestore(&a72_state_lock, flags);\n"
         "\treturn ret;\n"
         "}\n\n"
         "void mt6797_a72_hotplug_snapshot",
         "mt6797_a72_hotplug_retire_locked(\n"
         "\t\t\t1, MT6797_A72_HOTPLUG_REJECTED);\n"
         "\t\t*transaction = a72_owner.hotplug_active;\n"
         "\t\tret = 0;\n"
         "\t}\n"
         "\traw_spin_unlock_irqrestore(&a72_state_lock, flags);\n"
         "\treturn ret;\n"
         "}\n\n"
         "void mt6797_a72_hotplug_snapshot"),
        ("production-callback-bound", FILES[3],
         "\t.cpu_can_disable = mt6797_psci_cpu_can_disable,",
         "\t.cpu_down_preflight = mt6797_psci_cpu_up_preflight,\n"
         "\t.cpu_can_disable = mt6797_psci_cpu_can_disable,"),
        ("disable-veto-opened", FILES[3],
         "static bool mt6797_psci_cpu_can_disable(unsigned int cpu)\n"
         "{\n\treturn false;\n}",
         "static bool mt6797_psci_cpu_can_disable(unsigned int cpu)\n"
         "{\n\treturn true;\n}"),
        ("success-kunit-removed", FILES[2],
         "\tKUNIT_CASE(mt6797_a72_hotplug_success_lifecycle),",
         "\t/* success lifecycle omitted */"),
    )

    positive = validate(validator, source)
    if positive.returncode:
        sys.stderr.write(positive.stdout + positive.stderr)
        return 1

    rejected = 0
    for name, relative, old, new in mutations:
        with tempfile.TemporaryDirectory(prefix="gemini-hotplug-owner-") as temp:
            root = pathlib.Path(temp)
            for item in FILES:
                target = root / item
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source / item, target)
            replace_once(root / relative, old, new)
            result = validate(validator, root)
            if result.returncode == 0:
                print(f"mutation={name} result=unexpected-pass",
                      file=sys.stderr)
                return 1
            rejected += 1

    print(f"owner_source_mutation_rejections={rejected}")
    print("owner_source_validator_mutations=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
