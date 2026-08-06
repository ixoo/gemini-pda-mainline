#!/usr/bin/env python3
"""Reject representative P28 preparation mutations."""

from dataclasses import replace

from oracle import CPU8, Transaction, begin, complete, proof_for


def main() -> None:
    tx = Transaction(CPU8)
    inflight = begin(tx)
    proof = proof_for(inflight)
    mutations = {
        "wrong-operation": replace(proof, operation=9),
        "wrong-stage": replace(proof, stage=1),
        "wrong-effect-mask": replace(proof, effect_mask=0),
        "wrong-isolation-from": replace(proof, isolation_from=0),
        "wrong-isolation-to": replace(proof, isolation_to=2),
        "pwrap-not-deasserted": replace(proof, pwrap_deasserted=0),
        "guard-not-released": replace(proof, guard_released=0),
        "wrong-wait-before": replace(proof, wait_before_us=239),
        "wrong-sram-voltage": replace(proof, sram_mv=1000),
        "wrong-wait-after": replace(proof, wait_after_us=241),
        "wrong-selector": replace(proof, selector=0),
        "unstable-calibration": replace(proof, calibration_stable=0),
        "stale-provider": replace(proof, provider_cookie=0),
        "stale-generation": replace(proof, generation=0),
        "duplicate-p28": begin(inflight),
    }
    rejected = 0
    for name, candidate in mutations.items():
        result = (candidate is None if name == "duplicate-p28" else
                  complete(inflight, candidate) is None)
        print("mutation=%s result=%s" %
              (name, "rejected" if result else "accepted"))
        rejected += result
    print("mutations_rejected=%d/%d" % (rejected, len(mutations)))
    print("status=PASS" if rejected == len(mutations) else "status=FAIL")


if __name__ == "__main__":
    main()
