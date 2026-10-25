#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""The receive stream's state inside each chunk, on both ends.

usage: receive_stream.py <work-dir>   (after drain_accounting.py and transmit_probe.py; before prepare)

Boot M's receive chunk 5 slowed (4.83 MB in 4.05 s, one second at 218 KiB)
while frames kept arriving, so the driver's 200 ms silence rule recorded
nothing: the question is the stream's, not the frames'. Three readings need
three quantities over time:

- the device's advertised window: the laptop reads it (`snd_wnd`) but only
  after a successful send, so a blocked sender recorded nothing during the
  stall; it is now sampled every 50 ms whatever the send did, with the
  chunk-relative time and the laptop's unacknowledged backlog;
- the bytes waiting in the device's receive socket (`rx_queue`): the device
  prints it every 0.5 s from /proc/net/tcp for the established receive
  connection, stopped at the chunk's end;
- the frames arriving: 0283's per-second series already counts the bytes the
  driver delivers.

A window closing while frames arrive names the receiving application; a
window open while frames fall names the link; frames arriving while the
socket's queue and the window stay still names the stack. Recorded, not
gated.
"""
import sys
from pathlib import Path

work = Path(sys.argv[1])


def literal(path, old, new, count=1):
    s = path.read_text()
    assert s.count(old) == count, (path.name, old[:60], s.count(old))
    path.write_text(s.replace(old, new))


h = work / 'hosts/throughput-helper.py'
assert "'drain'" in h.read_text(), 'receive stream follows the drain accounting'
# device: rx_queue of the established receive connection every 0.5 s, killed at the chunk's end
literal(h, """        if [ "$dir" = TX ]; then
            $BB dd if=/dev/zero""",
        """        [ "$dir" = RX ] && { while $BB sleep .5;do $BB awk '/:BB82 /&&$4=="01"{print "TP5 '$i' "$5}' /proc/net/tcp;done & }; p=$!
        if [ "$dir" = TX ]; then
            $BB dd if=/dev/zero""")
literal(h, """        printf 'TP2_PROGRESS direction=%s chunk=%s phase=end rc=%s bytes=%s ns=' "$dir" "$i" "$rc" "$n"; clock
""", """        kill $p 2>/dev/null||:
        printf 'TP2_PROGRESS direction=%s chunk=%s phase=end rc=%s bytes=%s ns=' "$dir" "$i" "$rc" "$n"; clock
""")
# laptop: the window sampled every 50 ms even while the send blocks, with the chunk-relative time
sample = ("                            if self.sending and sys.platform == 'darwin' and time.monotonic_ns() >= next_sample:\n"
          "                                next_sample = time.monotonic_ns() + 50_000_000\n"
          "                                samples.append(tcp_info(connection))\n")
timed = ("                            if self.sending and sys.platform == 'darwin' and time.monotonic_ns() >= next_sample:\n"
         "                                next_sample = time.monotonic_ns() + 50_000_000\n"
         "                                info = tcp_info(connection)\n"
         "                                if info: info['t_ms'] = (time.monotonic_ns() - chunk_start) // 1_000_000\n"
         "                                samples.append(info)\n")
literal(h, sample, timed)
literal(h, """                        except socket.timeout:
                            continue
                        except (BrokenPipeError,ConnectionResetError) as error:""",
        """                        except socket.timeout:
""" + timed + """                            continue
                        except (BrokenPipeError,ConnectionResetError) as error:""")
literal(h, "            'snd_wnd_samples': [s['snd_wnd'] for s in samples],\n",
        "            'snd_wnd_samples': [s['snd_wnd'] for s in samples],\n"
        "            't_ms_samples': [s.get('t_ms') for s in samples],\n"
        "            'snd_sbbytes_samples': [s['snd_sbbytes'] for s in samples],\n")
# the record: the device's rx_queue samples per receive chunk
literal(h, "                if label=='RX':\n                    chunk.update(rate_basis='device received bytes over the device span')\n",
        "                if label=='RX':\n                    chunk.update(rate_basis='device received bytes over the device span')\n"
        "                    chunk['device_rx_queue_samples'] = [int(q, 16) for q in re.findall(\n"
        "                        rb'^TP5 '+str(chunk['ordinal']).encode()+rb' [0-9A-F]+:([0-9A-F]+)\\r?$', output, re.M)]\n"
        "                    chunk['device_rx_queue_interval_ms'] = 500\n")
compile(h.read_text(), str(h), 'exec')
print('receive stream: device rx_queue every 0.5 s, the laptop window every 50 ms with time, recorded not gated (helper, device leaf)')
