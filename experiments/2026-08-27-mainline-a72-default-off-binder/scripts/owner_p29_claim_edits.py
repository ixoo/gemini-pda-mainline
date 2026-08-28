#!/usr/bin/env python3
"""Complete the Binder public-admission sequence in legacy P29 fixtures."""

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


def function_bounds(text: str, name: str) -> tuple[int, int]:
    start = text.find(f"static void {name}(struct kunit *test)")
    require(start >= 0, f"function absent: {name}")
    end = text.find("\nstatic ", start + 1)
    require(end >= 0, f"function terminator absent: {name}")
    return start, end


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    path = args.source_root.resolve() / TEST_SOURCE
    require(path.is_file() and not path.is_symlink(),
            "membership test source absent or unsafe")
    text = path.read_text(encoding="utf-8")

    old = (
        "\tret = mt6797_a72_membership_preflight_up(8, CPUHP_ONLINE);\n"
        "\tKUNIT_ASSERT_EQ(test, ret, 0);\n"
        "\tret = mt6797_a72_membership_begin_provider_acquire("
        "&state->transaction);\n"
    )
    new = (
        "\tret = mt6797_a72_membership_preflight_up(8, CPUHP_ONLINE);\n"
        "\tKUNIT_ASSERT_EQ(test, ret, 0);\n"
        "\tret = mt6797_a72_membership_validate_up(8, 0, CPUHP_ONLINE);\n"
        "\tKUNIT_ASSERT_EQ(test, ret, 0);\n"
        "\tret = mt6797_a72_membership_claim_cpu8(&state->transaction);\n"
        "\tKUNIT_ASSERT_EQ(test, ret, 0);\n"
        "\tret = mt6797_a72_membership_begin_provider_acquire("
        "&state->transaction);\n"
    )
    for name in P29_CASES:
        start, end = function_bounds(text, name)
        body = text[start:end]
        require(body.count(old) == 1,
                f"{name} public-admission anchor count changed")
        body = body.replace(old, new, 1)
        text = text[:start] + body + text[end:]

    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
