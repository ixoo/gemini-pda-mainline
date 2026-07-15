#!/usr/bin/env python3
"""Normalize a private vendor CMDQ record/status capture without addresses."""

from __future__ import annotations

import argparse
import re
from collections import Counter
from pathlib import Path


SCENARIOS = {
    1: "primary-display",
    2: "primary-memory-output",
    11: "display-trigger-loop",
    15: "display-ESD-check",
    16: "display-screen-capture",
}

RECORD_RE = re.compile(
    r"^\s*\d+,\(\s*\d+,\s*(\d+),\s*0x[0-9a-fA-F]+,\s*\d+,\s*\d+,\s*\d+\),"
    r"\((\d+),\s*(\d+)\),",
    re.MULTILINE,
)
ENGINE_RE = re.compile(
    r"^([A-Z0-9_]+): count \d+, owner -?\d+, fail: (\d+), reset: (\d+)$",
    re.MULTILINE,
)
TOTAL_RE = re.compile(r"^====== Total (\d+) (Active|Wait) Task =======$", re.MULTILINE)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    args = parser.parse_args()

    text = args.capture.read_text(errors="replace")
    records = Counter(
        (int(scenario), int(thread), int(priority))
        for scenario, thread, priority in RECORD_RE.findall(text)
    )

    print("CMDQ normalized proc summary")
    for scenario, thread, priority in sorted(records):
        name = SCENARIOS.get(scenario, "unknown")
        print(
            f"scenario={scenario}|name={name}|thread={thread}|"
            f"hardware-priority={priority}|records={records[(scenario, thread, priority)]}"
        )

    for count, state in TOTAL_RE.findall(text):
        print(f"tasks.{state.lower()}={count}")

    failures = resets = 0
    engines = 0
    for _name, fail, reset in ENGINE_RE.findall(text):
        engines += 1
        failures += int(fail)
        resets += int(reset)
    print(f"engines={engines}|failures={failures}|resets={resets}")
    print("addresses-and-process-identifiers=excluded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
