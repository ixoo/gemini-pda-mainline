#!/usr/bin/env python3
"""Reject representative R01/R02 provider-boundary mutations."""

from dataclasses import replace

from oracle import CPU8, Proof, Transaction, begin, confirm


def main() -> None:
    inflight = begin(Transaction(CPU8))
    assert inflight is not None
    proof = Proof(CPU8, 1000, 0x80, 1, 0x46, 1,
                  inflight.generation, inflight.cookie, 2, 0xA7200101, 2)
    mutations = {
        "wrong-operation": replace(proof, operation=9),
        "wrong-settle": replace(proof, settle_us=999),
        "wrong-page": replace(proof, page=0x00),
        "wrong-vsel": replace(proof, vsel=0x45),
        "wrong-origin": replace(proof, origin=0),
        "stale-generation": replace(proof, generation=0),
        "stale-cookie": replace(proof, cookie=0),
        "missing-held-id": replace(proof, held_cookie=0),
        "wrong-origin-generation": replace(proof, origin_generation=1),
        "duplicate-r01": begin(inflight),
    }
    rejected = 0
    for name, candidate in mutations.items():
        result = (candidate is None if name == "duplicate-r01"
                  else confirm(inflight, candidate) is None)
        print("mutation=%s result=%s" %
              (name, "rejected" if result else "accepted"))
        rejected += result
    print("mutations_rejected=%d/%d" % (rejected, len(mutations)))
    print("status=PASS" if rejected == len(mutations) else "status=FAIL")


if __name__ == "__main__":
    main()
