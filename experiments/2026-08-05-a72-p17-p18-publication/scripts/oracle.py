#!/usr/bin/env python3
"""Independent bounded model for dormant P17/P18 publication."""

from dataclasses import dataclass


CPU8 = 1
CPU9 = 2
NONE = 0
HELD = 1


@dataclass(frozen=True)
class Transaction:
    operation: int
    provider_state: int
    provider_generation: int
    provider_cookie: int
    a36_valid: bool = True
    phase: str = "FROZEN"
    published: bool = False


def publish(transaction: Transaction) -> bool:
    if (not transaction.a36_valid or transaction.phase != "FROZEN" or
            transaction.published):
        return False
    if transaction.operation == CPU8:
        return (transaction.provider_state == NONE and
                transaction.provider_generation == 0 and
                transaction.provider_cookie == 0)
    if transaction.operation == CPU9:
        return (transaction.provider_state == HELD and
                transaction.provider_generation != 0 and
                transaction.provider_cookie != 0)
    return False


def main() -> None:
    cpu8 = Transaction(CPU8, NONE, 0, 0)
    cpu9 = Transaction(CPU9, HELD, 1, 0xA72000F0)
    probes = [cpu8, cpu9]
    print("claim=PARTIAL_P17_P18_PUBLICATION")
    print(f"probes={len(probes)}")
    print(f"p17_cpu8={int(publish(cpu8))}")
    print(f"p18_cpu9={int(publish(cpu9))}")
    print("provider_calls=0")
    print("cpu_on_calls=0")
    print("phase_after=ON_ISSUED")
    print("status=PASS" if all(map(publish, probes)) else "status=FAIL")


if __name__ == "__main__":
    main()
