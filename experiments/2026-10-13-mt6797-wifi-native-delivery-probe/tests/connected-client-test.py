#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Actual frozen verifier/retention with P1 stream/control; fake I/O only."""
import importlib.util
import contextlib
import io
import json
import types
import os
import re
import select
import shlex
import signal
import sys
import time
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch, Mock

HERE = Path(__file__).resolve().parent

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

S = load('p1_test_source', HERE.parent / 'laptop-wifi-ssh-connected.py')
F = load('p1_frozen_observation_fixture', HERE / 'ssh-observation-test.py')

class ConnectedClientTests(unittest.TestCase):
    def assert_clock_awk(self, command):
        programs = re.findall(r"awk '([^']*)'", command)
        self.assertTrue(programs)
        for program in programs:
            if 'PM credit clock' in program:
                raw = b'one-shot WLAN PM credit clock: ns=1000000000\n'
                expected = b'1000000000\n'
            else:
                raw, expected = b'1.25 0.0\n', b'1250000000\n'
            result = subprocess.run(['awk', program], input=raw, capture_output=True, check=True)
            self.assertEqual(result.stdout, expected)

    def exercise(self, ssh_rc=0, closed=False, bad_clock=False, control_rc=0, control_timeout=False, remote_unknown=False, buffered=False, receive_gap=False, early=False):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'ssh-client-observation'
            clock, wifi, controls = [0.0], [], []
            original_command = S.M.COMMAND
            S.R.D.O.C.MARKERS.clear()
            original_observer = S.R.D.O.observing_runner
            ticks = b''.join((f'P1_STREAM ordinal={i} boot={F.BOOT} pm_offset_ns={1000000000 + i * 500000000} clock_resolution_ns=10000000\n').encode() for i in range(243))

            def runner(argv, **kwargs):
                if argv[0] == '/usr/sbin/netstat':
                    return subprocess.CompletedProcess(argv, 0, stdout=b'Internet:\n')
                if argv[0] == '/usr/sbin/arp':
                    return subprocess.CompletedProcess(argv, 0, stdout=b'fixture neighbor\n')
                if any(a.startswith('HostKeyAlias=') for a in argv):
                    wifi.append(argv)
                    self.assertEqual(kwargs['timeout'], 135.0)
                    self.assertIn('P1_STREAM', argv[-1])
                    self.assertIn('-tt', argv)
                    self.assertNotIn('-T', argv)
                    self.assertNotIn('stdin', kwargs)
                    self.assertIn('timeout 125', argv[-1])
                    self.assertIn('sleep 0.05', argv[-1])
                    kwargs['stderr'].write(b'' if not ssh_rc else b'ssh: fixture failure\n')
                    clock[0] += (12.1 if early else 127.1 if receive_gap else 122.1)
                    owned = f'P1_OWNED_TTY boot={F.BOOT} owned_group=1 tag=P1_STREAM_OWNER_{F.BOOT}\n'.encode()
                    response = subprocess.CompletedProcess(argv, ssh_rc, stdout=(F.SERVED+owned+ticks).replace(b'\n',b'\r\n') if not ssh_rc else b'')
                    response.p1_receive_ticks = [[i,0 if buffered else i*500000000+(4000000000 if receive_gap and i>=100 else 0)] for i in range(243)] if not ssh_rc else []
                    response.p1_receive_tick_count = len(response.p1_receive_ticks)
                    return response
                if 'P1_REMOTE boot=' in argv[-1]:
                    if remote_unknown:
                        return subprocess.CompletedProcess(argv, 255, stdout=b'', stderr=b'fixture refusal')
                    self.assertNotIn('P1_STREAM_OWNER_' + F.BOOT, argv[-1])
                    subprocess.run(['/bin/sh', '-n'], input=argv[-1].encode(), check=True)
                    return subprocess.CompletedProcess(argv, 0, stdout=(f'P1_REMOTE boot={F.BOOT} pm_offset_ns=124000000000 owner_count=0 proc_cap=512 cmd_cap=4096\n').encode(), stderr=b'')
                if '/bin/wpa_cli -p /tmp/wpa -i wlan0 disconnect' in argv[-1]:
                    controls.append(argv)
                    self.assertEqual(kwargs['timeout'], 15)
                    self.assertIn('timeout 3 /bin/wpa_cli', argv[-1])
                    self.assertNotIn('sleep', argv[-1])
                    if control_timeout:
                        raise subprocess.TimeoutExpired(argv, 15, output=b'partial')
                    before,after=(13200000000,13500000000) if early else (123200000000,123500000000)
                    return subprocess.CompletedProcess(argv,control_rc,
                        stdout=(f'P1_DISCONNECT boot={F.BOOT} before_pm_offset_ns={before}\n'
                                f'P1_DISCONNECT_RESULT exit=0 after_pm_offset_ns={after} reply_ok=1\n').encode(),stderr=b'')
                result = F.PROBE
                if closed:
                    result = result.replace(b'FATAL=0', b'FATAL=1')
                if 'DATA_ENDED=' in argv[-1]:
                    subprocess.run(['/bin/sh', '-n'], input=argv[-1].encode(), check=True)
                    self.assert_clock_awk(argv[-1])
                    result += b'DATA_ENDED=0\nP1_PM_NS=' + (b'bad' if bad_clock else b'1000000000') + b'\nP1_NOW_NS=' + (b'14000000000\n' if early else b'124000000000\n')
                return subprocess.CompletedProcess(argv, 0, stdout=result)

            with patch.object(S.M, 'base_command', lambda keys: (['ssh', '-T'], 'root@10.0.0.1')), \
                    patch.object(S.R.D.O, 'observing_runner', lambda root, runner: original_observer(root, runner, monotonic_ns=lambda: int(clock[0] * 1e9))):
                result = S.run(root, Path('/unused'), F.BOOT, 1, 210, runner=runner,
                               monotonic=lambda: clock[0], sleep=lambda n: clock.__setitem__(0, clock[0] + n))
            self.assertEqual(S.M.COMMAND, original_command)
            return result, len(wifi), len(controls), clock[0]

    def test_stream_and_one_core_disconnect(self):
        result, wifi, controls, elapsed = self.exercise()
        self.assertTrue(result['all_pass'])
        self.assertTrue(result['p1_stream']['pass'])
        self.assertTrue(result['p1_core_disconnect']['accepted'])
        self.assertEqual((wifi, controls), (1, 1))
        self.assertGreater(elapsed, 121)
        self.assertFalse(result['p1_60s_budget_pass_claimed'])

    def test_ssh_failure_does_not_suppress_independent_control(self):
        result, wifi, controls, _ = self.exercise(ssh_rc=255)
        self.assertFalse(result['all_pass'])
        self.assertFalse(result['p1_stream']['pass'])
        self.assertTrue(result['p1_core_disconnect']['accepted'])
        self.assertEqual((wifi, controls), (1, 1))

    def test_failed_ssh_aborts_early_without_waiting_for_completed_stream_window(self):
        result,wifi,controls,elapsed=self.exercise(ssh_rc=255,early=True)
        self.assertEqual((wifi,controls),(1,1))
        self.assertLess(elapsed,20)
        self.assertFalse(result['all_pass'])
        self.assertTrue(result['p1_core_disconnect']['accepted'])
        self.assertEqual(result['p1_core_disconnect']['kind'],'abort_after_incomplete_stream')

    def test_unknown_remote_owner_prevents_control(self):
        result, wifi, controls, _ = self.exercise(remote_unknown=True)
        self.assertFalse(result['all_pass'])
        self.assertFalse(result['p1_remote_stream_quiescence']['quiesced'])
        self.assertEqual(len(result['p1_remote_stream_quiescence']['queries']), 1)
        self.assertEqual((wifi, controls), (1, 0))

    def test_closed_window_has_no_effect(self):
        result, wifi, controls, _ = self.exercise(closed=True)
        self.assertFalse(result['all_pass'])
        self.assertEqual((wifi, controls), (0, 0))

    def test_missing_clock_never_controls(self):
        result, wifi, controls, _ = self.exercise(bad_clock=True)
        self.assertFalse(result['all_pass'])
        self.assertEqual((wifi, controls), (1, 0))

    def test_control_refusal_is_not_retried(self):
        result, wifi, controls, _ = self.exercise(control_rc=49)
        self.assertFalse(result['all_pass'])
        self.assertEqual((wifi, controls), (1, 1))

    def test_control_timeout_is_not_retried(self):
        result, wifi, controls, _ = self.exercise(control_timeout=True)
        self.assertFalse(result['all_pass'])
        self.assertTrue(result['p1_core_disconnect']['timeout'])
        self.assertEqual((wifi, controls), (1, 1))

    def test_real_child_stdin_is_held_open_and_output_retained(self):
        program = "import select,sys; print('EOF' if select.select([sys.stdin],[],[],0.1)[0] else 'HELD')"
        with tempfile.TemporaryFile() as error:
            result = S.held_stdin_runner([sys.executable, '-c', program, 'HostKeyAlias=fixture'],
                                        stdout=subprocess.PIPE, stderr=error, timeout=2)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b'HELD\n')
        self.assertEqual(result.p1_stdout_total, 5)

    def test_real_child_timeout_keeps_partial_output(self):
        program = "import time; print('START',flush=True); time.sleep(2)"
        with tempfile.TemporaryFile() as error:
            with self.assertRaises(subprocess.TimeoutExpired) as caught:
                S.held_stdin_runner([sys.executable, '-c', program, 'HostKeyAlias=fixture'],
                                    stdout=subprocess.PIPE, stderr=error, timeout=0.2)
        self.assertEqual(caught.exception.output, b'START\n')

    @unittest.skipUnless(sys.platform.startswith('linux'), 'Linux PTY/proc contract')
    def test_actual_owned_pty_guard_and_hangup(self):
        import pty
        command = S.stream_command(F.BOOT).format(ready="'/tmp/fixture-ready'")
        inner = shlex.split(command[command.index('exec /bin/busybox timeout 125'):])[-1]
        guard = inner[:inner.index('# shellcheck disable=SC2016')].replace('BB=/bin/busybox', 'BB=')
        pid, fd = pty.fork()
        if pid == 0:
            os.execv('/bin/sh', ['/bin/sh', '-c', guard + "\nprintf 'OWN_READY\\n'; sleep 2"])
        reaped = False
        try:
            self.assertTrue(select.select([fd], [], [], 3)[0])
            self.assertIn(b'OWN_READY', os.read(fd, 1024))
            os.close(fd); fd = -1
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                done, status = os.waitpid(pid, os.WNOHANG)
                if done:
                    reaped = True
                    self.assertTrue(os.WIFSIGNALED(status) or os.WEXITSTATUS(status) == 37)
                    break
                time.sleep(0.05)
            self.assertTrue(reaped, 'owned PTY child did not stop on hangup')
        finally:
            if fd != -1:
                os.close(fd)
            if not reaped:
                # The unreaped child PID reserves this test-owned group identity.
                try:
                    os.killpg(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                os.waitpid(pid, 0)

    def test_actual_generated_awk_programs(self):
        command = S.stream_command(F.BOOT).format(ready="'/tmp/fixture-ready'")
        offset = command.index('exec /bin/busybox timeout 125')
        self.assert_clock_awk(command[:offset])
        self.assert_clock_awk(shlex.split(command[offset:])[-1])
        self.assert_clock_awk(S.disconnect_argument(F.BOOT, 1000000000))
        self.assert_clock_awk(S.remote_quiescence_argument(F.BOOT))


    def test_buffered_output_does_not_prove_sustained_receive(self):
        result, wifi, controls, _ = self.exercise(buffered=True)
        self.assertFalse(result['all_pass'])
        self.assertFalse(result['p1_stream']['receive_continuity_pass'])
        self.assertEqual((wifi,controls),(1,1))
        self.assertEqual(result['p1_core_disconnect']['kind'],'abort_after_incomplete_stream')

    def test_receive_stall_is_retained_as_a_separate_failure(self):
        result, wifi, controls, _ = self.exercise(receive_gap=True)
        self.assertFalse(result['p1_stream']['receive_continuity_pass'])
        self.assertEqual(result['p1_stream']['host_receive_max_gap_ns'],4500000000)
        self.assertEqual((wifi,controls),(1,1))

    def test_reader_consumes_first_line_before_child_can_finish(self):
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryFile() as error:
            seen=Path(d)/'seen'
            line=f'P1_STREAM ordinal=0 boot={F.BOOT} pm_offset_ns=1000000000 clock_resolution_ns=10000000\r\n'
            original=S.TICK
            class Observe:
                def fullmatch(self,data):
                    match=original.fullmatch(data)
                    if match:seen.write_text('observed')
                    return match
            program=('import sys,time,pathlib; sys.stdout.write('+repr(line)+'); sys.stdout.flush(); '
                     'p=pathlib.Path('+repr(str(seen))+'); end=time.monotonic()+1\n'
                     'while not p.exists() and time.monotonic()<end: time.sleep(.01)\n'
                     'sys.exit(0 if p.exists() else 2)')
            with patch.object(S,'TICK',Observe()):
                result=S.held_stdin_runner([sys.executable,'-c',program,'HostKeyAlias=fixture'],
                                           stdout=subprocess.PIPE,stderr=error,timeout=2)
            self.assertEqual(result.returncode,0)
            self.assertEqual(result.p1_receive_tick_count,1)
            self.assertEqual(result.p1_receive_ticks[0][0],0)

    def test_real_reader_caps_storage_and_drains_large_output(self):
        with tempfile.TemporaryFile() as error:
            result=S.held_stdin_runner([sys.executable,'-c','import sys; sys.stdout.write("x"*70000)',
                                       'HostKeyAlias=fixture'],stdout=subprocess.PIPE,stderr=error,timeout=2)
        self.assertEqual(result.returncode,0)
        self.assertEqual(len(result.stdout),65536)
        self.assertEqual(result.p1_stdout_total,70000)
        self.assertTrue(result.p1_output_overlong_line)

    def test_frozen_auth_ack_and_cli_bytecode_changes_only_limits(self):
        for text,name,mapping in [(S.FROZEN_CYCLE,'run_cycle',{25.0:135.0}),
                                  (S.FROZEN_MAIN,'main',{120:210})]:
            code=next(c for c in compile(text,'frozen-fixture','exec').co_consts
                      if isinstance(c,types.CodeType) and c.co_name==name)
            current=getattr(S.M,name).__code__
            self.assertEqual(code.co_code,current.co_code)
            expected=tuple(mapping.get(c,c) if isinstance(c,(int,float)) else
                           c.replace('120','210') if name=='main' and isinstance(c,str) else c
                           for c in code.co_consts)
            self.assertEqual(expected,current.co_consts)

    def test_actual_cli_accepts_only_owned_p1_and_long_poll(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve();session=root/'ccmp-stable-monitor'/S.SESSION
            session.mkdir(parents=True);receipt=session/'wifi-ssh-receipt.json'
            keys=root/'keys';keys.mkdir();(keys/'admin').write_text('fixture');(keys/'known_hosts').write_text('fixture')
            run=Mock(return_value={'boot_id':F.BOOT,'cycles_expected':1,'cycles':[], 'all_pass':True})
            argv=['p1.py',str(keys),F.BOOT,'--cycles','1','--poll-seconds','210','--receipt',str(receipt)]
            with patch.dict(os.environ,{'GEMINI_RUNTIME_ROOT':str(root)}), \
                    patch.object(sys,'argv',argv),patch.object(sys,'platform','darwin'), \
                    patch.object(S,'run',run),patch.object(S.subprocess,'run',side_effect=AssertionError('no commands')), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(S.main(),0)
                self.assertEqual(run.call_args.args[2:],(F.BOOT,1,210))
                self.assertEqual(receipt.stat().st_mode&0o777,0o600)
                run.reset_mock()
                with self.assertRaisesRegex(ValueError,'already exists'):S.main()
                run.assert_not_called()
                receipt.unlink()
                argv[argv.index('210')]='90'
                with self.assertRaisesRegex(ValueError,'reviewed 210'):S.main()
                run.assert_not_called()

    def test_helper_exception_retains_false_receipt_and_unknown_owner(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve();session=root/'ccmp-stable-monitor'/S.SESSION;session.mkdir(parents=True)
            receipt=session/'wifi-ssh-receipt.json';keys=root/'keys';keys.mkdir()
            (keys/'admin').write_text('fixture');(keys/'known_hosts').write_text('fixture')
            argv=['p1.py',str(keys),F.BOOT,'--cycles','1','--poll-seconds','210','--receipt',str(receipt)]
            with patch.dict(os.environ,{'GEMINI_RUNTIME_ROOT':str(root)}),patch.object(sys,'argv',argv), \
                    patch.object(sys,'platform','darwin'),patch.object(S,'run',side_effect=ValueError('fixture preflight')):
                with self.assertRaisesRegex(ValueError,'fixture preflight'):S.main()
            result=json.loads(receipt.read_text())
            self.assertFalse(result['all_pass'])
            self.assertFalse(result['p1_remote_stream_quiescence']['quiesced'])
            self.assertEqual(result['p1_host_exception']['detail'],'fixture preflight')

    def test_generated_shell_and_invalid_identity(self):
        stream = S.stream_command(F.BOOT).format(ready="'/tmp/fixture-ready'")
        for command in [stream, S.disconnect_argument(F.BOOT, 1000000000), S.remote_quiescence_argument(F.BOOT)]:
            subprocess.run(['/bin/sh', '-n'], input=command.encode(), check=True)
        for boot in ['bad', F.BOOT + ';touch nope']:
            with self.assertRaises(ValueError):
                S.stream_command(boot)
            with self.assertRaises(ValueError):
                S.disconnect_argument(boot, 1)
        for pm in [0, -1, '1;touch nope']:
            with self.assertRaises(ValueError):
                S.disconnect_argument(F.BOOT, pm)

if __name__ == '__main__':
    unittest.main()
