#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run the probe's device block in a local POSIX shell against a local trigger
listener: it must emit three TP3_UDP lines, count the datagrams the listener
sends to a closed port, and exit within a bound. Needs Linux (/proc/net/snmp)
and a busybox binary (the device's own, copied from its initramfs, when the
host is arm64); elsewhere it skips visibly.

usage: probe-device-block-test.py [BUSYBOX]"""
import os
import re
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'hosts'))
import receive_probe as rp  # noqa: E402

if sys.platform != 'linux' or not Path('/proc/net/snmp').exists():
    print('SKIP device block: needs Linux with /proc/net/snmp (not checked here)'); sys.exit(2)
busybox = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/bin/busybox')
if not busybox.is_file():
    print('SKIP device block: no busybox at', busybox); sys.exit(2)

# a local trigger listener: on each connection send one second of datagrams to a closed port
lis = socket.socket(); lis.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); lis.bind(('127.0.0.1', 48003)); lis.listen(1); lis.settimeout(0.5)
sent = []
def serve():
    for _ in range(3):
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            try:
                c, _ = lis.accept(); break
            except socket.timeout:
                continue
        else:
            return
        c.close()
        out = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); n = 0; end = time.monotonic() + 1.0
        while time.monotonic() < end:
            out.sendto(bytes(1400), ('127.0.0.1', 48004)); n += 1; time.sleep(0.002)
        out.close(); sent.append(n)
t = threading.Thread(target=serve, daemon=True); t.start()

block = rp.DEVICE_BLOCK.replace('HOST', '127.0.0.1')
script = 'BB=%s\nclock() { $BB awk \'{printf "%%.0f\\n", $1*1000000000}\' /proc/uptime; }\n' % busybox + block + 'echo BLOCK_DONE\n'
with tempfile.NamedTemporaryFile('w', suffix='.sh', delete=False) as f:
    f.write(script)
start = time.monotonic()
run = subprocess.run([str(busybox), 'sh', f.name], capture_output=True, text=True, timeout=40)
elapsed = time.monotonic() - start
t.join(timeout=5)
lines = [l for l in run.stdout.splitlines() if l.startswith('TP3_UDP')]
counts = [int(re.match(r'TP3_UDP (\d+) (-?\d+)', l)[2]) for l in lines]
rc_line = [l for l in run.stdout.splitlines() if l.startswith('TP3_RC=')]
ok = (len(lines) == 3 and 'BLOCK_DONE' in run.stdout and run.returncode == 0 and elapsed < 30 and rc_line == ['TP3_RC=0']
      and len(sent) == 3 and all(c > 0 for c in counts) and all(abs(c - s) <= max(3, s // 20) for c, s in zip(counts, sent)))
print('device block: lines=%r sent=%r elapsed=%.1fs rc=%d' % (lines, sent, elapsed, run.returncode))
print(('PASS' if ok else 'FAIL') + ' device block: three TP3_UDP lines, TP3_RC=0, counts match the listener within 5 %, exits within the bound')
sys.exit(0 if ok else 1)
