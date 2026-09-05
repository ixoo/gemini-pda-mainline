# SPDX-License-Identifier: MIT
"""Process-local timing receipt; never persisted or reconstructed from a timestamp.

Only the reviewed identity wrapper mints this after checking authenticated raw
output. Python callers are trusted orchestration code, not a security sandbox.
"""
from dataclasses import dataclass
import math
import time


@dataclass(frozen=True)
class LiveWindow:
    candidate: str
    boot: str
    session: str
    admission_sha256: str
    uptime: float
    monotonic_start: float
    wall_start: float

    def require(self, candidate, boot, session, admission_sha256, seconds, maximum_age=600):
        if not all(type(v) in (int, float) and math.isfinite(v) and v >= 0
                   for v in (self.uptime, self.monotonic_start, self.wall_start)):
            raise ValueError('live timing origin invalid')
        mono = time.monotonic() - self.monotonic_start
        wall = time.time() - self.wall_start
        values = (self.uptime, mono, wall)
        if not all(type(v) in (int, float) and math.isfinite(v) and v >= 0 for v in values):
            raise ValueError('live timing clock invalid or reversed')
        age = self.uptime + max(mono, wall)
        if (self.candidate != candidate or (boot is not None and self.boot != boot) or
                self.session != session or self.admission_sha256 != admission_sha256):
            raise ValueError('live timing candidate/boot/session mismatch')
        if age >= maximum_age or age + seconds >= 600:
            raise ValueError('insufficient live logger timing')
        return self.boot
