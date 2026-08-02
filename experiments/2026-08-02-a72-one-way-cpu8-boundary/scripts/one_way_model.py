#!/usr/bin/env python3
"""Pure state model for the MT6797 one-way CPU8 startup boundary."""

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class State:
    cpu8_online: bool | None = False
    cpu9_online: bool = False
    spm_reset: int = 0x00010132
    isolation: int | None = 0x00000002
    pwrap_reset: bool | None = False
    buck: bool = False
    sram_verified: bool = False
    dcm: int | None = 0
    watchdog_armed: bool = True
    terminal: str = "open"


ENTRY = State()
PREISO_STAGES = ("spm-reset", "pwrap-assert", "buck-enable", "buck-settle")
POSTISO_STAGES = (
    "isolation-write",
    "isolation-readback",
    "pwrap-deassert",
    "sram-request",
    "sram-readback",
    "psci",
    "secondary",
    "dcm",
)


def exact_entry(state: State) -> bool:
    return state == ENTRY


def rollback_preiso(state: State) -> State:
    return replace(
        state,
        spm_reset=ENTRY.spm_reset,
        isolation=ENTRY.isolation,
        pwrap_reset=False,
        buck=False,
        sram_verified=False,
        dcm=0,
        terminal="rolled-back-preiso",
    )


def fault_retain(state: State, stage: str) -> State:
    isolation = state.isolation
    pwrap_reset = False
    cpu8_online = state.cpu8_online
    dcm = state.dcm
    if stage in ("isolation-write", "isolation-readback"):
        isolation = None
    if stage == "pwrap-deassert":
        pwrap_reset = None
    if stage in ("psci", "psci-reconcile", "secondary"):
        cpu8_online = None
    if stage == "dcm":
        dcm = None
    return replace(
        state,
        cpu8_online=cpu8_online,
        isolation=isolation,
        pwrap_reset=pwrap_reset,
        dcm=dcm,
        terminal=f"fault-retain-postiso:{stage}",
    )


def run(
    state: State = ENTRY,
    *,
    target: int = 8,
    fail_at: str | None = None,
    psci_result: str = "success",
    affinity: str = "on",
    secondary: bool = True,
) -> State:
    if target != 8 or not exact_entry(state):
        return replace(state, terminal="rejected-prestate")

    current = replace(state, spm_reset=0x00010133)
    if fail_at == "spm-reset":
        return rollback_preiso(current)
    current = replace(current, pwrap_reset=True)
    if fail_at == "pwrap-assert":
        return rollback_preiso(current)
    current = replace(current, buck=True)
    if fail_at in ("buck-enable", "buck-settle"):
        return rollback_preiso(current)

    if fail_at == "isolation-write":
        return fault_retain(current, fail_at)
    if fail_at == "isolation-readback":
        return fault_retain(current, fail_at)
    current = replace(current, isolation=0)
    if fail_at == "pwrap-deassert":
        return fault_retain(current, fail_at)
    current = replace(current, pwrap_reset=False)

    if fail_at == "sram-request":
        return fault_retain(current, fail_at)
    if fail_at == "sram-readback":
        return fault_retain(current, fail_at)
    current = replace(current, sram_verified=True)

    if fail_at == "psci":
        return fault_retain(current, fail_at)
    accepted = psci_result == "success" or (
        psci_result in ("already-on", "on-pending")
        and affinity == "on"
        and secondary
    )
    if not accepted:
        return fault_retain(current, "psci-reconcile")
    if fail_at == "secondary" or not secondary:
        return fault_retain(current, "secondary")

    current = replace(current, cpu8_online=True)
    if fail_at == "dcm":
        return fault_retain(current, fail_at)
    return replace(current, dcm=0x0D, terminal="cpu8-online-held")
