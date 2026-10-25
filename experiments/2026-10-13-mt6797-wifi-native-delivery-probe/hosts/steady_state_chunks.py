#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Steady-state chunks for a derived throughput run: 16 MiB or 3 s per chunk,
whichever comes first, and a final-half rate beside the whole-chunk rate.

usage: steady_state_chunks.py <work-dir>   (last injection, after the probe and
the declared-chunk-count readings; before prepare)

The 1 MiB-per-chunk, 1 s protocol was set for the 6 Mbit/s era; at 54 Mbit/s
with ordinary data retired on credit arrival it truncated both directions
(boot E: TX filled 1 MiB in 0.91 s, RX in 0.45 s), so every chunk was a rate
over a window holding a large share of slow start, and the depth sweep's
predicted 26 Mbit/s would fill the cap in 0.3 s. The chunk count and the two
directions stay the same so the series stays comparable; rows measured under
the old cap are floors and say so. The device side's per-chunk command is
bounded by 4 s (one second past the laptop's duration, so a chunk that the
laptop ends by duration is never cut first by the device: on boot F the two
3 s bounds raced and a receive chunk read `device_timeout` at the device's
SIGTERM) and sends at most the cap; the SSH idle policy (30 s) and the leaf's
135 s bound hold with room.

The cap was 4 MiB through boot J, which filled it in about 2.1 s at 16.5
Mbit/s; a predicted 32 Mbit/s would fill it in about 1 s, censoring the
chunks exactly where a change is largest. At 16 MiB the 3 s duration binds
below about 45 Mbit/s, so every chunk measures steady state (from boot K).
Boot K showed the cost on receive: a duration-bound chunk keeps arriving
after the laptop's close (its send queue drains for 0.6-0.8 s), so the
device's 4 s bound races that drain (HIF section 21's result). From boot L
the device's bound is 6 s for a 3 s send, and drain_accounting.py measures
the receive chunk over the laptop's send window.
"""
import re
import sys
from pathlib import Path

work = Path(sys.argv[1])
CAP = 16 * 1024 * 1024
SECONDS = 3
DEVICE_BOUND = SECONDS + 3   # past the laptop's duration and any receive drain after its close (boot F raced at +0; boot K's drain at +1)


def literal(path, old, new, count=1):
    s = path.read_text()
    assert s.count(old) == count, (path.name, old[:60], s.count(old))
    path.write_text(s.replace(old, new))


h = work / 'hosts/throughput-helper.py'
literal(h, "DURATION = 1\n", "DURATION = %d  # steady-state chunks: %d MiB or %d s, whichever first\n" % (SECONDS, CAP >> 20, SECONDS))
literal(h, "MAX_BYTES = 1024 * 1024\n", "MAX_BYTES = %d\n" % CAP)
# the device side: the cap in zeros per transmit chunk, the device's bound on both legs
literal(h, "$BB dd if=/dev/zero bs=65536 count=16 2>/tmp/tp2-dd.log | $BB timeout 1 $BB nc HOST 48001 || rc=$?",
        "$BB dd if=/dev/zero bs=65536 count=%d 2>/tmp/tp2-dd.log | $BB timeout %d $BB nc HOST 48001 || rc=$?" % (CAP // 65536, DEVICE_BOUND))
literal(h, "n=$(set -o pipefail; $BB timeout 1 $BB nc HOST 48002 | $BB wc -c) || rc=$?",
        "n=$(set -o pipefail; $BB timeout %d $BB nc HOST 48002 | $BB wc -c) || rc=$?" % DEVICE_BOUND)
# with the device's bound past the laptop's duration, the laptop closes a transmit chunk first and the
# device's nc ends on the closed pipe with SIGPIPE (141; boot H's second run) or 1 (the first run's
# assumption): that close is the chunk's normal end on the transmit leg only; the receive leg sees a
# plain EOF (exit 0). Written as one pattern so the rendered command stays under its 4,096-byte bound.
literal(h, """        case "$rc" in 0|124|143) ;; *) exit 38;; esac
""", """        case "$rc$dir" in 0*|124*|143*|1TX|141TX) ;; *) exit 38;; esac
""")
# the laptop's verdict accepts the same transmit-leg closes (boot H's third run measured whole and read all_pass=false on them)
literal(h, "all(c.get('device_exit') in (0,124,143) for c in direction['chunks'])",
        "all(c.get('device_exit') in (0,124,143,1,141) for c in direction['chunks'])")   # the leaf itself refuses 1/141 on the receive leg
# the laptop side: progress samples every 50 ms, the rate over the final half of the chunk beside the whole-chunk rate
literal(h, "                    samples, next_sample = [], 0\n",
        "                    samples, next_sample = [], 0\n                    progress, next_progress = [], 0\n")
literal(h, "                            count += amount\n                            self.result['bytes'] += amount\n",
        "                            count += amount\n                            self.result['bytes'] += amount\n"
        "                            if time.monotonic_ns() >= next_progress:\n"
        "                                next_progress = time.monotonic_ns() + 50_000_000\n"
        "                                progress.append((time.monotonic_ns(), count))\n")
literal(h, "                    elapsed = time.monotonic_ns()-chunk_start\n",
        "                    elapsed = time.monotonic_ns()-chunk_start\n"
        "                    half = [p for p in progress if p[0] >= chunk_start + elapsed // 2]\n"
        "                    final_half = ((count - half[0][1]) * 8000 / (chunk_start + elapsed - half[0][0])\n"
        "                                  if half and chunk_start + elapsed > half[0][0] else None)\n")
literal(h, "                        'ended_by':'byte_cap' if count>=self.maximum else reason})\n",
        "                        'ended_by':'byte_cap' if count>=self.maximum else reason,\n"
        "                        'final_half_Mbit_s':final_half, 'progress_samples':len(progress)})\n")
p = work / 'hosts/throughput-prepare.py'
literal(p, "'seconds_per_chunk':1,'byte_cap_per_chunk':1048576,", "'seconds_per_chunk':%d,'byte_cap_per_chunk':%d," % (SECONDS, CAP))
r = work / 'review-installer.py'
# a work directory derived from an earlier steady-state one carries that run's record: replace whichever value it holds
for key, value in (('seconds_per_chunk', SECONDS), ('byte_cap_per_chunk', CAP)):
    old = re.findall(r"'%s': \d+," % key, r.read_text())
    assert len(old) == 1, (key, old)
    literal(r, old[0], "'%s': %d," % (key, value))
compile(h.read_text(), str(h), 'exec')
print('steady-state chunks: %d MiB or %d s each, final-half rate recorded (helper, device leaf, plan, review record)' % (CAP >> 20, SECONDS))
