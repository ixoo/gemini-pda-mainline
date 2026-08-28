#!/usr/bin/env python3
"""Reject incomplete or reordered default-off binder KUnit transcripts."""

from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parent / "classify-kunit.py"
spec = importlib.util.spec_from_file_location("binder_classifier", SCRIPT)
if spec is None or spec.loader is None:
    raise SystemExit("FAIL: classifier import unavailable")
classifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(classifier)


def transcript() -> str:
    lines = [
        f"Linux version {classifier.EXPECTED_RELEASE} (builder@example.invalid)",
        "KTAP version 1",
        f"1..{len(classifier.SUITES)}",
    ]
    for suite_index, (suite, cases) in enumerate(classifier.SUITES, start=1):
        lines.extend((
            f"# Subtest: {suite}",
            "KTAP version 1",
            f"1..{len(cases)}",
        ))
        lines.extend(
            f"ok {case_index} {case}"
            for case_index, case in enumerate(cases, start=1)
        )
        lines.append(
            f"# {suite}: pass:{len(cases)} fail:0 skip:0 total:{len(cases)}"
        )
        lines.append(
            f"# Totals: pass:{len(cases)} fail:0 skip:0 total:{len(cases)}"
        )
        lines.append(f"ok {suite_index} {suite}")
    lines.extend((
        classifier.PANIC_PREFIX,
        f"{classifier.PANIC_END_PREFIX} ]---",
    ))
    return "\n".join(lines) + "\n"


def rejected(raw: str, release: str = classifier.EXPECTED_RELEASE,
             exit_code: int = 124) -> bool:
    try:
        classifier.classify_runtime(raw, release, exit_code)
    except classifier.ClassificationError:
        return True
    return False


valid = transcript()
classifier.classify_runtime(valid, classifier.EXPECTED_RELEASE, 124)
owner = classifier.SUITES[0]
executor = classifier.SUITES[1]
binder = classifier.SUITES[2]
mutations = (
    valid.replace("1..30", "1..29", 1),
    valid.replace(f"ok 25 {owner[1][24]}", f"not ok 25 {owner[1][24]}", 1),
    valid.replace(f"ok 7 {executor[1][6]}", "ok 7 wrong_executor_case", 1),
    valid.replace(f"ok 4 {binder[1][3]}", f"ok 3 {binder[1][3]}", 1),
    valid.replace("# Totals: pass:12 fail:0 skip:0 total:12",
                  "# Totals: pass:11 fail:1 skip:0 total:12", 1),
    valid.replace(f"ok 3 {binder[0]}", f"ok 2 {binder[0]}", 1),
    valid.replace(classifier.PANIC_PREFIX, "different terminal state", 1),
    valid.replace(classifier.EXPECTED_RELEASE, "7.1.3-wrong", 1),
)
for number, mutation in enumerate(mutations, start=1):
    if not rejected(mutation):
        raise SystemExit(f"FAIL: classifier accepted mutation {number}")
if not rejected(valid, exit_code=0):
    raise SystemExit("FAIL: classifier accepted wrong QEMU exit")

print("kunit_classifier_test=pass")
print("valid_fixture=pass")
print("mutations_rejected=9")
print("suites=3")
print("tests=47")
print("device_action=none")
