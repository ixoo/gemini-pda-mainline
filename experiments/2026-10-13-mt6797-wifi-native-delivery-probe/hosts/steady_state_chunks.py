#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Steady-state chunks for a derived throughput run: 4 MiB or 3 s per chunk,
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
SIGTERM) and sends at most 4 MiB; the SSH idle policy (30 s) and the leaf's
135 s bound hold with room.
"""
import sys
from pathlib import Path

work = Path(sys.argv[1])
CAP = 4 * 1024 * 1024
SECONDS = 3
DEVICE_BOUND = SECONDS + 1   # the device's bound must outlast the laptop's duration, or the two 3 s bounds race (boot F, RX chunk 5)


def literal(path, old, new, count=1):
    s = path.read_text()
    assert s.count(old) == count, (path.name, old[:60], s.count(old))
    path.write_text(s.replace(old, new))


h = work / 'hosts/throughput-helper.py'
literal(h, "DURATION = 1\n", "DURATION = %d  # steady-state chunks: 4 MiB or 3 s, whichever first\n" % SECONDS)
literal(h, "MAX_BYTES = 1024 * 1024\n", "MAX_BYTES = %d\n" % CAP)
# the device side: 4 MiB of zeros per transmit chunk, 3 s bounds on both legs
literal(h, "$BB dd if=/dev/zero bs=65536 count=16 2>/tmp/tp2-dd.log | $BB timeout 1 $BB nc HOST 48001 || rc=$?",
        "$BB dd if=/dev/zero bs=65536 count=64 2>/tmp/tp2-dd.log | $BB timeout %d $BB nc HOST 48001 || rc=$?" % DEVICE_BOUND)
literal(h, "n=$(set -o pipefail; $BB timeout 1 $BB nc HOST 48002 | $BB wc -c) || rc=$?",
        "n=$(set -o pipefail; $BB timeout %d $BB nc HOST 48002 | $BB wc -c) || rc=$?" % DEVICE_BOUND)
# with the device's bound past the laptop's duration, the laptop closes a transmit chunk first and the
# device's nc ends on the closed pipe with SIGPIPE (141; boot H's second run) or 1 (the first run's
# assumption): that close is the chunk's normal end on the transmit leg only; the receive leg sees a
# plain EOF (exit 0). Written as one pattern so the rendered command stays under its 4,096-byte bound.
literal(h, """        case "$rc" in 0|124|143) ;; *) exit 38;; esac
""", """        case "$rc$dir" in 0*|124*|143*|1TX|141TX) ;; *) exit 38;; esac
""")
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
if "'seconds_per_chunk': %d," % SECONDS not in r.read_text():   # a work directory derived from one already on this protocol keeps its record
    literal(r, "'seconds_per_chunk': 1,", "'seconds_per_chunk': %d," % SECONDS)
    literal(r, "'byte_cap_per_chunk': 1048576,", "'byte_cap_per_chunk': %d," % CAP)
compile(h.read_text(), str(h), 'exec')
print('steady-state chunks: %d MiB or %d s each, final-half rate recorded (helper, device leaf, plan, review record)' % (CAP >> 20, SECONDS))
