#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Receive probe: a mechanism measurement recorded beside the graded TCP numbers.

Opt-in at prepare time (TP_RECEIVE_PROBE=1). Injected into the derived
helper by exact anchors; the guard test asserts the injected helper is the
reviewed one plus exactly these blocks, and that the device script still
passes the helper's own validators. Nothing here is graded: the receipt
gains a `receive_probe` record and `all_pass` does not read it.

Three readings in one boot, before the chunk loop (the device at rest):
- one ping from the device to the laptop (three echoes, the summary line),
  and the TCP round-trip time the laptop's kernel measures on each trigger
  connection from the device at rest (one byte out, the acknowledgement
  back), as a second reading of the same quantity, plus the laptop's own
  ping to the device at rest (before the command) and in-chunk (during the
  third receive chunk): slow only under load is queueing, slow at rest is
  policy or path;
- three offered UDP rates (10, 20, 30 Mbit/s, one second each, 1400-byte
  datagrams) sent by the laptop to a closed port on the device, counted by
  the device kernel's UDP `NoPorts` counter and the interface's rx_bytes,
  with no return traffic beyond the kernel's rate-limited port-unreachable
  (one per second by default). Loss is sent minus counted, not a sequence
  gap: the device has no UDP receiver.
And during the TCP receive chunks, from the laptop's send socket: the
device's advertised window, the congestion window, the segment size and
the round-trip time (macOS TCP_CONNECTION_INFO), sampled every 50 ms and
recorded as the interval samples beside their summary. The
device's receive buffer parameters are the kernel defaults (the initramfs
sets none); the device command has a 4096-byte bound, so they are not
read there and the advertised window is the measurement.

The block is inserted only when the flag is on, so with it off the device
script is byte-identical to the reviewed one.
"""
import os
import re
import sys
from pathlib import Path

DEVICE_BLOCK = r'''printf 'TP3_PING %s\n' "$($BB timeout 6 $BB ping -c3 HOST 2>&1 | $BB tail -1)"
u() { $BB awk '/^Udp:/{l=$3}END{print l}' /proc/net/snmp; }
for r in 10 20 30; do
    a=$(u)
    $BB nc -w2 HOST 48003 </dev/null 2>/dev/null >/dev/null
    $BB sleep 1.6; printf 'TP3_UDP %s %s\n' "$r" "$(($(u)-a))"
done
'''

LAPTOP_BLOCK = '''
RP_DEVICE_BLOCK = r\'\'\'__DEVICE_BLOCK__\'\'\'

def tcp_info(sock):
    """macOS TCP_CONNECTION_INFO: the peer's advertised window and the RTT."""
    import struct
    try:
        raw = sock.getsockopt(socket.IPPROTO_TCP, 0x106, 256)
        f = struct.unpack_from('<4B12I', raw, 0)
    except (OSError, struct.error):
        return None
    return {'snd_wscale': f[1], 'rcv_wscale': f[2], 'maxseg': f[7], 'snd_cwnd': f[9],
            'peer_window': f[10], 'snd_sbbytes': f[11], 'rttcur_ms': f[13], 'srtt_ms': f[14]}


def tcp_info_summary(samples):
    samples = [s for s in samples if s]
    if not samples:
        return None
    def med(key):
        v = sorted(s[key] for s in samples); return v[len(v) // 2]
    return {'samples': len(samples), 'maxseg': samples[-1]['maxseg'],
            'rttcur_ms_samples': [s['rttcur_ms'] for s in samples],
            'peer_window_samples': [s['peer_window'] for s in samples],
            'peer_window_min': min(s['peer_window'] for s in samples),
            'peer_window_median': med('peer_window'),
            'peer_window_max': max(s['peer_window'] for s in samples),
            'snd_cwnd_median': med('snd_cwnd'), 'rttcur_ms_median': med('rttcur_ms'),
            'rttcur_ms_max': max(s['rttcur_ms'] for s in samples), 'srtt_ms_last': samples[-1]['srtt_ms']}


def laptop_ping(peer, count=3, interval=0.3):
    """The laptop's own ping to the device: at rest before the command, and
    in-chunk during the third receive chunk. The summary line and the
    parsed round-trip min/avg/max."""
    try:
        out = subprocess.run(['ping', '-c', str(count), '-i', str(interval), peer], capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.TimeoutExpired):
        return {'summary': None, 'rtt_ms': None}
    line = [l for l in out.splitlines() if 'round-trip' in l or 'rtt' in l]
    m = re.search(r'= ([0-9.]+)/([0-9.]+)/([0-9.]+)', line[-1]) if line else None
    return {'summary': line[-1] if line else (out.strip().splitlines() or [''])[-1],
            'rtt_ms': {'min': float(m[1]), 'avg': float(m[2]), 'max': float(m[3])} if m else None}


class ProbeTrigger:
    """On each TCP trigger from the device, send UDP for one second at the next
    offered rate to a closed port there (recorded, not graded)."""
    DATAGRAM = 1400

    def __init__(self, address, port, peer, target_port, rates_mbit_s):
        self.socket = socket.socket()
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((address, port))
        self.socket.listen(1)
        self.socket.settimeout(0.2)
        self.peer, self.target, self.rates = peer, (peer, target_port), list(rates_mbit_s)
        self.result = {'sends': [], 'errors': 0, 'completed': False, 'datagram_bytes': self.DATAGRAM}
        self.result['laptop_ping_at_rest'] = laptop_ping(peer)
        self.in_chunk = {}
        self.cancel = threading.Event()
        self.thread = threading.Thread(target=self.work, daemon=True)
        self.thread.start()

    def send(self, rate):
        out = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            interval = self.DATAGRAM * 8 / (rate * 1e6)
            start = time.monotonic_ns(); end = start + 1_000_000_000
            n = 0
            while not self.cancel.is_set():
                due = start + int(n * interval * 1e9)
                if due >= end:
                    break
                while time.monotonic_ns() < due:
                    pass
                out.sendto(n.to_bytes(4, 'big') + bytes(self.DATAGRAM - 4), self.target)
                n += 1
            elapsed = time.monotonic_ns() - start
        finally:
            out.close()
        return {'rate_mbit_s': rate, 'datagrams': n, 'bytes': n * self.DATAGRAM, 'elapsed_ns': elapsed,
                'offered_mbit_s': n * self.DATAGRAM * 8000 / elapsed if elapsed else None}

    def work(self):
        try:
            for rate in self.rates:
                deadline = time.monotonic() + 80
                connection = None
                while not self.cancel.is_set() and time.monotonic() < deadline:
                    try:
                        connection = self.socket.accept()[0]
                        break
                    except socket.timeout:
                        continue
                if connection is None:
                    if self.cancel.is_set(): return
                    raise TimeoutError('probe trigger deadline')
                with connection:
                    if connection.getpeername()[0] != self.peer:
                        raise ValueError('unexpected probe peer')
                    try:
                        connection.send(b'x'); time.sleep(0.08)
                        info = tcp_info(connection)
                    except OSError:
                        info = None
                    self.result.setdefault('trigger_rtt_ms', []).append(info['rttcur_ms'] if info else None)
                self.result['sends'].append(self.send(rate))
            self.result['completed'] = True
        except Exception as error:
            if not self.cancel.is_set():
                self.result.update(errors=1, error=type(error).__name__)
        finally:
            self.socket.close()

    def close(self):
        self.cancel.set()
        self.thread.join(timeout=5)
        self.result['owner_quiescent'] = not self.thread.is_alive()


def receive_probe(output, probe, endpoints):
    """The probe record: device lines, the laptop's sends, the TCP samples."""
    record = {'graded': False, 'enabled': probe is not None}
    m = re.search(rb'^TP3_PING (.*?)\\r?$', output, re.M)
    if m:
        line = m[1].decode('ascii', 'replace')
        rtt = re.search(r'= ([0-9.]+)/([0-9.]+)/([0-9.]+) ms', line)
        record['ping'] = {'summary': line, 'rtt_ms': {'min': float(rtt[1]), 'avg': float(rtt[2]), 'max': float(rtt[3])} if rtt else None}
    udp = []
    for m in re.finditer(rb'^TP3_UDP ([0-9]+) (-?[0-9]+)\\r?$', output, re.M):
        udp.append({'rate_mbit_s': int(m[1]), 'device_counted': int(m[2])})
    sends = (probe.result.get('sends', []) if probe else [])
    for entry, sent in zip(udp, sends):
        if sent.get('rate_mbit_s') == entry['rate_mbit_s']:
            entry.update(laptop_sent=sent['datagrams'], laptop_offered_mbit_s=sent.get('offered_mbit_s'),
                         delivered_mbit_s=entry['device_counted'] * probe.DATAGRAM * 8000 / sent['elapsed_ns'] if sent.get('elapsed_ns') else None,
                         loss_fraction=1 - entry['device_counted'] / sent['datagrams'] if sent['datagrams'] else None)
    record['udp'] = udp
    if probe:
        record['laptop'] = {k: v for k, v in probe.result.items() if k != 'sends'}
        t = probe.in_chunk.get('thread')
        if t: t.join(timeout=12)
        record['laptop_ping_in_chunk'] = probe.in_chunk.get('ping')
    rx = [e for e in endpoints if e.sending]
    if rx:
        record['tcp_receive_chunks'] = [c.get('tcp_info') for c in rx[0].result.get('chunks', [])]
    return record

'''

HELPER_EDITS = [
    # 1. the device block before the chunk loop
    ("trap 'printf \"TP1_END_NS=\"; clock' EXIT\nfor dir in TX RX; do\n",
     "trap 'printf \"TP1_END_NS=\"; clock' EXIT\n__RP_BLOCK__for dir in TX RX; do\n"),
    # 2. the flag, substituted when the script is built
    # the block goes in before BOOT and HOST are substituted, so its own HOST
    # tokens are bound (the first probe boot left them literal: edit order)
    (".replace('BOOT', shlex.quote(boot)).replace('HOST', shlex.quote(host))\n    return script\n",
     ".replace('__RP_BLOCK__', RP_DEVICE_BLOCK if os.environ.get('TP_RECEIVE_PROBE') == '1' else '').replace('BOOT', shlex.quote(boot)).replace('HOST', shlex.quote(host))\n    return script\n"),
    # 3. the idle validator admits the probe's one extra bounded command
    ("    bounds = [int(n) for n in re.findall(r'\\$BB timeout ([0-9]+)',script)]\n    if (len(bounds)!=2 or max(bounds)+2>=idle or\n",
     "    bounds = [int(n) for n in re.findall(r'\\$BB timeout ([0-9]+)',script)]\n    if (len(bounds) not in (2, 3) or max(bounds)+2>=idle or\n"),
    # 4. the laptop side: the trigger, the TCP sampler and the record
    ("def remote_script(boot, host):\n", LAPTOP_BLOCK + "\ndef remote_script(boot, host):\n"),
    # 5. per-chunk TCP samples on the sending endpoint
    ("                    count = 0\n                    reason = 'duration'\n",
     "                    count = 0\n                    reason = 'duration'\n                    samples, next_sample = [], 0\n"
     "                    if self.sending and ordinal == 3 and getattr(self, 'probe', None) is not None:\n"
     "                        self.probe.in_chunk['thread'] = threading.Thread(target=lambda: self.probe.in_chunk.__setitem__('ping', laptop_ping(self.peer)), daemon=True); self.probe.in_chunk['thread'].start()\n"),
    ("                            count += amount\n                            self.result['bytes'] += amount\n",
     "                            count += amount\n                            self.result['bytes'] += amount\n"
     "                            if self.sending and sys.platform == 'darwin' and time.monotonic_ns() >= next_sample:\n"
     "                                next_sample = time.monotonic_ns() + 50_000_000\n"
     "                                samples.append(tcp_info(connection))\n"),
    ("                        'ended_by':'byte_cap' if count>=self.maximum else reason})\n",
     "                        'ended_by':'byte_cap' if count>=self.maximum else reason})\n"
     "                    if samples: self.result['chunks'][-1]['tcp_info'] = tcp_info_summary(samples)\n"),
    # 6. the trigger's lifetime and the record in the receipt
    ("    endpoints = []\n    measured = {}\n",
     "    endpoints = []\n    probe = None\n    measured = {}\n"),
    ("        endpoints.append(Endpoint(host,48002,peer,True,chunks=CHUNKS))\n",
     "        endpoints.append(Endpoint(host,48002,peer,True,chunks=CHUNKS))\n"
     "        if os.environ.get('TP_RECEIVE_PROBE') == '1':\n"
     "            nonlocal_probe[0] = ProbeTrigger(host,48003,peer,48004,(10,20,30))\n"
     "            endpoints[-1].probe = nonlocal_probe[0]\n"),
    ("    original_command = M.COMMAND\n",
     "    original_command = M.COMMAND\n    nonlocal_probe = [None]\n"),
    ("        for endpoint in endpoints:\n            endpoint.close()\n",
     "        for endpoint in endpoints:\n            endpoint.close()\n        probe = nonlocal_probe[0]\n        if probe: probe.close()\n"),
    ("    counter_names = {'rx_packets','tx_packets','rx_errors','tx_errors','rx_dropped','tx_dropped'}\n",
     "    result['throughput_measurement']['receive_probe'] = receive_probe(output, probe, endpoints)\n"
     "    counter_names = {'rx_packets','tx_packets','rx_errors','tx_errors','rx_dropped','tx_dropped'}\n"),
]

PREPARE_EDITS = [
    ("    console_progress = os.environ.get('TP_CONSOLE_PROGRESS') == '1'\n",
     "    receive_probe = os.environ.get('TP_RECEIVE_PROBE') == '1'\n    console_progress = os.environ.get('TP_CONSOLE_PROGRESS') == '1'\n"),
    ("    plan = {'schema':1,'console_progress':console_progress,",
     "    plan = {'schema':1,'receive_probe':receive_probe,'receive_probe_is_graded':False,'console_progress':console_progress,"),
    ("           'TP_CONSOLE_PROGRESS':'1' if console_progress else '0',",
     "           'TP_RECEIVE_PROBE':'1' if receive_probe else '0','TP_CONSOLE_PROGRESS':'1' if console_progress else '0',"),
]


def apply(text, edits, what):
    for old, new in edits:
        if text.count(old) != 1:
            raise ValueError('receive probe: %s anchor changed: %r' % (what, old[:60]))
        text = text.replace(old, new)
    return text


def helper_edits():
    return [(o, n.replace('__DEVICE_BLOCK__', DEVICE_BLOCK)) for o, n in HELPER_EDITS]


def inject_helper(text):
    return apply(text, helper_edits(), 'helper')


def inject_prepare(text):
    return apply(text, PREPARE_EDITS, 'prepare')


def main():
    work = Path(sys.argv[1])
    for name, fn in (('throughput-helper.py', inject_helper), ('throughput-prepare.py', inject_prepare)):
        p = work / 'hosts' / name
        s = fn(p.read_text())
        compile(s, str(p), 'exec')
        p.write_text(s)
    print('receive probe injected into', work / 'hosts')


if __name__ == '__main__':
    main()
