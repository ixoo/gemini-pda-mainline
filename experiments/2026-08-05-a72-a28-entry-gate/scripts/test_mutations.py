#!/usr/bin/env python3
"""Ensure each targeted A28 snapshot mutation is rejected."""

from __future__ import annotations

from dataclasses import replace

from oracle import CPU8_UP, CPU9_UP, fixture, validate


def main() -> int:
    mutations = {
        "attempt": (8, CPU9_UP, fixture(8)),
        "members": (8, CPU8_UP, replace(fixture(8), members=1)),
        "provider": (8, CPU8_UP, replace(fixture(8), provider=2)),
        "online": (9, CPU9_UP, replace(fixture(9), online=0)),
        "flags": (8, CPU8_UP, replace(fixture(8), flags=0b0111)),
        "cpuhp": (8, CPU8_UP, replace(fixture(8), cpuhp8=1)),
        "mpidr": (8, CPU8_UP, replace(fixture(8), mpidr9=0x301)),
    }
    for name, (cpu, attempt, entry) in mutations.items():
        result = validate(cpu, True, attempt, entry)
        assert result == "-EPERM", (name, result)
        print(f"mutation={name} result={result}")
    print(f"mutations_rejected={len(mutations)}/{len(mutations)}")
    print("status=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
