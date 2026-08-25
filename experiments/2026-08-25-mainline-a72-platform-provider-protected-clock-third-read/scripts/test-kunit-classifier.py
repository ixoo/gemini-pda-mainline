#!/usr/bin/env python3
"""Mutation tests for the platform/provider/protected-clock KUnit classifier."""

from __future__ import annotations

import importlib.util
from pathlib import Path


CLASSIFIER = Path(__file__).with_name("classify-kunit.py")
SPEC = importlib.util.spec_from_file_location("platform_provider_clock_classifier",
                                              CLASSIFIER)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
RELEASE = "7.1.3-gemini-a72-clock-third-kunit"


def valid_log() -> str:
    cases = "\n".join(
        f"ok {number} {case}"
        for number, case in enumerate(MODULE.EXPECTED_CASES, start=1)
    )
    return f"""Linux version {RELEASE} (builder) #1
KTAP version 1
1..1
# Subtest: {MODULE.SUITE}
KTAP version 1
1..8
{cases}
# {MODULE.SUITE}: pass:8 fail:0 skip:0 total:8
# Totals: pass:8 fail:0 skip:0 total:8
ok 1 {MODULE.SUITE}
{MODULE.PANIC_PREFIX} on unknown-block(0,0)
{MODULE.PANIC_END_PREFIX} on unknown-block(0,0) ]---
"""


def rejected(raw: str, release: str = RELEASE, exit_code: int = 124) -> bool:
    try:
        MODULE.classify_runtime(raw, release, exit_code)
    except MODULE.ClassificationError:
        return True
    return False


def main() -> None:
    raw = valid_log()
    MODULE.classify_runtime(raw, RELEASE, 124)
    cases = MODULE.EXPECTED_CASES
    mutations = (
        raw.replace(f"ok 1 {cases[0]}", f"not ok 1 {cases[0]}", 1),
        raw.replace(f"# Subtest: {MODULE.SUITE}",
                    f"# Subtest: unexpected\n# Subtest: {MODULE.SUITE}", 1),
        raw.replace(f"ok 2 {cases[1]}", "ok 2 wrong_case", 1),
        raw.replace("pass:8 fail:0", "pass:7 fail:1", 1),
        raw.replace("1..8", "1..7", 1),
        raw.replace(MODULE.PANIC_PREFIX, "panic missing", 1),
    )
    for number, mutation in enumerate(mutations, start=1):
        if not rejected(mutation):
            raise SystemExit(f"mutation {number} was accepted")
    if not rejected(raw, release="wrong-release"):
        raise SystemExit("release mutation was accepted")
    if not rejected(raw, exit_code=0):
        raise SystemExit("exit mutation was accepted")
    print("valid_fixture=pass")
    print("mutations_rejected=8")
    print("result=pass")


if __name__ == "__main__":
    main()
