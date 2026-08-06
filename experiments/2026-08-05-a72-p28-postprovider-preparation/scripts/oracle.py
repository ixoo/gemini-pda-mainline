#!/usr/bin/env python3
"""Independent bounded model for dormant P28."""

from dataclasses import dataclass, replace


CPU8 = 1
HELD = 2
AVAILABLE = 1
CONSUMED = 2
ON_ISSUED = "ON_ISSUED"
NONE = 0
INFLIGHT = 1
COMPLETE = 2
EFFECT_MASK = 0x1F


@dataclass(frozen=True)
class Transaction:
    operation: int
    phase: str = ON_ISSUED
    members: int = 0
    provider_state: int = HELD
    p27_complete: bool = True
    provider_acquire_valid: bool = True
    p28_budget: int = AVAILABLE
    p28_stage: int = NONE
    p28_valid: bool = False
    cpu_on_budget: int = AVAILABLE
    provider_generation: int = 2
    provider_cookie: int = 0xA7200101
    generation: int = 1
    cookie: int = 0xA7200001


@dataclass(frozen=True)
class Proof:
    operation: int
    stage: int
    effect_mask: int
    isolation_from: int
    isolation_to: int
    pwrap_deasserted: int
    guard_released: int
    wait_before_us: int
    sram_mv: int
    wait_after_us: int
    selector: int
    calibration_stable: int
    calibration_valid: int
    provider_generation: int
    provider_cookie: int
    generation: int
    cookie: int


def begin(tx: Transaction) -> Transaction | None:
    if (tx.operation != CPU8 or tx.phase != ON_ISSUED or tx.members != 0 or
            tx.provider_state != HELD or not tx.p27_complete or
            not tx.provider_acquire_valid or tx.p28_budget != AVAILABLE or
            tx.p28_stage != NONE or tx.p28_valid):
        return None
    return replace(tx, p28_budget=CONSUMED, p28_stage=INFLIGHT)


def complete(tx: Transaction, proof: Proof) -> Transaction | None:
    if (tx.operation != CPU8 or tx.phase != ON_ISSUED or tx.members != 0 or
            tx.provider_state != HELD or tx.p28_budget != CONSUMED or
            tx.p28_stage != INFLIGHT or tx.p28_valid or
            proof.operation != CPU8 or proof.stage != COMPLETE or
            proof.effect_mask != EFFECT_MASK or proof.isolation_from != 0x2 or
            proof.isolation_to != 0 or proof.pwrap_deasserted != 1 or
            proof.guard_released != 1 or proof.wait_before_us != 240 or
            proof.sram_mv != 1100 or proof.wait_after_us != 240 or
            proof.selector != 0x8FB or proof.calibration_stable != 1 or
            proof.calibration_valid != 1 or
            proof.provider_generation != tx.provider_generation or
            proof.provider_cookie != tx.provider_cookie or
            proof.generation != tx.generation or proof.cookie != tx.cookie):
        return None
    return replace(tx, p28_stage=COMPLETE, p28_valid=True)


def proof_for(tx: Transaction) -> Proof:
    return Proof(CPU8, COMPLETE, EFFECT_MASK, 0x2, 0, 1, 1, 240, 1100,
                 240, 0x8FB, 1, 1, tx.provider_generation,
                 tx.provider_cookie, tx.generation, tx.cookie)


def main() -> None:
    inflight = begin(Transaction(CPU8))
    complete_tx = complete(inflight, proof_for(inflight)) if inflight else None
    print("claim=PARTIAL_P28_POSTPROVIDER_PREPARATION")
    print("p28_inflight=%d" % (inflight is not None))
    print("p28_complete=%d" % (complete_tx is not None))
    print("provider_state=%d" % (complete_tx.provider_state if complete_tx else -1))
    print("members=%d" % (complete_tx.members if complete_tx else -1))
    print("provider_calls=0")
    print("cpu_on_calls=0")
    print("status=PASS" if complete_tx and complete_tx.p28_valid else
          "status=FAIL")


if __name__ == "__main__":
    main()
