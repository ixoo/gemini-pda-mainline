#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""One harmless production-duration lifecycle using the existing fixture harness."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import signal

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--compiler', required=True)
    parser.add_argument('--qemu', required=True)
    parser.add_argument('--work-root', required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    os.environ.update(MONITOR_TEST_CC=args.compiler, MONITOR_TEST_QEMU=args.qemu,
                      MONITOR_TEST_WORK_ROOT=args.work_root, MONITOR_TEST_FULL_DURATION='1')
    module = runpy.run_path(str(Path(__file__).with_name('test-monitor.py')))
    cls = module['MonitorTests']
    case = cls('runTest')
    try:
        cls.setUpClass()
        case.setUp()
        code, out, err, fields = case.run_case('ignore')
        case.assertEqual((code, err, int(fields['signal'])), (2, b'', signal.SIGKILL))
        case.assertIn(b'fixture-observation-boundary=202000\n', out)
        case.assertEqual((fields['reaped'], fields['identity_lost']), ('1', '0'))
        # Retain actual misses; never relax the admitted deadlines for scheduling.
        times = {k: int(fields[k]) for k in ('term_ms', 'kill_ms', 'reap_ms')}
        met = (0 <= times['term_ms'] <= 210000 and
               0 <= times['kill_ms'] <= 214000 and 0 <= times['reap_ms'] <= 215000)
        if args.output:
            args.output.mkdir(mode=0o700,exist_ok=False)
            for name,raw in [('observer.stdout',out),('observer.stderr',err),
                ('monitor.status',(case.root/'keyboard-attempt/monitor.status').read_bytes())]:
                (args.output/name).write_bytes(raw)
        here=Path(__file__).resolve().parent
        print(json.dumps({'classification': 'harmless-full-duration-lifecycle-observed',
                          'timing': times, 'status': fields, 'deadline_contract_met': met,
                          'monitor_source_sha256':hashlib.sha256((here/'monitor.c').read_bytes()).hexdigest(),
                          'fixture_source_sha256':hashlib.sha256((here/'monitor-fixture.c').read_bytes()).hexdigest(),
                          'fixture_binary_sha256':hashlib.sha256(cls.fixture.read_bytes()).hexdigest(),
                          'capture_sha256':hashlib.sha256(out).hexdigest(),
                          'device_action': 'none', 'keyboard_result': 'not-tested'}, sort_keys=True))
        if not met:
            raise ValueError('recorded full-duration deadline miss; no acceptance')
    finally:
        case.doCleanups()
        cls.doClassCleanups()

if __name__ == '__main__':
    main()
