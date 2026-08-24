#!/usr/bin/env python3
"""Validate generated A72 direct-state stack-safety follow-up patches."""

from __future__ import annotations

import argparse
from pathlib import Path


CORE = "0339-arm64-move-A72-direct-state-workspace-off-stack.patch"
TEST = "0340-arm64-move-A72-direct-state-KUnit-state-off-stack.patch"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def added(text: str) -> str:
    return "\n".join(
        line[1:] for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch-dir", type=Path, required=True)
    args = parser.parse_args()
    patch_dir = args.patch_dir.resolve()
    core = (patch_dir / CORE).read_text(encoding="utf-8")
    test = (patch_dir / TEST).read_text(encoding="utf-8")
    series = (patch_dir / "series").read_text(encoding="utf-8").splitlines()

    require(series == [CORE, TEST], "generated series order")
    require(core.count("diff --git ") == 1, "core file count")
    require(test.count("diff --git ") == 1, "test file count")
    require("arch/arm64/kernel/mt6797_a72_membership.c" in core,
            "core path")
    require("arch/arm64/kernel/mt6797_a72_direct_state_test.c" in test,
            "test path")
    combined = added(core) + "\n" + added(test)
    for token in (
        "a72_direct_state_workspace", "a72_direct_expected_owner",
        "memset(workspace, 0, sizeof(*workspace));",
        "struct mt6797_a72_direct_state_snapshot *observed =",
        "struct mt6797_a72_owner_snapshot owner_before;",
        "memchr_inv(snapshot, 0, sizeof(*snapshot))",
    ):
        require(token in combined, f"required stack token {token}")
    for forbidden in (
        "Signed-off-by:", "mt6797_a72_provider_snapshot(",
        "mt6797_a72_platform_state_snapshot(",
        "mt6797_dvfsp_clock_backend_read(",
        "mt6797_bigidvfs_backend_read(", "arm_smccc_smc(",
        "readl(", "writel(", "cpu_up(", "cpu_down(",
        "kernel_restart(", "emergency_restart(",
    ):
        require(forbidden not in combined, f"forbidden added effect {forbidden}")

    print("validation=a72-direct-state-stack-patches")
    print("generated_patch_count=2")
    print("core_changed_files=1")
    print("test_changed_files=1")
    print("physical_reader_callers=0")
    print("hardware_operations=0")
    print("cpu_requests=0")
    print("result=pass")


if __name__ == "__main__":
    main()
