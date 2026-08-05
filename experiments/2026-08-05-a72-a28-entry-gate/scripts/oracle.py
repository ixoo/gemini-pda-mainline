#!/usr/bin/env python3
"""Independent bounded oracle for the read-only A28 entry gate."""

from __future__ import annotations

from dataclasses import dataclass, replace

CPU8_UP = 1
CPU9_UP = 2
FLAGS = 0b1111
OFFLINE = 0
ONLINE = 1
NONE = 0
HELD = 2


@dataclass(frozen=True)
class Entry:
    members: int = 0
    provider: int = NONE
    online: int = 0
    cpuhp8: int = OFFLINE
    cpuhp9: int = OFFLINE
    flags: int = FLAGS
    mpidr8: int = 0x200
    mpidr9: int = 0x201


def fixture(cpu: int) -> Entry:
    if cpu == 8:
        return Entry()
    if cpu == 9:
        return Entry(members=1, provider=HELD, online=1, cpuhp8=ONLINE)
    raise ValueError(cpu)


def validate(cpu: int, target_online: bool, attempt: int, entry: Entry | None) -> str:
    if entry is None or not target_online or cpu not in (8, 9):
        return "-EINVAL"
    expected_attempt = CPU8_UP if cpu == 8 else CPU9_UP
    expected = fixture(cpu)
    if attempt != expected_attempt or entry != expected:
        return "-EPERM"
    return "OK"


def main() -> int:
    probes = [
        (8, True, CPU8_UP, fixture(8), "OK"),
        (9, True, CPU9_UP, fixture(9), "OK"),
        (7, True, CPU8_UP, fixture(8), "-EINVAL"),
        (8, False, CPU8_UP, fixture(8), "-EINVAL"),
        (8, True, CPU9_UP, fixture(8), "-EPERM"),
        (8, True, CPU8_UP, None, "-EINVAL"),
    ]
    for cpu, target_online, attempt, entry, expected in probes:
        actual = validate(cpu, target_online, attempt, entry)
        assert actual == expected, (cpu, actual, expected)

    state = {"attempts_consumed": 0, "owner": "CLOSED", "p30_changed": False}
    before = state.copy()
    assert validate(8, True, CPU8_UP, fixture(8)) == "OK"
    assert state == before
    print("claim=PARTIAL_A28_READ_ONLY_ENTRY_GATE")
    print("probes=6")
    print("valid_tuples=2")
    print("state_mutations=0")
    print("status=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
