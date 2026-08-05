#!/usr/bin/env python3
"""Reject representative P17/P18 publication mutations."""

from dataclasses import replace

from oracle import CPU8, CPU9, HELD, NONE, Transaction, publish


def main() -> None:
    cpu8 = Transaction(CPU8, NONE, 0, 0)
    cpu9 = Transaction(CPU9, HELD, 1, 0xA72000F0)
    mutations = {
        "a36-missing": replace(cpu8, a36_valid=False),
        "wrong-phase": replace(cpu8, phase="IDLE"),
        "duplicate-p17": replace(cpu8, published=True),
        "p17-provider-held": replace(cpu8, provider_state=HELD,
                                      provider_generation=1,
                                      provider_cookie=0xA72000F0),
        "p18-provider-none": replace(cpu9, provider_state=NONE,
                                      provider_generation=0,
                                      provider_cookie=0),
        "p18-provider-generation": replace(cpu9, provider_generation=0),
        "p18-provider-cookie": replace(cpu9, provider_cookie=0),
        "wrong-operation": replace(cpu8, operation=9),
    }
    rejected = 0
    for name, candidate in mutations.items():
        result = "-EPERM" if not publish(candidate) else "0"
        print(f"mutation={name} result={result}")
        rejected += result == "-EPERM"
    print(f"mutations_rejected={rejected}/{len(mutations)}")
    print("status=PASS" if rejected == len(mutations) else "status=FAIL")


if __name__ == "__main__":
    main()
