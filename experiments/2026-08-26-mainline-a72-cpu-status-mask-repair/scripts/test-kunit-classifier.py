#!/usr/bin/env python3
"""Reject incomplete or reordered CPU-status-mask KUnit transcripts."""

from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parent / "classify-kunit.py"
spec = importlib.util.spec_from_file_location("cpu_mask_classifier", SCRIPT)
if spec is None or spec.loader is None:
    raise SystemExit("FAIL: classifier import unavailable")
classifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(classifier)


def transcript() -> str:
    lines = [
        f"Linux version {classifier.EXPECTED_RELEASE} (builder@example.invalid)",
        "KTAP version 1", "1..2",
    ]
    for suite_index, (suite, cases) in enumerate(classifier.SUITES, start=1):
        lines.extend((f"# Subtest: {suite}", "KTAP version 1", f"1..{len(cases)}"))
        lines.extend(f"ok {index} {case}" for index, case in enumerate(cases, start=1))
        lines.append(f"# {suite}: pass:{len(cases)} fail:0 skip:0 total:{len(cases)}")
        lines.append(f"# Totals: pass:{len(cases)} fail:0 skip:0 total:{len(cases)}")
        lines.append(f"ok {suite_index} {suite}")
    lines.extend((
        classifier.PANIC_PREFIX,
        f"{classifier.PANIC_END_PREFIX} ]---",
    ))
    return "\n".join(lines) + "\n"


valid = transcript()
classifier.classify_runtime(valid, classifier.EXPECTED_RELEASE, 124)
mutations = (
    ("1..6", "1..5"),
    ("ok 5 mt6797_state_each_a72_identity_bit_test",
     "not ok 5 mt6797_state_each_a72_identity_bit_test"),
    ("# Totals: pass:6 fail:0 skip:0 total:6",
     "# Totals: pass:5 fail:1 skip:0 total:6"),
    (f"ok 2 {classifier.SUITES[1][0]}", f"ok 1 {classifier.SUITES[1][0]}"),
    (classifier.PANIC_PREFIX, "different terminal state"),
    (classifier.EXPECTED_RELEASE, "7.1.3-wrong"),
)
rejected = 0
for old, new in mutations:
    changed = valid.replace(old, new, 1)
    try:
        classifier.classify_runtime(changed, classifier.EXPECTED_RELEASE, 124)
    except classifier.ClassificationError:
        rejected += 1
    else:
        raise SystemExit(f"FAIL: accepted classifier mutation: {old}")

print("kunit_classifier_test=pass")
print(f"mutations_rejected={rejected}")
print("device_action=none")
