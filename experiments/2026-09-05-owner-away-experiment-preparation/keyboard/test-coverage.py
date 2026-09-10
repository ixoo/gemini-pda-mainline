#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run all twenty production-duration windows with PTY and synthetic evdev."""
import argparse
import os
from pathlib import Path
import pty
import re
import runpy
import subprocess
import tempfile
import termios
import threading

HERE = Path(__file__).resolve().parent
READER = runpy.run_path(str(HERE/'test-focused.py'))
ANALYZER = runpy.run_path(str(HERE/'analyze-focused.py'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--compiler', required=True)
    parser.add_argument('--qemu', required=True)
    parser.add_argument('--work', required=True, type=Path)
    args = parser.parse_args()
    entry = runpy.run_path(str(HERE/'test-focused-monitor.py'))
    entry['entry_check'].__globals__['ENTRY'] = entry['ENTRY'].replace(
        '/a53-keyboard-focused', '/a53-keyboard-coverage').replace(
        '--diagnose', '--coverage').replace('KEYBOARD_MONITOR_FOCUSED 1', 'KEYBOARD_MONITOR_COVERAGE 1')
    entry['entry_check'](args)
    source, binary = args.work/'coverage-fixture.c', args.work/'coverage-fixture'
    source.write_text(READER['FIXTURE'])
    subprocess.run([args.compiler, '-std=c11', '-static', '-Wall', '-Wextra', '-Werror',
                    '-idirafter', '/usr/aarch64-linux-gnu/include', '-I', str(HERE),
                    str(source), '-o', str(binary)], check=True)
    master, slave = pty.openpty()
    reader, writer = os.pipe()
    before = termios.tcgetattr(slave)
    process, feeder = None, None
    errors = []
    with tempfile.TemporaryFile(dir=args.work) as output:
        try:
            process = subprocess.Popen([args.qemu, str(binary), '--coverage', 'event0', '13', '64'],
                pass_fds=(reader, slave), stdout=output, stderr=subprocess.PIPE,
                env={**os.environ, 'INPUT_FD': str(reader), 'CONSOLE_FD': str(slave), 'REPEAT_PERIOD': '33'})

            def feed():
                try:
                    for step in ANALYZER['V1']['PROTOCOL']['steps']:
                        READER['wait_prompt'](master, f"{step['index']+1}/20 (".encode(), process, 13)
                        events = []
                        for code, value in step['key_edges']:
                            events += [(4, 4, ANALYZER['V1']['SCANS'][code]), (1, code, value), (0, 0, 0)]
                            # Exceed the old 64-event ceiling with valid modifier repeats.
                            if code == 125 and value == 1:
                                events += [(1, code, 2), (0, 0, 1)] * 80
                        payload = READER['packed'](events)
                        view = memoryview(payload)
                        while view:
                            view = view[os.write(writer, view):]
                        os.write(master, bytes.fromhex(step['vt_hex']))
                except BaseException as exc:
                    errors.append(exc)

            feeder = threading.Thread(target=feed, daemon=True)
            feeder.start()
            _, err = process.communicate(timeout=208)
            feeder.join(timeout=2)
            assert not feeder.is_alive() and not errors, errors
            output.seek(0)
            data = output.read(1048577)
            assert (process.returncode, err) == (0, b''), (process.returncode, err, data[-1024:])
            assert termios.tcgetattr(slave) == before
            result = ANALYZER['analyze'](data, coverage=True)
            assert result['outcome'] == 'observations-complete', result
            assert len(result['cases']) == 20
            assert all(c['input'] == c['vt'] == 'match' for c in result['cases']), result
            assert result['cases'][0]['repeat_events'] == 80
            assert ANALYZER['analyze'](data[:-10], coverage=True)['outcome'] == 'inconclusive'
            bad_sync = re.sub(rb'(event [0-9]+ 0 0) 1', rb'\1 0', data, count=1)
            assert ANALYZER['analyze'](bad_sync, coverage=True)['outcome'] == 'inconclusive'
            bad_vt = data.replace(b'tty hex=1b5b5b4161', b'tty hex=1b5b5b4261', 1)
            assert ANALYZER['analyze'](bad_vt, coverage=True)['cases'][0]['vt'] == 'mismatch'
            print('coverage-production-202s-20-windows-modifier-repeats-restoration-and-analysis=pass', flush=True)
        finally:
            if process and process.poll() is None:
                process.kill()
                process.wait(timeout=2)
            os.close(reader)
            if feeder:
                feeder.join(timeout=2)
            for fd in (master, slave, writer):
                os.close(fd)


if __name__ == '__main__':
    main()
