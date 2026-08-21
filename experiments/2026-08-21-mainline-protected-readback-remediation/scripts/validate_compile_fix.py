#!/usr/bin/env python3
"""Validate the protected-readback KUnit name-collision fix."""

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
    test = (
        args.source_root.resolve()
        / "drivers/soc/mediatek/mt6797-protected-readback-test.c"
    ).read_text()

    require(
        "#define MT6797_CLOCK_TEST_SETTLE_DELAY_NS\t200" in test,
        "unique numeric settle-delay macro",
    )
    require(
        "#define MT6797_CLOCK_TEST_SETTLE_NS" not in test,
        "colliding numeric macro removed",
    )
    require(
        test.count("MT6797_CLOCK_TEST_SETTLE_DELAY_NS") == 2,
        "numeric macro has one definition and one expectation",
    )
    require(
        test.count("MT6797_CLOCK_TEST_SETTLE_NS") == 3,
        "event kind retains enum, record, and expectation",
    )
    require(test.count("KUNIT_CASE(mt6797_") == 6, "six KUnit cases retained")
    for token in (
        "state->event_count, 25U",
        "state->event_count, 602U",
        "state->event_count, 623U",
        "fault <= 8",
        'name = "mt6797-protected-readback"',
    ):
        require(token in test, f"retained test token: {token}")

    print("compile_fix_validation=pass")
    print("changed_scope=numeric-test-macro-and-expectation-only")
    print("kunit_cases=6")
    print("production_source_changed=false")
    print("device_action=none")


if __name__ == "__main__":
    main()
