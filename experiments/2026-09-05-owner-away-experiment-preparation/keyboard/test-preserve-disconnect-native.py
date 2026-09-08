#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Host and AArch64-QEMU fixtures for the fixed preservation helper."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SOURCE = HERE / 'preserve-disconnect.c'
NAMES = ('observer.stdout', 'observer.stderr', 'monitor.status', 'outer-exit')
LIMITS = {'observer.stdout': 98304, 'observer.stderr': 98304,
          'monitor.status': 4096, 'outer-exit': 16}
MARKER = b'__PRESERVE_FILE_BEGIN__\n'
SCAN_BEGIN = b'__PRESERVE_SCAN_BEGIN__\n'

_parser = argparse.ArgumentParser(add_help=False)
_parser.add_argument('--compiler', default='cc')
_parser.add_argument('--qemu')
_parser.add_argument('--library-root')
_parser.add_argument('--work-root', default=None)
OPTIONS, _remaining = _parser.parse_known_args()
sys.argv = [sys.argv[0], *_remaining]


def fields(raw):
    result = {}
    for line in raw.decode('ascii').splitlines():
        key, separator, value = line.partition('=')
        if not separator or key in result or value != value.strip():
            raise AssertionError('bad field framing')
        result[key] = value
    return result


def parse(raw):
    if len(raw) > 524288 or not raw.startswith(b'__PRESERVE_BEGIN__\n'):
        raise AssertionError('bad bounded export')
    result = {}
    cursor = raw.index(b'__PRESERVE_HEADER_END__\n') + len(b'__PRESERVE_HEADER_END__\n')
    for expected in NAMES:
        if raw[cursor:cursor + len(MARKER)] != MARKER:
            raise AssertionError('missing file marker')
        cursor += len(MARKER)
        header_end = raw.index(b'__PRESERVE_DATA_BEGIN__\n', cursor)
        header = fields(raw[cursor:header_end])
        cursor = header_end + len(b'__PRESERVE_DATA_BEGIN__\n')
        length = int(header['data_bytes'])
        data = raw[cursor:cursor + length]
        if len(data) != length or raw[cursor + length:cursor + length + 1] != b'\n':
            raise AssertionError('bad length-delimited data')
        cursor += length + 1
        meta_marker = b'__PRESERVE_META_BEGIN__\n'
        meta_start = raw.index(meta_marker, cursor)
        meta_fields_start = meta_start + len(meta_marker)
        meta_end = raw.index(b'__PRESERVE_FILE_END__\n', meta_fields_start)
        metadata = fields(raw[meta_fields_start:meta_end])
        result[expected] = (header, data, metadata)
        cursor = meta_end + len(b'__PRESERVE_FILE_END__\n')
    files_end = b'__PRESERVE_FILES_END__\n'
    if raw[cursor:cursor + len(files_end)] != files_end:
        raise AssertionError('missing completion marker')
    cursor += len(files_end)
    if not raw.startswith(SCAN_BEGIN, cursor):
        raise AssertionError('missing scan marker')
    cursor += len(SCAN_BEGIN)
    scan_end = raw.index(b'__PRESERVE_SCAN_END__\n', cursor)
    result['__scan__'] = fields(raw[cursor:scan_end])
    if raw[scan_end + len(b'__PRESERVE_SCAN_END__\n'):] != b'__PRESERVE_END__\n':
        raise AssertionError('missing final marker')
    return result


class PreserverFixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.options = OPTIONS
        cls.work = Path(cls.options.work_root or tempfile.mkdtemp(prefix='preserver-fixtures-'))
        cls.work.mkdir(mode=0o700, parents=True, exist_ok=True)
        cls.cleanup_work = cls.options.work_root is None
        cls.base = cls.work / 'a53-keyboard-disconnect'
        cls.attempt = cls.base / 'run' / 'keyboard-attempt'
        cls.proc = cls.work / 'proc-fixture'
        (cls.proc / '1' / 'fd').mkdir(mode=0o700, parents=True)
        (cls.proc / '1' / 'cmdline').write_bytes(b'/bin/idle\0')
        (cls.proc / '1' / 'cmdline').chmod(0o600)
        (cls.proc / '1' / 'exe').symlink_to('/bin/idle')
        (cls.proc / '1' / 'fd' / '0').symlink_to('/dev/null')
        for path in (cls.base, cls.base / 'run', cls.attempt):
            path.mkdir(mode=0o700)
        cls.host = cls.work / 'preserver-host'
        cls.host_compiler = shutil.which('cc') or 'cc'
        cls.compile(cls.host_compiler, cls.host, static=False, deadline=60000)
        cls.arm = cls.work / 'preserver-arm64'
        if cls.options.qemu and cls.options.library_root:
            cls.compile(cls.options.compiler, cls.arm, static=True, deadline=60000)

    @classmethod
    def tearDownClass(cls):
        if cls.cleanup_work:
            shutil.rmtree(cls.work)

    @classmethod
    def compile(cls, compiler, output, static, pause=0, deadline=15000):
        owner = str(os.getuid())
        base = str(cls.base)
        command = [compiler, '-std=c11', '-Os', '-Wall', '-Wextra', '-Werror',
                   f'-DPRESERVER_BASE={json.dumps(base)}', f'-DPRESERVER_PROC={json.dumps(str(cls.proc))}',
                   f'-DPRESERVER_OWNER_UID={owner}', f'-DPRESERVER_DEADLINE_MS={deadline}']
        if static:
            command += ['-static']
        if pause:
            command += [f'-DPRESERVER_TEST_PAUSE_US={pause}']
        command += [str(SOURCE), '-o', str(output)]
        subprocess.run(command, check=True, capture_output=True)

    def setUp(self):
        for path in self.attempt.iterdir():
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
            else:
                path.unlink()

    def execute(self, binary, qemu=False, extra=()):
        command = [str(binary)]
        if qemu:
            command = [self.options.qemu, '-L', self.options.library_root, *command]
        return subprocess.run(command + list(extra), capture_output=True, timeout=5)

    def run_both(self):
        results = [('host', self.execute(self.host))]
        if self.options.qemu and self.options.library_root:
            results.append(('qemu-aarch64', self.execute(self.arm, True)))
        return results

    def populate(self, sizes=None):
        sizes = sizes or {name: min(32, LIMITS[name]) for name in NAMES}
        for name in NAMES:
            path = self.attempt / name
            path.write_bytes((name.encode() + b'\n') * (sizes[name] // (len(name) + 1)) +
                             b'x' * (sizes[name] % (len(name) + 1)))
            path.chmod(0o600)

    def assert_complete(self, results):
        for label, completed in results:
            self.assertEqual((completed.returncode, completed.stderr), (0, b''), label)
            parsed = parse(completed.stdout)
            for name in NAMES:
                header, data, metadata = parsed[name]
                self.assertEqual(header['name'], name)
                self.assertEqual(header['limit'], str(LIMITS[name]))
                self.assertEqual(header['state'], 'regular')
                self.assertEqual(metadata['stable'], 'yes')
                self.assertEqual(metadata['read_status'], '0')
                self.assertLessEqual(len(data), LIMITS[name])

    def test_complete_files_and_bounded_output(self):
        self.populate(LIMITS)
        results = self.run_both()
        self.assert_complete(results)
        for label, completed in results:
            self.assertEqual(parse(completed.stdout)['__scan__']['scan_status'], 'passed', label)
            self.assertLessEqual(len(completed.stdout), 524288)

    def test_missing_symlink_fifo_socket_and_device_refuse_without_blocking(self):
        cases = []
        self.populate()
        (self.attempt / 'observer.stdout').unlink()
        cases.append(('missing', 'observer.stdout', lambda path: None))
        (self.attempt / 'observer.stderr').unlink()
        target = self.work / 'target'
        target.write_bytes(b'secret')
        (self.attempt / 'observer.stderr').symlink_to(target)
        cases.append(('symlink', 'observer.stderr', lambda path: None))
        (self.attempt / 'monitor.status').unlink()
        os.mkfifo(self.attempt / 'monitor.status', 0o600)
        cases.append(('nonregular', 'monitor.status', lambda path: None))
        (self.attempt / 'outer-exit').unlink()
        sock = socket.socket(socket.AF_UNIX)
        socket_path = self.attempt / 'outer-exit'
        original_cwd = Path.cwd()
        try:
            try:
                os.chdir(self.attempt)
                sock.bind('outer-exit')
            finally:
                os.chdir(original_cwd)
        except BaseException:
            sock.close()
            raise

        def cleanup_socket(path):
            sock.close()
            path.unlink(missing_ok=True)

        cases.append(('nonregular', 'outer-exit', cleanup_socket))
        for label, name, cleanup in cases:
            with self.subTest(label=label):
                try:
                    for run_label, completed in self.run_both():
                        self.assertEqual(completed.returncode, 0, run_label)
                        self.assertEqual(parse(completed.stdout)[name][0]['state'], label)
                finally:
                    cleanup(self.attempt / name)

        if hasattr(os, 'mknod') and hasattr(os, 'makedev') and os.geteuid() == 0:
            path = self.attempt / 'outer-exit'
            os.mknod(path, 0o600 | 0o20000, os.makedev(1, 3))
            try:
                for run_label, completed in self.run_both():
                    self.assertEqual(completed.returncode, 0, run_label)
                    self.assertEqual(parse(completed.stdout)['outer-exit'][0]['state'],
                                     'nonregular')
            finally:
                path.unlink(missing_ok=True)

    def test_oversize_and_identity_drift_are_reported_independently(self):
        self.populate({**{name: 8 for name in NAMES}, 'observer.stdout': 98305})
        for label, completed in self.run_both():
            self.assertEqual(completed.returncode, 0, label)
            parsed = parse(completed.stdout)
            self.assertEqual(parsed['observer.stdout'][0]['state'], 'oversized')
            self.assertEqual(parsed['observer.stderr'][0]['state'], 'regular')

        self.setUp()
        self.populate({'observer.stdout': 98304, **{name: 8 for name in NAMES if name != 'observer.stdout'}})
        delayed = self.work / 'preserver-delayed'
        self.compile(self.host_compiler, delayed, static=False, pause=1000000)
        process = subprocess.Popen([str(delayed)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        changed = self.attempt / 'observer.stdout'
        self.assertEqual(process.stderr.readline(), b'__PRESERVER_TEST_OPENED__\n')
        replacement = self.attempt / 'observer.stdout.replacement'
        replacement.write_bytes(b'changed')
        replacement.chmod(0o600)
        os.replace(replacement, changed)
        stdout, stderr = process.communicate(timeout=5)
        self.assertEqual((process.returncode, stderr),
                         (0, b'__PRESERVER_TEST_OPENED__\n' * 3))
        self.assertEqual(parse(stdout)['observer.stdout'][0]['state'], 'changing')

    def test_scan_failures_retain_preservation_frames_and_validate_numeric_values(self):
        self.populate()
        malformed = self.proc / '001'
        (malformed / 'fd').mkdir(mode=0o700, parents=True)
        (malformed / 'cmdline').write_bytes(b'/bin/idle\0')
        (malformed / 'exe').symlink_to('/bin/idle')
        try:
            for label, completed in self.run_both():
                self.assertEqual(completed.returncode, 2, label)
                parsed = parse(completed.stdout)
                self.assertEqual(parsed['observer.stdout'][0]['state'], 'regular')
                self.assertEqual(parsed['__scan__']['scan_status'], 'incomplete')
        finally:
            shutil.rmtree(malformed)

    def test_scan_process_limit_overflow(self):
        self.populate()
        for number in range(2, 513):
            process = self.proc / str(number)
            (process / 'fd').mkdir(mode=0o700, parents=True)
            (process / 'cmdline').write_bytes(b'/bin/idle\0')
            (process / 'exe').symlink_to('/bin/idle')
            (process / 'fd' / '0').symlink_to('/dev/null')
        try:
            completed = self.execute(self.host)
            self.assertEqual(completed.returncode, 0)
            scan = parse(completed.stdout)['__scan__']
            self.assertEqual((scan['processes'], scan['scan_status']), ('512', 'passed'))
            process = self.proc / '513'
            (process / 'fd').mkdir(mode=0o700, parents=True)
            (process / 'cmdline').write_bytes(b'/bin/idle\0')
            (process / 'exe').symlink_to('/bin/idle')
            completed = self.execute(self.host)
            self.assertEqual(completed.returncode, 2)
            scan = parse(completed.stdout)['__scan__']
            self.assertEqual(scan['processes'], '512')
            self.assertEqual(scan['scan_status'], 'overflow')
        finally:
            shutil.rmtree(self.proc / '513', ignore_errors=True)
            for number in range(2, 513):
                shutil.rmtree(self.proc / str(number))

    def test_scan_descriptor_and_match_exact_limits_then_overflow(self):
        self.populate()
        baseline = self.proc / '1'
        held = self.proc / '.baseline-held'
        baseline.rename(held)
        process = self.proc / '2'
        (process / 'fd').mkdir(mode=0o700, parents=True)
        (process / 'cmdline').write_bytes(b'/bin/idle\0')
        (process / 'exe').symlink_to('/bin/idle')
        for number in range(4096):
            (process / 'fd' / str(number)).symlink_to('/dev/null')
        try:
            completed = self.execute(self.host)
            self.assertEqual(completed.returncode, 0)
            scan = parse(completed.stdout)['__scan__']
            self.assertEqual((scan['descriptors'], scan['scan_status']), ('4096', 'passed'))
            (process / 'fd' / '4096').symlink_to('/dev/null')
            completed = self.execute(self.host)
            self.assertEqual(completed.returncode, 2)
            scan = parse(completed.stdout)['__scan__']
            self.assertEqual((scan['descriptors'], scan['scan_status']), ('4096', 'overflow'))
            self.assertEqual(parse(completed.stdout)['observer.stdout'][0]['state'], 'regular')
        finally:
            shutil.rmtree(process)
            held.rename(baseline)

        process = self.proc / '3'
        (process / 'fd').mkdir(mode=0o700, parents=True)
        (process / 'cmdline').write_bytes(b'/bin/idle\0')
        (process / 'exe').symlink_to('/bin/idle')
        for number in range(256):
            (process / 'fd' / str(number)).symlink_to('/dev/input/preserver-nonexistent-review-node')
        try:
            completed = self.execute(self.host)
            self.assertEqual(completed.returncode, 2)
            scan = parse(completed.stdout)['__scan__']
            self.assertEqual((scan['matches'], scan['scan_status']), ('256', 'incomplete'))
            (process / 'fd' / '256').symlink_to('/dev/input/preserver-nonexistent-review-node')
            completed = self.execute(self.host)
            self.assertEqual(completed.returncode, 2)
            scan = parse(completed.stdout)['__scan__']
            self.assertEqual((scan['matches'], scan['scan_status']), ('256', 'overflow'))
            self.assertEqual(scan['match_overflow'], 'yes')
            self.assertEqual(parse(completed.stdout)['observer.stdout'][0]['state'], 'regular')
        finally:
            shutil.rmtree(process)

    def test_scan_truncated_proc_content_is_incomplete_after_preservation(self):
        self.populate()
        process = self.proc / '4'
        (process / 'fd').mkdir(mode=0o700, parents=True)
        (process / 'cmdline').write_bytes(b'x' * 4097)
        (process / 'exe').symlink_to('/bin/idle')
        try:
            completed = self.execute(self.host)
            self.assertEqual(completed.returncode, 2)
            parsed = parse(completed.stdout)
            self.assertEqual(parsed['observer.stdout'][0]['state'], 'regular')
            self.assertEqual(parsed['__scan__']['scan_status'], 'incomplete')
        finally:
            shutil.rmtree(process)

    def test_executable_identity_is_sanitized_independent_of_cmdline(self):
        self.populate()
        process = self.proc / '5'
        (process / 'fd').mkdir(mode=0o700, parents=True)
        (process / 'cmdline').write_bytes(b'changed-argv\0')
        (process / 'exe').symlink_to('/a53-keyboard-disconnect/probe (deleted)')
        try:
            completed = self.execute(self.host)
            self.assertEqual(completed.returncode, 0)
            scan = parse(completed.stdout)['__scan__']
            self.assertEqual(scan['scan_status'], 'passed')
            self.assertEqual(scan['exe_matches'], '1')
            self.assertEqual(scan['exe_deleted_matches'], '1')
            self.assertEqual(scan['cmdline_matches'], '0')
        finally:
            shutil.rmtree(process)

    def test_portable_console_rdev_alias_is_metadata_only(self):
        candidates = [Path('/dev/console'), Path('/dev/tty')]
        candidate = next((path for path in candidates if path.exists() and
                          os.stat(path).st_rdev and
                          (os.major(os.stat(path).st_rdev) in (4, 5, 13))), None)
        if candidate is None:
            self.skipTest('host has no portable Linux console/input rdev alias')
        self.populate()
        process = self.proc / '6'
        (process / 'fd').mkdir(mode=0o700, parents=True)
        (process / 'cmdline').write_bytes(b'/bin/idle\0')
        (process / 'exe').symlink_to('/bin/idle')
        (process / 'fd' / '0').symlink_to(candidate)
        try:
            completed = self.execute(self.host)
            self.assertEqual(completed.returncode, 0)
            scan = parse(completed.stdout)['__scan__']
            self.assertEqual(scan['scan_status'], 'passed')
            self.assertGreater(int(scan['console_matches']) + int(scan['input_matches']), 0)
        finally:
            shutil.rmtree(process)

    def test_deadline_blocked_stdout_and_static_no_process_paths(self):
        self.populate(LIMITS)
        delayed = self.work / 'preserver-short-deadline'
        self.compile(self.host_compiler, delayed, static=False, pause=100000, deadline=20)
        completed = subprocess.run([str(delayed)], capture_output=True, timeout=3)
        self.assertEqual(completed.returncode, 2)
        blocked = self.work / 'preserver-blocked-output'
        self.compile(self.host_compiler, blocked, static=False, deadline=20)
        read_fd, write_fd = os.pipe()
        os.set_blocking(write_fd, False)
        prefill = bytearray()
        while True:
            try:
                written = os.write(write_fd, b'p' * 4096)
                prefill.extend(b'p' * written)
            except BlockingIOError:
                break
        process = subprocess.Popen([str(blocked)], stdout=write_fd, stderr=subprocess.PIPE)
        os.close(write_fd)
        self.assertEqual(process.wait(timeout=3), 2)
        captured = bytearray()
        while True:
            chunk = os.read(read_fd, 65536)
            if not chunk:
                break
            captured.extend(chunk)
        os.close(read_fd)
        stderr = process.stderr.read()
        process.stderr.close()
        self.assertEqual((bytes(captured), stderr), (bytes(prefill), b''))
        source = SOURCE.read_text()
        for name in ('fork', 'exec', 'setsid', 'kill', 'signal'):
            self.assertIsNone(re.search(r'\b' + name + r'\s*\(', source), name)

    def test_no_arbitrary_arguments_and_no_output_on_invalid_ancestry(self):
        self.populate()
        for label, completed in self.run_both():
            command = self.execute(self.host if label == 'host' else self.arm,
                                   label != 'host', extra=('unexpected',))
            self.assertEqual(command.returncode, 2, label)
        run = self.base / 'run'
        run.chmod(0o755)
        try:
            for label, completed in self.run_both():
                self.assertEqual(completed.returncode, 2, label)
        finally:
            run.chmod(0o700)
        real = self.base / 'keyboard-attempt-real'
        self.attempt.rename(real)
        self.attempt.symlink_to(real)
        try:
            for label, completed in self.run_both():
                self.assertEqual(completed.returncode, 2, label)
        finally:
            self.attempt.unlink()
            real.rename(self.attempt)


if __name__ == '__main__':
    unittest.main()
