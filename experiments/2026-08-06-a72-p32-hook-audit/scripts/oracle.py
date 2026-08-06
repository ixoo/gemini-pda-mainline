#!/usr/bin/env python3
"""Independent model of the exact-generation P32 rollback side channel."""

from __future__ import annotations

from dataclasses import dataclass, field


CPU8 = 8
CPU9 = 9
P32_ABI = 1
STATE_NONE = "NONE"
STATE_PUBLISHED = "PUBLISHED"
STATE_GUARDED = "GUARDED"
STATE_PARKED = "PARKED"
STATE_CONSUMED = "CONSUMED"
BRANCH_NONE = "NONE"
BRANCH_A = "A"
BRANCH_D = "D"
BRANCH_F = "F"
BRANCH_X = "X"
BRANCH_R = "R"
GUARD_DISABLE = 1
GUARD_DIE = 2
GUARD_KILL = 4
GUARD_PARK = 8


@dataclass
class Record:
    abi: int = 0
    state: str = STATE_NONE
    branch: str = BRANCH_NONE
    guard_flags: int = 0
    cpu_up_error: int = 0
    callback_state: int = 0
    target_cpu: int = 0
    target_mpidr: int = 0
    generation: int = 0
    cookie: int = 0


@dataclass
class Transaction:
    health: str = "AVAILABLE"
    phase: str = "VERIFYING"
    valid: bool = True
    p32_valid: bool = False
    operation: str = "CPU8_UP"
    target_cpu: int = CPU8
    identity_mpidr: int = 0x800
    identity_generation: int = 7
    identity_cookie: int = 0xA5
    p30_mpidr: int = 0x800
    record: Record = field(default_factory=Record)
    effects: list[str] = field(default_factory=list)


def fresh(cpu: int = CPU8) -> Transaction:
    return Transaction(
        operation=f"CPU{cpu}_UP",
        target_cpu=cpu,
        identity_mpidr=0x800 + cpu,
        p30_mpidr=0x800 + cpu,
    )


def target_locked(tx: Transaction, cpu: int) -> bool:
    record = tx.record
    return (
        tx.health == "AVAILABLE"
        and tx.valid
        and tx.p32_valid
        and record.state != STATE_CONSUMED
        and record.abi == P32_ABI
        and record.target_cpu == cpu
        and tx.operation in ("CPU8_UP", "CPU9_UP")
        and tx.operation == f"CPU{cpu}_UP"
        and tx.target_cpu == cpu
        and tx.p30_mpidr == record.target_mpidr
        and tx.identity_mpidr == record.target_mpidr
        and tx.identity_generation == record.generation
        and tx.identity_cookie == record.cookie
    )


def publish(tx: Transaction, cpu: int, callback_state: int, error: int) -> str:
    if cpu not in (CPU8, CPU9) or error == 0:
        return "-EINVAL"
    if (
        tx.health != "AVAILABLE"
        or tx.phase != "VERIFYING"
        or not tx.valid
        or tx.p32_valid
        or tx.target_cpu != cpu
        or tx.operation != f"CPU{cpu}_UP"
        or not tx.identity_generation
        or not tx.identity_cookie
    ):
        return "-EAGAIN"
    tx.record = Record(
        abi=P32_ABI,
        state=STATE_PUBLISHED,
        branch=BRANCH_A,
        cpu_up_error=error,
        callback_state=callback_state,
        target_cpu=cpu,
        target_mpidr=tx.identity_mpidr,
        generation=tx.identity_generation,
        cookie=tx.identity_cookie,
    )
    tx.p32_valid = True
    tx.phase = "FAULT"
    return "0"


def cpu_disable(tx: Transaction, cpu: int) -> str:
    if not target_locked(tx, cpu):
        return "0"
    if tx.record.guard_flags & GUARD_DISABLE:
        return "-EALREADY"
    tx.record.guard_flags |= GUARD_DISABLE
    tx.record.branch = BRANCH_D
    tx.record.state = STATE_GUARDED
    tx.effects.append("disable-guard-before-arch-teardown")
    return "-EIO"


def cpu_die(tx: Transaction, cpu: int) -> bool:
    if not target_locked(tx, cpu):
        return False
    tx.record.guard_flags |= GUARD_DIE | GUARD_PARK
    tx.record.branch = BRANCH_F
    tx.record.state = STATE_PARKED
    tx.effects.append("park-without-CPU_OFF")
    return True


def cpu_kill(tx: Transaction, cpu: int, spins: int = 100) -> str:
    for _ in range(spins):
        matched = target_locked(tx, cpu)
        parked = matched and tx.record.state == STATE_PARKED
        if parked:
            tx.record.guard_flags |= GUARD_KILL
            tx.effects.append("kill-no-affinity")
            return "-EIO"
        if not matched:
            return "0"
    return "-ETIMEDOUT"


def consume(tx: Transaction, cpu: int, rollback_error: int) -> str:
    if not target_locked(tx, cpu):
        return "-EAGAIN"
    if tx.record.state != STATE_PARKED:
        tx.record.branch = BRANCH_X
        return "-EIO"
    if tx.record.cpu_up_error != rollback_error:
        tx.record.branch = BRANCH_X
        return "-EUCLEAN"
    tx.record.branch = BRANCH_R
    tx.record.state = STATE_CONSUMED
    return "0"


def rollback_trace(tx: Transaction, cpu: int, error: int) -> list[str]:
    """Model the controller order; nested AP rollback precedes publication."""
    trace = ["nested-ap-reset"]
    assert publish(tx, cpu, callback_state=42, error=error) == "0"
    trace += ["p32-published", "outer-reset", "outer-reverse", "p32-consume"]
    return trace
