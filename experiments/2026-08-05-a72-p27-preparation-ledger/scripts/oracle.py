#!/usr/bin/env python3
"""Independent bounded model for the dormant P27 preparation ledger."""

from dataclasses import dataclass, replace


CPU8 = 1
CPU9 = 2
NONE = 0
HELD = 1
AVAILABLE = 1
CONSUMED = 2
STAGE_NONE = 0
STAGE_INFLIGHT = 1
STAGE_COMPLETE = 2
EFFECT_MASK = 0x7


@dataclass(frozen=True)
class Transaction:
    operation: int
    phase: str = "ON_ISSUED"
    members: int = 0
    provider_state: int = NONE
    preparation_budget: int = AVAILABLE
    stage: int = STAGE_NONE
    valid: bool = True
    generation: int = 1
    cookie: int = 0xA7200001
    p17_published: bool = True
    p27_valid: bool = False


@dataclass(frozen=True)
class Preparation:
    operation: int
    stage: int
    effect_mask: int
    generation: int
    cookie: int


def begin(transaction: Transaction) -> Transaction | None:
    if (not transaction.valid or transaction.phase != "ON_ISSUED" or
            transaction.operation != CPU8 or transaction.members != 0 or
            transaction.provider_state != NONE or
            transaction.preparation_budget != AVAILABLE or
            transaction.stage != STAGE_NONE or not transaction.p17_published):
        return None
    return replace(transaction, preparation_budget=CONSUMED,
                   stage=STAGE_INFLIGHT)


def complete(transaction: Transaction,
             preparation: Preparation) -> Transaction | None:
    if (transaction.stage != STAGE_INFLIGHT or
            transaction.preparation_budget != CONSUMED or
            preparation.operation != CPU8 or
            preparation.stage != STAGE_COMPLETE or
            preparation.effect_mask != EFFECT_MASK or
            preparation.generation != transaction.generation or
            preparation.cookie != transaction.cookie):
        return None
    return replace(transaction, stage=STAGE_COMPLETE, p27_valid=True)


def main() -> None:
    started = begin(Transaction(CPU8))
    assert started is not None
    proof = Preparation(CPU8, STAGE_COMPLETE, EFFECT_MASK,
                        started.generation, started.cookie)
    finished = complete(started, proof)
    cpu9 = begin(Transaction(CPU9))
    print("claim=PARTIAL_P27_PREPARATION_LEDGER")
    print("begin_cpu8=%d" % (started is not None))
    print("complete_cpu8=%d" % (finished is not None))
    print("cpu8_budget=%s" % (finished.preparation_budget if finished else 0))
    print("cpu8_stage=%s" % (finished.stage if finished else 0))
    print("cpu9_rejected=%d" % (cpu9 is None))
    print("provider_calls=0")
    print("cpu_on_calls=0")
    print("status=PASS" if finished and cpu9 is None else "status=FAIL")


if __name__ == "__main__":
    main()
