#!/usr/bin/env python3
"""Reject representative A36 prestate mutations."""

from dataclasses import replace

from oracle import Prestate, valid


def main() -> None:
    base = Prestate()
    mutations = {
        "bad-abi": replace(base, abi=0),
        "bad-operation": replace(base, operation=9),
        "bad-mpidr": replace(base, target_mpidr=0x201),
        "bad-entry": replace(base, entry_pa=0),
        "bad-generation": replace(base, generation=2),
        "bad-cookie": replace(base, cookie=0),
        "bad-cpu8-spm": replace(base, spm_218=0),
        "bad-cpu8-page": replace(base, page=0),
        "bad-cpu9-cluster": replace(
            base, operation=2, cpu8_online=1, cluster_dcm=0,
            target_mpidr=0x201),
        "bad-watchdog": replace(base, watchdog=0),
    }
    rejected = 0
    for name, candidate in mutations.items():
        result = "-EPERM" if not valid(candidate) else "0"
        print(f"mutation={name} result={result}")
        rejected += result == "-EPERM"
    print(f"mutations_rejected={rejected}/{len(mutations)}")
    print("status=PASS" if rejected == len(mutations) else "status=FAIL")


if __name__ == "__main__":
    main()
