#!/usr/bin/env python3
"""I/O-free model of the CPU8 default-off binder contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
import errno


EREMOTEIO = 121
LEDGER_MAX_STAGE = 10


class Stage(IntEnum):
    WATCHDOG = 1
    P27 = 2
    PROVIDER = 3
    ISOLATION = 4
    SRAM = 5
    CPU_ON = 6
    ONLINE_WAIT = 7
    IPI = 8
    DCM = 9
    MEMBERSHIP = 10


class Lifecycle(IntEnum):
    IDLE = 0
    STARTING = 1
    CPU_ON_ACCEPTED = 2
    SECONDARY_COMPLETE = 3
    TERMINAL = 4


class OwnerPhase(IntEnum):
    IDLE = 0
    ON_ISSUED = 1
    VERIFYING = 2
    REJECTED = 3
    FAULT = 4


class Terminal(IntEnum):
    NONE = 0
    REJECTED_PRESTATE = 1
    ROLLED_BACK_PREISO = 2
    ROLLBACK_FAULT_PREISO = 3
    FAULT_RETAIN_POSTISO = 4
    CPU8_ONLINE_PROOF = 5


@dataclass(frozen=True)
class Admission:
    armed: bool = True
    token_owned: bool = True
    cpu: int = 8
    target: str = "CPUHP_ONLINE"
    tasks_frozen: bool = False
    cpu8_online: bool = False
    cpu9_online: bool = False


@dataclass(frozen=True)
class Faults:
    ledger_begin: bool = False
    effect: Stage | None = None
    checkpoint: tuple[str, Stage] | None = None
    terminal: bool = False
    malformed: Stage | None = None
    provider_release: bool = False
    p27_release: bool = False


@dataclass
class Result:
    terminal: Terminal = Terminal.REJECTED_PRESTATE
    last_stage: Stage | None = None
    stage_errno: int = 0
    rollback_errno: int = 0
    checkpoint_errno: int = 0
    attempted: bool = False
    watchdog_armed: bool = False
    isolation_attempted: bool = False
    isolation_crossed: bool = False
    cpu_on_accepted: bool = False
    p27_owned: bool = False
    provider_owned: bool = False
    membership_published: bool = False
    owner_phase: OwnerPhase = OwnerPhase.IDLE
    owner_active: bool = False
    owner_members: int = 0
    owner_p27_complete: bool = False
    owner_p28_started: bool = False
    owner_p28_complete: bool = False
    owner_cpu_on_consumed: bool = False
    p32_required: bool = False
    p32_published: bool = False
    cpu8_online: bool = False
    cpu9_online: bool = False
    cpu_requests: int = 0
    cpu_off_requests: int = 0
    retries: int = 0
    checkpoints: int = 0
    terminal_commits: int = 0
    uncertain: set[str] = field(default_factory=set)
    retained: set[str] = field(default_factory=set)
    rolled_back: list[str] = field(default_factory=list)


class BinderModel:
    """One-shot split-lifecycle model with injected failures."""

    def __init__(self, faults: Faults = Faults()) -> None:
        self.faults = faults
        self.lifecycle = Lifecycle.IDLE
        self.consumed = False
        self.events: list[str] = []
        self.result = Result()

    @staticmethod
    def admission_valid(admission: Admission) -> bool:
        return (
            admission.armed
            and admission.token_owned
            and admission.cpu == 8
            and admission.target == "CPUHP_ONLINE"
            and not admission.tasks_frozen
            and not admission.cpu8_online
            and not admission.cpu9_online
        )

    def _set_retained(self) -> None:
        retained = set(self.result.uncertain)
        if self.result.p27_owned:
            retained.add("p27")
        if self.result.provider_owned:
            retained.add("provider")
        if self.result.cpu8_online:
            retained.add("cpu8")
        self.result.retained = retained

    def _terminal(self, terminal: Terminal, error: int) -> int:
        self.result.terminal = terminal
        self.result.stage_errno = error
        if terminal in (
            Terminal.REJECTED_PRESTATE,
            Terminal.ROLLED_BACK_PREISO,
        ):
            self.result.owner_active = False
            self.result.owner_phase = OwnerPhase.REJECTED
        elif terminal == Terminal.ROLLBACK_FAULT_PREISO:
            self.result.owner_phase = OwnerPhase.FAULT
        elif terminal == Terminal.FAULT_RETAIN_POSTISO:
            self.result.p32_required = True
        self._set_retained()
        self.events.append(f"terminal:{terminal.name.lower()}")
        self.result.terminal_commits += 1
        if self.faults.terminal:
            self.result.checkpoint_errno = -errno.ENOSPC
            if terminal == Terminal.CPU8_ONLINE_PROOF:
                self.result.terminal = Terminal.FAULT_RETAIN_POSTISO
                self.result.stage_errno = -errno.ENOSPC
                self.result.p32_required = True
                error = -errno.ENOSPC
        elif terminal == Terminal.CPU8_ONLINE_PROOF:
            if (
                not self.result.owner_active
                or self.result.owner_phase != OwnerPhase.VERIFYING
                or self.result.owner_members != 1
            ):
                self.result.terminal = Terminal.FAULT_RETAIN_POSTISO
                self.result.stage_errno = -errno.EPROTO
                self.result.p32_required = True
                error = -errno.EPROTO
            else:
                self.result.owner_active = False
                self.result.owner_phase = OwnerPhase.IDLE
        self.lifecycle = Lifecycle.TERMINAL
        return error

    def _publish_p32(self, error: int) -> int:
        if not error or not self.result.p32_required:
            return -errno.EINVAL
        if (
            not self.result.owner_active
            or self.result.owner_phase not in (
                OwnerPhase.ON_ISSUED,
                OwnerPhase.VERIFYING,
            )
        ):
            return -errno.EAGAIN
        self.events.append("p32:published")
        self.result.p32_required = False
        self.result.p32_published = True
        self.result.owner_phase = OwnerPhase.FAULT
        return 0

    def _checkpoint(self, phase: str, stage: Stage) -> int:
        self.result.last_stage = stage
        self.result.checkpoints += 1
        self.events.append(f"{phase}:{stage.name.lower()}")
        if self.faults.checkpoint == (phase, stage):
            self.result.checkpoint_errno = -errno.EIO
            return -errno.EIO
        return 0

    def _effect(self, stage: Stage) -> int:
        self.events.append(f"effect:{stage.name.lower()}")
        return -errno.EIO if self.faults.effect == stage else 0

    def _rollback(self, error: int) -> int:
        if self.result.provider_owned:
            self.events.append("release:provider")
            if self.faults.provider_release:
                self.result.rollback_errno = -EREMOTEIO
                return self._terminal(
                    Terminal.ROLLBACK_FAULT_PREISO, -EREMOTEIO
                )
            self.result.provider_owned = False
            self.result.rolled_back.append("provider")
        if self.result.p27_owned:
            self.events.append("release:p27")
            if self.faults.p27_release:
                self.result.rollback_errno = -EREMOTEIO
                return self._terminal(
                    Terminal.ROLLBACK_FAULT_PREISO, -EREMOTEIO
                )
            self.result.p27_owned = False
            self.result.rolled_back.append("p27")
        return self._terminal(Terminal.ROLLED_BACK_PREISO, error)

    def _postiso(self, error: int) -> int:
        return self._terminal(Terminal.FAULT_RETAIN_POSTISO, error)

    def _checkpoint_failure(self, stage: Stage, error: int) -> int:
        if stage == Stage.WATCHDOG and not self.result.watchdog_armed:
            return self._terminal(Terminal.REJECTED_PRESTATE, error)
        if not self.result.isolation_attempted:
            return self._rollback(error)
        return self._postiso(error)

    def _stage(self, stage: Stage) -> int:
        ret = self._checkpoint("before", stage)
        if ret:
            return self._checkpoint_failure(stage, ret)

        if stage == Stage.P27 and self.faults.malformed != stage:
            self.result.p27_owned = True
        elif stage == Stage.PROVIDER and self.faults.malformed != stage:
            self.result.provider_owned = True
        elif stage == Stage.ISOLATION:
            self.result.isolation_attempted = True
        elif stage == Stage.CPU_ON:
            self.result.cpu_requests += 1

        ret = self._effect(stage)
        if ret:
            if stage == Stage.WATCHDOG:
                return self._terminal(Terminal.REJECTED_PRESTATE, ret)
            if stage in (Stage.P27, Stage.PROVIDER):
                return self._rollback(ret)
            return self._postiso(ret)

        if self.faults.malformed == stage:
            if stage == Stage.WATCHDOG:
                return self._terminal(Terminal.REJECTED_PRESTATE,
                                      -errno.EPROTO)
            if stage == Stage.P27:
                self.result.uncertain.add("p27")
                return self._terminal(Terminal.ROLLBACK_FAULT_PREISO,
                                      -errno.EPROTO)
            if stage == Stage.PROVIDER:
                self.result.uncertain.add("provider")
                return self._terminal(Terminal.ROLLBACK_FAULT_PREISO,
                                      -errno.EPROTO)

        if stage == Stage.WATCHDOG:
            self.result.watchdog_armed = True
        elif stage == Stage.P27:
            self.result.owner_p27_complete = True
        elif stage == Stage.PROVIDER:
            pass
        elif stage == Stage.ISOLATION:
            self.result.isolation_crossed = True
            self.result.owner_p28_started = True
        elif stage == Stage.SRAM:
            self.result.owner_p28_complete = True
        elif stage == Stage.CPU_ON:
            self.result.cpu_on_accepted = True
            self.result.owner_cpu_on_consumed = True
        elif stage == Stage.MEMBERSHIP:
            self.result.membership_published = True
            self.result.owner_members = 1
            self.result.owner_phase = OwnerPhase.VERIFYING

        ret = self._checkpoint("after", stage)
        if ret:
            return self._checkpoint_failure(stage, ret)
        return 0

    def begin(self, admission: Admission = Admission()) -> int:
        if self.consumed or self.lifecycle != Lifecycle.IDLE:
            return -errno.EALREADY
        self.result = Result()
        if not self.admission_valid(admission):
            return -errno.EPERM
        self.consumed = True
        self.lifecycle = Lifecycle.STARTING
        self.result.attempted = True
        self.result.terminal = Terminal.NONE
        self.result.owner_active = True
        self.result.owner_phase = OwnerPhase.ON_ISSUED
        self.events.append("ledger:begin")
        if self.faults.ledger_begin:
            return self._terminal(Terminal.REJECTED_PRESTATE, -errno.EIO)

        for stage in (
            Stage.WATCHDOG,
            Stage.P27,
            Stage.PROVIDER,
            Stage.ISOLATION,
            Stage.SRAM,
            Stage.CPU_ON,
        ):
            ret = self._stage(stage)
            if ret:
                return ret
        self.lifecycle = Lifecycle.CPU_ON_ACCEPTED
        return 0

    def secondary_complete(self, cpu: int = 8, cpu8_online: bool = True,
                           cpu9_online: bool = False) -> int:
        if self.lifecycle != Lifecycle.CPU_ON_ACCEPTED:
            return -errno.EALREADY
        self.result.cpu8_online = cpu8_online
        self.result.cpu9_online = cpu9_online
        if cpu != 8 or not cpu8_online or cpu9_online:
            return self._postiso(-errno.EPROTO)
        ret = self._stage(Stage.ONLINE_WAIT)
        if ret:
            return ret
        self.lifecycle = Lifecycle.SECONDARY_COMPLETE
        return 0

    def complete(self, cpu: int = 8, cpu8_online: bool = True,
                 cpu9_online: bool = False) -> int:
        if self.lifecycle != Lifecycle.SECONDARY_COMPLETE:
            return -errno.EALREADY
        self.result.cpu8_online = cpu8_online
        self.result.cpu9_online = cpu9_online
        if cpu != 8 or not cpu8_online or cpu9_online:
            return self._postiso(-errno.EPROTO)
        for stage in (Stage.IPI, Stage.DCM, Stage.MEMBERSHIP):
            ret = self._stage(stage)
            if ret:
                return ret
        return self._terminal(Terminal.CPU8_ONLINE_PROOF, 0)

    def fail(self, error: int, cpu: int = 8, cpu8_online: bool = False,
             cpu9_online: bool = False) -> int:
        if not error:
            return -errno.EINVAL
        if self.lifecycle not in (
            Lifecycle.CPU_ON_ACCEPTED,
            Lifecycle.SECONDARY_COMPLETE,
        ):
            return -errno.EALREADY
        self.result.cpu8_online = cpu8_online
        self.result.cpu9_online = cpu9_online
        if cpu != 8 or cpu9_online or (
            self.lifecycle == Lifecycle.SECONDARY_COMPLETE and not cpu8_online
        ):
            error = -errno.EPROTO
        if self.lifecycle == Lifecycle.CPU_ON_ACCEPTED:
            ret = self._checkpoint("before", Stage.ONLINE_WAIT)
            if ret:
                error = ret
        return self._postiso(error)

    def generic_failure(self, error: int, cpu: int = 8,
                        cpu8_online: bool = False,
                        cpu9_online: bool = False) -> int:
        if not error:
            return -errno.EINVAL
        if self.lifecycle != Lifecycle.TERMINAL:
            terminal_ret = self.fail(error, cpu, cpu8_online, cpu9_online)
            if terminal_ret != error:
                error = terminal_ret
        if self.result.p32_required:
            ret = self._publish_p32(error)
            if ret:
                return ret
        return error

    def run(self, admission: Admission = Admission()) -> int:
        ret = self.begin(admission)
        if ret:
            if self.result.attempted:
                return self.generic_failure(ret)
            return ret
        ret = self.secondary_complete()
        if ret:
            return self.generic_failure(ret)
        ret = self.complete()
        if ret:
            return self.generic_failure(ret, cpu8_online=True)
        return 0
