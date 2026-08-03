#!/usr/bin/env python3
"""Pure model of the CPU8 held-online follow-up; performs no I/O."""

from dataclasses import dataclass


@dataclass
class HoldState:
    cpu8_online: bool = True
    cpu9_online: bool = False
    hps_target: int = 0
    notifier_calls: int = 0
    platform_off_calls: int = 0
    ipi_hits: int = 0
    terminal: str = "pending"


def clamp_hps(state: HoldState, cluster_min: int = 8, cluster_max: int = 9) -> int:
    if cluster_min == 8 and cluster_max == 9 and state.cpu8_online:
        state.hps_target = max(state.hps_target, 1)
    return state.hps_target


def cpu_down_entry(state: HoldState, cpu: int) -> int:
    if cpu in (8, 9):
        return -1  # -EPERM, before notifier or platform callbacks.
    state.notifier_calls += 1
    state.platform_off_calls += 1
    return 0


def ipi_sample(state: HoldState, callback_cpu: int, call_result: int = 0) -> bool:
    if (
        call_result
        or callback_cpu != 8
        or not state.cpu8_online
        or state.cpu9_online
        or state.terminal != "pending"
    ):
        state.terminal = "fault"
        return False
    state.ipi_hits += 1
    if state.ipi_hits == 2:
        state.terminal = "pass"
    return True
