#!/usr/bin/env python3
"""Validate the generated A72 preflight target test-only patch."""

from __future__ import annotations

import argparse
from pathlib import Path


PATCH = "0341-arm64-fix-A72-direct-state-preflight-target-test.patch"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch-dir", type=Path, required=True)
    args = parser.parse_args()

    patch_dir = args.patch_dir.resolve()
    text = (patch_dir / PATCH).read_text(encoding="utf-8")
    series = (patch_dir / "series").read_text(encoding="utf-8").splitlines()
    require(series == [PATCH], "generated series order")
    require(text.count("diff --git ") == 1, "patch file count")
    path = "arch/arm64/kernel/mt6797_a72_direct_state_test.c"
    require(f"diff --git a/{path} b/{path}" in text,
            "test-only path changed")

    added = [line[1:] for line in text.splitlines()
             if line.startswith("+") and not line.startswith("+++")]
    removed = [line[1:] for line in text.splitlines()
               if line.startswith("-") and not line.startswith("---")]
    corrected = "mt6797_a72_membership_preflight_up(8, CPUHP_ONLINE)"
    incorrect = "mt6797_a72_membership_preflight_up(8, CPUHP_OFFLINE)"
    require(len(added) == 2 and len(removed) == 2,
            "patch is not a two-line substitution")
    require(sum(corrected in line for line in added) == 2,
            "corrected target additions")
    require(sum(incorrect in line for line in removed) == 2,
            "incorrect target removals")
    require(all(corrected in line for line in added),
            "unexpected added code")
    require(all(incorrect in line for line in removed),
            "unexpected removed code")

    print("validation=a72-direct-state-target-fix-patch")
    print("generated_patch_count=1")
    print("changed_files=1")
    print("changed_lines=2")
    print("production_code_changes=0")
    print("hardware_operations=0")
    print("cpu_requests=0")
    print("device_action=none")
    print("boot_candidate=false")
    print("result=pass")


if __name__ == "__main__":
    main()
