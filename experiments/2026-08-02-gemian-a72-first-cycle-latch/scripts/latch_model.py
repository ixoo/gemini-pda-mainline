#!/usr/bin/env python3
"""Executable reference model for the CPU8 first-cycle latch."""

from dataclasses import dataclass, field


WAIT_UP = "wait-up"
CAPTURE_UP = "capture-up"
WAIT_DOWN = "wait-down"
CAPTURE_DOWN = "capture-down"
FROZEN_COMPLETE = "frozen-complete"
FROZEN_UP_FAILED = "frozen-up-failed"
FROZEN_DOWN_FAILED = "frozen-down-failed"
FROZEN_CPU9 = "frozen-cpu9"
FROZEN_PROTOCOL = "frozen-protocol"
FROZEN_OVERFLOW = "frozen-overflow"

TERMINAL = {
    FROZEN_COMPLETE,
    FROZEN_UP_FAILED,
    FROZEN_DOWN_FAILED,
    FROZEN_CPU9,
    FROZEN_PROTOCOL,
    FROZEN_OVERFLOW,
}

UP_BEGIN = "hps-up-begin"
UP_END = "hps-up-end"
DOWN_BEGIN = "hps-down-begin"
DOWN_END = "hps-down-end"


@dataclass(frozen=True)
class Event:
    cpu: int
    phase: str
    tx: int
    result: int = 0


@dataclass
class Latch:
    capacity: int = 256
    state: str = WAIT_UP
    up_tx: int = 0
    down_tx: int = 0
    overflow: int = 0
    records: list[Event] = field(default_factory=list)

    def accepts_sampling(self, cpu: int) -> bool:
        return cpu == 8 and self.state in {CAPTURE_UP, CAPTURE_DOWN}

    def _retain(self, event: Event) -> bool:
        if len(self.records) >= self.capacity:
            self.overflow = 1
            self.state = FROZEN_OVERFLOW
            return False
        self.records.append(event)
        return True

    def _freeze_protocol(self, event: Event) -> None:
        self._retain(event)
        if self.state != FROZEN_OVERFLOW:
            self.state = FROZEN_PROTOCOL

    def append(self, event: Event) -> None:
        if self.state in TERMINAL:
            return

        if self.state == WAIT_UP:
            if event.cpu == 8 and event.phase == UP_BEGIN and event.tx:
                if self._retain(event):
                    self.up_tx = event.tx
                    self.state = CAPTURE_UP
            return

        if event.cpu == 9:
            self._retain(event)
            if self.state != FROZEN_OVERFLOW:
                self.state = FROZEN_CPU9
            return

        if event.cpu != 8:
            self._freeze_protocol(event)
            return

        if self.state == CAPTURE_UP:
            if event.phase in {UP_BEGIN, DOWN_BEGIN, DOWN_END}:
                self._freeze_protocol(event)
                return
            if event.tx != self.up_tx:
                self._freeze_protocol(event)
                return
            if not self._retain(event):
                return
            if event.phase == UP_END:
                self.state = WAIT_DOWN if event.result == 0 else FROZEN_UP_FAILED
            return

        if self.state == WAIT_DOWN:
            if event.phase == DOWN_BEGIN:
                if not event.tx or event.tx == self.up_tx:
                    self._freeze_protocol(event)
                elif self._retain(event):
                    self.down_tx = event.tx
                    self.state = CAPTURE_DOWN
                return
            if event.phase in {UP_BEGIN, UP_END, DOWN_END}:
                self._freeze_protocol(event)
            return

        if self.state == CAPTURE_DOWN:
            if event.phase in {UP_BEGIN, UP_END, DOWN_BEGIN}:
                self._freeze_protocol(event)
                return
            if event.tx != self.down_tx:
                self._freeze_protocol(event)
                return
            if not self._retain(event):
                return
            if event.phase == DOWN_END:
                self.state = (
                    FROZEN_COMPLETE if event.result == 0 else FROZEN_DOWN_FAILED
                )

    def header(self) -> str:
        return (
            "abi=mt6797-a72-transition-observer-v2 "
            f"state={self.state} count={len(self.records)} "
            f"overflow={self.overflow} up_tx={self.up_tx} down_tx={self.down_tx}"
        )
