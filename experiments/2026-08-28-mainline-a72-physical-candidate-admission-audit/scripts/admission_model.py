#!/usr/bin/env python3
"""I/O-free model of the derived CPU8 admission/controller boundary."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto


class Stage(Enum):
    BINDER_READY = auto()
    SOURCE_CAPTURE = auto()
    A34_BOOTSTRAP = auto()
    DERIVE_TRANSACTION = auto()
    P17_P18 = auto()
    ADD_CPU8 = auto()
    LEDGER_BEGIN = auto()
    WATCHDOG_TAKEOVER = auto()
    P27_FIRST_MUTATION = auto()


@dataclass(frozen=True)
class Inputs:
    binder_ready: bool = True
    source_ready: bool = True
    ready_token: bool = True
    source_exact: bool = True
    owner_pristine: bool = True
    publish_ok: bool = True
    add_cpu_ok: bool = True
    binder_ledger_ok: bool = True
    binder_watchdog_ok: bool = True


@dataclass
class Result:
    probe_ret: int
    operation_ret: int
    consumed: bool
    cpu_requests: int
    cpu_off_requests: int
    retries: int
    events: list[Stage] = field(default_factory=list)
    a36_recovery_fields: tuple[int, int, int] = (0, 0, 0)
    caller_identity_words: int = 0


class Controller:
    """One boot-local controller; errors after consumption never reprobe."""

    EPROBE_DEFER = -517
    EAGAIN = -11
    EALREADY = -114
    EPERM = -1
    EIO = -5

    def __init__(self) -> None:
        self.consumed = False

    @staticmethod
    def _terminal(operation_ret: int, events: list[Stage],
                  cpu_requests: int = 0) -> Result:
        return Result(
            probe_ret=0,
            operation_ret=operation_ret,
            consumed=True,
            cpu_requests=cpu_requests,
            cpu_off_requests=0,
            retries=0,
            events=events,
        )

    def run(self, inputs: Inputs) -> Result:
        if self.consumed:
            return self._terminal(self.EALREADY, [])

        # Driver-core deferral is allowed only before any owner mutation or
        # one-shot consumption.
        if not inputs.binder_ready or not inputs.source_ready:
            return Result(
                probe_ret=self.EPROBE_DEFER,
                operation_ret=self.EPROBE_DEFER,
                consumed=False,
                cpu_requests=0,
                cpu_off_requests=0,
                retries=0,
            )
        if not inputs.ready_token:
            return Result(
                probe_ret=self.EAGAIN,
                operation_ret=self.EAGAIN,
                consumed=False,
                cpu_requests=0,
                cpu_off_requests=0,
                retries=0,
                events=[Stage.BINDER_READY],
            )

        # Every later result is terminal for this boot, including a read-only
        # capture error. This precedes bootstrap, the first owner mutation.
        self.consumed = True
        events = [Stage.BINDER_READY, Stage.SOURCE_CAPTURE]
        if not inputs.source_exact:
            return self._terminal(self.EPERM, events)

        events.append(Stage.A34_BOOTSTRAP)
        if not inputs.owner_pristine:
            return self._terminal(self.EPERM, events)

        # The membership owner mints and binds its identity internally. The
        # three obsolete A36 caller assertions are reserved zero.
        events.append(Stage.DERIVE_TRANSACTION)
        events.append(Stage.P17_P18)
        if not inputs.publish_ok:
            return self._terminal(self.EPERM, events)

        events.append(Stage.ADD_CPU8)
        if not inputs.add_cpu_ok:
            return self._terminal(self.EIO, events, cpu_requests=1)

        events.append(Stage.LEDGER_BEGIN)
        if not inputs.binder_ledger_ok:
            return self._terminal(self.EIO, events, cpu_requests=1)

        events.append(Stage.WATCHDOG_TAKEOVER)
        if not inputs.binder_watchdog_ok:
            return self._terminal(self.EIO, events, cpu_requests=1)

        events.append(Stage.P27_FIRST_MUTATION)
        return self._terminal(0, events, cpu_requests=1)
