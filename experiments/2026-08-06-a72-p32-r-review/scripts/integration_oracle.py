#!/usr/bin/env python3
"""Independent model of the P32A/P32X/P32R integration contract."""

from __future__ import annotations

from dataclasses import dataclass, field, replace


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
FORBIDDEN_HANDOFF_SIDE_EFFECTS = {
    "hps_success",
    "provider_release",
    "retry",
    "membership_commit",
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
    operation: str | None = None
    target_cpu: int | None = None
    target_mpidr: int | None = None
    generation: int | None = None
    cookie: int | None = None
    events: list[Event] = field(default_factory=list)
    nested_reset: bool = False
    outer_reset: bool = False
    reverse_complete: bool = False
    overflow: bool = False
    unknown: bool = False
    effects: list[str] = field(default_factory=list)

    def bind(self, tx: "Transaction") -> None:
        self.operation = tx.operation
        self.target_cpu = tx.target_cpu
        self.target_mpidr = tx.target_mpidr
        self.generation = tx.generation
        self.cookie = tx.cookie

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
    operation: str = "CPU8_UP"
    generation: int = 7
    cookie: int = 0xA5
    target_cpu: int = 8
    target_mpidr: int = 0x200
    error: int = -19
    parked: bool = False
    retired: bool = False
    fault_latched: bool = False
    handoff: str | None = None
    terminal_snapshot: "LedgerSnapshot | None" = None
    ledger: "LedgerSnapshot" = field(default_factory=lambda: LedgerSnapshot())
    side_effects: set[str] = field(default_factory=set)
    trace: Trace = field(default_factory=Trace)


@dataclass
class LedgerSnapshot:
    members: int = 0x0
    provider_identity: int = 0xD0
    provider_state: str = "HELD"
    phase: str = "VERIFYING"
    health: str = "AVAILABLE"
    a30_disposition: str = "NONE"


def publish_nested(tx: Transaction) -> None:
    tx.trace.bind(tx)
    tx.trace.append(Event("rollback", 12, 0, tx.error))
    tx.trace.nested_reset = True


def publish_outer(tx: Transaction) -> None:
    tx.trace.append(Event("startup", 42, 0, tx.error, warning=True))
    tx.trace.outer_reset = True


def publish_dynamic(tx: Transaction) -> None:
    """Model a dynamic multi-instance callback in execution order."""
    tx.trace.append(Event("startup", 50, 0, 0))
    tx.trace.append(Event("startup", 50, 1, 0))


def reverse(tx: Transaction) -> None:
    tx.trace.append(Event("rollback", 41, 0, 0))
    tx.trace.append(Event("rollback", 40, 0, 0))
    tx.trace.reverse_complete = True


def lose(tx: Transaction, result: str) -> str:
    tx.handoff = "FAULT_ROLLBACK_LOST"
    tx.fault_latched = True
    tx.ledger.phase = "FAULT"
    tx.ledger.health = "FAULTED"
    return result


def complete(
    tx: Transaction,
    generation: int,
    cookie: int,
    error: int,
    operation: str | None = None,
    target_cpu: int | None = None,
    target_mpidr: int | None = None,
) -> str:
    if tx.retired or tx.fault_latched:
        return "-EAGAIN"
    observed_identity = (
        tx.operation if operation is None else operation,
        tx.target_cpu if target_cpu is None else target_cpu,
        tx.target_mpidr if target_mpidr is None else target_mpidr,
        generation,
        cookie,
    )
    expected_identity = (
        tx.operation,
        tx.target_cpu,
        tx.target_mpidr,
        tx.generation,
        tx.cookie,
    )
    if observed_identity != expected_identity or error != tx.error:
        return lose(tx, "-EUCLEAN")
    trace_identity = (
        tx.trace.operation,
        tx.trace.target_cpu,
        tx.trace.target_mpidr,
        tx.trace.generation,
        tx.trace.cookie,
    )
    if trace_identity != expected_identity:
        return lose(tx, "-EUCLEAN")
    if not tx.trace.reverse_complete:
        return "-EINPROGRESS"
    if tx.trace.overflow or tx.trace.unknown:
        return lose(tx, "-EIO")
    if not tx.parked:
        return lose(tx, "-EIO")
    if not tx.trace.nested_reset or not tx.trace.outer_reset:
        return lose(tx, "-EIO")
    if FORBIDDEN_EFFECTS.intersection(tx.trace.effects):
        return lose(tx, "-EIO")
    if set(REQUIRED_EFFECTS) - set(tx.trace.effects):
        return lose(tx, "-EIO")
    if tx.side_effects.intersection(FORBIDDEN_HANDOFF_SIDE_EFFECTS):
        return lose(tx, "-EPERM")
    tx.terminal_snapshot = replace(tx.ledger)
    tx.handoff = "FAULT_ROLLBACK_RECORDED"
    tx.ledger.phase = "FAULT"
    tx.ledger.health = "FAULTED"
    if tx.ledger.provider_state == "HELD":
        tx.ledger.provider_state = "FAULT_UNKNOWN"
    tx.ledger.a30_disposition = "FAULT_ROLLBACK_RECORDED"
    tx.retired = True
    return "0"


def main() -> int:
    probes = 0

    tx = Transaction()
    publish_nested(tx)
    publish_outer(tx)
    publish_dynamic(tx)
    reverse(tx)
    tx.parked = True
    for effect in sorted(REQUIRED_EFFECTS):
        tx.trace.effect(effect)
    assert [event.instance for event in tx.trace.events[2:4]] == [0, 1]
    assert tx.trace.events[0].direction == "rollback"
    assert tx.trace.events[1].warning
    assert complete(tx, 7, 0xA5, -19) == "0"
    assert tx.handoff == "FAULT_ROLLBACK_RECORDED"
    assert tx.terminal_snapshot == LedgerSnapshot()
    assert tx.ledger.members == 0x0
    assert tx.ledger.provider_identity == 0xD0
    assert tx.ledger.provider_state == "FAULT_UNKNOWN"
    assert tx.ledger.phase == "FAULT"
    assert tx.ledger.health == "FAULTED"
    assert tx.ledger.a30_disposition == "FAULT_ROLLBACK_RECORDED"
    assert not tx.side_effects
    assert tx.retired
    probes += 1

    incomplete = Transaction()
    publish_nested(incomplete)
    publish_outer(incomplete)
    incomplete.parked = True
    for effect in sorted(REQUIRED_EFFECTS):
        incomplete.trace.effect(effect)
    assert complete(incomplete, 7, 0xA5, -19) == "-EINPROGRESS"
    probes += 1

    assert complete(tx, 7, 0xA5, -19) == "-EAGAIN"
    probes += 1

    for mutation in (
        "operation",
        "target_cpu",
        "target_mpidr",
        "generation",
        "cookie",
        "error",
    ):
        bad = Transaction()
        publish_nested(bad)
        publish_outer(bad)
        reverse(bad)
        bad.parked = True
        for effect in sorted(REQUIRED_EFFECTS):
            bad.trace.effect(effect)
        values = {
            "operation": bad.operation,
            "target_cpu": bad.target_cpu,
            "target_mpidr": bad.target_mpidr,
            "generation": bad.generation,
            "cookie": bad.cookie,
            "error": bad.error,
        }
        if mutation == "operation":
            values[mutation] = "CPU9_UP"
        else:
            values[mutation] += 1
        assert complete(bad, **values) == "-EUCLEAN"
        assert bad.handoff == "FAULT_ROLLBACK_LOST"
        probes += 1

    trace_identity = Transaction()
    publish_nested(trace_identity)
    publish_outer(trace_identity)
    reverse(trace_identity)
    trace_identity.parked = True
    for effect in sorted(REQUIRED_EFFECTS):
        trace_identity.trace.effect(effect)
    trace_identity.trace.target_mpidr ^= 1
    assert complete(trace_identity, 7, 0xA5, -19) == "-EUCLEAN"
    assert trace_identity.handoff == "FAULT_ROLLBACK_LOST"
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

    unknown_event = Transaction()
    publish_nested(unknown_event)
    publish_outer(unknown_event)
    reverse(unknown_event)
    unknown_event.parked = True
    for effect in sorted(REQUIRED_EFFECTS):
        unknown_event.trace.effect(effect)
    unknown_event.trace.effect("UNLISTED_EFFECT")
    assert complete(unknown_event, 7, 0xA5, -19) == "-EIO"
    assert unknown_event.handoff == "FAULT_ROLLBACK_LOST"
    probes += 1

    premature = Transaction()
    publish_nested(premature)
    publish_outer(premature)
    reverse(premature)
    premature.parked = True
    for effect in sorted(REQUIRED_EFFECTS):
        premature.trace.effect(effect)
    premature.side_effects.add("provider_release")
    assert complete(premature, 7, 0xA5, -19) == "-EPERM"
    assert premature.handoff == "FAULT_ROLLBACK_LOST"
    assert premature.terminal_snapshot is None
    assert not premature.retired
    assert premature.ledger.provider_state == "HELD"
    probes += 1

    no_provider = Transaction(ledger=LedgerSnapshot(provider_identity=0,
                                                      provider_state="NONE"))
    publish_nested(no_provider)
    publish_outer(no_provider)
    reverse(no_provider)
    no_provider.parked = True
    for effect in sorted(REQUIRED_EFFECTS):
        no_provider.trace.effect(effect)
    assert complete(no_provider, 7, 0xA5, -19) == "0"
    assert no_provider.terminal_snapshot.provider_state == "NONE"
    assert no_provider.ledger.provider_state == "NONE"
    probes += 1

    print("claim=P32R_INTEGRATION_CONTRACT_ORACLE")
    print(f"probes={probes}")
    print("nested_before_outer=1")
    print("dynamic_multi_instance_order=0,1")
    print("identity_and_error_mutations_rejected=6/6")
    print("trace_identity_mutation_rejected=1")
    print("pre_reverse_completion_rejected=1")
    print("overflow_rejected=1")
    print("forbidden_and_unknown_effects_rejected=2/2")
    print("ledger_handoff_one_shot=1")
    print("ledger_snapshot_and_provider_fault=1")
    print("premature_side_effect_rejected=1")
    print("provider_none_snapshot_preserved=1")
    print("status=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
