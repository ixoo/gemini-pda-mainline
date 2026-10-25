#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Guard for the receive-probe injection: the injected helper and prepare are
the originals plus exactly the known blocks; the device script passes the
helper's own validators with the flag on and off, fits the command bound and
parses as shell; the probe record parses a synthetic device output; the
trigger paces its offered rates on loopback. A skipped half is a skip."""
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

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'hosts'))
import receive_probe as rp  # noqa: E402

REPO = HERE.parents[2]
HELPER = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / 'artifacts/wifi-tx-rxbatch4-work/hosts/throughput-helper.py'
PREPARE = Path(sys.argv[2]) if len(sys.argv) > 2 else REPO / 'artifacts/wifi-tx-rxbatch4-work/hosts/throughput-prepare.py'
SKIPPED = []


def strip(text, edits):
    for old, new in edits:
        assert text.count(new) == 1, 'injected block not unique: %r' % new[:50]
        text = text.replace(new, old)
    return text


def check_helper():
    if not HELPER.is_file():
        print('SKIP helper: no helper at', HELPER); SKIPPED.append('helper'); return
    original = HELPER.read_text()
    injected = rp.inject_helper(original)
    assert strip(injected, rp.helper_edits()) == original, 'injected helper is not the original plus the known blocks'
    compile(injected, 'helper', 'exec')
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'throughput-helper.py'; path.write_text(injected)
        mod = runpy.run_path(str(path))
        os.environ['TP_RECEIVE_PROBE'] = '0'
        path0 = Path(tmp) / 'original.py'; path0.write_text(original)
        mod0_script = runpy.run_path(str(path0))['remote_script']('00000000-0000-4000-8000-000000000000', '192.0.2.1')
        for flag in ('0', '1'):
            os.environ['TP_RECEIVE_PROBE'] = flag
            script = mod['remote_script']('00000000-0000-4000-8000-000000000000', '192.0.2.1')
            mod['validate_idle_safety'](script); mod['validate_receive_safety'](script)
            assert ('TP3_UDP' in script) == (flag == '1')
            if flag == '0':
                assert script == mod0_script, 'flag off: device script differs from the reviewed one'
            # the base command measured at 405 bytes (M.COMMAND); 420 leaves a margin
            command = 'x' * 420 + '; exec /bin/busybox timeout 135 /bin/busybox sh -c ' + shlex.quote(script) + ' TP1_OWNER_00000000-0000-4000-8000-000000000000'
            assert len(command.encode()) <= 4096, 'device command exceeds the 4096-byte bound: %d' % len(command.encode())
            with tempfile.NamedTemporaryFile('w', suffix='.sh', delete=False) as f:
                f.write(script)
            subprocess.run(['bash', '-n', f.name], check=True)
        # the record parses a synthetic device output
        output = (b'TP3_PING round-trip min/avg/max = 3.912/4.401/5.120 ms\r\n'
                  b'TP3_UDP 10 880\r\n'
                  b'TP3_UDP 20 1700\r\n')
        class P:
            DATAGRAM = 1400
            result = {'sends': [{'rate_mbit_s': 10, 'datagrams': 893, 'elapsed_ns': 1_000_000_000, 'offered_mbit_s': 10.0},
                                {'rate_mbit_s': 20, 'datagrams': 1786, 'elapsed_ns': 1_000_000_000, 'offered_mbit_s': 20.0}], 'completed': True}
        rec = mod['receive_probe'](output, P(), [])
        assert rec['ping']['rtt_ms']['avg'] == 4.401 and len(rec['udp']) == 2
        assert rec['udp'][0]['device_counted'] == 880 and abs(rec['udp'][0]['loss_fraction'] - (1 - 880 / 893)) < 1e-9
        assert abs(rec['udp'][0]['delivered_mbit_s'] - 880 * 1400 * 8 / 1e6) < 1e-6 and rec['graded'] is False
        # the trigger paces its offered rates on loopback (a closed UDP port)
        trig = mod['ProbeTrigger']('127.0.0.1', 0, '127.0.0.1', 1, (10, 30))
        port = trig.socket.getsockname()[1]
        for _ in (10, 30):
            socket.create_connection(('127.0.0.1', port)).close(); time.sleep(1.3)
        trig.thread.join(timeout=5); trig.close()
        sends = trig.result['sends']
        assert trig.result['completed'] and [s['rate_mbit_s'] for s in sends] == [10, 30], trig.result
        for s in sends:
            assert abs(s['offered_mbit_s'] - s['rate_mbit_s']) / s['rate_mbit_s'] < 0.15, s
    print('PASS helper: original plus the known blocks; validators and command bound with the flag on and off; record parses; trigger paces within 15 %%: %s' %
          ', '.join('%d->%.1f Mbit/s' % (s['rate_mbit_s'], s['offered_mbit_s']) for s in sends))


def check_prepare():
    if not PREPARE.is_file():
        print('SKIP prepare: no prepare at', PREPARE); SKIPPED.append('prepare'); return
    original = PREPARE.read_text()
    injected = rp.inject_prepare(original)
    assert strip(injected, rp.PREPARE_EDITS) == original
    compile(injected, 'prepare', 'exec')
    print('PASS prepare: original plus the known lines; plan flag and environment pass-through')


if __name__ == '__main__':
    check_helper()
    check_prepare()
    if SKIPPED:
        print('RESULT: SKIP (%s not checked here); the other half passed' % ' and '.join(SKIPPED)); sys.exit(2)
    print('RESULT: PASS (helper and prepare)')
