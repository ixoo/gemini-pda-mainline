#!/usr/bin/env python3
"""Validate the physical-source production stack repair."""

from __future__ import annotations

import argparse
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    path = (
        args.source_root.resolve()
        / "drivers/soc/mediatek/mt6797-a72-physical-source-observer.c"
    )
    text = path.read_text(encoding="utf-8")
    start = text.index("mt6797_a72_physical_source_probe(")
    end = text.index("static const struct of_device_id", start)
    probe = text[start:end]

    require("#include <linux/slab.h>" in text, "allocation API include")
    require(
        "struct mt6797_a72_direct_state_snapshot snapshot;" not in probe,
        "production direct-state result is not on the kernel stack",
    )
    require(
        probe.count("struct mt6797_a72_direct_state_snapshot *snapshot;") == 1,
        "one production result pointer",
    )
    require(
        probe.count("snapshot = kvzalloc(sizeof(*snapshot), GFP_KERNEL);") == 1,
        "one sleepable allocation with vmalloc fallback",
    )
    require(probe.count("if (!snapshot)\n\t\treturn -ENOMEM;") == 1,
            "allocation failure closes the probe")
    require(probe.count("kvfree(snapshot);") == 1, "one matching result free")
    require(probe.index("kvzalloc(") < probe.index("mediatek,platform-state"),
            "allocation occurs before device references")
    require(probe.index("kvfree(snapshot);") > probe.index("put_device(context.platform)"),
            "result remains live through reference release")
    require(probe.count("mt6797_a72_physical_source_run(") == 1,
            "one public direct snapshot run")
    require(probe.count("mt6797_a72_physical_source_log(dev, snapshot)") == 1,
            "one successful result log")
    require("&snapshot" not in probe, "pointer is not passed as pointer-to-pointer")
    require("goto free_snapshot;" in probe,
            "first-reference failure releases allocation")
    require(probe.count("return ") == 2,
            "no post-allocation direct return bypasses cleanup")
    for token in (
        "put_device(context.bigidvfs)",
        "put_device(context.clock)",
        "put_device(context.platform)",
    ):
        require(probe.count(token) == 1, f"reference release preserved: {token}")
    for forbidden in (
        "cpu_up(",
        "cpu_down(",
        "writel(",
        "regmap_write(",
        "i2c_transfer(",
        "arm_smccc_smc(",
    ):
        require(forbidden not in text, f"new physical operation absent: {forbidden}")

    print("validation=a72-physical-source-production-stack-fix-source")
    print("production_direct_state_stack_objects=0")
    print("production_result_allocations=1")
    print("production_result_frees=1")
    print("physical_operations_added=0")
    print("result=pass")


if __name__ == "__main__":
    main()
