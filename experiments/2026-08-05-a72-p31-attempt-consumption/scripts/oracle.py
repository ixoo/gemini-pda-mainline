#!/usr/bin/env python3
"""Independent bounded oracle for the dormant P31 attempt ledger."""

from __future__ import annotations

from dataclasses import dataclass, replace


CPU8 = 8
CPU9 = 9
CPU8_ATTEMPT = 1
CPU9_ATTEMPT = 2
MASK = 0b1111


@dataclass(frozen=True)
class State:
    health: str = "CLOSED"
    phase: str = "UNINITIALIZED"
    available: int = 0
    consumed: int = 0
    token: bool = False
    p30_changed: bool = False


@dataclass(frozen=True)
class Entry:
    window_open: bool = True
    a28_valid: bool = True


def operation_attempt(cpu: int) -> int | None:
    return {CPU8: CPU8_ATTEMPT, CPU9: CPU9_ATTEMPT}.get(cpu)


def begin(state: State, cpu: int, attempt: int, entry: Entry | None) -> tuple[str, State]:
    expected = operation_attempt(cpu)
    if expected is None or entry is None or not entry.window_open:
        return "-EINVAL" if expected is None or entry is None else "-EPERM", state
    if attempt != expected:
        return "-EPERM", state
    if state.health == "CLOSED":
        return "-EAGAIN", state
    if state.health != "AVAILABLE":
        return "-ESHUTDOWN", state
    if state.phase != "IDLE":
        return "-EBUSY", state
    if not (state.available & expected) or state.consumed & expected:
        return "-EALREADY", state
    consumed = state.consumed | expected
    available = state.available & ~expected
    after = replace(state, available=available, consumed=consumed)
    if not entry.a28_valid:
        return "-EPERM", after
    return "-EOPNOTSUPP", after


def main() -> int:
    closed = State()
    status, after = begin(closed, CPU8, CPU8_ATTEMPT, Entry())
    assert status == "-EAGAIN" and after == closed

    available = State(health="AVAILABLE", phase="IDLE", available=MASK)
    status, after = begin(available, CPU8, CPU8_ATTEMPT, Entry())
    assert status == "-EOPNOTSUPP"
    assert after.available == MASK & ~CPU8_ATTEMPT
    assert after.consumed == CPU8_ATTEMPT
    assert not after.token and not after.p30_changed

    status, repeated = begin(after, CPU8, CPU8_ATTEMPT, Entry())
    assert status == "-EALREADY" and repeated == after
    status, rejected = begin(
        after, CPU9, CPU9_ATTEMPT, Entry(a28_valid=False)
    )
    assert status == "-EPERM"
    assert rejected.consumed == CPU8_ATTEMPT | CPU9_ATTEMPT
    assert rejected.available == MASK & ~(CPU8_ATTEMPT | CPU9_ATTEMPT)
    status, closed_window = begin(
        rejected, CPU9, CPU9_ATTEMPT, Entry(window_open=False)
    )
    assert status == "-EPERM" and closed_window == rejected

    print("claim=PARTIAL_P31_ATTEMPT_LEDGER")
    print("probes=5")
    print("closed_unchanged=1")
    print("one_shot_consumption=2")
    print("a28_rejection_preserves_consumption=1")
    print("token_allocations=0")
    print("p30_mutations=0")
    print("status=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
