#!/usr/bin/env python3
"""Check bounded P31 safety mutations."""

from __future__ import annotations

from dataclasses import replace

from oracle import CPU8, CPU8_ATTEMPT, Entry, MASK, State, begin


def main() -> int:
    available = State(health="AVAILABLE", phase="IDLE", available=MASK)
    mutations = {
        "closed-window": (CPU8, CPU8_ATTEMPT, Entry(window_open=False), "-EPERM"),
        "wrong-attempt": (CPU8, 2, Entry(), "-EPERM"),
        "a28-reject": (CPU8, CPU8_ATTEMPT, Entry(a28_valid=False), "-EPERM"),
        "already-consumed": (
            CPU8, CPU8_ATTEMPT, Entry(), "-EALREADY",
        ),
    }
    for name, (cpu, attempt, entry, expected) in mutations.items():
        state = replace(available, consumed=CPU8_ATTEMPT,
                        available=MASK & ~CPU8_ATTEMPT) \
            if name == "already-consumed" else available
        actual, after = begin(state, cpu, attempt, entry)
        assert actual == expected, (name, actual, expected)
        if name != "a28-reject":
            assert after == state, (name, after, state)
        print(f"mutation={name} result={actual}")
    print(f"mutations_rejected={len(mutations)}/{len(mutations)}")
    print("status=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
