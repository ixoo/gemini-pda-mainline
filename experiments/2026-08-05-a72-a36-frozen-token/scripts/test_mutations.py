#!/usr/bin/env python3
"""Check bounded READY identity and frozen-token mutations."""

from __future__ import annotations

from dataclasses import replace

from oracle import CPU8_ATTEMPT, MASK, Ready, State, mint


def main() -> int:
    ready = Ready()
    state = State(health="AVAILABLE", phase="IDLE", available=MASK,
                  consumed=CPU8_ATTEMPT, next_generation=1,
                  next_cookie=0xA7200001)
    mutations = {
        "bad-abi": replace(ready, abi=6),
        "bad-profile": replace(ready, profile="other"),
        "empty-plan": replace(ready, identities=(0, 2, 3, 4)),
        "bad-target": replace(ready, targets=(8, 7)),
        "bad-expected-mpidr": replace(ready, expected_mpidr=(0x200, 0x301)),
        "bad-observed-mpidr": replace(ready, observed_mpidr=(0x200, 0x301)),
    }
    for name, candidate in mutations.items():
        result, after = mint(state, 8, CPU8_ATTEMPT, True, candidate)
        assert result == "-EPERM", (name, result)
        assert after == state, (name, after)
        print(f"mutation={name} result={result}")
    result, after = mint(state, 8, CPU8_ATTEMPT, False, ready)
    assert result == "-EPERM" and after == state
    print("mutation=a28-reject result=-EPERM")
    print("mutations_rejected=7/7")
    print("status=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
