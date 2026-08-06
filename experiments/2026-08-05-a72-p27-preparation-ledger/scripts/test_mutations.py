#!/usr/bin/env python3
"""Reject representative mutations of the dormant P27 ledger."""

from dataclasses import replace

from oracle import (CPU8, EFFECT_MASK, STAGE_COMPLETE, Transaction,
                    Preparation, begin, complete)


def main() -> None:
    started = begin(Transaction(CPU8))
    assert started is not None
    proof = Preparation(CPU8, STAGE_COMPLETE, EFFECT_MASK,
                        started.generation, started.cookie)
    mutations = {
        "wrong-operation": replace(proof, operation=9),
        "wrong-stage": replace(proof, stage=1),
        "missing-effect": replace(proof, effect_mask=EFFECT_MASK ^ 2),
        "stale-generation": replace(proof, generation=0),
        "stale-cookie": replace(proof, cookie=0),
        "duplicate-begin": begin(started),
    }
    rejected = 0
    for name, candidate in mutations.items():
        result = (candidate is None if name == "duplicate-begin"
                  else complete(started, candidate) is None)
        print("mutation=%s result=%s" % (name, "rejected" if result else "accepted"))
        rejected += result
    print("mutations_rejected=%d/%d" % (rejected, len(mutations)))
    print("status=PASS" if rejected == len(mutations) else "status=FAIL")


if __name__ == "__main__":
    main()
