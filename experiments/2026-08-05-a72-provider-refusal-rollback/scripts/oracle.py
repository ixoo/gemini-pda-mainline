#!/usr/bin/env python3
"""Independent bounded model for dormant R03/P29."""

from dataclasses import dataclass, replace


CPU8 = 1
NONE = 0
INFLIGHT = 1
AVAILABLE = 1
CONSUMED = 2
ON_ISSUED = "ON_ISSUED"
REJECTED = "REJECTED"
P27_MASK = 0x7


@dataclass(frozen=True)
class Transaction:
    operation: int
    phase: str = ON_ISSUED
    members: int = 0
    provider_state: int = INFLIGHT
    provider_budget: int = CONSUMED
    cpu_on_budget: int = AVAILABLE
    p27_complete: bool = True
    rejection_valid: bool = False
    p29_valid: bool = False
    active: bool = True
    generation: int = 1
    cookie: int = 0xA7200001


@dataclass(frozen=True)
class Rejection:
    operation: int
    result: int
    returned: int
    vote_requested: int
    provider_mutated: int
    rail_mutated: int
    generation: int
    cookie: int


@dataclass(frozen=True)
class Rollback:
    operation: int
    restored_effect_mask: int
    residual_effect_mask: int
    p28_started: int
    cpu_on_issued: int
    generation: int
    cookie: int


def reject(tx: Transaction, proof: Rejection) -> Transaction | None:
    if (not tx.active or tx.operation != CPU8 or tx.phase != ON_ISSUED or
            tx.members != 0 or tx.provider_state != INFLIGHT or
            tx.provider_budget != CONSUMED or not tx.p27_complete or
            tx.rejection_valid or proof.operation != CPU8 or
            proof.result != 1 or proof.returned != 1 or
            proof.vote_requested or proof.provider_mutated or
            proof.rail_mutated or proof.generation != tx.generation or
            proof.cookie != tx.cookie):
        return None
    return replace(tx, provider_state=NONE, rejection_valid=True)


def rollback(tx: Transaction, proof: Rollback) -> Transaction | None:
    if (not tx.active or tx.operation != CPU8 or tx.phase != ON_ISSUED or
            tx.members != 0 or tx.provider_state != NONE or
            not tx.p27_complete or not tx.rejection_valid or tx.p29_valid or
            tx.cpu_on_budget != AVAILABLE or proof.operation != CPU8 or
            proof.restored_effect_mask != P27_MASK or
            proof.residual_effect_mask != 0 or proof.p28_started or
            proof.cpu_on_issued or proof.generation != tx.generation or
            proof.cookie != tx.cookie):
        return None
    return replace(tx, phase=REJECTED, p29_valid=True, active=False)


def main() -> None:
    tx = Transaction(CPU8)
    rejection = Rejection(CPU8, 1, 1, 0, 0, 0, tx.generation, tx.cookie)
    after_r03 = reject(tx, rejection)
    rollback_proof = Rollback(CPU8, P27_MASK, 0, 0, 0,
                               tx.generation, tx.cookie)
    after_p29 = rollback(after_r03, rollback_proof) if after_r03 else None
    print("claim=PARTIAL_R03_P29_REFUSAL_ROLLBACK")
    print("r03_provider_none=%d" % (after_r03 is not None and
                                    after_r03.provider_state == NONE))
    print("p29_rejected=%d" % (after_p29 is not None and
                               after_p29.phase == REJECTED))
    print("members=%d" % (after_p29.members if after_p29 else -1))
    print("provider_calls=0")
    print("cpu_on_calls=0")
    print("status=PASS" if after_p29 and not after_p29.active else
          "status=FAIL")


if __name__ == "__main__":
    main()
