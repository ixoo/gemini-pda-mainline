#!/usr/bin/env python3
"""Independent bounded oracle for the lifecycle-closed P24 owner.

Claim: PARTIAL_P24_CLOSED_OWNER_MODEL.

The oracle uses only frozen Python values.  It deliberately performs no Linux
source inspection and supplies no production caller/opener, generic hook,
build/runtime/device result, or P30E proof.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, replace
from enum import Enum

sys.dont_write_bytecode = True

CLAIM = "PARTIAL_P24_CLOSED_OWNER_MODEL"


class Rejected(ValueError):
    """A control action has no authority in the closed-owner model."""


class OwnerHealth(Enum):
    CLOSED = "CLOSED"
    AVAILABLE = "AVAILABLE"


class MembershipPhase(Enum):
    UNINITIALIZED = "UNINITIALIZED"
    IDLE = "IDLE"
    FROZEN = "FROZEN"


class ProviderState(Enum):
    NONE = "NONE"
    HELD = "HELD"


class Decision(Enum):
    DENIED_CLOSED = "DENIED_CLOSED"
    INVALID_IDENTITY = "INVALID_IDENTITY"
    AUTHORIZED = "AUTHORIZED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESET_ACCEPTED = "RESET_ACCEPTED"


@dataclass(frozen=True, order=True)
class RequestIdentity:
    operation: str
    cpu: int
    mpidr: int
    cpuhp_target: str
    generation: int
    cookie: int

    @property
    def short(self) -> str:
        return f"CPU{self.cpu}/gen{self.generation}"


CPU8_GEN42 = RequestIdentity(
    "CPU8_UP", 8, 0x200, "CPUHP_ONLINE", 42, 0x8A720042
)
CPU9_GEN7 = RequestIdentity(
    "CPU9_UP", 9, 0x201, "CPUHP_ONLINE", 7, 0x9A720007
)
EXACT_REQUESTS = (CPU8_GEN42, CPU9_GEN7)


NAMED_PREREQUISITES = (
    "A34_BOOTSTRAP",
    "A41_READY",
    "A25_CALLBACKS",
    "PROVIDER_OWNER",
    "A36_PRESTATE",
    "P30_INTEGRATION",
    "P30E_MMU_OFF",
    "P14_P15",
    "P32_ROLLBACK",
    "A33_COMMIT",
    "FAILSTOP_RESET",
    "A26_VETO",
    "OWNER_IMPLEMENTATION",
)
ALL_NAMED_PREREQUISITES = frozenset(NAMED_PREREQUISITES)
WITHOUT_A26 = ALL_NAMED_PREREQUISITES - {"A26_VETO"}


def _malformed_requests() -> tuple[RequestIdentity, ...]:
    malformed: list[RequestIdentity] = []
    for request, other in ((CPU8_GEN42, CPU9_GEN7), (CPU9_GEN7, CPU8_GEN42)):
        malformed.extend(
            (
                replace(request, operation=other.operation),
                replace(request, cpu=other.cpu),
                replace(request, mpidr=other.mpidr),
                replace(request, cpuhp_target="CPUHP_OFFLINE"),
                replace(request, generation=request.generation + 1),
                replace(request, cookie=request.cookie ^ 1),
            )
        )
    result = tuple(malformed)
    assert len(set(result)) == len(result)
    assert not set(result).intersection(EXACT_REQUESTS)
    return result


MALFORMED_REQUESTS = _malformed_requests()


@dataclass(frozen=True)
class OwnerState:
    health: OwnerHealth = OwnerHealth.CLOSED
    membership_phase: MembershipPhase = MembershipPhase.UNINITIALIZED
    all_applicable_review_complete: bool = False
    a26_veto_lifted: bool = False
    implementation_enabled: bool = False
    p31_entered: bool = False
    a38_consumed: bool = False
    attempts_consumed: int = 0
    live_token: RequestIdentity | None = None
    p17_published: bool = False
    p18_published: bool = False
    p30_handoff: bool = False
    provider_state: ProviderState = ProviderState.NONE
    members: int = 0
    members_valid: bool = False
    hardware_effect: bool = False
    cpu_on_issued: bool = False
    p14_published: bool = False
    p15_published: bool = False
    a33_committed: bool = False
    p32_entered: bool = False
    denial_epoch: int = 0
    denial_acknowledged: bool = False
    reset_epoch: int = 0


@dataclass(frozen=True)
class Rules:
    trust_caller_readiness: bool = False
    bounded_list_sufficient: bool = False
    ignore_a26_veto: bool = False
    infer_all_applicable_review: bool = False
    infer_implementation_enabled: bool = False
    accept_malformed_identity: bool = False
    enter_p31: bool = False
    consume_a38: bool = False
    consume_attempt: bool = False
    allocate_live_token: bool = False
    enter_frozen: bool = False
    publish_p17: bool = False
    publish_p18: bool = False
    handoff_p30: bool = False
    mutate_provider: bool = False
    commit_member: bool = False
    mutate_hardware: bool = False
    issue_cpu_on: bool = False
    publish_p14: bool = False
    publish_p15: bool = False
    commit_a33: bool = False
    enter_p32: bool = False
    mutable_denial: bool = False
    allow_ack: bool = False
    allow_reset: bool = False


CORRECT_RULES = Rules()


@dataclass(frozen=True)
class Transition:
    command: str
    before: OwnerState
    after: OwnerState
    decision: Decision
    request: RequestIdentity | None = None
    claimed_prerequisites: frozenset[str] = frozenset()
    caller_ready: bool = False


@dataclass(frozen=True)
class AuditReport:
    prerequisite_subsets: int
    exact_probes: int
    exact_denials: int
    malformed_probes: int
    malformed_rejections: int
    owner_states: int
    authorized_outcomes: int
    violations: frozenset[str]


def initial_state() -> OwnerState:
    return OwnerState()


def prerequisite_subsets() -> tuple[frozenset[str], ...]:
    """Return every subset of the frozen 13-name diagnostic universe."""

    return tuple(
        frozenset(
            name
            for bit, name in enumerate(NAMED_PREREQUISITES)
            if mask & (1 << bit)
        )
        for mask in range(1 << len(NAMED_PREREQUISITES))
    )


def _mutated_denial_state(
    state: OwnerState,
    request: RequestIdentity,
    claimed: frozenset[str],
    rules: Rules,
) -> OwnerState:
    """Apply exactly the unsafe effects selected by a mutation rule."""

    after = state
    if rules.infer_all_applicable_review and claimed == ALL_NAMED_PREREQUISITES:
        after = replace(after, all_applicable_review_complete=True)
    if rules.infer_implementation_enabled and "OWNER_IMPLEMENTATION" in claimed:
        after = replace(after, implementation_enabled=True)
    if rules.enter_p31:
        after = replace(after, p31_entered=True)
    if rules.consume_a38:
        after = replace(after, a38_consumed=True)
    if rules.consume_attempt:
        after = replace(after, attempts_consumed=after.attempts_consumed + 1)
    if rules.allocate_live_token:
        after = replace(after, live_token=request)
    if rules.enter_frozen:
        after = replace(after, membership_phase=MembershipPhase.FROZEN)
    if rules.publish_p17 and request == CPU8_GEN42:
        after = replace(after, p17_published=True)
    if rules.publish_p18 and request == CPU9_GEN7:
        after = replace(after, p18_published=True)
    if rules.handoff_p30:
        after = replace(after, p30_handoff=True)
    if rules.mutate_provider:
        after = replace(after, provider_state=ProviderState.HELD)
    if rules.commit_member:
        members = 0x1 if request == CPU8_GEN42 else 0x3
        after = replace(after, members=members, members_valid=True)
    if rules.mutate_hardware:
        after = replace(after, hardware_effect=True)
    if rules.issue_cpu_on:
        after = replace(after, cpu_on_issued=True)
    if rules.publish_p14 and request == CPU8_GEN42:
        after = replace(after, p14_published=True)
    if rules.publish_p15 and request == CPU9_GEN7:
        after = replace(after, p15_published=True)
    if rules.commit_a33:
        after = replace(after, a33_committed=True)
    if rules.enter_p32:
        after = replace(after, p32_entered=True)
    if rules.mutable_denial:
        after = replace(after, denial_epoch=after.denial_epoch + 1)
    return after


def admit(
    state: OwnerState,
    request: RequestIdentity,
    claimed_prerequisites: frozenset[str],
    caller_ready: bool,
    rules: Rules = CORRECT_RULES,
) -> Transition:
    """Evaluate one request without reading any external authority."""

    if not claimed_prerequisites.issubset(ALL_NAMED_PREREQUISITES):
        raise ValueError("unknown diagnostic prerequisite")

    exact = request in EXACT_REQUESTS
    if not exact and not rules.accept_malformed_identity:
        return Transition(
            "ADMIT",
            state,
            state,
            Decision.INVALID_IDENTITY,
            request,
            claimed_prerequisites,
            caller_ready,
        )

    decision = Decision.DENIED_CLOSED
    if exact:
        if rules.trust_caller_readiness and caller_ready:
            decision = Decision.AUTHORIZED
        elif (
            rules.bounded_list_sufficient
            and claimed_prerequisites == ALL_NAMED_PREREQUISITES
        ):
            decision = Decision.AUTHORIZED
        elif rules.ignore_a26_veto and WITHOUT_A26.issubset(claimed_prerequisites):
            decision = Decision.AUTHORIZED

    after = state
    if exact:
        after = _mutated_denial_state(
            state, request, claimed_prerequisites, rules
        )
    return Transition(
        "ADMIT",
        state,
        after,
        decision,
        request,
        claimed_prerequisites,
        caller_ready,
    )


def acknowledge_denial(
    state: OwnerState, rules: Rules = CORRECT_RULES
) -> Transition:
    if not rules.allow_ack:
        raise Rejected("closed denial is not acknowledgeable authority")
    after = replace(state, denial_acknowledged=True)
    return Transition("ACK", state, after, Decision.ACKNOWLEDGED)


def reset_owner(state: OwnerState, rules: Rules = CORRECT_RULES) -> Transition:
    if not rules.allow_reset:
        raise Rejected("no reset/bootstrap owner exists in this model")
    after = replace(
        state,
        health=OwnerHealth.AVAILABLE,
        membership_phase=MembershipPhase.IDLE,
        reset_epoch=state.reset_epoch + 1,
    )
    return Transition("RESET", state, after, Decision.RESET_ACCEPTED)


def state_violations(state: OwnerState) -> set[str]:
    violations: set[str] = set()
    if state.health is not OwnerHealth.CLOSED:
        violations.add("CLOSED_LIFECYCLE_ONLY")
    if state.membership_phase is not MembershipPhase.UNINITIALIZED:
        violations.add("MEMBERSHIP_PHASE_UNINITIALIZED")
    if state.all_applicable_review_complete:
        violations.add("ALL_APPLICABLE_REVIEW_REMAINS_FALSE")
    if state.a26_veto_lifted:
        violations.add("A26_VETO_LIFTED_REMAINS_FALSE")
    if state.implementation_enabled:
        violations.add("IMPLEMENTATION_ENABLED_REMAINS_FALSE")
    if state.p31_entered:
        violations.add("P31_NOT_ENTERED")
    if state.a38_consumed:
        violations.add("A38_NOT_CONSUMED")
    if state.attempts_consumed:
        violations.add("ATTEMPT_NOT_CONSUMED")
    if state.live_token is not None:
        violations.add("NO_LIVE_TOKEN")
    if state.p17_published:
        violations.add("P17_NOT_PUBLISHED")
    if state.p18_published:
        violations.add("P18_NOT_PUBLISHED")
    if state.p30_handoff:
        violations.add("P30_NOT_REACHED")
    if state.provider_state is not ProviderState.NONE:
        violations.add("PROVIDER_UNTOUCHED")
    if state.members != 0 or state.members_valid:
        violations.add("MEMBERSHIP_UNTOUCHED")
    if state.hardware_effect:
        violations.add("HARDWARE_UNTOUCHED")
    if state.cpu_on_issued:
        violations.add("CPU_ON_NOT_ISSUED")
    if state.p14_published:
        violations.add("P14_NOT_PUBLISHED")
    if state.p15_published:
        violations.add("P15_NOT_PUBLISHED")
    if state.a33_committed:
        violations.add("A33_NOT_COMMITTED")
    if state.p32_entered:
        violations.add("P32_NOT_ENTERED")
    if state.denial_epoch or state.denial_acknowledged or state.reset_epoch:
        violations.add("DENIAL_IMMUTABLE")
    return violations


def transition_violations(transition: Transition) -> set[str]:
    violations = state_violations(transition.after)

    if transition.command == "ADMIT":
        assert transition.request is not None
        exact = transition.request in EXACT_REQUESTS
        if exact:
            if transition.decision is not Decision.DENIED_CLOSED:
                violations.add("CLOSED_REQUEST_ALWAYS_DENIED")
        elif transition.decision is not Decision.INVALID_IDENTITY:
            violations.add("EXACT_REQUEST_IDENTITY")

        if transition.after != transition.before:
            violations.add("DENIAL_IMMUTABLE")
        if transition.decision is Decision.AUTHORIZED:
            violations.add("NO_AUTHORIZED_STATE")
            if not transition.before.a26_veto_lifted:
                violations.add("A26_VETO_REQUIRED")
            if not transition.before.all_applicable_review_complete:
                violations.add("ALL_APPLICABLE_REVIEW_REQUIRED")
            if not transition.before.implementation_enabled:
                violations.add("IMPLEMENTATION_ENABLE_REQUIRED")
    elif transition.command == "ACK":
        violations.add("ACK_NOT_AUTHORITY")
        if transition.after != transition.before:
            violations.add("DENIAL_IMMUTABLE")
    elif transition.command == "RESET":
        violations.add("RESET_NOT_AUTHORITY")
        if transition.after != transition.before:
            violations.add("DENIAL_IMMUTABLE")
    else:
        violations.add("UNKNOWN_COMMAND")
    return violations


def audit_contract(rules: Rules = CORRECT_RULES) -> AuditReport:
    start = initial_state()
    subsets = prerequisite_subsets()
    violations = state_violations(start)
    owner_states = {start}
    exact_probes = 0
    exact_denials = 0
    malformed_probes = 0
    malformed_rejections = 0
    authorized_outcomes = 0

    for claimed in subsets:
        for request in EXACT_REQUESTS:
            readiness_results: list[Transition] = []
            for caller_ready in (False, True):
                transition = admit(start, request, claimed, caller_ready, rules)
                readiness_results.append(transition)
                exact_probes += 1
                exact_denials += transition.decision is Decision.DENIED_CLOSED
                authorized_outcomes += transition.decision is Decision.AUTHORIZED
                owner_states.add(transition.after)
                violations.update(transition_violations(transition))

                if (
                    claimed == ALL_NAMED_PREREQUISITES
                    and transition.decision is not Decision.DENIED_CLOSED
                ):
                    violations.add("BOUNDED_LIST_NOT_AUTHORITY")
                if (
                    claimed == WITHOUT_A26
                    and transition.decision is not Decision.DENIED_CLOSED
                ):
                    violations.add("A26_VETO_REQUIRED")

            if (
                readiness_results[0].decision != readiness_results[1].decision
                or readiness_results[0].after != readiness_results[1].after
            ):
                violations.add("CALLER_READINESS_NOT_AUTHORITY")

    for request in MALFORMED_REQUESTS:
        transition = admit(
            start,
            request,
            ALL_NAMED_PREREQUISITES,
            caller_ready=True,
            rules=rules,
        )
        malformed_probes += 1
        malformed_rejections += transition.decision is Decision.INVALID_IDENTITY
        authorized_outcomes += transition.decision is Decision.AUTHORIZED
        owner_states.add(transition.after)
        violations.update(transition_violations(transition))

    first = admit(start, CPU8_GEN42, frozenset(), False, rules)
    second = admit(
        first.after,
        CPU9_GEN7,
        ALL_NAMED_PREREQUISITES,
        True,
        rules,
    )
    if (
        first.decision is not Decision.DENIED_CLOSED
        or second.decision is not Decision.DENIED_CLOSED
        or first.after != start
        or second.after != start
    ):
        violations.add("SEQUENTIAL_DENIAL_IMMUTABLE")

    for control in (acknowledge_denial, reset_owner):
        try:
            transition = control(start, rules)
        except Rejected:
            continue
        owner_states.add(transition.after)
        violations.update(transition_violations(transition))

    return AuditReport(
        prerequisite_subsets=len(subsets),
        exact_probes=exact_probes,
        exact_denials=exact_denials,
        malformed_probes=malformed_probes,
        malformed_rejections=malformed_rejections,
        owner_states=len(owner_states),
        authorized_outcomes=authorized_outcomes,
        violations=frozenset(violations),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    report = audit_contract()
    print(CLAIM)
    print(f"named_prerequisites={len(NAMED_PREREQUISITES)}")
    print(f"named_prerequisite_subsets={report.prerequisite_subsets}")
    print(f"exact_requests={len(EXACT_REQUESTS)}")
    print("caller_readiness_values=2")
    print(f"exact_admission_probes={report.exact_probes}")
    print(f"exact_denials={report.exact_denials}")
    print(f"malformed_probes={report.malformed_probes}")
    print(f"malformed_rejections={report.malformed_rejections}")
    print(f"reachable_owner_states={report.owner_states}")
    print(f"authorized_outcomes={report.authorized_outcomes}")
    print("sequential_denial_witness=CPU8/gen42 -> CPU9/gen7")
    print(f"violations={len(report.violations)}")
    if report.violations:
        for violation in sorted(report.violations):
            print(f"FAIL {violation}")
        return 1
    print("PASS immutable CLOSED/UNINITIALIZED denial contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
