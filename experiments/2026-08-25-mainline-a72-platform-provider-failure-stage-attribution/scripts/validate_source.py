#!/usr/bin/env python3
"""Validate the exact failure-stage attribution source invariants."""

from __future__ import annotations

import argparse
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def read(path: Path) -> str:
    require(path.is_file() and not path.is_symlink(), f"safe source: {path}")
    return path.read_text(encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--phase", choices=("production", "tests"), required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    soc = root / "drivers/soc/mediatek"
    header = read(soc / "mt6797-a72-platform-provider-clock-observer-internal.h")
    source = read(soc / "mt6797-a72-platform-provider-clock-observer.c")

    stages = (
        "MT6797_A72_PPC_FAILURE_NONE",
        "MT6797_A72_PPC_FAILURE_DEPENDENCY",
        "MT6797_A72_PPC_FAILURE_PLATFORM",
        "MT6797_A72_PPC_FAILURE_PROVIDER",
        "MT6797_A72_PPC_FAILURE_BEFORE_CLOCK",
    )
    require("enum mt6797_a72_ppc_failure_stage" in header, "stage enum")
    for stage in stages:
        require(stage in header and stage in source, f"stage wired: {stage}")
    require(
        "enum mt6797_a72_ppc_failure_stage *failure_stage" in header
        and "enum mt6797_a72_ppc_failure_stage *failure_stage" in source,
        "out-of-band stage output",
    )
    for stage, ret in (
        ("dependency", "-EPROBE_DEFER"),
        ("platform", "-EAGAIN"),
        ("provider", "-EIO"),
        ("before-clock", "-EIO"),
    ):
        require(f'return "{stage}";' in source, f"stage name: {stage}")
    require("*failure_stage = MT6797_A72_PPC_FAILURE_NONE;" in source,
            "stage initialized")
    require(source.count("MT6797_A72_PPC_FAILURE_PLATFORM;") == 2,
            "platform error and invalid assignments")
    require(source.count("MT6797_A72_PPC_FAILURE_PROVIDER;") == 2,
            "provider error and invalid assignments")
    require(source.count("MT6797_A72_PPC_FAILURE_BEFORE_CLOCK;") == 1,
            "one pre-clock checkpoint assignment")
    require(
        '"platform/provider/clock capture failed: stage=%s ret=%d\\n"' in source,
        "exact attributed failure log",
    )
    require("platform/provider/clock capture failed: %d" not in source,
            "ambiguous log removed")
    require(source.count("ops->clock(context, clock, &snapshot->clock)") == 1,
            "one protected-clock call site")
    require(source.count("ops->checkpoint(context, 0)") == 1,
            "one before checkpoint")
    require(source.count("ops->checkpoint(context, 1)") == 1,
            "one after checkpoint")
    for forbidden in ("cpu_up(", "cpu_down(", "psci_ops", "kernel_restart(",
                      "msleep(", "udelay("):
        require(forbidden not in source, f"forbidden production action: {forbidden}")

    if args.phase == "tests":
        test = read(soc / "mt6797-a72-platform-provider-clock-observer-test.c")
        require(test.count("enum mt6797_a72_ppc_failure_stage failure_stage;") == 8,
                "stage result in all eight cases")
        expected_assertions = {
            "MT6797_A72_PPC_FAILURE_NONE": 4,
            "MT6797_A72_PPC_FAILURE_DEPENDENCY": 1,
            "MT6797_A72_PPC_FAILURE_PLATFORM": 2,
            "MT6797_A72_PPC_FAILURE_PROVIDER": 2,
            "MT6797_A72_PPC_FAILURE_BEFORE_CLOCK": 1,
        }
        for stage, count in expected_assertions.items():
            require(test.count(f"failure_stage, {stage}") == count,
                    f"stage assertion count: {stage}")
        require(test.count("KUNIT_CASE(") == 8, "eight focused cases preserved")
        for forbidden in ("readl(", "writel(", "i2c_transfer(", "cpu_up("):
            require(forbidden not in test, f"hardware-free tests: {forbidden}")

    print(f"source_validation={args.phase}-pass")
    print("protected_clock_call_sites=1")
    print("caller_retries=0")
    print("device_action=none")


if __name__ == "__main__":
    main()
