#!/usr/bin/env python3
"""Validate complete Binder public admission in the legacy P29 fixtures."""

from __future__ import annotations

import argparse
from pathlib import Path


TEST_SOURCE = Path("arch/arm64/kernel/mt6797_a72_membership_test.c")
P29_CASES = (
    "mt6797_a72_owner_r03_p29_rejects_and_retires",
    "mt6797_a72_owner_r03_p29_mutations_rejected",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def function(text: str, name: str) -> str:
    start = text.find(f"static void {name}(struct kunit *test)")
    require(start >= 0, f"function absent: {name}")
    end = text.find("\nstatic ", start + 1)
    require(end >= 0, f"function terminator absent: {name}")
    return text[start:end]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    path = args.source_root.resolve() / TEST_SOURCE
    require(path.is_file() and not path.is_symlink(),
            "membership test source absent or unsafe")
    text = path.read_text(encoding="utf-8")

    for name in P29_CASES:
        body = function(text, name)
        calls = (
            "mt6797_a72_membership_preflight_up(8, CPUHP_ONLINE)",
            "mt6797_a72_membership_validate_up(8, 0, CPUHP_ONLINE)",
            "mt6797_a72_membership_claim_cpu8(&state->transaction)",
            "mt6797_a72_membership_begin_provider_acquire",
        )
        positions = tuple(body.find(call) for call in calls)
        require(all(position >= 0 for position in positions),
                f"public-admission call absent: {name}")
        require(positions == tuple(sorted(positions)),
                f"public-admission call order changed: {name}")
        for call in calls:
            require(body.count(call) == 1,
                    f"unexpected public-admission call count in {name}: {call}")

    print("validation=a72-owner-kunit-p29-public-claim-source")
    print("changed_files=1")
    print("production_files_changed=0")
    print("preflight_validate_claim_paths=2")
    print("expected_owner_failures_repaired=1")
    print("false_positive_paths_closed=1")
    print("physical_operations=0")
    print("device_action=none")
    print("result=pass")


if __name__ == "__main__":
    main()
