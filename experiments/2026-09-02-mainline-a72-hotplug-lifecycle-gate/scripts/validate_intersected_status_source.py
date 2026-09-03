#!/usr/bin/env python3
"""Validate the exact MT6797 intersected CPU9-off status repair."""

from __future__ import annotations

import argparse
from pathlib import Path


def body(text: str, name: str) -> str:
    start = text.find(name + "(")
    if start < 0:
        raise ValueError(f"function missing: {name}")
    brace = text.find("{", start)
    depth = 0
    for index in range(brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[brace:index + 1]
    raise ValueError(f"function unterminated: {name}")


def validate(root: Path) -> list[str]:
    source = (
        root / "drivers/soc/mediatek/mt6797-a72-hotplug-executor.c"
    ).read_text(encoding="utf-8")
    test = (
        root / "drivers/soc/mediatek/mt6797-a72-hotplug-executor-test.c"
    ).read_text(encoding="utf-8")
    errors: list[str] = []

    try:
        status = body(source, "mt6797_a72_hotplug_status_exact")
        predicate = body(
            source, "mt6797_a72_hotplug_readback_proves_cpu9_off"
        )
        mismatch = body(source, "mt6797_a72_hotplug_readback_mismatch")
        rejection = body(test, "mt6797_hotplug_readback_rejections")
    except ValueError as exc:
        return [str(exc)]

    intersection = (
        "!((readback->spm_cpu_pwr_status &\n"
        "\t\t   readback->spm_cpu_pwr_status_2nd) & forbidden)"
    )
    if status.count(intersection) != 1:
        errors.append("status helper lacks the exact two-word intersection")
    for stale in (
        "!(readback->spm_cpu_pwr_status & forbidden)",
        "!(readback->spm_cpu_pwr_status_2nd & forbidden)",
    ):
        if stale in status:
            errors.append("independent CPU9-off mirror rule remains")
    for marker in (
        "MT6797_A72_HOTPLUG_MISMATCH_POST_STATUS_CPU9 |",
        "MT6797_A72_HOTPLUG_MISMATCH_POST_STATUS2_CPU9;",
        "!mt6797_a72_hotplug_status_exact(post_state, false)",
        "mismatch = mt6797_a72_hotplug_readback_mismatch(",
        "return !(mismatch & ~raw_cpu9_mismatch);",
    ):
        if predicate.count(marker) != 1:
            errors.append(f"predicate contract changed: {marker}")
    for forbidden in (
        "MISMATCH_POST_STATUS_CPU8",
        "MISMATCH_POST_STATUS2_CPU8",
        "MISMATCH_BASELINE_STATUS_CPU9",
        "MISMATCH_BASELINE_STATUS2_CPU9",
        "MISMATCH_POST_INVALID",
    ):
        if forbidden in predicate:
            errors.append(f"predicate ignores forbidden term: {forbidden}")
    if mismatch.count("MT6797_A72_HOTPLUG_MISMATCH_") != 24:
        errors.append("24-term raw mismatch evaluator changed")
    if "return mismatch;" not in mismatch:
        errors.append("raw mismatch return changed")

    expected_assertions = {
        "post.spm_cpu_pwr_status |= MT6797_A72_HOTPLUG_CPU9_STATUS;": 2,
        "post.spm_cpu_pwr_status_2nd |= MT6797_A72_HOTPLUG_CPU9_STATUS;": 1,
        "MT6797_A72_HOTPLUG_MISMATCH_POST_STATUS_CPU9);": 1,
        "MT6797_A72_HOTPLUG_MISMATCH_POST_STATUS2_CPU9);": 1,
    }
    for marker, count in expected_assertions.items():
        if rejection.count(marker) != count:
            errors.append(f"focused intersection assertion changed: {marker}")
    if rejection.count("mt6797_a72_hotplug_readback_proves_cpu9_off") != 14:
        errors.append("focused acceptance/rejection assertion count changed")
    if rejection.count("KUNIT_EXPECT_TRUE") != 3:
        errors.append("single-mirror acceptance coverage changed")
    if rejection.count("KUNIT_EXPECT_FALSE") != 11:
        errors.append("fail-closed rejection coverage changed")

    for forbidden in (
        "writel", "writeq", "cpu_down", "cpu_up", "remove_cpu",
        "add_cpu", "psci_ops", "arm_smccc", "smp_call_function",
        "msleep", "udelay", "retry",
    ):
        if forbidden in status or forbidden in predicate:
            errors.append(f"effect or delay added to status proof: {forbidden}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    errors = validate(args.source_root.resolve())
    if errors:
        for error in errors:
            print(f"intersected_status_source=fail reason={error}")
        return 1
    print("intersected_status_source=pass")
    print("cpu8_status_rule=both-mirrors")
    print("cpu9_off_status_rule=two-word-intersection-clear")
    print("raw_bitmap_terms=24-unchanged")
    print("snapshot_calls=unchanged")
    print("hardware_effect_calls=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
