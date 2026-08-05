#!/usr/bin/env python3
"""Independent bounded oracle for closed P24 CPU-up admission hooks.

Claim: PARTIAL_P24_CLOSED_ADMISSION_HOOKS.

This module uses only immutable Python values.  It deliberately performs no
Linux source inspection and proves no C implementation, build, runtime,
device, P17/P18/P24 transaction, or P30E property.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, replace
from enum import Enum

sys.dont_write_bytecode = True

CLAIM = "PARTIAL_P24_CLOSED_ADMISSION_HOOKS"


class Platform(Enum):
    OTHER_ARCH = "OTHER_ARCH"
    ARM64_OTHER_METHOD = "ARM64_OTHER_METHOD"
    MT6797 = "MT6797"


class Stage(Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"


class Caller(Enum):
    PUBLIC = "PUBLIC"
    INTERNAL_GENERIC = "INTERNAL_GENERIC"
    THAW = "THAW"
    SMT = "SMT"


class Target(Enum):
    ONLINE = "CPUHP_ONLINE"
    INTERMEDIATE = "CPUHP_AP_ONLINE"


class Decision(Enum):
    PASS_THROUGH = "PASS_THROUGH"
    EAGAIN = "-EAGAIN"
    EPERM = "-EPERM"
    EINVAL = "-EINVAL"
    EOPNOTSUPP = "-EOPNOTSUPP"


class Point(Enum):
    PUBLIC_HOOK = "PUBLIC_HOOK"
    CPU_POSSIBLE = "CPU_POSSIBLE"
    NODE_ONLINE_WORK = "NODE_ONLINE_WORK"
    CPU_MAPS_LOCK = "CPU_MAPS_LOCK"
    INTERNAL_HOOK = "INTERNAL_HOOK"
    PER_CPU_STATE = "PER_CPU_STATE"
    CPUS_WRITE_LOCK = "CPUS_WRITE_LOCK"
    CPUHP_STATE = "CPUHP_STATE"
    CPUHP_CALLBACK = "CPUHP_CALLBACK"
    CPU_BOOT_METHOD = "CPU_BOOT_METHOD"


PUBLIC_DOWNSTREAM = (
    Point.CPU_POSSIBLE,
    Point.NODE_ONLINE_WORK,
    Point.CPU_MAPS_LOCK,
)
INTERNAL_DOWNSTREAM = (
    Point.PER_CPU_STATE,
    Point.CPUS_WRITE_LOCK,
    Point.CPUHP_STATE,
    Point.CPUHP_CALLBACK,
    Point.CPU_BOOT_METHOD,
)


@dataclass(frozen=True)
class HookState:
    owner_closed: bool = True
    membership_uninitialized: bool = True
    opener_present: bool = False
    begin_up_called: bool = False
    transaction_allocated: bool = False
    output_persisted: bool = False
    transition_mutex_taken_early: bool = False
    p31_entered: bool = False
    a38_consumed: bool = False
    attempts_consumed: int = 0
    token_live: bool = False
    p17_published: bool = False
    p18_published: bool = False
    p30_changed: bool = False
    provider_changed: bool = False
    members_changed: bool = False
    hardware_changed: bool = False
    cpu_on_issued: bool = False
    cpu_boot_called: bool = False
    cpu_boot_backstop: bool = True
    cpu_disable_backstop: bool = True


@dataclass(frozen=True)
class Rules:
    omit_public_hook: bool = False
    omit_internal_hook: bool = False
    public_after_cpu_possible: bool = False
    public_after_node_work: bool = False
    public_after_maps: bool = False
    internal_after_per_cpu: bool = False
    internal_after_cpus_write: bool = False
    internal_after_cpuhp: bool = False
    internal_after_callback: bool = False
    internal_after_boot: bool = False
    bypass_thaw: bool = False
    bypass_smt: bool = False
    deny_other_arch: bool = False
    deny_other_method: bool = False
    deny_a53: bool = False
    deny_out_of_range: bool = False
    admit_a72: bool = False
    accept_intermediate: bool = False
    accept_frozen: bool = False
    call_begin_up: bool = False
    take_transition_mutex_early: bool = False
    allocate_transaction: bool = False
    persist_output: bool = False
    add_opener: bool = False
    enter_p31: bool = False
    consume_a38: bool = False
    consume_attempt: bool = False
    allocate_token: bool = False
    enter_membership_phase: bool = False
    publish_p17: bool = False
    publish_p18: bool = False
    mutate_p30: bool = False
    mutate_provider: bool = False
    mutate_members: bool = False
    mutate_hardware: bool = False
    issue_cpu_on: bool = False
    call_cpu_boot: bool = False
    remove_cpu_boot_backstop: bool = False
    remove_cpu_disable_backstop: bool = False


CORRECT_RULES = Rules()


@dataclass(frozen=True)
class Scenario:
    name: str
    platform: Platform
    cpu: int
    in_range: bool
    stage: Stage
    caller: Caller
    target: Target
    tasks_frozen: bool
    expected: Decision

    @property
    def is_a72(self) -> bool:
        return self.platform is Platform.MT6797 and self.cpu in {8, 9}


@dataclass(frozen=True)
class Transition:
    scenario: Scenario
    before: HookState
    after: HookState
    decision: Decision
    hook_invoked: bool
    method_callback_invoked: bool
    owner_validator_invoked: bool


@dataclass(frozen=True)
class AuditReport:
    admission_probes: int
    pass_through: int
    eagain: int
    eperm: int
    einval: int
    owner_validator_calls: int
    reachable_states: int
    a72_authorizations: int
    violations: frozenset[str]
    public_order: tuple[Point, ...]
    internal_order: tuple[Point, ...]


def _scenarios() -> tuple[Scenario, ...]:
    scenarios: list[Scenario] = [
        Scenario(
            "other-arch-public",
            Platform.OTHER_ARCH,
            8,
            True,
            Stage.PUBLIC,
            Caller.PUBLIC,
            Target.ONLINE,
            False,
            Decision.PASS_THROUGH,
        ),
        Scenario(
            "other-arch-internal",
            Platform.OTHER_ARCH,
            8,
            True,
            Stage.INTERNAL,
            Caller.INTERNAL_GENERIC,
            Target.ONLINE,
            False,
            Decision.PASS_THROUGH,
        ),
        Scenario(
            "other-method-public",
            Platform.ARM64_OTHER_METHOD,
            8,
            True,
            Stage.PUBLIC,
            Caller.PUBLIC,
            Target.ONLINE,
            False,
            Decision.PASS_THROUGH,
        ),
        Scenario(
            "other-method-internal",
            Platform.ARM64_OTHER_METHOD,
            8,
            True,
            Stage.INTERNAL,
            Caller.INTERNAL_GENERIC,
            Target.ONLINE,
            False,
            Decision.PASS_THROUGH,
        ),
        Scenario(
            "out-of-range-public",
            Platform.MT6797,
            64,
            False,
            Stage.PUBLIC,
            Caller.PUBLIC,
            Target.ONLINE,
            False,
            Decision.PASS_THROUGH,
        ),
        Scenario(
            "out-of-range-internal",
            Platform.MT6797,
            64,
            False,
            Stage.INTERNAL,
            Caller.INTERNAL_GENERIC,
            Target.ONLINE,
            False,
            Decision.PASS_THROUGH,
        ),
    ]

    for cpu in range(8):
        scenarios.extend(
            (
                Scenario(
                    f"a53-cpu{cpu}-public",
                    Platform.MT6797,
                    cpu,
                    True,
                    Stage.PUBLIC,
                    Caller.PUBLIC,
                    Target.ONLINE,
                    False,
                    Decision.PASS_THROUGH,
                ),
                Scenario(
                    f"a53-cpu{cpu}-internal",
                    Platform.MT6797,
                    cpu,
                    True,
                    Stage.INTERNAL,
                    Caller.INTERNAL_GENERIC,
                    Target.ONLINE,
                    False,
                    Decision.PASS_THROUGH,
                ),
            )
        )

    for cpu in (8, 9):
        scenarios.extend(
            (
                Scenario(
                    f"a72-cpu{cpu}-public-online",
                    Platform.MT6797,
                    cpu,
                    True,
                    Stage.PUBLIC,
                    Caller.PUBLIC,
                    Target.ONLINE,
                    False,
                    Decision.EAGAIN,
                ),
                Scenario(
                    f"a72-cpu{cpu}-public-intermediate",
                    Platform.MT6797,
                    cpu,
                    True,
                    Stage.PUBLIC,
                    Caller.PUBLIC,
                    Target.INTERMEDIATE,
                    False,
                    Decision.EINVAL,
                ),
                Scenario(
                    f"a72-cpu{cpu}-internal-online",
                    Platform.MT6797,
                    cpu,
                    True,
                    Stage.INTERNAL,
                    Caller.SMT,
                    Target.ONLINE,
                    False,
                    Decision.EAGAIN,
                ),
                Scenario(
                    f"a72-cpu{cpu}-internal-frozen",
                    Platform.MT6797,
                    cpu,
                    True,
                    Stage.INTERNAL,
                    Caller.THAW,
                    Target.ONLINE,
                    True,
                    Decision.EPERM,
                ),
                Scenario(
                    f"a72-cpu{cpu}-internal-intermediate",
                    Platform.MT6797,
                    cpu,
                    True,
                    Stage.INTERNAL,
                    Caller.SMT,
                    Target.INTERMEDIATE,
                    False,
                    Decision.EINVAL,
                ),
            )
        )
    return tuple(scenarios)


SCENARIOS = _scenarios()


def initial_state(rules: Rules = CORRECT_RULES) -> HookState:
    return HookState(
        owner_closed=not rules.add_opener,
        membership_uninitialized=not rules.enter_membership_phase,
        opener_present=rules.add_opener,
        cpu_boot_backstop=not rules.remove_cpu_boot_backstop,
        cpu_disable_backstop=not rules.remove_cpu_disable_backstop,
    )


def _insert_after(
    downstream: tuple[Point, ...], hook: Point, after: Point | None
) -> tuple[Point, ...]:
    points = list(downstream)
    index = 0 if after is None else points.index(after) + 1
    points.insert(index, hook)
    return tuple(points)


def public_order(rules: Rules = CORRECT_RULES) -> tuple[Point, ...]:
    if rules.omit_public_hook:
        return PUBLIC_DOWNSTREAM
    after: Point | None = None
    if rules.public_after_cpu_possible:
        after = Point.CPU_POSSIBLE
    if rules.public_after_node_work:
        after = Point.NODE_ONLINE_WORK
    if rules.public_after_maps:
        after = Point.CPU_MAPS_LOCK
    return _insert_after(PUBLIC_DOWNSTREAM, Point.PUBLIC_HOOK, after)


def internal_order(rules: Rules = CORRECT_RULES) -> tuple[Point, ...]:
    if rules.omit_internal_hook:
        return INTERNAL_DOWNSTREAM
    after: Point | None = None
    if rules.internal_after_per_cpu:
        after = Point.PER_CPU_STATE
    if rules.internal_after_cpus_write:
        after = Point.CPUS_WRITE_LOCK
    if rules.internal_after_cpuhp:
        after = Point.CPUHP_STATE
    if rules.internal_after_callback:
        after = Point.CPUHP_CALLBACK
    if rules.internal_after_boot:
        after = Point.CPU_BOOT_METHOD
    return _insert_after(INTERNAL_DOWNSTREAM, Point.INTERNAL_HOOK, after)


def _hook_bypassed(scenario: Scenario, rules: Rules) -> bool:
    return (scenario.caller is Caller.THAW and rules.bypass_thaw) or (
        scenario.caller is Caller.SMT and rules.bypass_smt
    )


def _mutate_owner_state(
    state: HookState, scenario: Scenario, rules: Rules
) -> HookState:
    after = state
    if rules.call_begin_up:
        after = replace(after, begin_up_called=True)
    if rules.allocate_transaction:
        after = replace(after, transaction_allocated=True)
    if rules.persist_output:
        after = replace(after, output_persisted=True)
    if rules.take_transition_mutex_early and scenario.stage is Stage.INTERNAL:
        after = replace(after, transition_mutex_taken_early=True)
    if rules.enter_p31:
        after = replace(after, p31_entered=True)
    if rules.consume_a38:
        after = replace(after, a38_consumed=True)
    if rules.consume_attempt:
        after = replace(after, attempts_consumed=after.attempts_consumed + 1)
    if rules.allocate_token:
        after = replace(after, token_live=True)
    if rules.publish_p17:
        after = replace(after, p17_published=True)
    if rules.publish_p18:
        after = replace(after, p18_published=True)
    if rules.mutate_p30:
        after = replace(after, p30_changed=True)
    if rules.mutate_provider:
        after = replace(after, provider_changed=True)
    if rules.mutate_members:
        after = replace(after, members_changed=True)
    if rules.mutate_hardware:
        after = replace(after, hardware_changed=True)
    if rules.issue_cpu_on:
        after = replace(after, cpu_on_issued=True)
    if rules.call_cpu_boot:
        after = replace(after, cpu_boot_called=True)
    return after


def probe(
    scenario: Scenario, rules: Rules = CORRECT_RULES
) -> Transition:
    before = initial_state(rules)
    order = public_order(rules) if scenario.stage is Stage.PUBLIC else internal_order(rules)
    hook = Point.PUBLIC_HOOK if scenario.stage is Stage.PUBLIC else Point.INTERNAL_HOOK
    hook_invoked = hook in order and not _hook_bypassed(scenario, rules)

    if not hook_invoked:
        return Transition(
            scenario,
            before,
            before,
            Decision.PASS_THROUGH,
            False,
            False,
            False,
        )

    if scenario.platform is Platform.OTHER_ARCH:
        decision = Decision.EAGAIN if rules.deny_other_arch else Decision.PASS_THROUGH
        return Transition(scenario, before, before, decision, True, False, False)

    if not scenario.in_range:
        decision = (
            Decision.EAGAIN if rules.deny_out_of_range else Decision.PASS_THROUGH
        )
        return Transition(scenario, before, before, decision, True, False, False)

    if scenario.platform is Platform.ARM64_OTHER_METHOD:
        decision = (
            Decision.EAGAIN if rules.deny_other_method else Decision.PASS_THROUGH
        )
        return Transition(scenario, before, before, decision, True, False, False)

    if scenario.cpu not in {8, 9}:
        decision = Decision.EAGAIN if rules.deny_a53 else Decision.PASS_THROUGH
        return Transition(scenario, before, before, decision, True, True, False)

    after = _mutate_owner_state(before, scenario, rules)
    if (
        scenario.stage is Stage.INTERNAL
        and Point.INTERNAL_HOOK in order
        and order.index(Point.CPU_BOOT_METHOD) < order.index(Point.INTERNAL_HOOK)
    ):
        after = replace(after, cpu_boot_called=True)

    if scenario.target is Target.INTERMEDIATE:
        decision = (
            Decision.PASS_THROUGH if rules.accept_intermediate else Decision.EINVAL
        )
    elif scenario.stage is Stage.INTERNAL and scenario.tasks_frozen:
        decision = Decision.PASS_THROUGH if rules.accept_frozen else Decision.EPERM
    elif not before.owner_closed:
        decision = Decision.EOPNOTSUPP
    elif rules.admit_a72:
        decision = Decision.PASS_THROUGH
    else:
        decision = Decision.EAGAIN

    return Transition(scenario, before, after, decision, True, True, True)


def order_violations(
    public: tuple[Point, ...], internal: tuple[Point, ...]
) -> set[str]:
    violations: set[str] = set()
    if Point.PUBLIC_HOOK not in public:
        violations.add("PUBLIC_HOOK_PRESENT")
    else:
        public_checks = (
            (Point.CPU_POSSIBLE, "PUBLIC_BEFORE_CPU_POSSIBLE"),
            (Point.NODE_ONLINE_WORK, "PUBLIC_BEFORE_NODE_WORK"),
            (Point.CPU_MAPS_LOCK, "PUBLIC_BEFORE_MAPS"),
        )
        for point, invariant in public_checks:
            if public.index(Point.PUBLIC_HOOK) > public.index(point):
                violations.add(invariant)

    if Point.INTERNAL_HOOK not in internal:
        violations.add("INTERNAL_HOOK_PRESENT")
    else:
        internal_checks = (
            (Point.PER_CPU_STATE, "INTERNAL_BEFORE_PER_CPU"),
            (Point.CPUS_WRITE_LOCK, "INTERNAL_BEFORE_CPUS_WRITE"),
            (Point.CPUHP_STATE, "INTERNAL_BEFORE_CPUHP"),
            (Point.CPUHP_CALLBACK, "INTERNAL_BEFORE_CALLBACK"),
            (Point.CPU_BOOT_METHOD, "INTERNAL_BEFORE_CPU_BOOT"),
        )
        for point, invariant in internal_checks:
            if internal.index(Point.INTERNAL_HOOK) > internal.index(point):
                violations.add(invariant)
    return violations


def state_violations(state: HookState) -> set[str]:
    violations: set[str] = set()
    if not state.owner_closed:
        violations.add("OWNER_REMAINS_CLOSED")
    if not state.membership_uninitialized:
        violations.add("MEMBERSHIP_REMAINS_UNINITIALIZED")
    if state.opener_present:
        violations.add("NO_OPENER")
    if state.begin_up_called:
        violations.add("NO_BEGIN_UP")
    if state.transaction_allocated:
        violations.add("NO_TRANSACTION")
    if state.output_persisted:
        violations.add("NO_OUTPUT")
    if state.transition_mutex_taken_early:
        violations.add("EARLY_NO_TRANSITION_MUTEX")
    if state.p31_entered:
        violations.add("NO_P31")
    if state.a38_consumed:
        violations.add("NO_A38")
    if state.attempts_consumed:
        violations.add("NO_ATTEMPT_CONSUMPTION")
    if state.token_live:
        violations.add("NO_TOKEN")
    if state.p17_published:
        violations.add("NO_P17")
    if state.p18_published:
        violations.add("NO_P18")
    if state.p30_changed:
        violations.add("NO_P30")
    if state.provider_changed:
        violations.add("NO_PROVIDER_EFFECT")
    if state.members_changed:
        violations.add("NO_MEMBER_EFFECT")
    if state.hardware_changed:
        violations.add("NO_HARDWARE_EFFECT")
    if state.cpu_on_issued:
        violations.add("NO_CPU_ON")
    if state.cpu_boot_called:
        violations.add("NO_CPU_BOOT")
    if not state.cpu_boot_backstop:
        violations.add("CPU_BOOT_BACKSTOP_RETAINED")
    if not state.cpu_disable_backstop:
        violations.add("CPU_DISABLE_BACKSTOP_RETAINED")
    return violations


def _decision_invariant(scenario: Scenario) -> str:
    if scenario.platform is Platform.OTHER_ARCH:
        return "WEAK_DEFAULT_PASS_THROUGH"
    if not scenario.in_range:
        return "BOUNDS_PRESERVE_GENERIC"
    if scenario.platform is Platform.ARM64_OTHER_METHOD:
        return "OPTIONAL_CALLBACK_PASS_THROUGH"
    if scenario.platform is Platform.MT6797 and scenario.cpu not in {8, 9}:
        return "MT6797_A53_PASS_THROUGH"
    if scenario.target is Target.INTERMEDIATE:
        return "INTERMEDIATE_TARGET_REJECTED"
    if scenario.stage is Stage.INTERNAL and scenario.tasks_frozen:
        return "FROZEN_INTERNAL_REJECTED"
    return "A72_CLOSED_DENIAL"


def transition_violations(transition: Transition) -> set[str]:
    scenario = transition.scenario
    violations = state_violations(transition.before)
    violations.update(state_violations(transition.after))

    if transition.after != transition.before:
        violations.add("HOOK_STATE_IMMUTABLE")
    if not transition.hook_invoked:
        if scenario.stage is Stage.PUBLIC:
            violations.add("PUBLIC_HOOK_PRESENT")
        else:
            violations.add("INTERNAL_HOOK_PRESENT")
    if transition.decision is not scenario.expected:
        violations.add(_decision_invariant(scenario))
    if scenario.caller is Caller.THAW and not transition.hook_invoked:
        violations.add("THAW_USES_INTERNAL_HOOK")
    if scenario.caller is Caller.SMT and not transition.hook_invoked:
        violations.add("SMT_USES_INTERNAL_HOOK")
    if scenario.is_a72 and transition.decision is Decision.PASS_THROUGH:
        violations.add("NO_A72_AUTHORIZATION")
    return violations


def audit_contract(rules: Rules = CORRECT_RULES) -> AuditReport:
    public = public_order(rules)
    internal = internal_order(rules)
    start = initial_state(rules)
    violations = order_violations(public, internal)
    violations.update(state_violations(start))
    states = {start}
    decisions: dict[Decision, int] = {decision: 0 for decision in Decision}
    owner_validator_calls = 0
    a72_authorizations = 0

    for scenario in SCENARIOS:
        transition = probe(scenario, rules)
        decisions[transition.decision] += 1
        owner_validator_calls += transition.owner_validator_invoked
        a72_authorizations += (
            scenario.is_a72
            and transition.decision is Decision.PASS_THROUGH
        )
        states.add(transition.after)
        violations.update(transition_violations(transition))

    return AuditReport(
        admission_probes=len(SCENARIOS),
        pass_through=decisions[Decision.PASS_THROUGH],
        eagain=decisions[Decision.EAGAIN],
        eperm=decisions[Decision.EPERM],
        einval=decisions[Decision.EINVAL],
        owner_validator_calls=owner_validator_calls,
        reachable_states=len(states),
        a72_authorizations=a72_authorizations,
        violations=frozenset(violations),
        public_order=public,
        internal_order=internal,
    )


def _order_text(order: tuple[Point, ...]) -> str:
    return " -> ".join(point.value for point in order)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    report = audit_contract()
    print(CLAIM)
    print(f"public_order={_order_text(report.public_order)}")
    print(f"internal_order={_order_text(report.internal_order)}")
    print(f"admission_probes={report.admission_probes}")
    print(f"pass_through={report.pass_through}")
    print(f"eagain={report.eagain}")
    print(f"eperm={report.eperm}")
    print(f"einval={report.einval}")
    print(f"owner_validator_calls={report.owner_validator_calls}")
    print("direct_internal_paths=THAW,SMT")
    print(f"reachable_hook_states={report.reachable_states}")
    print(f"a72_authorizations={report.a72_authorizations}")
    print(f"violations={len(report.violations)}")
    if report.violations:
        for violation in sorted(report.violations):
            print(f"FAIL {violation}")
        return 1
    print("PASS closed generic admission-hook contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
