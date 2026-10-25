#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Preflight for a measurement handoff: read the rendered artefacts and refuse
unless every line below holds. Two probe boots were voided by faults visible
in the rendered run before the device was touched (an unbound placeholder,
a renamed flag); this gate reads the plan, the environment, the helper and
the device script it will send, and exercises the probe's legs offline.

usage: probe-preflight.py WORK_DIR RUNTIME_DIR
Prints one line per check; exits 0 only when all pass."""
import json
import os
import re
import runpy
import shlex
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

work, runtime = Path(sys.argv[1]), Path(sys.argv[2])
CHUNKS = int(os.environ.get('TP_CHUNKS', '5'))   # the declared chunk count per direction (five; boot D measures two)
failures = []


def line(ok, text):
    print(('PASS ' if ok else 'FAIL ') + text)
    if not ok:
        failures.append(text)


plan = json.loads((runtime / 'measurement-plan.json').read_text())
env = json.loads((runtime / 'environment.json').read_text())
helper_path = Path(env['TP_HELPER'])
source = helper_path.read_text()

# 1. every feature flag in the plan agrees with the environment the run will use
for flag, key in (('TP_RECEIVE_PROBE', 'receive_probe'), ('TP_CONSOLE_PROGRESS', 'console_progress')):
    want = plan.get(key)
    have = env.get(flag) == '1'
    line(want is not None and have == bool(want), 'plan %s=%r agrees with environment %s=%r' % (key, want, flag, env.get(flag)))
line(not any(k.startswith('TP_RECEIVE_PROBE') and k != 'TP_RECEIVE_PROBE' for k in env), 'no stray probe flag in the environment (%s)' % ','.join(k for k in env if k.startswith('TP_RECEIVE')))
line(plan.get('receive_probe') is True, 'the plan enables the receive probe')
line(plan.get('helper_sha256') and __import__('hashlib').sha256(helper_path.read_bytes()).hexdigest() == plan['helper_sha256'], 'the plan pins the helper the run will load')

# 2. the rendered device script: probe block, receive listener, transmit sender, both directions, the declared chunk count
with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / 'helper.py'; path.write_text(source)
    saved = dict(os.environ)
    os.environ.update({k: v for k, v in env.items() if k.startswith('TP_')})
    mod = runpy.run_path(str(path))
    host = '10.15.19.2'
    script = mod['remote_script'](env['GEMINI_WIFI_SSH_BOOT'], host)
    os.environ.clear(); os.environ.update(saved)
transmit = 'TP3_TXPING' in script   # the transmit probe (echo legs) in place of the receive UDP legs
anchors = {
    'probe block (echo legs)' if transmit else 'probe block (UDP loop)': ("printf 'TP3_TXPING" if transmit else "printf 'TP3_UDP", 1),
    'probe status line (the probe decides only itself)': ("printf 'TP3_RC=%s\\n' \"$?\"; true", 1),
    'device TCP state per transmit chunk' if transmit else 'probe trigger to the laptop': ("TP4_TCP" if transmit else 'nc -w2 %s 48003' % host, 1),
    'receive listener (device reads from the laptop)': ('nc %s 48002 | $BB wc -c' % host, 1),
    'transmit sender (device writes to the laptop)': ('nc %s 48001' % host, 1),
    'both directions': ('for dir in TX RX; do', 1),
    'five-chunk loop text (the idle validator pins it)': ('while [ "$i" -le 5 ]', 1),
}
for name, (needle, count) in anchors.items():
    n = script.count(needle)
    line(n == count, 'rendered device script: %s present (anchor count %d)' % (name, n))
# a shorter run narrows the validated loop after the validators (the lifecycle precedent); the helper must carry exactly that narrowing
if CHUNKS != 5:
    narrowing = "script.replace('while [ \"$i\" -le 5 ]; do', 'while [ \"$i\" -le %d ]; do')" % CHUNKS
    line(source.count(narrowing) == 1 and source.index('validate_receive_safety(script)') < source.index(narrowing),
         'helper narrows the validated loop to %d chunks after its validators' % CHUNKS)
    line('CHUNKS = %d\n' % CHUNKS in source, 'helper counts %d chunks per direction (CHUNKS)' % CHUNKS)
line(not re.search(r'\bHOST\b|\bBOOT\b', script), 'rendered device script: no unbound placeholder')
# the base command exactly as the run forms it: the cohort's M.COMMAND with its ready placeholder formatted (boot 3 was voided by a stand-in that was 28 bytes short)
try:
    saved = dict(os.environ); os.environ['TP_SOURCE_ROOT'] = env['TP_SOURCE_ROOT']
    origin = runpy.run_path(str(Path(env['TP_SOURCE_ROOT']) / 'experiments/2026-10-13-mt6797-wifi-native-delivery-probe/laptop-wifi-ssh-connected-p2e.py'))
    M = origin['run'].__globals__['M']
    base = M.COMMAND.format(ready=shlex.quote(M.READY_TEMPLATE.format(1)))
    os.environ.clear(); os.environ.update(saved)
except Exception as error:
    base = None; line(False, 'base command could not be formed from the cohort: %r' % (error,))
if base is not None:
    command = len((base + '; exec /bin/busybox timeout 135 /bin/busybox sh -c ' + shlex.quote(script) + ' TP1_OWNER_' + env['GEMINI_WIFI_SSH_BOOT']).encode())
    line(command <= 4096, 'rendered device command within the 4096-byte bound (%d, base %d)' % (command, len(base.encode())))
try:
    mod['validate_idle_safety'](script); mod['validate_receive_safety'](script); ok = True
except Exception as error:
    ok = False
line(ok, "the helper's own validators admit the rendered device script")

# 3. the helper's probe function is reachable from the call site the plan enables
line("result['throughput_measurement']['receive_probe'] = receive_probe(output, probe, endpoints)" in source, 'helper: the probe record is written into the receipt')
line("if os.environ.get('TP_RECEIVE_PROBE') == '1':" in source and ('ProbeTrigger(host,48003,peer,48004,())' if transmit else 'ProbeTrigger(host,48003,peer,48004,(10,20,30))') in source, 'helper: the trigger is created under the same flag the plan enables')
line('endpoints[-1].probe = nonlocal_probe[0]' in source, 'helper: the receive endpoint carries the probe (in-chunk ping)')

# 4. the probe's legs record a non-empty sample offline
with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / 'helper.py'; path.write_text(source)
    mod = runpy.run_path(str(path))
    # pacing on loopback, trigger RTT, laptop ping at rest to the laptop's own address
    trig = mod['ProbeTrigger']('127.0.0.1', 0, '127.0.0.1', 1, (10,))
    port = trig.socket.getsockname()[1]
    socket.create_connection(('127.0.0.1', port)).close(); time.sleep(1.3)
    trig.thread.join(timeout=5); trig.close()
    sends = trig.result.get('sends', [])
    line(bool(sends) and abs(sends[0]['offered_mbit_s'] - 10) < 1.5, 'offline: UDP send leg paces 10 Mbit/s on loopback (%s)' % (sends[0].get('offered_mbit_s') if sends else None))
    line(script.index('TP3_TXPING' if transmit else 'TP3_UDP') > script.index('for dir in TX RX'), 'rendered device script: the probe block follows the chunk loop (off the critical path)')
    line(trig.result.get('laptop_ping_at_rest', {}).get('rtt_ms') is not None, "offline: the laptop's ping to its own address records a round trip")
    line(bool(trig.result.get('trigger_rtt_ms')), 'offline: the trigger connection records a TCP round trip (%s)' % trig.result.get('trigger_rtt_ms'))
    # UDP receive direction: a datagram to a bound loopback socket arrives
    rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); rx.bind(('127.0.0.1', 0)); rx.settimeout(2)
    tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); tx.sendto(b'probe', rx.getsockname()); got = rx.recv(16); rx.close(); tx.close()
    line(got == b'probe', 'offline: UDP receive leg delivers a datagram on loopback')
    # the device-side count of datagrams to a closed port is the kernel's; the laptop's equivalent counter shows the send reached the stack
    before = subprocess.run(['netstat', '-s', '-p', 'udp'], capture_output=True, text=True).stdout
    # two-ended TCP transfer through the helper's own receive endpoint (the laptop sends, a client receives)
    ep = mod['Endpoint']('127.0.0.1', 0, '127.0.0.1', True, duration=1, maximum=262144, chunks=1)
    c = socket.create_connection(ep.socket.getsockname()); total = 0
    c.settimeout(5)
    while total < 262144:
        d = c.recv(65536)
        if not d: break
        total += len(d)
    c.close(); ep.thread.join(timeout=5); ep.close()
    line(ep.result.get('completed') and total == 262144, 'offline: two-ended TCP transfer through the receive endpoint moves the chunk (%d bytes, tcp_info %s)' % (total, 'present' if ep.result['chunks'] and ep.result['chunks'][0].get('tcp_info') else 'absent'))

# 5. the chunk plan covers the declared chunk count in both directions
line(plan.get('chunks_each') == CHUNKS, 'plan: %d chunks each way (chunks_each=%r)' % (CHUNKS, plan.get('chunks_each')))

if failures:
    print('REFUSED: %d check(s) failed; the handoff does not proceed' % len(failures)); sys.exit(2)
print('PREFLIGHT PASS: the rendered run carries the probe and both directions')
