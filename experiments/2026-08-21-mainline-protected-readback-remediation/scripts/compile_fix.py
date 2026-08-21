#!/usr/bin/env python3
"""Apply the deterministic protected-readback KUnit name-collision fix."""

from __future__ import annotations

import argparse
from pathlib import Path


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        first = old.splitlines()[0]
        raise SystemExit(
            f"{path}: expected one anchor beginning {first!r}, found {count}"
        )
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    test = (
        args.source_root.resolve()
        / "drivers/soc/mediatek/mt6797-protected-readback-test.c"
    )

    replace_once(
        test,
        "#define MT6797_CLOCK_TEST_SETTLE_NS\t200\n",
        "#define MT6797_CLOCK_TEST_SETTLE_DELAY_NS\t200\n",
    )
    replace_once(
        test,
        "KUNIT_EXPECT_EQ(test, state->events[4].value,\n"
        "\t\t\tMT6797_CLOCK_TEST_SETTLE_NS);",
        "KUNIT_EXPECT_EQ(test, state->events[4].value,\n"
        "\t\t\tMT6797_CLOCK_TEST_SETTLE_DELAY_NS);",
    )


if __name__ == "__main__":
    main()
