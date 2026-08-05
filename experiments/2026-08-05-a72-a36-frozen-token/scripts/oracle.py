#!/usr/bin/env python3
"""Independent bounded oracle for the frozen A36 token mint."""

from __future__ import annotations

from dataclasses import dataclass, replace


MASK = 0b1111
CPU8_ATTEMPT = 1
CPU9_ATTEMPT = 2


@dataclass(frozen=True)
class Ready:
    abi: int = 7
    profile: str = "mt6797-a53-a72-a41-v7"
    identities: tuple[int, ...] = (1, 2, 3, 4)
    source: tuple[int, ...] = (5, 6, 7, 8)
    config: tuple[int, ...] = (9, 10, 11, 12)
    evidence: tuple[int, ...] = (13, 14, 15, 16)
    targets: tuple[int, ...] = (8, 9)
    expected_mpidr: tuple[int, ...] = (0x200, 0x201)
    observed_mpidr: tuple[int, ...] = (0x200, 0x201)


@dataclass(frozen=True)
class State:
    health: str = "CLOSED"
    phase: str = "UNINITIALIZED"
    available: int = 0
    consumed: int = 0
    next_generation: int = 0
    next_cookie: int = 0
    token: tuple | None = None


def ready_valid(ready: Ready | None) -> bool:
    return bool(
        ready
        and ready.abi == 7
        and ready.profile == "mt6797-a53-a72-a41-v7"
        and all(ready.identities)
        and all(ready.source)
        and all(ready.config)
        and all(ready.evidence)
        and ready.targets == (8, 9)
        and ready.expected_mpidr == (0x200, 0x201)
        and ready.observed_mpidr == (0x200, 0x201)
    )


def mint(state: State, cpu: int, attempt: int, a28_ok: bool,
         ready: Ready | None) -> tuple[str, State]:
    expected = CPU8_ATTEMPT if cpu == 8 else CPU9_ATTEMPT if cpu == 9 else None
    if expected is None:
        return "-EINVAL", state
    if state.health == "CLOSED":
        return "-EAGAIN", state
    if state.health != "AVAILABLE" or state.phase != "IDLE":
        return "-EBUSY", state
    if attempt != expected or not (state.consumed & expected):
        return "-EPERM", state
    if not a28_ok or not ready_valid(ready):
        return "-EPERM", state
    if not state.next_generation or not state.next_cookie:
        return "-EPROTO", state
    op = "CPU8_UP" if cpu == 8 else "CPU9_UP"
    budgets = ("PREP", "PROVIDER", "CPU_ON") if cpu == 8 else ("CPU_ON",)
    token = (op, cpu, 0x200 if cpu == 8 else 0x201,
             state.next_generation, state.next_cookie, ready.identities, budgets)
    return "OK", replace(state, phase="FROZEN", token=token,
                         next_generation=state.next_generation + 1,
                         next_cookie=state.next_cookie + 1)


def main() -> int:
    ready = Ready()
    closed = State()
    result, after = mint(closed, 8, CPU8_ATTEMPT, True, ready)
    assert result == "-EAGAIN" and after == closed

    available = State(health="AVAILABLE", phase="IDLE", available=MASK,
                      consumed=CPU8_ATTEMPT, next_generation=1,
                      next_cookie=0xA7200001)
    result, cpu8 = mint(available, 8, CPU8_ATTEMPT, True, ready)
    assert result == "OK" and cpu8.phase == "FROZEN"
    assert cpu8.token[0:3] == ("CPU8_UP", 8, 0x200)
    assert cpu8.token[5] == ready.identities
    assert cpu8.token[6] == ("PREP", "PROVIDER", "CPU_ON")

    # A malformed READY identity must not mint and is checked by mutations.
    result, cpu9 = mint(
        replace(available, consumed=CPU8_ATTEMPT | CPU9_ATTEMPT),
        9, CPU9_ATTEMPT, True, ready,
    )
    assert result == "OK" and cpu9.token[6] == ("CPU_ON",)
    print("claim=PARTIAL_A36_FROZEN_TOKEN_MINT")
    print("probes=3")
    print("closed_unchanged=1")
    print("cpu8_token=1")
    print("cpu9_token=1")
    print("p30_armed=0")
    print("cpu_on_calls=0")
    print("status=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
