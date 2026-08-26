#!/usr/bin/env python3
"""I/O-free model for the first mainline CPU8 active transition."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


CPU8 = 8
CPU9 = 9
CPU_ON_WAIT_MS = 10_000
RECOVERY_TIMEOUT_MS = 15_000


class Stage(str, Enum):
    WATCHDOG = "watchdog"
    P27 = "p27"
    PROVIDER = "provider"
    ISOLATION = "isolation"
    SRAM = "sram"
    CPU_ON = "cpu-on"
    ONLINE_WAIT = "online-wait"
    IPI = "ipi"
    DCM = "dcm"


@dataclass
class Outcome:
    terminal: str = ""
    last_stage: str = "entry"
    checkpoints: list[str] = field(default_factory=list)
    attempted: bool = False
    watchdog_armed: bool = False
    isolation_crossed: bool = False
    p27_owned: bool = False
    provider_owned: bool = False
    cpu8_online: bool = False
    cpu9_online: bool = False
    cpu_requests: int = 0
    cpu_off_requests: int = 0
    retries: int = 0
    rollback: list[str] = field(default_factory=list)
    retained_power: list[str] = field(default_factory=list)


def _checkpoint(outcome: Outcome, phase: str, stage: Stage) -> None:
    outcome.last_stage = stage.value
    outcome.checkpoints.append(f"{phase}:{stage.value}")


def run(
    *,
    cpu: int = CPU8,
    prefix_complete: bool = True,
    fail: Stage | None = None,
    repeat: bool = False,
) -> Outcome:
    outcome = Outcome()
    if cpu != CPU8 or not prefix_complete or repeat:
        outcome.terminal = "rejected-prestate"
        return outcome

    outcome.attempted = True
    for stage in Stage:
        _checkpoint(outcome, "before", stage)
        if stage is Stage.WATCHDOG:
            if fail is stage:
                outcome.terminal = "rejected-prestate"
                return outcome
            outcome.watchdog_armed = True
        elif stage is Stage.P27:
            outcome.p27_owned = True
        elif stage is Stage.PROVIDER:
            outcome.provider_owned = True
        elif stage is Stage.ISOLATION and fail is not stage:
            outcome.isolation_crossed = True
        elif stage is Stage.CPU_ON:
            outcome.cpu_requests += 1
        elif stage is Stage.ONLINE_WAIT and fail is not stage:
            outcome.cpu8_online = True

        if fail is stage:
            if outcome.isolation_crossed or stage in (
                Stage.ISOLATION,
                Stage.SRAM,
                Stage.CPU_ON,
                Stage.ONLINE_WAIT,
                Stage.IPI,
                Stage.DCM,
            ):
                outcome.terminal = "fault-retain-postiso"
                if outcome.p27_owned:
                    outcome.retained_power.append("p27")
                if outcome.provider_owned:
                    outcome.retained_power.append("provider")
            else:
                if outcome.provider_owned:
                    outcome.rollback.append("provider")
                    outcome.provider_owned = False
                if outcome.p27_owned:
                    outcome.rollback.append("p27")
                    outcome.p27_owned = False
                outcome.terminal = "rolled-back-preiso"
            return outcome
        _checkpoint(outcome, "after", stage)

    outcome.terminal = "cpu8-online-proof"
    outcome.retained_power = ["p27", "provider", "cpu8"]
    return outcome
