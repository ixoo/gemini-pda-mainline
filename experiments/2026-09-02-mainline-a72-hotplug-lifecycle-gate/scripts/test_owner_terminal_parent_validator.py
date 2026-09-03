#!/usr/bin/env python3
"""Require terminal-parent safety mutations to fail closed."""

from __future__ import annotations

import argparse
import pathlib
import shutil
import subprocess
import sys
import tempfile


SOURCE = "arch/arm64/kernel/mt6797_a72_membership.c"
FILES = (
    "arch/arm64/include/asm/mt6797_a72_membership.h",
    SOURCE,
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
         "--require-tests", "--require-terminal-parent-fix"],
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
        ("active-parent-reused", SOURCE,
         "!mt6797_a72_cpu9_terminal_parent_valid_locked() ||",
         "!mt6797_a72_cpu9_retired_parent_valid_locked(BIT(0) | BIT(1)) ||"),
        ("cpu9-retired-slot-optional", SOURCE,
         "a72_owner.retired_mask == (BIT(0) | BIT(1))",
         "(a72_owner.retired_mask & BIT(0))"),
        ("cpu9-success-unpublished", SOURCE,
         "!cpu9->cpu8_success_published && cpu9->cpu9_success_published &&",
         "!cpu9->cpu8_success_published && !cpu9->cpu9_success_published &&"),
        ("cpu9-terminal-target-cpu8", SOURCE,
         "cpu9->identity.target_cpu == 9 &&",
         "cpu9->identity.target_cpu == 8 &&"),
        ("cpu9-identity-alias-accepted", SOURCE,
         "cpu9->identity.generation != cpu8->identity.generation &&",
         "cpu9->identity.generation == cpu8->identity.generation &&"),
        ("down-parent-selects-cpu8", SOURCE,
         "parent = &a72_owner.retired[1];",
         "parent = &a72_owner.retired[0];"),
    )

    positive = validate(validator, source)
    if positive.returncode:
        sys.stderr.write(positive.stdout + positive.stderr)
        return 1

    rejected = 0
    for name, relative, old, new in mutations:
        with tempfile.TemporaryDirectory(
            prefix="gemini-hotplug-terminal-parent-"
        ) as temp:
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

    print(f"owner_terminal_parent_mutation_rejections={rejected}")
    print("owner_terminal_parent_validator_mutations=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
