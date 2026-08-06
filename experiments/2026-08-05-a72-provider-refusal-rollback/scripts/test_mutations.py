#!/usr/bin/env python3
"""Reject representative R03/P29 refusal and rollback mutations."""

from dataclasses import replace

from oracle import (CPU8, P27_MASK, Rejection, Rollback, Transaction,
                    reject, rollback)


def main() -> None:
    tx = Transaction(CPU8)
    rejection = Rejection(CPU8, 1, 1, 0, 0, 0, tx.generation, tx.cookie)
    mutations = {
        "wrong-operation": replace(rejection, operation=9),
        "wrong-result": replace(rejection, result=0),
        "not-returned": replace(rejection, returned=0),
        "vote-requested": replace(rejection, vote_requested=1),
        "provider-mutated": replace(rejection, provider_mutated=1),
        "rail-mutated": replace(rejection, rail_mutated=1),
        "stale-generation": replace(rejection, generation=0),
        "stale-cookie": replace(rejection, cookie=0),
    }
    rejected = 0
    for name, candidate in mutations.items():
        result = reject(tx, candidate) is None
        print("mutation=%s result=%s" %
              (name, "rejected" if result else "accepted"))
        rejected += result

    after_r03 = reject(tx, rejection)
    rollback_proof = Rollback(CPU8, P27_MASK, 0, 0, 0,
                               tx.generation, tx.cookie)
    rollback_mutations = {
        "wrong-effect-mask": replace(rollback_proof,
                                      restored_effect_mask=P27_MASK ^ 1),
        "residual-effect": replace(rollback_proof, residual_effect_mask=1),
        "p28-started": replace(rollback_proof, p28_started=1),
        "cpu-on-issued": replace(rollback_proof, cpu_on_issued=1),
        "rollback-stale-generation": replace(rollback_proof, generation=0),
        "rollback-stale-cookie": replace(rollback_proof, cookie=0),
        "duplicate-p29": rollback(rollback(after_r03, rollback_proof),
                                   rollback_proof),
    }
    for name, candidate in rollback_mutations.items():
        result = (candidate is None if name == "duplicate-p29" else
                  rollback(after_r03, candidate) is None)
        print("mutation=%s result=%s" %
              (name, "rejected" if result else "accepted"))
        rejected += result

    total = len(mutations) + len(rollback_mutations)
    print("mutations_rejected=%d/%d" % (rejected, total))
    print("status=PASS" if rejected == total else "status=FAIL")


if __name__ == "__main__":
    main()
