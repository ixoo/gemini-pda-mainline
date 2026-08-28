#!/usr/bin/env python3
"""Validate the exact CPU8/CPU9 register-capsule child and mutations."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from capsule_edits import (
    CAPSULE_ANCHOR,
    CAPSULE_BLOCK,
    CAPTURE_CALL_CHILD,
    CAPTURE_CALL_PARENT,
    EMIT_CHILD,
    EMIT_PARENT,
    INCLUDE_CHILD,
    INCLUDE_PARENT,
    RESULT_CHILD,
    RESULT_PARENT,
    reverse_text,
    transform_text,
)


class ValidationError(RuntimeError):
    pass


IDENTITY_FIELDS = (
    "abi",
    "fields",
    "valid",
    "error",
    "cpu",
    "midr",
    "revidr",
    "cntfrq",
    "ctr",
    "dczid",
    "cpuinfo_match",
    "mpidr",
    "clidr",
    "id_aa64dfr0",
    "id_aa64isar0",
    "id_aa64isar1",
    "id_aa64mmfr0",
    "id_aa64mmfr1",
    "id_aa64pfr0",
    "id_aa64pfr1",
    "id_isar0",
    "id_isar1",
    "id_isar2",
    "id_isar3",
    "id_isar4",
    "id_isar5",
    "id_mmfr0",
    "id_mmfr1",
    "id_mmfr2",
    "id_mmfr3",
    "id_pfr0",
    "id_pfr1",
)

CPUINFO_FIELDS = (
    "cntfrq",
    "ctr",
    "dczid",
    "midr",
    "id_aa64isar0",
    "id_aa64isar1",
    "id_aa64mmfr0",
    "id_aa64mmfr1",
    "id_aa64pfr0",
    "id_aa64pfr1",
    "id_isar0",
    "id_isar1",
    "id_isar2",
    "id_isar3",
    "id_isar4",
    "id_isar5",
    "id_mmfr0",
    "id_mmfr1",
    "id_mmfr2",
    "id_mmfr3",
    "id_pfr0",
    "id_pfr1",
)

FORBIDDEN = (
    r"\bpsci_ops\b",
    r"\bcpu_up\b",
    r"\bcpu_down\b",
    r"\bcpu_on\b",
    r"\bcpu_off\b",
    r"\binvoke_psci\b",
    r"\bioremap\b",
    r"\breadl(?:_relaxed)?\b",
    r"\bwritel(?:_relaxed)?\b",
    r"\bregulator_",
    r"\bclk_",
    r"\bsmc\b",
    r"\bhvc\b",
    r"\bschedule_(?:work|delayed_work)\b",
    r"\b(?:u|m|ms)sleep\b",
    r"\b(?:u|m)delay\b",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def validate_semantics(child: str, parent: str) -> None:
    require(child == transform_text(parent), "child is not the exact transform")
    require(reverse_text(child) == parent, "child does not reverse to parent")
    require(child.count("gemini-a72-pair-v7 result=%s parent_pass=%d") == 1,
            "pair-v7 terminal identity changed")
    require(parent.count("gemini-a72-pair-v7 result=%s parent_pass=%d") == 1,
            "parent pair-v7 terminal is not unique")
    require(child.index("phase=task-capture-before") <
            child.index("phase=task-ready-before"),
            "capture is not before task readiness")
    require(child.count("phase=task-capture-before") == 1 and
            child.count("phase=task-capture-after") == 1,
            "capture marker inventory changed")
    require(CAPSULE_BLOCK.count("get_cpu();") == 1,
            "capture does not have one get_cpu")
    require(CAPSULE_BLOCK.count("put_cpu();") == 1,
            "capture does not have one put_cpu")
    require(CAPSULE_BLOCK.count("this_cpu_ptr(&cpu_data)") == 1,
            "per-CPU startup record lookup changed")
    require("for (" not in CAPSULE_BLOCK and "while (" not in CAPSULE_BLOCK,
            "capture acquired an unbounded loop")
    require(CAPSULE_BLOCK.count("read_cpuid(") == 22,
            "fixed direct register-read count changed")
    for call in (
        "read_cpuid_mpidr()",
        "read_cpuid_id()",
        "read_cpuid_cachetype()",
        "arch_timer_get_cntfrq()",
    ):
        require(CAPSULE_BLOCK.count(call) == 1, f"read inventory changed: {call}")
    require(CAPSULE_BLOCK.index("smp_wmb();") <
            CAPSULE_BLOCK.index("WRITE_ONCE(capsule->complete, 1);"),
            "capsule publication barrier changed")
    identity = CAPSULE_BLOCK.split(
        "static u64 mt6797_a72_regcap_identity", 1
    )[1].split("static bool mt6797_a72_regcap_cpuinfo_match", 1)[0]
    for field in IDENTITY_FIELDS:
        require(len(re.findall(rf"capsule->{field}\b", identity)) == 1,
                f"identity field count changed: {field}")
    require(len(IDENTITY_FIELDS) == 32, "canonical identity field count changed")
    match = CAPSULE_BLOCK.split(
        "static bool mt6797_a72_regcap_cpuinfo_match", 1
    )[1].split("static int mt6797_a72_regcap_capture", 1)[0]
    for field in CPUINFO_FIELDS:
        require(len(re.findall(rf"capsule->{field}\b", match)) == 1,
                f"cpuinfo capsule comparison changed: {field}")
        require(len(re.findall(rf"info->reg_{field}\b", match)) == 1,
                f"cpuinfo stored comparison changed: {field}")
    require(len(CPUINFO_FIELDS) == 22, "cpuinfo comparison count changed")
    for part in ("core", "aa64", "a32isar", "a32mm"):
        require(CAPSULE_BLOCK.count(f"part={part} result=%s") == 1,
                f"capsule output part changed: {part}")
    require(EMIT_CHILD.count("mt6797_a72_regcap_emit") == 2,
            "per-target terminal emission changed")
    delta = INCLUDE_CHILD + CAPSULE_BLOCK + RESULT_CHILD + CAPTURE_CALL_CHILD + EMIT_CHILD
    for pattern in FORBIDDEN:
        require(re.search(pattern, delta) is None,
                f"forbidden action entered capsule delta: {pattern}")


def synthetic_parent() -> str:
    return (
        "prefix\n"
        + INCLUDE_PARENT
        + "middle\n"
        + CAPSULE_ANCHOR
        + RESULT_PARENT
        + CAPTURE_CALL_PARENT
        + 'pr_emerg("gemini-a72-pair-v7 result=%s parent_pass=%d\\n");\n'
        + EMIT_PARENT
        + "suffix\n"
    )


def expect_reject(name: str, child: str, parent: str) -> None:
    try:
        validate_semantics(child, parent)
    except (ValidationError, RuntimeError):
        return
    raise ValidationError(f"unsafe mutation accepted: {name}")


def self_test() -> None:
    parent = synthetic_parent()
    child = transform_text(parent)
    validate_semantics(child, parent)
    mutations = (
        ("abi", child.replace("MT6797_A72_REGCAP_ABI 1",
                              "MT6797_A72_REGCAP_ABI 2", 1)),
        ("field-count", child.replace("MT6797_A72_REGCAP_FIELDS 32",
                                      "MT6797_A72_REGCAP_FIELDS 31", 1)),
        ("preemption-open", child.replace("cpu = get_cpu();", "cpu = 8;", 1)),
        ("preemption-close", child.replace("put_cpu();", "preempt_enable();", 1)),
        ("target-record", child.replace("this_cpu_ptr(&cpu_data)",
                                        "&per_cpu(cpu_data, 0)", 1)),
        ("revidr-read", child.replace(
            "capsule->revidr = read_cpuid(REVIDR_EL1);\n", "", 1)),
        ("cpuinfo-bypass", child.replace(
            "if (mt6797_a72_regcap_cpuinfo_match(capsule, info)) {",
            "if (true || mt6797_a72_regcap_cpuinfo_match(capsule, info)) {", 1)),
        ("publication-barrier", child.replace("\tsmp_wmb();\n", "", 1)),
        ("publication-marker", child.replace(
            "WRITE_ONCE(capsule->complete, 1);", "capsule->complete = 1;", 1)),
        ("identity-field", child.replace(
            "\tidentity = mt6797_a72_regcap_mix(identity, capsule->revidr);\n",
            "", 1)),
        ("output-part", child.replace(
            'part=a32mm result=%s', 'part=missing result=%s', 1)),
        ("physical-action", child.replace(
            "capsule->error = error;", "psci_ops.cpu_on(0, 0);\n\tcapsule->error = error;", 1)),
    )
    for name, mutated in mutations:
        expect_reject(name, mutated, parent)
    print("validation=a72-target-register-capsule-definition")
    print(f"identity_fields={len(IDENTITY_FIELDS)}")
    print(f"cpuinfo_comparisons={len(CPUINFO_FIELDS)}")
    print(f"negative_mutations={len(mutations)}")
    print("physical_actions=none")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path)
    parser.add_argument("--parent-psci", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if args.source is None or args.parent_psci is None:
        parser.error("--source and --parent-psci are required without --self-test")
    child = (args.source / "arch/arm64/kernel/psci.c").read_text(encoding="utf-8")
    parent = args.parent_psci.read_text(encoding="utf-8")
    validate_semantics(child, parent)
    print("validation=a72-target-register-capsule-source")
    print("parent_reversal=byte-identical")
    print("changed_path=arch/arm64/kernel/psci.c")
    print("physical_actions=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
