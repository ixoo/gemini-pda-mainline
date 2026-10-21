#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""P2E custody regressions, actual pipe acquisition and generated guard execution."""
import hashlib
import os
from pathlib import Path
import re
import runpy
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
probe = HERE.parent
fixture = (HERE / 'p2-client-test.py').read_text()
FIXTURE_SHA = 'e224d94027e6d64a12ef9be4e4327fb1e45c2845efaeb8a9e359c20510064c43'
if hashlib.sha256(fixture.encode()).hexdigest() != FIXTURE_SHA:
    raise ValueError('reviewed P2 client fixture changed')
fixture = fixture.replace("'laptop-wifi-ssh-connected-p2.py'",
                          "'laptop-wifi-ssh-connected-p2e.py'", 1)
fixture = fixture.replace("exec(compile(source, __file__, 'exec'), globals())",
                          'FIXTURE_SOURCE = source', 1)
state = {'__file__': __file__, '__name__': 'p2e_inherited_client_fixture'}
exec(compile(fixture, __file__, 'exec'), state)
source = state['FIXTURE_SOURCE']
anchor = '                    return subprocess.CompletedProcess(argv,control_rc,\n'
assert source.count(anchor) == 1
source = source.replace(anchor,
    "                    if control_rc == 49:\n"
    "                        return subprocess.CompletedProcess(argv,49,stdout=(\n"
    "                            f'P2_DISCONNECT_REFUSED boot={F.BOOT} before_pm_offset_ns=608000000001 lower_ns={6000000000 if early else 604000000000} upper_ns=608000000000\\n'\n"
    "                            ).encode(),stderr=b'')\n" + anchor)
exec(compile(source, __file__, 'exec'), state)
ConnectedClientTests = state['ConnectedClientTests']
S, F = state['S'], state['F']
E = runpy.run_path(str(probe / 'p2-evidence-successor.py'))


class EvidenceTests(unittest.TestCase):
    def ticks(self, count):
        return b''.join(
            f'P2_STREAM ordinal={n} boot={F.BOOT} pm_offset_ns={1_000_000_000+n*1_000_000_000}\n'.encode()
            for n in range(count))

    def reader(self, count, *, fragmented=False, timeout=False):
        data = self.ticks(count)
        program = 'import os,time\ndata=' + repr(data) + '\n'
        if fragmented:
            program += 'for start in range(0,len(data),17): os.write(1,data[start:start+17])\n'
        else:
            program += 'os.write(1,data)\n'
        if timeout:
            program += 'time.sleep(30)\n'
        with tempfile.TemporaryFile() as error:
            return S.held_stdin_runner(
                [sys.executable, '-c', program, 'HostKeyAlias=fixture'],
                stdout=subprocess.PIPE, stderr=error, timeout=0.75 if timeout else 5)

    def test_real_pipe_retains_all_602_arrivals(self):
        for fragmented in (False, True):
            with self.subTest(fragmented=fragmented):
                result = self.reader(602, fragmented=fragmented)
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stdout, self.ticks(602))
                self.assertEqual(result.p2_receive_tick_count, 602)
                self.assertEqual([row[0] for row in result.p2_receive_ticks], list(range(602)))
                clocks = [row[1] for row in result.p2_receive_ticks]
                self.assertEqual(clocks, sorted(clocks))
                # Fast local delivery does not prove the 600-second receive gate.
                self.assertLess(clocks[-1] - clocks[0], 600_000_000_000)

    def test_excess_arrival_counted_with_one_retained_sentinel(self):
        result = self.reader(605)
        self.assertEqual(result.p2_receive_tick_count, 605)
        self.assertEqual([row[0] for row in result.p2_receive_ticks], list(range(603)))
        self.assertEqual(result.stdout, self.ticks(605))

    def test_consumed_reader_reproduces_the_244_entry_defect(self):
        old = state['load']('p2_consumed_reader', probe / 'laptop-wifi-ssh-connected-p2.py')
        program = 'import os; os.write(1,' + repr(self.ticks(350)) + ')'
        with tempfile.TemporaryFile() as error:
            result = old.held_stdin_runner(
                [sys.executable, '-c', program, 'HostKeyAlias=fixture'],
                stdout=subprocess.PIPE, stderr=error, timeout=5)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.p2_receive_tick_count, 350)
        self.assertEqual(len(result.p2_receive_ticks), 244)
        corrected = self.reader(350)
        self.assertEqual(len(corrected.p2_receive_ticks), 350)

    def test_timeout_preserves_more_than_old_cap(self):
        with self.assertRaises(subprocess.TimeoutExpired) as caught:
            self.reader(350, timeout=True)
        result = caught.exception
        self.assertEqual(result.output, self.ticks(350))
        self.assertEqual(result.p2_receive_tick_count, 350)
        self.assertEqual([row[0] for row in result.p2_receive_ticks], list(range(350)))

    def test_refusal_retained_without_retry_or_success(self):
        result, wifi, controls, _ = ConnectedClientTests().exercise(control_rc=49)
        control = result['p2_core_disconnect']
        self.assertFalse(result['all_pass'])
        self.assertFalse(control['accepted'])
        self.assertEqual((wifi, controls), (1, 1))
        self.assertEqual(control['refused_pm_offset_ns'], 608_000_000_001)
        self.assertEqual(control['refused_interval_ns'], [604_000_000_000, 608_000_000_000])
        self.assertTrue(control['refusal_outside_interval'])

    def test_host_precheck_retains_existing_snapshot(self):
        result, _, controls, _ = ConnectedClientTests().exercise(late_window=True)
        self.assertEqual(controls, 0)
        control = result['p2_core_disconnect']
        self.assertEqual(control['precheck_pm_offset_ns'], 609_000_000_000)
        self.assertEqual(control['precheck_interval_ns'], [604_000_000_000, 608_000_000_000])
        self.assertFalse(control['attempted'])

    def test_refusal_identity_and_bounds_remain_required(self):
        raw = (f'P2_DISCONNECT_REFUSED boot={F.BOOT} before_pm_offset_ns=608000000001 '
               'lower_ns=604000000000 upper_ns=608000000000\n').encode()
        parse = E['disconnect_refusal']
        self.assertTrue(parse(raw, 49, F.BOOT, 604_000_000_000)['pm_interval_refusal_observed'])
        self.assertEqual(parse(raw, 0, F.BOOT, 604_000_000_000), {})
        for mutated in (raw.replace(F.BOOT.encode(), b'other-boot'),
                        raw.replace(b'lower_ns=604', b'lower_ns=603'),
                        raw.replace(b'upper_ns=608', b'upper_ns=609'), raw+b'extra\n'):
            self.assertFalse(parse(mutated, 49, F.BOOT, 604_000_000_000)['pm_interval_refusal_observed'])

    def test_origin_mutation_refused(self):
        with self.assertRaises(ValueError):
            E['client']((probe / 'laptop-wifi-ssh-connected.py').read_text()+'\n')

    @unittest.skipUnless(shutil.which('busybox'), 'Linux BusyBox fixture')
    def test_actual_disconnect_guard_boundaries_and_refused_offsets(self):
        busybox = shutil.which('busybox')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bb = root / 'bb'
            bb.write_text('''#!/bin/sh
case "$1" in
 sha256sum) printf '%s  /bin/wpa_cli\n' "$TEST_CLI_SHA" ;;
 awk)
  if [ "$3" = /proc/uptime ]; then printf '%s\n' "$TEST_NOW";
  else exec "$TEST_BUSYBOX" "$@"; fi ;;
 timeout) printf 'called\n' >> "$TEST_CALLS"; printf 'OK\n' ;;
 *) exec "$TEST_BUSYBOX" "$@" ;;
esac
''')
            bb.chmod(0o700)
            for early, lower in ((False, 604_000_000_000), (True, 6_000_000_000)):
                for offset in (lower-1, lower, 608_000_000_000, 608_000_000_001):
                    with self.subTest(early=early, offset=offset):
                        calls = root / 'calls'
                        if calls.exists():
                            calls.unlink()
                        script = S.disconnect_argument(F.BOOT, 1_000_000_000, early)
                        self.assertEqual(script.count('BB=/bin/busybox\n'), 1)
                        script = script.replace('BB=/bin/busybox\n', 'BB='+shlex.quote(str(bb))+'\n')
                        prefix = (f"cat() {{ printf '%s\\n' {shlex.quote(F.BOOT)}; }}\n"
                                  "uname() { printf '7.1.3-gemini-a53-wifi-ccmp-stable-monitor\\n'; }\n"
                                  "dmesg() { printf 'one-shot WLAN native-diag: state=2 ok\\none-shot WLAN PM credit clock: ns=1000000000\\n'; }\n")
                        env = {**os.environ, 'TEST_CLI_SHA': S.WPA_CLI_SHA,
                               'TEST_NOW': str(1_000_000_000+offset),
                               'TEST_BUSYBOX': busybox, 'TEST_CALLS': str(calls)}
                        result = subprocess.run(['/bin/sh', '-s'], input=(prefix+script).encode(),
                                                capture_output=True, env=env, timeout=5)
                        admitted = lower <= offset <= 608_000_000_000
                        self.assertEqual(result.returncode, 0 if admitted else 49, result.stderr)
                        self.assertFalse(result.stderr)
                        self.assertEqual(calls.exists(), admitted)
                        if not admitted:
                            refusal = E['disconnect_refusal'](result.stdout, 49, F.BOOT, lower)
                            self.assertEqual(refusal['refused_pm_offset_ns'], offset)


if __name__ == '__main__':
    unittest.main(verbosity=2)
