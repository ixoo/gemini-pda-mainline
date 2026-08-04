#!/usr/bin/env python3
"""Validate phase-marker inventory, order, and exact-parent equivalence."""

from __future__ import annotations

import argparse
from pathlib import Path


PHASES = (
    "task-ready-before", "task-ready-after", "task-start-wait-before",
    "task-start-wait-after", "task-work-before", "task-work-after",
    "task-done-before", "task-done-after", "create8-before", "create8-after",
    "create9-before", "create9-after", "wake8-before", "wake8-after",
    "wake9-before", "wake9-after", "ready8-wait-before", "ready8-wait-after",
    "ready9-wait-before", "ready9-wait-after", "release-before", "release-after",
    "done8-wait-before", "done8-wait-after", "done9-wait-before",
    "done9-wait-after", "stop8-before", "stop8-after", "stop9-before",
    "stop9-after", "run-exit",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"error: {message}")


def without_markers(text: str) -> str:
    return "".join(
        line for line in text.splitlines(keepends=True)
        if "gemini-a72-sc-phase" not in line
    )


def ordered(text: str, phases: tuple[str, ...]) -> bool:
    positions = [text.index(f"phase={phase}\\n") for phase in phases]
    return positions == sorted(positions)


def swap_marker_lines(text: str, first: str, second: str) -> str:
    first_line = next(line for line in text.splitlines(keepends=True)
                      if f"phase={first}\\n" in line)
    second_line = next(line for line in text.splitlines(keepends=True)
                       if f"phase={second}\\n" in line)
    placeholder = "\t/* phase-marker-swap-placeholder */\n"
    return text.replace(first_line, placeholder, 1).replace(
        second_line, first_line, 1
    ).replace(placeholder, second_line, 1)


def validate(child: str, parent: str) -> None:
    require(without_markers(child) == parent, "non-marker source change detected")
    require(child.count("gemini-a72-sc-phase") == len(PHASES), "marker count changed")
    for phase in PHASES:
        require(child.count(f"phase={phase}\\n") == 1, f"marker changed: {phase}")
    require(ordered(child, (
        "task-ready-before", "task-ready-after", "task-start-wait-before",
        "task-start-wait-after", "task-work-before", "task-work-after",
        "task-done-before", "task-done-after",
    )), "task marker order changed")
    require(ordered(child, (
        "create8-before", "create8-after", "create9-before", "create9-after",
        "wake8-before", "wake8-after", "wake9-before", "wake9-after",
        "ready8-wait-before", "ready8-wait-after", "ready9-wait-before",
        "ready9-wait-after", "release-before", "release-after",
        "done8-wait-before", "done8-wait-after", "done9-wait-before",
        "done9-wait-after", "stop8-before", "stop8-after", "stop9-before",
        "stop9-after", "run-exit",
    )), "parent marker order changed")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--parent-psci", required=True, type=Path)
    args = parser.parse_args()
    child = (args.source / "arch/arm64/kernel/psci.c").read_text()
    parent = args.parent_psci.read_text()
    validate(child, parent)

    mutations = 0
    for phase in PHASES:
        line = next(line for line in child.splitlines(keepends=True)
                    if f"phase={phase}\\n" in line)
        mutated = child.replace(line, "", 1)
        try:
            validate(mutated, parent)
        except SystemExit:
            mutations += 1
            continue
        raise SystemExit(f"error: missing marker accepted: {phase}")
    require(mutations == len(PHASES), "marker mutations were not all rejected")
    for first, second in (("task-ready-before", "task-ready-after"),
                          ("create8-before", "create8-after")):
        try:
            validate(swap_marker_lines(child, first, second), parent)
        except SystemExit:
            mutations += 1
            continue
        raise SystemExit(f"error: marker-order mutation accepted: {first}")
    print("validation=a72-scheduler-phase-markers")
    print(f"markers={len(PHASES)}")
    print(f"mutations={mutations}-rejected")
    print("non_marker_diff=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
