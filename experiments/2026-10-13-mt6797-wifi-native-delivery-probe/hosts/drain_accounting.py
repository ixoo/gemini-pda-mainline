#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Receive chunks measured over the laptop's send window, the drain after it
recorded and excluded.

usage: drain_accounting.py <work-dir>   (after steady_state_chunks.py; before prepare)

A duration-bound receive chunk keeps arriving after the laptop stops sending:
on boot K the laptop's send queue (up to 1.8 MB at round trips of 300-370 ms)
drained for 0.6-0.8 s past its close, and the device's bound, one second past
the duration, read that drain as `device_timeout`. The device cannot time the
laptop's close itself: the end of stream reaches it behind the drain. The
laptop's own socket can, on one clock: at the close it reads the bytes still
unacknowledged (`snd_sbbytes`), so the bytes the device had acknowledged by
the close are the sent bytes less that backlog, and it polls until the backlog
is empty to time the drain. The chunk rate is the acknowledged bytes over the
send window; the drain is recorded beside it, never as a rate. The device's
own byte count and exit stay in the record. A drain longer than the limit is
recorded as incomplete; only a stall can then leave a shortfall.
"""
import sys
from pathlib import Path

work = Path(sys.argv[1])
DRAIN_LIMIT_S = 2.5   # inside the device's 6 s bound for a 3 s send


def literal(path, old, new, count=1):
    s = path.read_text()
    assert s.count(old) == count, (path.name, old[:60], s.count(old))
    path.write_text(s.replace(old, new))


h = work / 'hosts/throughput-helper.py'
assert 'DURATION = 3' in h.read_text(), 'drain accounting follows the steady-state chunks'
literal(h, "                    if samples: self.result['chunks'][-1]['tcp_info'] = tcp_info_summary(samples)\n",
        "                    if samples: self.result['chunks'][-1]['tcp_info'] = tcp_info_summary(samples)\n"
        "                    if self.sending and reason == 'duration' and sys.platform == 'darwin':\n"
        "                        # the send window closed: the backlog not yet acknowledged drains after it\n"
        "                        first = tcp_info(connection); drained = None\n"
        "                        while first and time.monotonic_ns() < chunk_start + elapsed + %d:\n"
        "                            info = tcp_info(connection)\n"
        "                            if info and info['snd_sbbytes'] == 0:\n"
        "                                drained = time.monotonic_ns(); break\n"
        "                            time.sleep(0.01)\n"
        "                        if first:\n"
        "                            acked = count - first['snd_sbbytes']\n"
        "                            self.result['chunks'][-1]['drain'] = {\n"
        "                                'bytes_acked_at_close': acked, 'bytes_after_close': first['snd_sbbytes'],\n"
        "                                'drain_ns': drained - (chunk_start + elapsed) if drained else None,\n"
        "                                'drain_complete': drained is not None, 'drain_limit_ns': %d,\n"
        "                                'send_window_ns': elapsed, 'send_window_Mbit_s': acked * 8000 / elapsed}\n"
        % (int(DRAIN_LIMIT_S * 1e9), int(DRAIN_LIMIT_S * 1e9)))
# the receive chunk's rate is the send-window rate; the device's count and elapsed stay beside it
literal(h, "                             ended_by='device_timeout' if chunk.get('device_exit') in (124,143) else\n"
           "                                      'byte_cap' if chunk.get('device_received_bytes')==MAX_BYTES else 'peer_eof')\n",
           "                             ended_by='device_timeout' if chunk.get('device_exit') in (124,143) else\n"
           "                                      'byte_cap' if chunk.get('device_received_bytes')==MAX_BYTES else 'peer_eof')\n"
           "                if label=='RX' and chunk.get('drain'):\n"
           "                    chunk.update(Mbit_s=chunk['drain']['send_window_Mbit_s'],\n"
           "                                 rate_basis='bytes the device acknowledged by the laptop close over the send window')\n")
literal(h, "'seconds_per_chunk':DURATION,", "'seconds_per_chunk':DURATION,'device_bound_seconds':DURATION+3,'drain_limit_seconds':%s," % DRAIN_LIMIT_S)
compile(h.read_text(), str(h), 'exec')
print('drain accounting: receive chunks over the send window, drain recorded up to %.1f s (helper)' % DRAIN_LIMIT_S)
