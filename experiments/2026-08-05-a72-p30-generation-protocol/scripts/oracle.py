#!/usr/bin/env python3
"""Independent bounded oracle for the corrected P30 generation protocol.

Claim: PARTIAL_P30_PROTOCOL_MODEL.

This module is intentionally independent of Linux source and generated build
inputs.  It proves properties only of this bounded specification model.  It
does not supply a P24 production owner, production hooks, a build/runtime
result, or a P30E MMU-off proof.
"""

from __future__ import annotations

import argparse
import sys
from collections import deque
from dataclasses import dataclass, replace
from enum import Enum
from typing import Iterable

sys.dont_write_bytecode = True

CLAIM = "PARTIAL_P30_PROTOCOL_MODEL"


class Rejected(ValueError):
    """The requested transition is outside the modeled contract."""


class Phase(Enum):
    FREE = "FREE"
    PREPARED = "PREPARED"
    ABORTED = "ABORTED"
    ARMED = "ARMED"
    PUBLISHING = "PUBLISHING"
    PUBLISHED = "PUBLISHED"
    CANCELLED = "CANCELLED"
    FAILING = "FAILING"
    FAULTED = "FAULTED"
    PARKED = "PARKED"
    PANICKED = "PANICKED"


class Winner(Enum):
    PUBLISH = "publish"
    CANCEL = "cancel"
    FAILURE = "failure"
    FAULT = "fault"


class Branch(Enum):
    K = "K"
    C = "C"
    P = "P"
    E = "E"
    U = "U"


class Kind(Enum):
    PREPARE = "prepare"
    ABORT_PROVEN = "abort-proven"
    DISPATCH_AMBIGUOUS = "dispatch-ambiguous"
    RELEASE_ABORT = "release-abort"
    ARM = "arm"
    CLAIM_PUBLISH = "claim-publish"
    CLAIM_CANCEL = "claim-cancel"
    CPU_ON_FAULT = "cpu-on-fault"
    CLAIM_FAIL = "claim-fail"
    SECOND_WINNER = "second-winner"
    INTERRUPT_PUBLISH = "interrupt-publish"
    FINISH_PUBLISH = "finish-publish"
    EXTERNAL_QUARANTINE = "external-quarantine"
    REPLACE_QUARANTINE = "replace-quarantine"
    DRAIN = "drain"
    RETIRE_P14_P15 = "retire-p14-p15"
    PARK = "park"
    PANIC_RECORD = "panic-record"
    PANIC_PUBLISH = "panic-publish"
    TERMINAL_OVERWRITE = "terminal-overwrite"


@dataclass(frozen=True, order=True)
class Token:
    operation: str
    cpu: int
    mpidr: int
    generation: int
    cookie: int

    @property
    def target_tuple(self) -> tuple[int, int, int, int]:
        return (self.cpu, self.mpidr, self.generation, self.cookie)

    @property
    def short(self) -> str:
        return f"{self.operation}/gen{self.generation}"


CPU8_GEN42 = Token("CPU8", 8, 0x200, 42, 0x8A720042)
CPU9_GEN7 = Token("CPU9", 9, 0x201, 7, 0x9A720007)
TOKENS = (CPU8_GEN42, CPU9_GEN7)


@dataclass(frozen=True)
class Quarantine:
    cause: str
    subject: Token
    presented: Token


@dataclass(frozen=True)
class Terminal:
    branch: Branch
    reason: str
    effects: tuple[str, ...]
    target_tuple: tuple[int, int, int, int]


@dataclass(frozen=True)
class State:
    phase: Phase = Phase.FREE
    active: Token | None = None
    retired: frozenset[Token] = frozenset()
    quarantine: Quarantine | None = None
    winners: frozenset[Winner] = frozenset()
    failure_branch: Branch | None = None
    completion_ready: bool = False
    completion_consumed: bool = False
    online_drained: bool = False
    online_ok: bool = False
    panic_recorded: bool = False
    panic_interlock: bool = False
    terminal: Terminal | None = None


@dataclass(frozen=True)
class Action:
    kind: Kind
    token: Token | None = None
    branch: Branch | None = None
    observed_online: bool | None = None
    claimed_online: bool | None = None

    @property
    def label(self) -> str:
        fields = [self.kind.value]
        if self.token is not None:
            fields.append(self.token.short)
        if self.branch is not None:
            fields.append(self.branch.value)
        if self.observed_online is not None:
            fields.append(f"observed={int(self.observed_online)}")
        if self.claimed_online is not None:
            fields.append(f"claimed={int(self.claimed_online)}")
        return ":".join(fields)


@dataclass(frozen=True)
class Rules:
    global_generation_order: bool = False
    allow_retired_replay: bool = False
    ambiguity_aborts: bool = False
    drop_prearmed_claim_fault: bool = False
    armed_fault_without_quarantine: bool = False
    allow_second_winner: bool = False
    interrupt_publishing: bool = False
    allow_retire_with_quarantine: bool = False
    quarantine_blocks_drain: bool = False
    allow_retire_without_drain: bool = False
    trust_claimed_online: bool = False
    ignore_target_tuple: bool = False
    allow_c_to_k: bool = False
    allow_p_park: bool = False
    panicked_without_interlock: bool = False
    replace_quarantine: bool = False
    mutable_terminal: bool = False


CORRECT_RULES = Rules()


@dataclass(frozen=True)
class Transition:
    before: State
    action: Action
    after: State


@dataclass(frozen=True)
class AuditReport:
    states: int
    transitions: int
    violations: frozenset[str]
    golden_trace: tuple[str, ...]


TERMINAL_EFFECTS = {
    Branch.K: ("online-cleared", "ipi-masked", "clean-return-parked"),
    Branch.C: ("online-cleared", "cpu-die-returned", "post-c-parked"),
    Branch.P: ("panic-recorded", "panic-interlock"),
    Branch.E: ("exception-recorded", "exception-parked"),
    Branch.U: ("bounded-failure-recorded", "unknown-parked"),
}


def initial_state() -> State:
    return State()


def wrong_token(token: Token) -> Token:
    """Return a deterministic tuple mismatch in the same operation namespace."""

    return replace(token, mpidr=token.mpidr ^ 1)


def _require_active(state: State) -> Token:
    if state.active is None:
        raise Rejected("no-active-operation")
    return state.active


def _latch_quarantine(
    state: State, cause: str, presented: Token | None = None
) -> State:
    active = _require_active(state)
    if state.quarantine is not None:
        return state
    return replace(
        state,
        quarantine=Quarantine(cause, active, presented if presented is not None else active),
    )


def _target_matches(state: State, action: Action, rules: Rules) -> bool:
    active = _require_active(state)
    return rules.ignore_target_tuple or action.token == active


def _target_mismatch(state: State, action: Action) -> State:
    presented = action.token if action.token is not None else wrong_token(_require_active(state))
    return _latch_quarantine(state, "exact-target-tuple-mismatch", presented)


def _free_after_retirement(state: State) -> State:
    active = _require_active(state)
    return State(retired=state.retired | frozenset({active}))


def _terminal(state: State, branch: Branch, phase: Phase) -> State:
    active = _require_active(state)
    reason = {
        Branch.K: "bounded-clean-return",
        Branch.C: "post-c-return",
        Branch.P: "panic-closure",
        Branch.E: "exception-closure",
        Branch.U: "unknown-or-protocol-closure",
    }[branch]
    return replace(
        state,
        phase=phase,
        terminal=Terminal(branch, reason, TERMINAL_EFFECTS[branch], active.target_tuple),
    )


def step(state: State, action: Action, rules: Rules = CORRECT_RULES) -> State:
    """Apply one action or raise Rejected when its preconditions do not hold."""

    if state.phase in {Phase.PARKED, Phase.PANICKED}:
        if not rules.mutable_terminal or action.kind is not Kind.TERMINAL_OVERWRITE:
            raise Rejected("terminal-immutable")
        assert state.terminal is not None
        if state.terminal.reason == "mutated-after-publication":
            raise Rejected("bounded-terminal-mutation-already-applied")
        changed = replace(
            state.terminal,
            reason="mutated-after-publication",
            effects=state.terminal.effects + ("unsafe-mutation",),
        )
        return replace(state, terminal=changed)

    if action.kind is Kind.PREPARE:
        if state.phase is not Phase.FREE or action.token not in TOKENS:
            raise Rejected("prepare-state-or-token")
        assert action.token is not None
        if action.token in state.retired and not rules.allow_retired_replay:
            raise Rejected("retired-token-replay")
        if rules.global_generation_order and state.retired:
            if action.token.generation <= max(token.generation for token in state.retired):
                raise Rejected("global-generation-floor")
        return replace(state, phase=Phase.PREPARED, active=action.token)

    active = _require_active(state)

    if (
        action.kind in {Kind.CLAIM_PUBLISH, Kind.CLAIM_FAIL}
        and state.phase in {Phase.PREPARED, Phase.ABORTED}
    ):
        if action.token != active:
            raise Rejected("prearmed-target-claim-token")
        if rules.drop_prearmed_claim_fault:
            raise Rejected("prearmed-target-claim-dropped")
        faulted = replace(
            state, phase=Phase.FAULTED, winners=frozenset({Winner.FAULT})
        )
        return _latch_quarantine(faulted, "ILLEGAL_EDGE")

    if action.kind is Kind.ABORT_PROVEN:
        if state.phase is not Phase.PREPARED:
            raise Rejected("abort-state")
        return replace(state, phase=Phase.ABORTED)

    if action.kind is Kind.DISPATCH_AMBIGUOUS:
        if state.phase is not Phase.PREPARED:
            raise Rejected("dispatch-ambiguity-state")
        if rules.ambiguity_aborts:
            return replace(state, phase=Phase.ABORTED)
        faulted = replace(
            state, phase=Phase.FAULTED, winners=frozenset({Winner.FAULT})
        )
        return _latch_quarantine(faulted, "prepared-dispatch-ambiguous")

    if action.kind is Kind.RELEASE_ABORT:
        if state.phase is not Phase.ABORTED or state.quarantine is not None:
            raise Rejected("release-abort-state")
        return _free_after_retirement(state)

    if action.kind is Kind.ARM:
        if state.phase is not Phase.PREPARED or action.token != active:
            raise Rejected("arm-state-or-token")
        return replace(state, phase=Phase.ARMED)

    if action.kind is Kind.CLAIM_PUBLISH:
        if state.phase is not Phase.ARMED:
            raise Rejected("publish-claim-state")
        return replace(
            state, phase=Phase.PUBLISHING, winners=frozenset({Winner.PUBLISH})
        )

    if action.kind is Kind.CLAIM_CANCEL:
        if state.phase is not Phase.ARMED:
            raise Rejected("cancel-claim-state")
        cancelled = replace(
            state, phase=Phase.CANCELLED, winners=frozenset({Winner.CANCEL})
        )
        return _latch_quarantine(cancelled, "armed-cancelled")

    if action.kind is Kind.CPU_ON_FAULT:
        if state.phase is not Phase.ARMED:
            raise Rejected("cpu-on-fault-state")
        faulted = replace(
            state, phase=Phase.FAULTED, winners=frozenset({Winner.FAULT})
        )
        if rules.armed_fault_without_quarantine:
            return faulted
        return _latch_quarantine(faulted, "armed-cpu-on-fault")

    if action.kind is Kind.CLAIM_FAIL:
        if state.phase is not Phase.ARMED or action.branch is None:
            raise Rejected("failure-claim-state")
        if action.branch not in {Branch.K, Branch.C, Branch.P, Branch.E, Branch.U}:
            raise Rejected("failure-branch")
        failing = replace(
            state,
            phase=Phase.FAILING,
            winners=frozenset({Winner.FAILURE}),
            failure_branch=action.branch,
        )
        return _latch_quarantine(failing, f"armed-failure-{action.branch.value}")

    if action.kind is Kind.SECOND_WINNER:
        if not rules.allow_second_winner or state.phase not in {
            Phase.CANCELLED,
            Phase.FAILING,
            Phase.FAULTED,
        }:
            raise Rejected("second-winner")
        return replace(state, winners=state.winners | frozenset({Winner.PUBLISH}))

    if action.kind is Kind.INTERRUPT_PUBLISH:
        if not rules.interrupt_publishing or state.phase is not Phase.PUBLISHING:
            raise Rejected("publishing-indivisible")
        interrupted = replace(
            state, phase=Phase.CANCELLED, winners=frozenset({Winner.CANCEL})
        )
        return _latch_quarantine(interrupted, "publishing-interrupted")

    if action.kind is Kind.FINISH_PUBLISH:
        if state.phase is not Phase.PUBLISHING:
            raise Rejected("finish-publish-state")
        if not _target_matches(state, action, rules):
            return _target_mismatch(state, action)
        return replace(state, phase=Phase.PUBLISHED, completion_ready=True)

    if action.kind is Kind.EXTERNAL_QUARANTINE:
        if state.phase not in {Phase.PUBLISHING, Phase.PUBLISHED}:
            raise Rejected("external-quarantine-state")
        return _latch_quarantine(state, "external-first-cause")

    if action.kind is Kind.REPLACE_QUARANTINE:
        if not rules.replace_quarantine or state.quarantine is None:
            raise Rejected("quarantine-first-cause")
        return replace(
            state,
            quarantine=Quarantine("unsafe-replacement", active, wrong_token(active)),
        )

    if action.kind is Kind.DRAIN:
        if (
            state.phase is not Phase.PUBLISHED
            or not state.completion_ready
            or state.completion_consumed
            or action.observed_online is None
            or action.claimed_online is None
            or action.token != active
        ):
            raise Rejected("drain-state-or-token")
        if rules.quarantine_blocks_drain and state.quarantine is not None:
            raise Rejected("quarantine-blocked-drain")
        online = (
            action.claimed_online if rules.trust_claimed_online else action.observed_online
        )
        drained = replace(
            state,
            completion_consumed=True,
            online_drained=True,
            online_ok=online,
        )
        if online:
            return drained
        return _latch_quarantine(drained, "internal-online-sample-false")

    if action.kind is Kind.RETIRE_P14_P15:
        if state.phase is not Phase.PUBLISHED or action.token != active:
            raise Rejected("retire-state-or-token")
        if state.quarantine is not None and not rules.allow_retire_with_quarantine:
            raise Rejected("quarantine-blocks-p14-p15")
        if not rules.allow_retire_without_drain and (
            not state.completion_ready
            or not state.completion_consumed
            or not state.online_drained
            or not state.online_ok
        ):
            raise Rejected("publication-not-drained-online")
        return _free_after_retirement(state)

    if action.kind is Kind.PARK:
        if action.branch is None:
            raise Rejected("park-branch")
        if not _target_matches(state, action, rules):
            return _target_mismatch(state, action)
        legal = False
        if state.phase in {Phase.CANCELLED, Phase.FAULTED}:
            legal = action.branch is Branch.U
        elif state.phase is Phase.FAILING:
            if state.failure_branch is Branch.K:
                legal = action.branch in {Branch.K, Branch.C}
            elif state.failure_branch is Branch.C:
                legal = action.branch is Branch.C or (
                    rules.allow_c_to_k and action.branch is Branch.K
                )
            elif state.failure_branch in {Branch.E, Branch.U}:
                legal = action.branch is state.failure_branch
            elif state.failure_branch is Branch.P:
                legal = rules.allow_p_park and action.branch is Branch.P
        if not legal:
            raise Rejected("illegal-terminal-branch")
        return _terminal(state, action.branch, Phase.PARKED)

    if action.kind is Kind.PANIC_RECORD:
        if state.phase is not Phase.FAILING or state.failure_branch is not Branch.P:
            raise Rejected("panic-record-state")
        if not _target_matches(state, action, rules):
            return _target_mismatch(state, action)
        return replace(state, panic_recorded=True)

    if action.kind is Kind.PANIC_PUBLISH:
        if (
            state.phase is not Phase.FAILING
            or state.failure_branch is not Branch.P
            or not state.panic_recorded
            or action.token != active
        ):
            raise Rejected("panic-publish-state-or-token")
        panicked = _terminal(state, Branch.P, Phase.PANICKED)
        return replace(
            panicked, panic_interlock=not rules.panicked_without_interlock
        )

    raise Rejected(f"unsupported-action:{action.kind.value}")


def enabled_actions(state: State, rules: Rules = CORRECT_RULES) -> tuple[Action, ...]:
    """Return a finite superset of actions worth trying from one state."""

    if state.phase is Phase.FREE:
        return tuple(Action(Kind.PREPARE, token) for token in TOKENS)
    active = _require_active(state)
    wrong = wrong_token(active)

    if state.phase is Phase.PREPARED:
        return (
            Action(Kind.ABORT_PROVEN, active),
            Action(Kind.DISPATCH_AMBIGUOUS, active),
            Action(Kind.CLAIM_PUBLISH, active),
            Action(Kind.CLAIM_FAIL, active, Branch.K),
            Action(Kind.ARM, active),
        )
    if state.phase is Phase.ABORTED:
        return (
            Action(Kind.RELEASE_ABORT, active),
            Action(Kind.CLAIM_PUBLISH, active),
            Action(Kind.CLAIM_FAIL, active, Branch.K),
        )
    if state.phase is Phase.ARMED:
        return (
            Action(Kind.CLAIM_PUBLISH, active),
            Action(Kind.CLAIM_CANCEL, active),
            Action(Kind.CPU_ON_FAULT, active),
            *(Action(Kind.CLAIM_FAIL, active, branch) for branch in Branch),
        )
    if state.phase is Phase.PUBLISHING:
        actions = [
            Action(Kind.FINISH_PUBLISH, active),
            Action(Kind.FINISH_PUBLISH, wrong),
            Action(Kind.EXTERNAL_QUARANTINE, active),
        ]
        if rules.interrupt_publishing:
            actions.append(Action(Kind.INTERRUPT_PUBLISH, active))
        if rules.replace_quarantine and state.quarantine is not None:
            actions.append(Action(Kind.REPLACE_QUARANTINE, active))
        return tuple(actions)
    if state.phase is Phase.PUBLISHED:
        actions = [
            Action(Kind.DRAIN, active, observed_online=True, claimed_online=True),
            Action(Kind.DRAIN, active, observed_online=False, claimed_online=True),
            Action(Kind.EXTERNAL_QUARANTINE, active),
            Action(Kind.RETIRE_P14_P15, active),
        ]
        if rules.replace_quarantine and state.quarantine is not None:
            actions.append(Action(Kind.REPLACE_QUARANTINE, active))
        return tuple(actions)
    if state.phase in {Phase.CANCELLED, Phase.FAULTED}:
        actions = [
            Action(Kind.PARK, active, Branch.U),
            Action(Kind.PARK, wrong, Branch.U),
        ]
        if rules.allow_second_winner:
            actions.append(Action(Kind.SECOND_WINNER, active))
        if rules.replace_quarantine:
            actions.append(Action(Kind.REPLACE_QUARANTINE, active))
        return tuple(actions)
    if state.phase is Phase.FAILING:
        actions: list[Action] = []
        if state.failure_branch is Branch.K:
            actions.extend(
                [Action(Kind.PARK, active, Branch.K), Action(Kind.PARK, active, Branch.C)]
            )
        elif state.failure_branch is Branch.C:
            actions.append(Action(Kind.PARK, active, Branch.C))
            if rules.allow_c_to_k:
                actions.append(Action(Kind.PARK, active, Branch.K))
        elif state.failure_branch in {Branch.E, Branch.U}:
            actions.append(Action(Kind.PARK, active, state.failure_branch))
        elif state.failure_branch is Branch.P:
            actions.extend(
                [
                    Action(Kind.PANIC_RECORD, active),
                    Action(Kind.PANIC_RECORD, wrong),
                    Action(Kind.PANIC_PUBLISH, active),
                ]
            )
            if rules.allow_p_park:
                actions.append(Action(Kind.PARK, active, Branch.P))
        if rules.allow_second_winner:
            actions.append(Action(Kind.SECOND_WINNER, active))
        if rules.replace_quarantine:
            actions.append(Action(Kind.REPLACE_QUARANTINE, active))
        return tuple(actions)
    if state.phase in {Phase.PARKED, Phase.PANICKED} and rules.mutable_terminal:
        return (Action(Kind.TERMINAL_OVERWRITE, active),)
    return ()


def state_violations(state: State) -> set[str]:
    violations: set[str] = set()
    terminal_phase = state.phase in {Phase.PARKED, Phase.PANICKED}

    if state.phase is Phase.FREE:
        if any(
            (
                state.active is not None,
                state.quarantine is not None,
                bool(state.winners),
                state.failure_branch is not None,
                state.completion_ready,
                state.completion_consumed,
                state.online_drained,
                state.online_ok,
                state.panic_recorded,
                state.panic_interlock,
                state.terminal is not None,
            )
        ):
            violations.add("FREE_IS_CLEAN")
        return violations

    if state.active is None:
        violations.add("ACTIVE_OPERATION_REQUIRED")
        return violations
    if state.active in state.retired:
        violations.add("ONE_SHOT_RETIREMENT")
    expected_target = {"CPU8": (8, 0x200), "CPU9": (9, 0x201)}.get(
        state.active.operation
    )
    if expected_target != (state.active.cpu, state.active.mpidr):
        violations.add("EXACT_TARGET_TUPLE")

    owner_phases = {
        Phase.PUBLISHING: Winner.PUBLISH,
        Phase.PUBLISHED: Winner.PUBLISH,
        Phase.CANCELLED: Winner.CANCEL,
        Phase.FAILING: Winner.FAILURE,
        Phase.FAULTED: Winner.FAULT,
    }
    if state.phase in {Phase.PREPARED, Phase.ABORTED, Phase.ARMED}:
        if state.winners:
            violations.add("SINGLE_WINNER")
    elif state.phase in owner_phases:
        if state.winners != frozenset({owner_phases[state.phase]}):
            violations.add("SINGLE_WINNER")
    elif terminal_phase and len(state.winners) != 1:
        violations.add("SINGLE_WINNER")

    if state.phase in {Phase.CANCELLED, Phase.FAILING, Phase.FAULTED} | {
        Phase.PARKED,
        Phase.PANICKED,
    }:
        if state.quarantine is None:
            if state.phase is Phase.FAULTED:
                violations.add("ARMED_FAULTING")
            else:
                violations.add("FAULT_TERMINAL_QUARANTINE")

    if state.failure_branch is not None and state.winners != frozenset(
        {Winner.FAILURE}
    ):
        violations.add("FAILURE_BRANCH_OWNERSHIP")
    if state.completion_consumed and not (
        state.completion_ready and state.online_drained
    ):
        violations.add("DRAIN_BEFORE_RETIREMENT")
    if state.online_ok and not state.completion_consumed:
        violations.add("INTERNAL_ONLINE_OBSERVATION")
    if any(
        (
            state.completion_ready,
            state.completion_consumed,
            state.online_drained,
            state.online_ok,
        )
    ) and state.phase is not Phase.PUBLISHED:
        violations.add("PUBLICATION_COMPLETION_SCOPE")

    if terminal_phase != (state.terminal is not None):
        violations.add("TERMINAL_RECORD_POLARITY")
    if state.terminal is not None:
        if state.terminal.target_tuple != state.active.target_tuple:
            violations.add("EXACT_TARGET_TUPLE")
        if state.phase is Phase.PANICKED:
            if (
                state.terminal.branch is not Branch.P
                or state.failure_branch is not Branch.P
                or not state.panic_recorded
                or not state.panic_interlock
            ):
                violations.add("P_INTERLOCK")
        if state.phase is Phase.PARKED:
            if state.terminal.branch is Branch.P or state.panic_interlock:
                violations.add("P_INTERLOCK")
            if state.winners == frozenset({Winner.FAILURE}):
                legal = {
                    Branch.K: {Branch.K, Branch.C},
                    Branch.C: {Branch.C},
                    Branch.E: {Branch.E},
                    Branch.U: {Branch.U},
                }.get(state.failure_branch, set())
                if state.terminal.branch not in legal:
                    violations.add("K_C_P_E_U_TERMINAL_RULES")
            elif state.terminal.branch is not Branch.U:
                violations.add("K_C_P_E_U_TERMINAL_RULES")
    elif state.panic_interlock:
        violations.add("P_INTERLOCK")

    if state.quarantine is not None and state.quarantine.subject != state.active:
        violations.add("QUARANTINE_STICKY")
    return violations


def transition_violations(transition: Transition) -> set[str]:
    before, action, after = transition.before, transition.action, transition.after
    violations: set[str] = set()

    if before.quarantine is not None and after.quarantine != before.quarantine:
        violations.add("QUARANTINE_STICKY")
    if not before.retired.issubset(after.retired):
        violations.add("ONE_SHOT_RETIREMENT")
    if before.phase in {Phase.PARKED, Phase.PANICKED} and after != before:
        violations.add("TERMINAL_IMMUTABILITY")
    if before.phase is Phase.PUBLISHING and action.kind not in {
        Kind.FINISH_PUBLISH,
        Kind.EXTERNAL_QUARANTINE,
        Kind.REPLACE_QUARANTINE,
    }:
        violations.add("PUBLISHING_INDIVISIBLE")
    if before.phase is Phase.PUBLISHING and action.kind is Kind.FINISH_PUBLISH:
        if action.token == before.active and after.phase is not Phase.PUBLISHED:
            violations.add("PUBLISHING_INDIVISIBLE")
        if action.token != before.active and (
            after.phase is not before.phase or after.terminal != before.terminal
        ):
            violations.add("EXACT_TARGET_TUPLE")
    if action.kind in {Kind.PARK, Kind.PANIC_RECORD} and action.token != before.active:
        if after.phase is not before.phase or after.terminal != before.terminal:
            violations.add("EXACT_TARGET_TUPLE")
    if action.kind is Kind.DISPATCH_AMBIGUOUS:
        if after.phase is not Phase.FAULTED or after.quarantine is None:
            violations.add("PREPARED_FAULTING")
    if action.kind is Kind.CPU_ON_FAULT:
        if after.phase is not Phase.FAULTED or after.quarantine is None:
            violations.add("ARMED_FAULTING")
    if (
        action.kind in {Kind.CLAIM_PUBLISH, Kind.CLAIM_FAIL}
        and before.phase in {Phase.PREPARED, Phase.ABORTED}
    ):
        if (
            after.phase is not Phase.FAULTED
            or after.quarantine is None
            or after.quarantine.cause != "ILLEGAL_EDGE"
        ):
            violations.add("PREARMED_TARGET_CLAIM_FAULT")
    if action.kind is Kind.RETIRE_P14_P15 and after.phase is Phase.FREE:
        if before.quarantine is not None:
            violations.add("QUARANTINE_RETIREMENT")
        if not (
            before.completion_ready
            and before.completion_consumed
            and before.online_drained
        ):
            violations.add("DRAIN_BEFORE_RETIREMENT")
        if not before.online_ok:
            violations.add("INTERNAL_ONLINE_OBSERVATION")
    return violations


def explore(rules: Rules = CORRECT_RULES) -> tuple[set[State], list[Transition]]:
    """Breadth-first enumeration of the complete bounded reachable graph."""

    start = initial_state()
    states = {start}
    queue: deque[State] = deque([start])
    transitions: list[Transition] = []

    while queue:
        before = queue.popleft()
        for action in enabled_actions(before, rules):
            try:
                after = step(before, action, rules)
            except Rejected:
                continue
            transition = Transition(before, action, after)
            transitions.append(transition)
            if after not in states:
                states.add(after)
                queue.append(after)
    return states, transitions


def run_actions(
    actions: Iterable[Action], rules: Rules = CORRECT_RULES
) -> tuple[State, tuple[str, ...]]:
    state = initial_state()
    labels: list[str] = []
    for action in actions:
        state = step(state, action, rules)
        labels.append(action.label)
    return state, tuple(labels)


def _success_actions(token: Token) -> tuple[Action, ...]:
    return (
        Action(Kind.PREPARE, token),
        Action(Kind.ARM, token),
        Action(Kind.CLAIM_PUBLISH, token),
        Action(Kind.FINISH_PUBLISH, token),
        Action(
            Kind.DRAIN,
            token,
            observed_online=True,
            claimed_online=True,
        ),
        Action(Kind.RETIRE_P14_P15, token),
    )


def golden_retirement_trace(
    rules: Rules = CORRECT_RULES,
) -> tuple[State, tuple[str, ...]]:
    return run_actions((*_success_actions(CPU8_GEN42), *_success_actions(CPU9_GEN7)), rules)


def _scenario_checks(rules: Rules) -> tuple[set[str], tuple[str, ...]]:
    violations: set[str] = set()
    golden_labels: tuple[str, ...] = ()
    try:
        final, golden_labels = golden_retirement_trace(rules)
        if final.phase is not Phase.FREE or final.retired != frozenset(TOKENS):
            violations.add("PER_OPERATION_OPAQUE_GENERATION")
    except Rejected:
        violations.add("PER_OPERATION_OPAQUE_GENERATION")
        final = State(retired=frozenset(TOKENS))

    for token in TOKENS:
        try:
            step(final, Action(Kind.PREPARE, token), rules)
        except Rejected:
            pass
        else:
            violations.add("ONE_SHOT_RETIREMENT")

    prepared = step(initial_state(), Action(Kind.PREPARE, CPU8_GEN42), rules)
    aborted = step(prepared, Action(Kind.ABORT_PROVEN, CPU8_GEN42), rules)
    prearmed_claims = (
        Action(Kind.CLAIM_PUBLISH, CPU8_GEN42),
        Action(Kind.CLAIM_FAIL, CPU8_GEN42, Branch.K),
    )
    for state in (prepared, aborted):
        for claim in prearmed_claims:
            try:
                faulted = step(state, claim, rules)
            except Rejected:
                violations.add("PREARMED_TARGET_CLAIM_FAULT")
                continue
            if (
                faulted.phase is not Phase.FAULTED
                or faulted.quarantine is None
                or faulted.quarantine.cause != "ILLEGAL_EDGE"
            ):
                violations.add("PREARMED_TARGET_CLAIM_FAULT")

    publishing, _ = run_actions(
        (
            Action(Kind.PREPARE, CPU8_GEN42),
            Action(Kind.ARM, CPU8_GEN42),
            Action(Kind.CLAIM_PUBLISH, CPU8_GEN42),
            Action(Kind.EXTERNAL_QUARANTINE, CPU8_GEN42),
            Action(Kind.FINISH_PUBLISH, CPU8_GEN42),
        ),
        rules,
    )
    try:
        drained = step(
            publishing,
            Action(
                Kind.DRAIN,
                CPU8_GEN42,
                observed_online=True,
                claimed_online=True,
            ),
            rules,
        )
    except Rejected:
        violations.add("QUARANTINE_ALLOWS_DRAIN")
    else:
        if not drained.completion_consumed or not drained.online_drained:
            violations.add("QUARANTINE_ALLOWS_DRAIN")
        try:
            step(
                drained,
                Action(Kind.RETIRE_P14_P15, CPU8_GEN42),
                rules,
            )
        except Rejected:
            pass
        else:
            violations.add("QUARANTINE_RETIREMENT")

    before_drain, _ = run_actions(
        (
            Action(Kind.PREPARE, CPU8_GEN42),
            Action(Kind.ARM, CPU8_GEN42),
            Action(Kind.CLAIM_PUBLISH, CPU8_GEN42),
            Action(Kind.FINISH_PUBLISH, CPU8_GEN42),
        ),
        rules,
    )
    sampled = step(
        before_drain,
        Action(
            Kind.DRAIN,
            CPU8_GEN42,
            observed_online=False,
            claimed_online=True,
        ),
        rules,
    )
    if sampled.online_ok or sampled.quarantine is None:
        violations.add("INTERNAL_ONLINE_OBSERVATION")
    return violations, golden_labels


def audit_contract(rules: Rules = CORRECT_RULES) -> AuditReport:
    states, transitions = explore(rules)
    violations: set[str] = set()
    for state in states:
        violations.update(state_violations(state))
    for transition in transitions:
        violations.update(transition_violations(transition))
    reachable_terminals = {
        (state.phase, state.terminal.branch)
        for state in states
        if state.terminal is not None
    }
    required_terminals = {
        (Phase.PARKED, Branch.K),
        (Phase.PARKED, Branch.C),
        (Phase.PANICKED, Branch.P),
        (Phase.PARKED, Branch.E),
        (Phase.PARKED, Branch.U),
    }
    if not required_terminals.issubset(reachable_terminals):
        violations.add("K_C_P_E_U_TERMINAL_RULES")
    scenario_violations, golden = _scenario_checks(rules)
    violations.update(scenario_violations)
    return AuditReport(len(states), len(transitions), frozenset(violations), golden)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    report = audit_contract()
    print(CLAIM)
    print(f"reachable_states={report.states}")
    print(f"accepted_transitions={report.transitions}")
    print("opaque_generation_witness=CPU8/gen42 -> CPU9/gen7")
    print(f"golden_actions={len(report.golden_trace)}")
    print(f"violations={len(report.violations)}")
    if report.violations:
        for violation in sorted(report.violations):
            print(f"FAIL {violation}")
        return 1
    print("PASS corrected bounded contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
