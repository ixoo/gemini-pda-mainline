#!/usr/bin/env python3
"""Independent bounded model for dormant provider R01/R02."""

from dataclasses import dataclass, replace


CPU8 = 1
CPU9 = 2
NONE = 0
INFLIGHT = 1
HELD = 2
AVAILABLE = 1
CONSUMED = 2


@dataclass(frozen=True)
class Transaction:
    operation: int
    phase: str = "ON_ISSUED"
    members: int = 0
    provider_state: int = NONE
    acquire_budget: int = AVAILABLE
    p27_complete: bool = True
    p17_published: bool = True
    generation: int = 1
    cookie: int = 0xA7200001
    held_generation: int = 0
    held_cookie: int = 0
    acquire_confirmed: bool = False


@dataclass(frozen=True)
class Proof:
    operation: int
    settle_us: int
    page: int
    enabled: int
    vsel: int
    origin: int
    generation: int
    cookie: int
    held_generation: int
    held_cookie: int
    origin_generation: int


def begin(tx: Transaction) -> Transaction | None:
    if (tx.operation != CPU8 or tx.phase != "ON_ISSUED" or
            tx.members != 0 or tx.provider_state != NONE or
            tx.acquire_budget != AVAILABLE or not tx.p27_complete or
            not tx.p17_published or tx.acquire_confirmed):
        return None
    return replace(tx, acquire_budget=CONSUMED, provider_state=INFLIGHT)


def confirm(tx: Transaction, proof: Proof) -> Transaction | None:
    if (tx.provider_state != INFLIGHT or tx.acquire_budget != CONSUMED or
            tx.acquire_confirmed or proof.operation != CPU8 or
            proof.settle_us != 1000 or proof.page != 0x80 or
            proof.enabled != 1 or proof.vsel != 0x46 or proof.origin != 1 or
            proof.generation != tx.generation or proof.cookie != tx.cookie or
            not proof.held_generation or not proof.held_cookie or
            proof.origin_generation != proof.held_generation):
        return None
    return replace(tx, provider_state=HELD, held_generation=proof.held_generation,
                   held_cookie=proof.held_cookie, acquire_confirmed=True)


def main() -> None:
    inflight = begin(Transaction(CPU8))
    assert inflight is not None
    proof = Proof(CPU8, 1000, 0x80, 1, 0x46, 1,
                  inflight.generation, inflight.cookie, 2, 0xA7200101, 2)
    held = confirm(inflight, proof)
    print("claim=PARTIAL_R01_R02_PROVIDER_LEDGER")
    print("r01_inflight=%d" % (inflight is not None))
    print("r02_held=%d" % (held is not None))
    print("members=%d" % (held.members if held else -1))
    print("provider_state=%s" % (held.provider_state if held else -1))
    print("provider_calls=0")
    print("cpu_on_calls=0")
    print("status=PASS" if held and held.members == 0 else "status=FAIL")


if __name__ == "__main__":
    main()
