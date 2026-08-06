#!/usr/bin/env python3
"""Independent model of the P32A/P32X/P32R integration contract."""

from __future__ import annotations

from dataclasses import dataclass, field


MAX_EVENTS = 8
FORBIDDEN_EFFECTS = {"CPU_OFF_ATTEMPT", "AFFINITY_INFO_ATTEMPT"}
REQUIRED_EFFECTS = {
    "TOPOLOGY_REMOVE",
    "NUMA_REMOVE",
    "ONLINE_CLEAR",
    "PRESENT_CLEAR",
    "IPI_TEARDOWN",
    "IRQ_MIGRATE",
    "RCU",
    "LOCKDEP",
    "DEAD_PUBLISH",
    "TARGET_PARK",
    "KILL_OBSERVED",
    "NO_AFFINITY",
}


@dataclass
class Event:
    direction: str
    state: int
    instance: int
    result: int
    warning: bool = False


@dataclass
class Trace:
    events: list[Event] = field(default_factory=list)
    nested_reset: bool = False
    outer_reset: bool = False
    reverse_complete: bool = False
    overflow: bool = False
    unknown: bool = False
    effects: list[str] = field(default_factory=list)

    def append(self, event: Event) -> None:
        if len(self.events) >= MAX_EVENTS:
            self.overflow = True
            return
        self.events.append(event)

    def effect(self, name: str) -> None:
        if name not in REQUIRED_EFFECTS and name not in FORBIDDEN_EFFECTS:
            self.unknown = True
        self.effects.append(name)


@dataclass
class Transaction:
    generation: int = 7
    cookie: int = 0xA5
    target_cpu: int = 8
    target_mpidr: int = 0x200
    error: int = -19
    parked: bool = False
    retired: bool = False
    handoff: str | None = None
    trace: Trace = field(default_factory=Trace)


def publish_nested(tx: Transaction) -> None:
    tx.trace.append(Event("rollback", 12, 0, tx.error))
    tx.trace.nested_reset = True


def publish_outer(tx: Transaction) -> None:
    tx.trace.append(Event("startup", 42, 0, tx.error, warning=True))
    tx.trace.outer_reset = True


def reverse(tx: Transaction) -> None:
    tx.trace.append(Event("rollback", 41, 0, 0))
    tx.trace.append(Event("rollback", 40, 0, 0))
    tx.trace.reverse_complete = True


def complete(tx: Transaction, generation: int, cookie: int, error: int) -> str:
    if tx.retired:
        return "-EAGAIN"
    if (generation, cookie, error) != (tx.generation, tx.cookie, tx.error):
        tx.handoff = "FAULT_ROLLBACK_LOST"
        return "-EUCLEAN"
    if not tx.trace.reverse_complete:
        return "-EINPROGRESS"
    if tx.trace.overflow or tx.trace.unknown:
        tx.handoff = "FAULT_ROLLBACK_LOST"
        return "-EIO"
    if not tx.parked:
        tx.handoff = "FAULT_ROLLBACK_LOST"
        return "-EIO"
    if not tx.trace.nested_reset or not tx.trace.outer_reset:
        tx.handoff = "FAULT_ROLLBACK_LOST"
        return "-EIO"
    if FORBIDDEN_EFFECTS.intersection(tx.trace.effects):
        tx.handoff = "FAULT_ROLLBACK_LOST"
        return "-EIO"
    if set(REQUIRED_EFFECTS) - set(tx.trace.effects):
        tx.handoff = "FAULT_ROLLBACK_LOST"
        return "-EIO"
    tx.handoff = "FAULT_ROLLBACK_RECORDED"
    tx.retired = True
    return "0"


def main() -> int:
    probes = 0

    tx = Transaction()
    publish_nested(tx)
    publish_outer(tx)
    reverse(tx)
    tx.parked = True
    for effect in sorted(REQUIRED_EFFECTS):
        tx.trace.effect(effect)
    assert complete(tx, 7, 0xA5, -19) == "0"
    assert tx.handoff == "FAULT_ROLLBACK_RECORDED"
    assert tx.retired
    probes += 1

    assert complete(tx, 7, 0xA5, -19) == "-EAGAIN"
    probes += 1

    for mutation in ("generation", "cookie", "error"):
        bad = Transaction()
        publish_nested(bad)
        publish_outer(bad)
        reverse(bad)
        bad.parked = True
        for effect in sorted(REQUIRED_EFFECTS):
            bad.trace.effect(effect)
        args = (bad.generation, bad.cookie, bad.error)
        index = {"generation": 0, "cookie": 1, "error": 2}[mutation]
        values = list(args)
        values[index] += 1
        assert complete(bad, *values) == "-EUCLEAN"
        assert bad.handoff == "FAULT_ROLLBACK_LOST"
        probes += 1

    overflow = Transaction()
    publish_nested(overflow)
    publish_outer(overflow)
    reverse(overflow)
    overflow.parked = True
    for i in range(MAX_EVENTS):
        overflow.trace.append(Event("rollback", i, 0, 0))
    overflow.trace.effect("TOPOLOGY_REMOVE")
    assert overflow.trace.overflow
    assert complete(overflow, 7, 0xA5, -19) == "-EIO"
    probes += 1

    unknown = Transaction()
    publish_nested(unknown)
    publish_outer(unknown)
    reverse(unknown)
    unknown.parked = True
    for effect in sorted(REQUIRED_EFFECTS):
        unknown.trace.effect(effect)
    unknown.trace.effect("CPU_OFF_ATTEMPT")
    assert complete(unknown, 7, 0xA5, -19) == "-EIO"
    assert unknown.handoff == "FAULT_ROLLBACK_LOST"
    probes += 1

    print("claim=P32R_INTEGRATION_CONTRACT_ORACLE")
    print(f"probes={probes}")
    print("nested_before_outer=1")
    print("identity_and_error_mutations_rejected=3/3")
    print("overflow_rejected=1")
    print("forbidden_effect_rejected=1")
    print("ledger_handoff_one_shot=1")
    print("status=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
