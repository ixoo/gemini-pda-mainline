#!/usr/bin/env python3
"""Positive and fail-closed tests for the first-cycle latch model."""

from latch_model import (
    CAPTURE_DOWN,
    CAPTURE_UP,
    DOWN_BEGIN,
    DOWN_END,
    Event,
    FROZEN_COMPLETE,
    FROZEN_CPU9,
    FROZEN_DOWN_FAILED,
    FROZEN_OVERFLOW,
    FROZEN_PROTOCOL,
    FROZEN_UP_FAILED,
    Latch,
    UP_BEGIN,
    UP_END,
    WAIT_DOWN,
    WAIT_UP,
)


def event(phase: str, tx: int, *, cpu: int = 8, result: int = 0) -> Event:
    return Event(cpu=cpu, phase=phase, tx=tx, result=result)


def start_up(latch: Latch, tx: int = 11) -> None:
    latch.append(event(UP_BEGIN, tx))
    assert latch.state == CAPTURE_UP
    assert latch.accepts_sampling(8)


def finish_up(latch: Latch, tx: int = 11, result: int = 0) -> None:
    latch.append(event("power-on-pre", tx))
    latch.append(event(UP_END, tx, result=result))


def start_down(latch: Latch, tx: int = 12) -> None:
    latch.append(event(DOWN_BEGIN, tx))
    assert latch.state == CAPTURE_DOWN
    assert latch.accepts_sampling(8)


def complete_pair(latch: Latch) -> None:
    start_up(latch)
    finish_up(latch)
    assert latch.state == WAIT_DOWN
    assert not latch.accepts_sampling(8)
    start_down(latch)
    latch.append(event("offline-final", 12))
    latch.append(event(DOWN_END, 12))


def main() -> int:
    latch = Latch()
    latch.append(event("pre-arm-noise", 1))
    latch.append(event(UP_BEGIN, 2, cpu=9))
    assert latch.state == WAIT_UP and not latch.records
    complete_pair(latch)
    assert latch.state == FROZEN_COMPLETE
    assert (latch.up_tx, latch.down_tx, latch.overflow) == (11, 12, 0)
    assert latch.records[0] == event(UP_BEGIN, 11)
    frozen = list(latch.records)
    latch.append(event(UP_BEGIN, 13))
    assert latch.records == frozen
    assert not latch.accepts_sampling(8)
    assert latch.header() == (
        "abi=mt6797-a72-transition-observer-v2 "
        "state=frozen-complete count=6 overflow=0 up_tx=11 down_tx=12"
    )

    up_failed = Latch()
    start_up(up_failed)
    finish_up(up_failed, result=-5)
    assert up_failed.state == FROZEN_UP_FAILED

    down_failed = Latch()
    start_up(down_failed)
    finish_up(down_failed)
    start_down(down_failed)
    down_failed.append(event(DOWN_END, 12, result=-16))
    assert down_failed.state == FROZEN_DOWN_FAILED

    cpu9 = Latch()
    start_up(cpu9)
    cpu9.append(event("psci-raw", 21, cpu=9))
    assert cpu9.state == FROZEN_CPU9
    assert cpu9.records[-1].cpu == 9

    wrong_tx = Latch()
    start_up(wrong_tx)
    wrong_tx.append(event("power-on-pre", 99))
    assert wrong_tx.state == FROZEN_PROTOCOL

    repeated_up = Latch()
    start_up(repeated_up)
    repeated_up.append(event(UP_BEGIN, 12))
    assert repeated_up.state == FROZEN_PROTOCOL

    reused_tx = Latch()
    start_up(reused_tx)
    finish_up(reused_tx)
    reused_tx.append(event(DOWN_BEGIN, 11))
    assert reused_tx.state == FROZEN_PROTOCOL

    incomplete = Latch()
    start_up(incomplete)
    finish_up(incomplete)
    incomplete.append(event("between-transactions-noise", 0))
    assert incomplete.state == WAIT_DOWN
    assert len(incomplete.records) == 3

    overflow = Latch(capacity=3)
    start_up(overflow)
    overflow.append(event("sample-1", 11))
    overflow.append(event("sample-2", 11))
    overflow.append(event("sample-3", 11))
    assert overflow.state == FROZEN_OVERFLOW
    assert overflow.overflow == 1 and len(overflow.records) == 3

    print("PASS: first-cycle latch model and 8 fail-closed boundaries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
