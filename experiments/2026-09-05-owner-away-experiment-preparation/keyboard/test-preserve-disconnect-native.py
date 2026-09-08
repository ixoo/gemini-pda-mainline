#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Host and AArch64-QEMU fixtures for the fixed preservation helper."""
import argparse
from collections import Counter
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import select
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import time
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


def validate_matrix(matrix, required=()):
    """Reject missing, duplicate, skipped or failed required matrix cells."""
    if len(matrix) > 256 or len(json.dumps(matrix, sort_keys=True,
                                            separators=(',', ':'))) > 65536:
        raise AssertionError('unbounded preservation matrix')
    keys = [(entry.get('scenario'), entry.get('architecture')) for entry in matrix]
    counts = Counter(keys)
    for key in required:
        if counts[key] != 1:
            raise AssertionError(f'required matrix cell count {key}: {counts[key]}')
        entry = next(entry for entry in matrix
                     if (entry.get('scenario'), entry.get('architecture')) == key)
        if entry.get('result') != 'pass' or entry.get('skip_reason') is not None:
            raise AssertionError(f'required matrix cell did not pass: {key}')


def matrix_entry(scenario, architecture, binary, result, skip_reason=None):
    return {'architecture': architecture, 'fixture_sha256': hashlib.sha256(
        Path(binary).read_bytes()).hexdigest(), 'result': result,
            'scenario': scenario, 'skip_reason': skip_reason}


@contextmanager
def matrix_case(matrix, scenario, architecture, binary):
    """Record one case only after all execution and semantic checks finish."""
    entry = matrix_entry(scenario, architecture, binary, None)
    try:
        yield
    except BaseException:
        entry['result'] = 'fail'
        matrix.append(entry)
        raise
    else:
        entry['result'] = 'pass'
        matrix.append(entry)


def emit_matrix(matrix):
    encoded = json.dumps(matrix, sort_keys=True, separators=(',', ':'))
    if len(matrix) > 256 or len(encoded) > 65536:
        encoded = json.dumps({'entries': len(matrix), 'matrix_status': 'invalid-unbounded'},
                             sort_keys=True, separators=(',', ':'))
    print('__PRESERVE_MATRIX_BEGIN__')
    print(encoded)
    print('__PRESERVE_MATRIX_END__')


def finish_matrix(matrix, required, cleanup, emit=emit_matrix):
    """Preserve validation failure while always attempting diagnostics and cleanup."""
    validation_error = diagnostic_error = cleanup_error = None
    try:
        validate_matrix(matrix, required)
    except BaseException as error:
        validation_error = error
    try:
        emit(matrix)
    except BaseException as error:
        diagnostic_error = error
    try:
        cleanup()
    except BaseException as error:
        cleanup_error = error
    if validation_error is not None:
        raise validation_error
    if diagnostic_error is not None:
        raise diagnostic_error
    if cleanup_error is not None:
        raise cleanup_error


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
    matrix = []
    required_arm_scenarios = frozenset({
        'identity-drift', 'process-limit-exact', 'process-limit-overflow',
        'descriptor-limit-exact', 'descriptor-limit-overflow', 'match-limit-exact',
        'match-limit-overflow', 'truncated-process-value',
        'executable-identity-exact', 'executable-identity-deleted',
        'portable-console-rdev-alias', 'deadline-expiry', 'blocked-stdout'})

    @classmethod
    def setUpClass(cls):
        cls.options = OPTIONS
        if bool(cls.options.qemu) != bool(cls.options.library_root):
            raise RuntimeError('--qemu and --library-root must be supplied together')
        if cls.options.qemu:
            qemu = Path(cls.options.qemu)
            library = Path(cls.options.library_root)
            if not qemu.is_file() or not os.access(qemu, os.X_OK):
                raise RuntimeError('requested QEMU is not an executable file')
            if not library.is_dir():
                raise RuntimeError('requested QEMU library root is not a directory')
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
        cls.matrix = []

    @classmethod
    def tearDownClass(cls):
        if cls.options.qemu:
            required = {(scenario, architecture)
                        for scenario in cls.required_arm_scenarios
                        for architecture in ('native', 'arm64-qemu')}
        else:
            required = set()
        cleanup = (lambda: shutil.rmtree(cls.work)) if cls.cleanup_work else (lambda: None)
        finish_matrix(cls.matrix, required, cleanup)

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
        self._reset_attempt_files()

    def _reset_attempt_files(self):
        for path in self.attempt.iterdir():
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
            else:
                path.unlink()

    def architectures(self):
        cases = [('native', self.host, False)]
        if self.options.qemu and self.options.library_root:
            cases.append(('arm64-qemu', self.arm, True))
        return cases

    def execute(self, binary, qemu=False, extra=()):
        command = [str(binary)]
        if qemu:
            command = [self.options.qemu, '-L', self.options.library_root, *command]
        completed = subprocess.run(command + list(extra), capture_output=True, timeout=5)
        return completed

    @contextmanager
    def observed(self, scenario, label, binary, qemu=False, extra=()):
        with matrix_case(self.matrix, scenario, label, binary):
            yield self.execute(binary, qemu, extra)

    def compile_variant(self, name, pause=0, deadline=15000):
        host = self.work / f'{name}-native'
        self.compile(self.host_compiler, host, static=False, pause=pause, deadline=deadline)
        arm = None
        if self.options.qemu and self.options.library_root:
            arm = self.work / f'{name}-arm64'
            self.compile(self.options.compiler, arm, static=True, pause=pause, deadline=deadline)
        return [('native', host, False)] + ([('arm64-qemu', arm, True)] if arm else [])

    def populate(self, sizes=None):
        sizes = sizes or {name: min(32, LIMITS[name]) for name in NAMES}
        for name in NAMES:
            path = self.attempt / name
            path.write_bytes((name.encode() + b'\n') * (sizes[name] // (len(name) + 1)) +
                             b'x' * (sizes[name] % (len(name) + 1)))
            path.chmod(0o600)

    def snapshot_files(self):
        snapshot = {}
        for name in NAMES:
            path = self.attempt / name
            info = os.stat(path, follow_symlinks=False)
            self.assertTrue(stat.S_ISREG(info.st_mode))
            snapshot[name] = {
                'data': path.read_bytes(), 'size': info.st_size,
                'identity': f'{info.st_dev}:{info.st_ino}',
                'mode': info.st_mode & 0o7777, 'uid': info.st_uid,
                'nlink': info.st_nlink,
            }
        return snapshot

    def assert_preserved_files(self, parsed, snapshot, label=''):
        for name in NAMES:
            header, data, metadata = parsed[name]
            expected = snapshot[name]
            self.assertEqual(header['state'], 'regular', label)
            self.assertEqual(header['size_before'], str(expected['size']), label)
            self.assertEqual(header['identity_before'], expected['identity'], label)
            self.assertEqual(data, expected['data'], label)
            self.assertEqual(metadata['size_after'], str(expected['size']), label)
            self.assertEqual(metadata['identity_after'], expected['identity'], label)
            self.assertEqual(metadata['read_status'], '0', label)
            self.assertEqual(metadata['stable'], 'yes', label)
            self.assertEqual(metadata['captured_bytes'], str(expected['size']), label)
            self.assertEqual(expected['mode'], 0o600, label)
            self.assertEqual(expected['nlink'], 1, label)
            self.assertEqual(expected['uid'], os.getuid(), label)

    def run_identity_drift(self, scenario, label, binary, qemu=False):
        """Run one independently populated, marker-synchronized drift case."""
        self._reset_attempt_files()
        self.populate({'observer.stdout': 98304,
                       **{name: 8 for name in NAMES if name != 'observer.stdout'}})
        command = [str(binary)]
        if qemu:
            command = [self.options.qemu, '-L', self.options.library_root, *command]
        process = None
        with matrix_case(self.matrix, scenario, label, binary):
            try:
                process = subprocess.Popen(command, stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE)
                deadline = time.monotonic() + 2
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise AssertionError(f'{label}: marker wait timeout')
                    ready, _, _ = select.select([process.stderr], [], [], remaining)
                    if not ready:
                        raise AssertionError(f'{label}: marker wait timeout')
                    if process.stderr.readline() == b'__PRESERVER_TEST_OPENED__\n':
                        break
                changed = self.attempt / 'observer.stdout'
                replacement = self.attempt / 'observer.stdout.replacement'
                replacement.write_bytes(b'changed')
                replacement.chmod(0o600)
                os.replace(replacement, changed)
                stdout, stderr = process.communicate(timeout=5)
                self.assertEqual((process.returncode, stderr),
                                 (0, b'__PRESERVER_TEST_OPENED__\n' * 3), label)
                self.assertEqual(parse(stdout)['observer.stdout'][0]['state'],
                                 'changing', label)
            finally:
                if process is not None:
                    if process.poll() is None:
                        process.kill()
                    process.wait(timeout=2)
                    process.stdout.close()
                    process.stderr.close()
        return hashlib.sha256(Path(binary).read_bytes()).hexdigest()

    def assert_complete(self, completed, label):
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
        for label, binary, qemu in self.architectures():
            with self.subTest(architecture=label):
                with self.observed('complete-files', label, binary, qemu) as completed:
                    self.assert_complete(completed, label)
                    self.assertEqual(parse(completed.stdout)['__scan__']['scan_status'],
                                     'passed', label)
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
                    for run_label, binary, qemu in self.architectures():
                        with self.observed(f'unsafe-{label}-{name}', run_label,
                                           binary, qemu) as completed:
                            self.assertEqual(completed.returncode, 0, run_label)
                            self.assertEqual(parse(completed.stdout)[name][0]['state'], label)
                finally:
                    cleanup(self.attempt / name)

        if hasattr(os, 'mknod') and hasattr(os, 'makedev') and os.geteuid() == 0:
            path = self.attempt / 'outer-exit'
            os.mknod(path, 0o600 | 0o20000, os.makedev(1, 3))
            try:
                for run_label, binary, qemu in self.architectures():
                    with self.observed('unsafe-device-node', run_label,
                                       binary, qemu) as completed:
                        self.assertEqual(completed.returncode, 0, run_label)
                        self.assertEqual(parse(completed.stdout)['outer-exit'][0]['state'],
                                         'nonregular')
            finally:
                path.unlink(missing_ok=True)

    def test_oversize_and_identity_drift_are_reported_independently(self):
        self.populate({**{name: 8 for name in NAMES}, 'observer.stdout': 98305})
        for label, binary, qemu in self.architectures():
            with self.subTest(architecture=label, scenario='oversized-file'):
                with self.observed('oversized-file', label, binary, qemu) as completed:
                    self.assertEqual(completed.returncode, 0, label)
                    parsed = parse(completed.stdout)
                    self.assertEqual(parsed['observer.stdout'][0]['state'], 'oversized')
                    self.assertEqual(parsed['observer.stderr'][0]['state'], 'regular')

        for label, delayed, qemu in self.compile_variant('preserver-delayed', pause=1000000):
            with self.subTest(architecture=label, scenario='identity-drift'):
                self.run_identity_drift('identity-drift', label, delayed, qemu)

    def test_scan_failures_retain_preservation_frames_and_validate_numeric_values(self):
        self.populate()
        snapshot = self.snapshot_files()
        malformed = self.proc / '001'
        (malformed / 'fd').mkdir(mode=0o700, parents=True)
        (malformed / 'cmdline').write_bytes(b'/bin/idle\0')
        (malformed / 'exe').symlink_to('/bin/idle')
        try:
            for label, binary, qemu in self.architectures():
                with self.subTest(architecture=label):
                    with self.observed('malformed-process-entry', label,
                                       binary, qemu) as completed:
                        self.assertEqual(completed.returncode, 2, label)
                        parsed = parse(completed.stdout)
                        self.assert_preserved_files(parsed, snapshot, label)
                        self.assertEqual(parsed['__scan__']['scan_status'], 'incomplete')
        finally:
            shutil.rmtree(malformed)

    def test_scan_process_limit_overflow(self):
        self.populate()
        snapshot = self.snapshot_files()
        for number in range(2, 513):
            process = self.proc / str(number)
            (process / 'fd').mkdir(mode=0o700, parents=True)
            (process / 'cmdline').write_bytes(b'/bin/idle\0')
            (process / 'exe').symlink_to('/bin/idle')
            (process / 'fd' / '0').symlink_to('/dev/null')
        try:
            for label, binary, qemu in self.architectures():
                with self.subTest(architecture=label, boundary='exact'):
                    with self.observed('process-limit-exact', label,
                                       binary, qemu) as completed:
                        self.assertEqual(completed.returncode, 0, label)
                        scan = parse(completed.stdout)['__scan__']
                        self.assertEqual((scan['processes'], scan['scan_status']),
                                         ('512', 'passed'), label)
                        self.assert_preserved_files(parse(completed.stdout), snapshot, label)
                process = self.proc / '513'
                (process / 'fd').mkdir(mode=0o700, parents=True)
                (process / 'cmdline').write_bytes(b'/bin/idle\0')
                (process / 'exe').symlink_to('/bin/idle')
                with self.subTest(architecture=label, boundary='overflow'):
                    with self.observed('process-limit-overflow', label,
                                       binary, qemu) as completed:
                        self.assertEqual(completed.returncode, 2, label)
                        scan = parse(completed.stdout)['__scan__']
                        self.assertEqual(scan['processes'], '512', label)
                        self.assertEqual(scan['scan_status'], 'overflow', label)
                        self.assert_preserved_files(parse(completed.stdout), snapshot, label)
                shutil.rmtree(process)
        finally:
            shutil.rmtree(self.proc / '513', ignore_errors=True)
            for number in range(2, 513):
                shutil.rmtree(self.proc / str(number))

    def test_scan_descriptor_and_match_exact_limits_then_overflow(self):
        self.populate()
        snapshot = self.snapshot_files()
        baseline = self.proc / '1'
        held = self.proc / '.baseline-held'
        for label, binary, qemu in self.architectures():
            baseline.rename(held)
            process = self.proc / '2'
            (process / 'fd').mkdir(mode=0o700, parents=True)
            (process / 'cmdline').write_bytes(b'/bin/idle\0')
            (process / 'exe').symlink_to('/bin/idle')
            for number in range(4096):
                (process / 'fd' / str(number)).symlink_to('/dev/null')
            try:
                with self.subTest(architecture=label, descriptor='exact'):
                    with self.observed('descriptor-limit-exact', label,
                                       binary, qemu) as completed:
                        self.assertEqual(completed.returncode, 0, label)
                        scan = parse(completed.stdout)['__scan__']
                        self.assertEqual((scan['descriptors'], scan['scan_status']),
                                         ('4096', 'passed'), label)
                        self.assert_preserved_files(parse(completed.stdout), snapshot, label)
                (process / 'fd' / '4096').symlink_to('/dev/null')
                with self.subTest(architecture=label, descriptor='overflow'):
                    with self.observed('descriptor-limit-overflow', label,
                                       binary, qemu) as completed:
                        self.assertEqual(completed.returncode, 2, label)
                        scan = parse(completed.stdout)['__scan__']
                        self.assertEqual((scan['descriptors'], scan['scan_status']),
                                         ('4096', 'overflow'), label)
                        self.assert_preserved_files(parse(completed.stdout), snapshot, label)
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
                with self.subTest(architecture=label, matches='exact'):
                    with self.observed('match-limit-exact', label,
                                       binary, qemu) as completed:
                        self.assertEqual(completed.returncode, 2, label)
                        scan = parse(completed.stdout)['__scan__']
                        self.assertEqual((scan['matches'], scan['scan_status']),
                                         ('256', 'incomplete'), label)
                        self.assert_preserved_files(parse(completed.stdout), snapshot, label)
                (process / 'fd' / '256').symlink_to('/dev/input/preserver-nonexistent-review-node')
                with self.subTest(architecture=label, matches='overflow'):
                    with self.observed('match-limit-overflow', label,
                                       binary, qemu) as completed:
                        self.assertEqual(completed.returncode, 2, label)
                        scan = parse(completed.stdout)['__scan__']
                        self.assertEqual((scan['matches'], scan['scan_status']),
                                         ('256', 'overflow'), label)
                        self.assertEqual(scan['match_overflow'], 'yes', label)
                        self.assert_preserved_files(parse(completed.stdout), snapshot, label)
            finally:
                shutil.rmtree(process)

    def test_scan_truncated_proc_content_is_incomplete_after_preservation(self):
        self.populate()
        snapshot = self.snapshot_files()
        process = self.proc / '4'
        (process / 'fd').mkdir(mode=0o700, parents=True)
        (process / 'cmdline').write_bytes(b'x' * 4097)
        (process / 'exe').symlink_to('/bin/idle')
        try:
            for label, binary, qemu in self.architectures():
                with self.subTest(architecture=label):
                    with self.observed('truncated-process-value', label,
                                       binary, qemu) as completed:
                        self.assertEqual(completed.returncode, 2, label)
                        parsed = parse(completed.stdout)
                        self.assert_preserved_files(parsed, snapshot, label)
                        self.assertEqual(parsed['__scan__']['scan_status'], 'incomplete', label)
        finally:
            shutil.rmtree(process)

    def test_executable_identity_is_sanitized_independent_of_cmdline(self):
        for variant, executable, deleted in (
                ('exact', '/a53-keyboard-disconnect/probe', False),
                ('deleted', '/a53-keyboard-disconnect/probe (deleted)', True)):
            self._reset_attempt_files()
            self.populate()
            process = self.proc / '5'
            (process / 'fd').mkdir(mode=0o700, parents=True)
            (process / 'cmdline').write_bytes(b'changed-argv\0')
            (process / 'exe').symlink_to(executable)
            try:
                for label, binary, qemu in self.architectures():
                    with self.subTest(architecture=label, executable=variant):
                        with self.observed('executable-identity-' + variant, label,
                                           binary, qemu) as completed:
                            self.assertEqual(completed.returncode, 0, label)
                            scan = parse(completed.stdout)['__scan__']
                            self.assertEqual(scan['scan_status'], 'passed', label)
                            self.assertEqual(scan['exe_matches'], '1', label)
                            self.assertEqual(scan['exe_deleted_matches'],
                                             '1' if deleted else '0', label)
                            self.assertEqual(scan['cmdline_matches'], '0', label)
            finally:
                shutil.rmtree(process)

    def test_portable_console_rdev_alias_is_metadata_only(self):
        candidates = [Path('/dev/console'), Path('/dev/tty')]
        candidate = next((path for path in candidates if path.exists() and
                          os.stat(path).st_rdev and
                          (os.major(os.stat(path).st_rdev) in (4, 5, 13))), None)
        if candidate is None:
            if self.options.qemu:
                self.matrix.append({'architecture': 'native', 'fixture_sha256': hashlib.sha256(
                    self.host.read_bytes()).hexdigest(), 'result': 'fail',
                    'scenario': 'portable-console-rdev-alias',
                    'skip_reason': 'required Linux alias unavailable'})
                self.fail('required Linux console/input rdev alias unavailable')
            self.matrix.append({'architecture': 'native', 'fixture_sha256': hashlib.sha256(
                self.host.read_bytes()).hexdigest(), 'result': 'skip',
                'scenario': 'portable-console-rdev-alias',
                'skip_reason': 'host has no portable Linux console/input rdev alias'})
            self.skipTest('host has no portable Linux console/input rdev alias')
        self.populate()
        process = self.proc / '6'
        (process / 'fd').mkdir(mode=0o700, parents=True)
        (process / 'cmdline').write_bytes(b'/bin/idle\0')
        (process / 'exe').symlink_to('/bin/idle')
        (process / 'fd' / '0').symlink_to(candidate)
        try:
            for label, binary, qemu in self.architectures():
                with self.subTest(architecture=label):
                    with self.observed('portable-console-rdev-alias', label,
                                       binary, qemu) as completed:
                        self.assertEqual(completed.returncode, 0, label)
                        scan = parse(completed.stdout)['__scan__']
                        self.assertEqual(scan['scan_status'], 'passed', label)
                        self.assertGreater(int(scan['console_matches']) +
                                           int(scan['input_matches']), 0, label)
        finally:
            shutil.rmtree(process)

    def test_deadline_blocked_stdout_and_static_no_process_paths(self):
        self.populate(LIMITS)
        for label, delayed, qemu in self.compile_variant(
                'preserver-short-deadline', pause=100000, deadline=20):
            command = [str(delayed)]
            if qemu:
                command = [self.options.qemu, '-L', self.options.library_root, *command]
            with self.subTest(architecture=label, condition='deadline'):
                with matrix_case(self.matrix, 'deadline-expiry', label, delayed):
                    completed = subprocess.run(command, capture_output=True, timeout=3)
                    self.assertEqual(completed.returncode, 2, label)

        for label, blocked, qemu in self.compile_variant('preserver-blocked-output', deadline=20):
            command = [str(blocked)]
            if qemu:
                command = [self.options.qemu, '-L', self.options.library_root, *command]
            read_fd, write_fd = os.pipe()
            process = None
            try:
                os.set_blocking(write_fd, False)
                prefill = bytearray()
                while True:
                    try:
                        written = os.write(write_fd, b'p' * 4096)
                        prefill.extend(b'p' * written)
                    except BlockingIOError:
                        break
                with self.subTest(architecture=label, condition='blocked-stdout'):
                    with matrix_case(self.matrix, 'blocked-stdout', label, blocked):
                        process = subprocess.Popen(command, stdout=write_fd,
                                                   stderr=subprocess.PIPE)
                        os.close(write_fd)
                        write_fd = None
                        self.assertEqual(process.wait(timeout=3), 2, label)
                        captured = bytearray()
                        while True:
                            chunk = os.read(read_fd, 65536)
                            if not chunk:
                                break
                            captured.extend(chunk)
                        stderr = process.stderr.read()
                        process.stderr.close()
                        self.assertEqual((bytes(captured), stderr),
                                         (bytes(prefill), b''), label)
            finally:
                if write_fd is not None:
                    os.close(write_fd)
                os.close(read_fd)
                if process is not None:
                    if process.poll() is None:
                        process.kill()
                    process.wait(timeout=2)
                    if process.stderr is not None and not process.stderr.closed:
                        process.stderr.close()
        source = SOURCE.read_text()
        for name in ('fork', 'exec', 'setsid', 'kill', 'signal'):
            self.assertIsNone(re.search(r'\b' + name + r'\s*\(', source), name)

    def test_native_consecutive_variants_isolate_fixture_state(self):
        """Non-ARM discriminator: two distinct delayed variants isolate state."""
        first = self.compile_variant('identity-isolation-first', pause=900000)[0]
        second = self.compile_variant('identity-isolation-second', pause=1100000)[0]
        first_hash = hashlib.sha256(first[1].read_bytes()).hexdigest()
        second_hash = hashlib.sha256(second[1].read_bytes()).hexdigest()
        self.assertNotEqual(first_hash, second_hash)
        self.run_identity_drift('non-arm-identity-isolation-first', *first)
        self.run_identity_drift('non-arm-identity-isolation-second', *second)

    def test_matrix_rejects_missing_duplicate_failure_and_skip(self):
        binary = self.host
        required = {('cell', 'native')}
        good = [matrix_entry('cell', 'native', binary, 'pass')]
        validate_matrix(good, required)
        for mutation in (
                [],
                good + [matrix_entry('cell', 'native', binary, 'pass')],
                [matrix_entry('cell', 'native', binary, 'fail')],
                [matrix_entry('cell', 'native', binary, 'skip', 'fixture unavailable')]):
            with self.subTest(mutation=mutation):
                with self.assertRaises(AssertionError):
                    validate_matrix(mutation, required)

    def test_matrix_case_records_semantic_outcomes(self):
        binary = self.host
        successful = []
        with matrix_case(successful, 'success', 'native', binary):
            self.assertTrue(True)
        self.assertEqual([entry['result'] for entry in successful], ['pass'])

        for exception in (AssertionError('assertion'), RuntimeError('ordinary')):
            failed = []
            with self.subTest(exception=type(exception).__name__):
                with self.assertRaises(type(exception)):
                    with matrix_case(failed, 'failure', 'native', binary):
                        raise exception
                self.assertEqual([entry['result'] for entry in failed], ['fail'])

        subtest_matrix = []

        class NestedFailure(unittest.TestCase):
            def runTest(nested):
                with nested.subTest(cell='real-subtest'):
                    with matrix_case(subtest_matrix, 'subtest', 'native', binary):
                        nested.fail('retained nested failure')

        nested_result = unittest.TestResult()
        NestedFailure().run(nested_result)
        self.assertEqual(len(nested_result.failures), 1)
        self.assertIn('retained nested failure', nested_result.failures[0][1])
        self.assertEqual([entry['result'] for entry in subtest_matrix], ['fail'])

    def test_matrix_finish_always_emits_and_cleans_up(self):
        calls = []

        def emit(_matrix):
            calls.append('emit')
            raise RuntimeError('diagnostic failure must not replace validation')

        def cleanup():
            calls.append('cleanup')

        with self.assertRaisesRegex(AssertionError, 'required matrix cell count'):
            finish_matrix([], {('missing', 'native')}, cleanup, emit)
        self.assertEqual(calls, ['emit', 'cleanup'])

    def test_no_arbitrary_arguments_and_no_output_on_invalid_ancestry(self):
        self.populate()
        for label, binary, qemu in self.architectures():
            with self.subTest(architecture=label, refusal='argument'):
                with self.observed('unexpected-argument', label, binary, qemu,
                                   extra=('unexpected',)) as completed:
                    self.assertEqual(completed.returncode, 2, label)
        run = self.base / 'run'
        run.chmod(0o755)
        try:
            for label, binary, qemu in self.architectures():
                with self.subTest(architecture=label, refusal='mode'):
                    with self.observed('invalid-run-ancestry-mode', label,
                                       binary, qemu) as completed:
                        self.assertEqual(completed.returncode, 2, label)
        finally:
            run.chmod(0o700)
        real = self.base / 'keyboard-attempt-real'
        self.attempt.rename(real)
        self.attempt.symlink_to(real)
        try:
            for label, binary, qemu in self.architectures():
                with self.subTest(architecture=label, refusal='symlink'):
                    with self.observed('symlink-run-ancestry', label,
                                       binary, qemu) as completed:
                        self.assertEqual(completed.returncode, 2, label)
        finally:
            self.attempt.unlink()
            real.rename(self.attempt)


if __name__ == '__main__':
    unittest.main()
