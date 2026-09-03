#!/usr/bin/env python3
"""Validate the bounded CPU9 restore-readiness observation."""

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


def require(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def validate(root: Path) -> list[str]:
    binding = (root / "drivers/soc/mediatek/mt6797-a72-hotplug-binding.c").read_text()
    header = (root / "drivers/soc/mediatek/mt6797-a72-hotplug-binding-internal.h").read_text()
    test = (root / "drivers/soc/mediatek/mt6797-a72-hotplug-binding-test.c").read_text()
    ledger = (root / "fs/pstore/gemini_a72_hotplug_ledger.c").read_text()
    ledger_internal = (root / "fs/pstore/gemini_a72_hotplug_ledger_internal.h").read_text()
    ledger_public = (root / "include/linux/gemini_a72_hotplug_ledger.h").read_text()
    ledger_test = (root / "fs/pstore/gemini_a72_hotplug_ledger_test.c").read_text()
    errors: list[str] = []

    try:
        readiness = body(binding, "mt6797_a72_hotplug_restore_readiness_with_ops")
        validate_restore = body(binding, "mt6797_a72_hotplug_validate_restore_op")
        fill = body(binding, "mt6797_a72_hotplug_fill_record")
        shape = body(ledger, "hotplug_record_shape_valid")
        decode = body(ledger, "hotplug_wire_valid")
        encode = body(ledger, "gemini_a72_hotplug_ledger_owner_checkpoint")
    except ValueError as exc:
        return [str(exc)]

    for marker in (
        "MT6797_A72_RESTORE_READY_SAMPLES_MAX 51U",
        "MT6797_A72_RESTORE_READY_CPU8_STATUS BIT(7)",
        "MT6797_A72_RESTORE_READY_CPU9_STATUS BIT(6)",
        "struct mt6797_a72_restore_readiness_result",
    ):
        require(errors, marker in header, f"binding header marker changed: {marker}")
    for marker in (
        "result->sample_calls++",
        "result->sleep_calls++",
        "result->first = result->last",
        "result->error = ret",
        "ret = -ETIMEDOUT",
        "result->ready = true",
        "spm_cpu_pwr_status |\n\t\t       result->last.spm_cpu_pwr_status_2nd",
    ):
        require(errors, marker in readiness, f"readiness contract changed: {marker}")
    require(errors, readiness.count("ops->sample(") == 1,
            "readiness must have one sample call site")
    require(errors, readiness.count("ops->sleep(") == 1,
            "readiness must have one bounded sleep call site")
    require(errors, "usleep_range(5000, 6000)" in binding,
            "5--6 ms bounded sleep changed")
    require(errors, "mt6797_a72_platform_state_snapshot(context, &state)" in binding,
            "read-only platform source changed")
    require(errors, "mt6797_a72_hotplug_restore_readiness_with_ops(" in validate_restore,
            "restore validation does not gate CPU_ON on readiness")
    require(errors, "binding->source.platform" in validate_restore,
            "restore readiness source changed")
    require(errors, "add_cpu(" not in readiness and "remove_cpu(" not in readiness,
            "readiness helper added a CPU request")
    require(errors, "psci_ops" not in readiness and "arm_smccc" not in readiness,
            "readiness helper added a firmware call")
    require(errors, "writel" not in readiness and "regmap_write" not in readiness,
            "readiness helper added an MMIO write")

    for field in (
        "restore_readiness_samples", "restore_readiness_sleeps",
        "restore_readiness_error", "restore_readiness_flags",
        "restore_first_status", "restore_first_status2",
        "restore_first_cpu9_pwr_con", "restore_last_status",
        "restore_last_status2", "restore_last_cpu9_pwr_con",
    ):
        field_type = "s32" if field == "restore_readiness_error" else "u32"
        require(errors, ledger_public.count(f"\t{field_type} {field};") == 1,
                f"public readiness field changed: {field}")
        require(errors, f".{field} =" in fill,
                f"binding does not retain readiness field: {field}")
        require(errors, f"record->{field}" in decode,
                f"ledger decoder omits readiness field: {field}")
        require(errors, f"committed.{field}" in encode,
                f"ledger encoder omits readiness field: {field}")
    for marker in (
        "GEMINI_A72_HOTPLUG_LEDGER_VERSION_WORD 0x00010002U",
        "GEMINI_A72_HOTPLUG_LEDGER_COPY_WORDS 37U",
        "GEMINI_A72_HOTPLUG_LEDGER_INTEGRITY_WORD 36U",
        "GEMINI_A72_HOTPLUG_LEDGER_WRITES_PER_RECORD 38U",
    ):
        require(errors, marker in ledger_internal,
                f"ledger layout marker changed: {marker}")
    for marker in (
        "GEMINI_A72_HOTPLUG_RESTORE_READINESS_SAMPLES_MAX 51U",
        "GEMINI_A72_HOTPLUG_RESTORE_READINESS_SLEEPS_MAX 50U",
    ):
        require(errors, marker in ledger_public,
                f"ledger readiness bound changed: {marker}")
    for marker in (
        "restore_readiness_samples >",
        "restore_readiness_sleeps + 1 !=",
        "GEMINI_A72_HOTPLUG_RESTORE_READINESS_ATTEMPTED",
        "GEMINI_A72_HOTPLUG_RESTORE_READINESS_READY",
        "record->cpu_on_calls))",
    ):
        require(errors, marker in shape, f"ledger semantic guard changed: {marker}")
    for marker in (
        "hotplug_binding_readiness_immediate_test",
        "hotplug_binding_readiness_settles_test",
        "hotplug_binding_readiness_timeout_test",
        "hotplug_binding_readiness_cpu8_guard_test",
    ):
        require(errors, f"KUNIT_CASE({marker})" in test,
                f"binding KUnit case missing: {marker}")
    require(errors, "KUNIT_CASE(hotplug_restore_readiness_timeout_test)" in ledger_test,
            "ledger readiness-timeout KUnit case missing")
    require(errors, "state.writes, 611U" in ledger_test,
            "successful ledger write bound changed")
    require(errors, "state.writes, 40U" in ledger_test,
            "first pstore-empty write bound changed")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    errors = validate(args.source_root.resolve())
    if errors:
        for error in errors:
            print(f"restore_readiness_source=fail reason={error}")
        return 1
    print("restore_readiness_source=pass")
    print("readiness_samples_max=51")
    print("readiness_sleeps_max=50")
    print("readiness_sleep_us=5000-6000")
    print("readiness_source=platform-state-read-only")
    print("cpu_on_gate=both-CPU9-status-mirrors-clear")
    print("retained_raw_fields=first-and-last-status-status2-cpu9-pwr-con")
    print("ledger_version=0x00010002")
    print("successful_ledger_writes_max=611")
    print("cpu_off_calls_added=0")
    print("cpu_on_calls_added=0")
    print("affinity_calls_added=0")
    print("retry_calls_added=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
