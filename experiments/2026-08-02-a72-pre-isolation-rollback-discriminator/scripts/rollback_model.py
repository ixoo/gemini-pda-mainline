#!/usr/bin/env python3
"""Executable model for the CPU8 pre-isolation rollback discriminator."""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class State:
    cpu8: int = 0
    cpu9: int = 0
    page: int = 0x80
    buck: int = 0
    vsel: int = 0x46
    spm_reset: int = 0x00010132
    isolation: int = 0x2
    pwrap_reset: int = 0
    secure_zero: bool = True
    dcm: int = 0
    forbidden_events: int = 0


ENTRY = State()


@dataclass(frozen=True)
class Result:
    state: str
    final: State
    actions: tuple[str, ...]


def run(
    entry: State = ENTRY,
    *,
    buck_owned: bool = True,
    reset_owned: bool = True,
    pwrap_owned: bool = True,
    buck_disable_readback: bool = True,
    reset_restore_readback: bool = True,
    pwrap_clear_readback: bool = True,
    violate_boundary: bool = False,
) -> Result:
    if entry != ENTRY:
        return Result("rejected-prestate", entry, ())

    current = replace(entry, spm_reset=0x00010133)
    actions = ["spm-reset-release"]
    current = replace(current, pwrap_reset=1)
    actions.append("pwrap-assert")
    current = replace(current, buck=1)
    actions.extend(("buck-enable", "settled-readback", "inject-stop"))

    if violate_boundary:
        current = replace(current, isolation=0, forbidden_events=1)

    fault = bool(current.forbidden_events)
    if buck_owned and current.page == 0x80 and current.buck == 1 and current.vsel == 0x46:
        actions.append("buck-disable")
        current = replace(current, buck=0 if buck_disable_readback else 1)
        fault |= not buck_disable_readback
    else:
        actions.append("buck-retain")
        fault = True

    if reset_owned and current.isolation == 0x2 and current.spm_reset == 0x00010133:
        actions.append("spm-reset-restore")
        current = replace(
            current, spm_reset=0x00010132 if reset_restore_readback else 0x00010133
        )
        fault |= not reset_restore_readback
    else:
        actions.append("spm-reset-retain")
        fault = True

    if pwrap_owned and current.pwrap_reset == 1:
        actions.append("pwrap-deassert")
        current = replace(current, pwrap_reset=0 if pwrap_clear_readback else 1)
        fault |= not pwrap_clear_readback
    else:
        actions.append("pwrap-retain")
        fault = True

    exact = current == ENTRY
    return Result("rolled-back" if exact and not fault else "fault-retain", current, tuple(actions))
