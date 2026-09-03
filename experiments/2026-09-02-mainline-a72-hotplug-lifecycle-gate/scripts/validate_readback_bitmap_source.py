#!/usr/bin/env python3
"""Validate the exact behavior-neutral CPU9 readback bitmap source shape."""

from __future__ import annotations

import argparse
from pathlib import Path


BITS = (
    "BASELINE_NULL", "POST_NULL", "BASELINE_INVALID",
    "BASELINE_STATUS_CPU8", "BASELINE_STATUS2_CPU8",
    "BASELINE_STATUS_CPU9", "BASELINE_STATUS2_CPU9",
    "BASELINE_CCI_BEFORE", "BASELINE_CCI_AFTER", "POST_INVALID",
    "POST_STATUS_CPU8", "POST_STATUS2_CPU8", "POST_STATUS_CPU9",
    "POST_STATUS2_CPU9", "POST_CCI_BEFORE", "POST_CCI_AFTER",
    "MP2_CPUSYS_PWR_CON", "CPU8_PWR_CON", "EXT_ISO", "DCM",
    "CCI_REQUEST", "PROVIDER", "CLOCK", "BIGIDVFS",
)


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
    header = (root / "drivers/soc/mediatek/mt6797-a72-hotplug-executor-internal.h").read_text()
    source = (root / "drivers/soc/mediatek/mt6797-a72-hotplug-executor.c").read_text()
    test = (root / "drivers/soc/mediatek/mt6797-a72-hotplug-executor-test.c").read_text()
    binding = (root / "drivers/soc/mediatek/mt6797-a72-hotplug-binding.c").read_text()
    errors: list[str] = []

    for index, name in enumerate(BITS):
        marker = f"#define MT6797_A72_HOTPLUG_MISMATCH_{name} BIT({index})"
        if header.count(marker) != 1:
            errors.append(f"bit changed: {name}")
        if source.count(f"MT6797_A72_HOTPLUG_MISMATCH_{name}") != 1:
            errors.append(f"source term changed: {name}")
        if test.count(f"MT6797_A72_HOTPLUG_MISMATCH_{name}") != 1:
            errors.append(f"test term changed: {name}")
    for marker in (
        "#define MT6797_A72_HOTPLUG_READBACK_BITMAP_V1 BIT(31)",
        "#define MT6797_A72_HOTPLUG_MISMATCH_MASK GENMASK(23, 0)",
        "u32 mt6797_a72_hotplug_readback_mismatch(",
    ):
        if header.count(marker) != 1:
            errors.append(f"header contract changed: {marker}")

    try:
        mismatch = body(source, "mt6797_a72_hotplug_readback_mismatch")
        predicate = body(source, "mt6797_a72_hotplug_readback_proves_cpu9_off")
    except ValueError as exc:
        errors.append(str(exc))
        mismatch = predicate = ""
    for marker in (
        "if (!baseline)", "if (!post_state)",
        "if (!baseline || !post_state)",
        "memcmp(baseline->provider", "memcmp(baseline->clock",
        "memcmp(baseline->bigidvfs", "return mismatch;",
    ):
        if marker not in mismatch:
            errors.append(f"mismatch evaluator changed: {marker}")
    if "return !mt6797_a72_hotplug_readback_mismatch(baseline, post_state);" not in predicate:
        errors.append("Boolean predicate no longer delegates exactly")
    for forbidden in (
        "writel", "writeq", "cpu_down", "cpu_up", "remove_cpu",
        "add_cpu", "psci_ops", "arm_smccc", "smp_call_function",
    ):
        if forbidden in mismatch:
            errors.append(f"effectful mismatch evaluator: {forbidden}")

    binding_fragment = (
        ".readback_mismatch = binding->down_result.snapshots == 2 ?\n"
        "\t\t\tMT6797_A72_HOTPLUG_READBACK_BITMAP_V1 |\n"
        "\t\t\tmt6797_a72_hotplug_readback_mismatch("
    )
    if binding.count(binding_fragment) != 1:
        errors.append("record-4 bitmap publication changed")
    if ".readback_mismatch = binding->down_result.snapshots == 2 &&" in binding:
        errors.append("legacy Boolean publication remains")
    if test.count("static void mt6797_hotplug_readback_bitmap(") != 1:
        errors.append("focused bitmap KUnit case missing")
    if test.count("KUNIT_CASE(mt6797_hotplug_readback_bitmap)") != 1:
        errors.append("focused bitmap KUnit case unregistered")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    errors = validate(args.source_root.resolve())
    if errors:
        for error in errors:
            print(f"readback_bitmap_source=fail reason={error}")
        return 1
    print("readback_bitmap_source=pass")
    print(f"mismatch_bits={len(BITS)}")
    print("bitmap_format_bit=31")
    print("predicate_behavior_changed=false")
    print("physical_effect_calls=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
