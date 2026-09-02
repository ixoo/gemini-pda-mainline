#!/usr/bin/env python3
"""Require the CPU9 hotplug-owner KUnit classifier to fail closed."""

from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "hotplug_owner_kunit_classifier", SCRIPT_DIR / "classify-kunit.py")
if SPEC is None or SPEC.loader is None:
    raise SystemExit("classifier import failed")
CLASSIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CLASSIFIER)


def render() -> str:
    lines = [
        f"Linux version {CLASSIFIER.EXPECTED_RELEASE} test",
        "KTAP version 1",
        f"1..{len(CLASSIFIER.SUITES)}",
    ]
    for suite_index, (suite, cases) in enumerate(CLASSIFIER.SUITES, start=1):
        lines.extend(("KTAP version 1", f"# Subtest: {suite}",
                      f"1..{len(cases)}"))
        lines.extend(
            f"ok {case_index} {case}"
            for case_index, case in enumerate(cases, start=1)
        )
        lines.extend((
            f"# {suite}: pass:{len(cases)} fail:0 skip:0 total:{len(cases)}",
            f"# Totals: pass:{len(cases)} fail:0 skip:0 total:{len(cases)}",
            f"ok {suite_index} {suite}",
        ))
    lines.extend((
        CLASSIFIER.PANIC_PREFIX,
        f"---[ end {CLASSIFIER.PANIC_PREFIX} ]---",
    ))
    return "\n".join(lines) + "\n"


def replace_once(value: str, old: str, new: str) -> str:
    if value.count(old) != 1:
        raise RuntimeError(f"mutation anchor changed: {old}")
    return value.replace(old, new, 1)


def rejects(raw: str, qemu_exit: int = 124) -> bool:
    try:
        CLASSIFIER.classify_runtime(
            raw, CLASSIFIER.EXPECTED_RELEASE, qemu_exit)
    except CLASSIFIER.ClassificationError:
        return True
    return False


def main() -> None:
    positive = render()
    CLASSIFIER.classify_runtime(positive, CLASSIFIER.EXPECTED_RELEASE, 124)
    mutations = []
    for case in (
        "mt6797_a72_hotplug_success_lifecycle",
        "mt6797_a72_hotplug_entry_rejections",
        "mt6797_a72_hotplug_precommit_rejection",
        "mt6797_a72_hotplug_postcommit_fault",
        "mt6797_a72_hotplug_restore_fault",
    ):
        ordinal = next(
            index for index, name in enumerate(CLASSIFIER.SUITES[0][1], start=1)
            if name == case)
        old = f"ok {ordinal} {case}"
        mutations.append(replace_once(positive, old, f"not {old}"))
    mutations.extend((
        replace_once(positive, "1..39", "1..38"),
        replace_once(positive, "KTAP version 1\n1..3",
                     "KTAP version 1\nKTAP version 1\n1..3"),
        positive.replace(CLASSIFIER.EXPECTED_RELEASE,
                         "7.1.3-gemini-wrong", 1),
    ))
    rejected = sum(rejects(mutation) for mutation in mutations)
    if rejected != len(mutations) or not rejects(positive, qemu_exit=0):
        raise SystemExit("kunit_classifier_mutations=fail")
    print(f"kunit_classifier_mutation_rejections={rejected + 1}")
    print("kunit_classifier_mutations=pass")


if __name__ == "__main__":
    main()
