#!/usr/bin/env python3
"""Mutation tests for the closed A72 direct-state QEMU classifier."""

from __future__ import annotations

import importlib.util
from pathlib import Path


CLASSIFIER = Path(__file__).with_name("classify-kunit.py")
SPEC = importlib.util.spec_from_file_location("direct_state_classifier", CLASSIFIER)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def valid_log() -> str:
    cases = "\n".join(
        f"ok {number} {case}"
        for number, case in enumerate(MODULE.EXPECTED_CASES, start=1)
    )
    return f"""Linux version 7.1.3-gemini-direct-state-test (builder) #1
KTAP version 1
1..1
# Subtest: {MODULE.SUITE}
KTAP version 1
1..7
{cases}
# {MODULE.SUITE}: pass:7 fail:0 skip:0 total:7
# Totals: pass:7 fail:0 skip:0 total:7
ok 1 {MODULE.SUITE}
{MODULE.PANIC_PREFIX} on unknown-block(0,0)
{MODULE.PANIC_END_PREFIX} on unknown-block(0,0) ]---
"""


def rejected(raw: str, release: str = "7.1.3-gemini-direct-state-test",
             exit_code: int = 124) -> bool:
    try:
        MODULE.classify_runtime(raw, release, exit_code)
    except MODULE.ClassificationError:
        return True
    return False


def main() -> None:
    raw = valid_log()
    MODULE.classify_runtime(raw, "7.1.3-gemini-direct-state-test", 124)
    mutations = (
        raw.replace("ok 1 direct_snapshot_success",
                    "not ok 1 direct_snapshot_success", 1),
        raw.replace(f"# Subtest: {MODULE.SUITE}",
                    f"# Subtest: unexpected\n# Subtest: {MODULE.SUITE}", 1),
        raw.replace("ok 2 direct_registry_guards",
                    "ok 2 direct_source_mutations_rejected", 1),
        raw.replace("pass:7 fail:0", "pass:6 fail:1", 1),
        raw.replace("1..7", "1..8", 1),
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
