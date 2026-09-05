#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Synthetic immutable proof refusal fixtures; no timing run or transport."""
import json
from pathlib import Path
import runpy
import tempfile
import struct
import shutil
import gc
import subprocess
import shlex
import time
from types import SimpleNamespace
from unittest.mock import patch
import unittest

HERE = Path(__file__).resolve().parent
P = runpy.run_path(str(HERE / 'duration-proof.py'))
WORK = HERE.parents[2] / 'artifacts/a53-authenticated/development/duration-proof'


class ProofTests(unittest.TestCase):
    def setUp(self):
        WORK.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=WORK)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.sources = P['sources']()
        output = b'fixture-child=123\nfixture-observation-boundary=202000\n'
        self.status = {'schema': 'keyboard-monitor-v1', 'reason': 'deadline', 'reaped': '1',
                       'identity_lost': '0', 'exit': '-1', 'signal': '9', 'cancel': '0',
                       'term_errno': '0', 'kill_errno': '0', 'late': '0', 'stderr_bytes': '0',
                       'term_ms': '209001', 'kill_ms': '213001', 'reap_ms': '213002',
                       'stdout_bytes': str(len(output)), 'forwarded_bytes': str(len(output))}
        self.inputs = {'schema': 'keyboard-duration-inputs-v1', 'sources': self.sources,
                       'mode': 'harmless-ignore-production-duration-arm64-qemu',
                       'musl_archive_sha256': 'd585fd3b613c66151fc3249e8ed44f77020cb5e6c1e635a616d3f9f82460512a',
                       'tool_inputs_sha256': 'd'*64,
                       'fixture_sha256': P['sha'](b'synthetic fixture'),
                       'tools': {'compiler': 'a'*64, 'qemu': 'b'*64}, 'library': {'lib/libc.a': 'c'*64, 'bin/musl-gcc': 'a'*64}}
        self.raw = {'inputs.json': b'', 'process.json': json.dumps({'returncode': 2,
                    'elapsed_seconds': 213.1, 'error': None}).encode(), 'fixture': b'synthetic fixture',
                    'stdout': output, 'stderr': b'', 'observer.stdout': output,
                    'observer.stderr': b'', 'monitor.status': b''}

    def save(self):
        self.raw['inputs.json'] = json.dumps(self.inputs).encode()
        self.raw['monitor.status'] = ''.join(k+'='+v+'\n' for k,v in self.status.items()).encode()
        for name, raw in self.raw.items():
            (self.root/name).write_bytes(raw)
        (self.root/'SHA256SUMS').unlink(missing_ok=True)
        P['seal'](self.root)

    def classify(self):
        return P['classify'](self.root, self.sources)

    def test_complete_expected_forced_lifecycle(self):
        self.save()
        self.assertEqual(self.classify()['classification'], 'passed')
        self.assertEqual(self.classify()['device_action'], 'none')

    def test_each_control_failure_refuses(self):
        for key in ('reaped', 'identity_lost', 'exit', 'signal', 'cancel', 'term_errno', 'kill_errno', 'late', 'reason'):
            with self.subTest(key=key):
                original = self.status[key]
                self.status[key] = 'unexpected'
                self.save()
                self.assertEqual(self.classify()['classification'], 'failed')
                self.status[key] = original

    def test_early_late_and_unordered_times(self):
        for key,value in [('term_ms','208999'),('term_ms','210001'),('kill_ms','212999'),
                          ('kill_ms','214001'),('reap_ms','213000'),('reap_ms','215001')]:
            with self.subTest(key=key,value=value):
                original=self.status[key]
                self.status[key]=value
                self.save()
                self.assertEqual(self.classify()['classification'],'failed')
                self.status[key]=original

    def test_missing_truncated_or_mutated_bytes(self):
        self.save()
        (self.root/'stdout').write_bytes(b'')
        with self.assertRaisesRegex(ValueError,'checksum'):self.classify()
        self.save()
        (self.root/'stderr').unlink()
        with self.assertRaisesRegex(ValueError,'inventory'):self.classify()

    def test_source_and_binary_mismatch(self):
        self.inputs['sources'] = {**self.sources,'monitor.c':'f'*64}
        self.save()
        with self.assertRaisesRegex(ValueError,'source mismatch'):self.classify()
        self.inputs['sources']=self.sources
        self.inputs['fixture_sha256']='f'*64
        self.save()
        with self.assertRaisesRegex(ValueError,'fixture identity'):self.classify()

    def test_incomplete_process_and_forwarding(self):
        for name,value in [('process.json',b'{"error":"outer timeout","returncode":null,"elapsed_seconds":226}'),
                           ('stdout',b''),('observer.stderr',b'error')]:
            original=self.raw[name]
            self.raw[name]=value
            self.save()
            self.assertEqual(self.classify()['classification'],'failed')
            self.raw[name]=original

    def test_duplicate_status_and_inventory_refuse(self):
        self.save()
        self.raw['monitor.status']=(self.root/'monitor.status').read_bytes()+b'late=0\n'
        (self.root/'monitor.status').write_bytes(self.raw['monitor.status'])
        (self.root/'SHA256SUMS').unlink()
        P['seal'](self.root)
        self.assertEqual(self.classify()['classification'],'failed')
        (self.root/'extra').touch()
        with self.assertRaisesRegex(ValueError,'inventory'):self.classify()

    def runner_fixture(self, fault=None, completed=False):
        runner = runpy.run_path(str(HERE / 'full-duration.py'))
        root = self.root
        binary = bytearray(120)
        binary[:6] = b'\x7fELF\x02\x01'
        struct.pack_into('<H', binary, 18, 183)
        struct.pack_into('<Q', binary, 32, 64)
        struct.pack_into('<HH', binary, 54, 56, 1)
        struct.pack_into('<I', binary, 64, 1)
        fixture = root / 'fixture-build'
        fixture.write_bytes(binary)
        tool = root / 'tool'
        tool.write_bytes(b'synthetic tool')
        library = root / 'library'
        (library / 'bin').mkdir(parents=True)
        (library / 'bin/musl-gcc').write_bytes(b'synthetic tool')
        events = []
        class Fake:
            def __init__(self, _name):
                pass
            @classmethod
            def setUpClass(cls):
                cls.fixture = fixture
            def setUp(self):
                self.root = root / 'case'
                (self.root / 'keyboard-attempt').mkdir(parents=True)
            def run_case(self, mode):
                self.last_run = {'process': SimpleNamespace(returncode=2 if completed else None),
                                 'stdout': bytearray(b'partial raw bytes'), 'stderr': bytearray(b''),
                                 'start': time.monotonic() - (213 if completed else 226)}
                (self.root / 'keyboard-attempt/observer.stdout').write_bytes(
                    b'x' * 131073 if fault == 'oversize' else b'partial raw bytes')
                if not completed:
                    raise AssertionError('outer fixture deadline')
            def doCleanups(self):
                P['require']((root / 'proof/SHA256SUMS').is_file(), 'cleanup preceded evidence')
                shutil.rmtree(self.root)
                events.append('case-cleanup')
                return True
            @classmethod
            def doClassCleanups(cls):
                fixture.unlink()
                events.append('build-cleanup')
                cls.tearDown_exceptions = []
        argv = ['full-duration.py', '--compiler', str(tool), '--qemu', str(tool),
                '--library-root', str(library), '--work-root', str(root), '--output', str(root/'proof'),
                '--tool-inputs', str(tool), '--musl-archive', str(tool),
                '--cleanup-receipt', str(root/'duration-cleanup-safe')]
        helpers = runner['main'].__globals__['P']
        original_read, original_write = helpers['read'], helpers['write']
        def read(path, bound=2097152):
            if fault == 'read' and path.name == 'observer.stdout':
                raise OSError('injected read failure')
            return original_read(path, bound)
        def write(path, raw):
            if fault == 'first-write':
                raise OSError('injected first write failure')
            if fault == 'fsync':
                with patch('os.fsync', side_effect=OSError('injected fsync failure')):
                    return original_write(path, raw)
            if fault == 'partial-write' and path.name == 'stdout':
                original_write(path, raw[:3])
                raise OSError('injected partial write failure')
            return original_write(path, raw)
        def seal(_path):
            raise OSError('injected seal failure')
        overrides = {'read': read, 'write': write}
        if fault == 'seal': overrides['seal'] = seal
        with patch('sys.argv', argv), patch('runpy.run_path', return_value={'MonitorTests': Fake}), \
                patch.dict('os.environ', {}, clear=False), patch.dict(helpers, overrides):
            message = ('proof file type/size' if fault == 'oversize' else 'injected') if fault else ('build input binding' if completed else 'terminal state uncertain')
            with self.assertRaisesRegex((ValueError, OSError), message):
                runner['main']()
        return events

    def test_uncertain_process_retains_sealed_proof_and_originals(self):
        self.assertEqual(self.runner_fixture(), [])
        self.assertTrue((self.root/'proof/SHA256SUMS').is_file())
        self.assertTrue((self.root/'fixture-build').is_file())
        self.assertEqual((self.root/'case/keyboard-attempt/observer.stdout').read_bytes(), b'partial raw bytes')
        self.assertFalse((self.root/'duration-cleanup-safe').exists())

    def test_proof_io_failures_preserve_originals(self):
        for fault in ('read', 'oversize', 'first-write', 'partial-write', 'fsync', 'seal'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory(dir=WORK) as temporary:
                original = self.root
                self.root = Path(temporary)
                try:
                    self.assertEqual(self.runner_fixture(fault=fault, completed=True), [])
                    self.assertTrue((self.root/'fixture-build').is_file())
                    self.assertEqual((self.root/'case/keyboard-attempt/observer.stdout').read_bytes(),
                                     b'x' * 131073 if fault == 'oversize' else b'partial raw bytes')
                    self.assertFalse((self.root/'proof/SHA256SUMS').exists())
                    self.assertFalse((self.root/'duration-cleanup-safe').exists())
                    if fault == 'partial-write':
                        self.assertEqual((self.root/'proof/stdout').read_bytes(), b'par')
                finally:
                    self.root = original

    def test_sealed_terminal_run_allows_explicit_cleanup(self):
        self.assertEqual(self.runner_fixture(completed=True), ['case-cleanup', 'build-cleanup'])
        self.assertTrue((self.root/'proof/SHA256SUMS').is_file())
        self.assertFalse((self.root/'fixture-build').exists())
        self.assertFalse((self.root/'case').exists())
        self.assertEqual((self.root/'duration-cleanup-safe').read_bytes(), b'sealed-terminal-cleanup-complete\n')

    def test_retained_harness_directories_have_no_auto_cleanup(self):
        with patch.dict('os.environ', {'MONITOR_TEST_FIXTURE_ONLY': '1',
                                      'MONITOR_TEST_WORK_ROOT': str(self.root)}):
            harness = runpy.run_path(str(HERE/'test-monitor.py'))
        directory = harness['temporary']('retained-')
        path = Path(directory.name)
        (path/'original').write_bytes(b'evidence')
        del directory
        gc.collect()
        self.assertEqual((path/'original').read_bytes(), b'evidence')
        # Also exercise interpreter shutdown, where TemporaryDirectory finalizers run.
        child = subprocess.run(['python3', '-c',
            'import runpy; m=runpy.run_path('+repr(str(HERE/'test-monitor.py'))+'); '
            'd=m["temporary"]("exit-"); print(d.name)'],
            env={**__import__('os').environ, 'MONITOR_TEST_FIXTURE_ONLY':'1',
                 'MONITOR_TEST_WORK_ROOT':str(self.root)}, capture_output=True, text=True, timeout=2, check=True)
        self.assertTrue(Path(child.stdout.strip()).is_dir())

    def test_shell_timeout_and_missing_proof_retain_whole_stage(self):
        source = (HERE/'build-monitor.sh').read_text()
        cleanup = source[source.index('cleanup() {'):source.index('trap cleanup EXIT')]
        stale = source[source.index('[[ ! -L $stage ]]'):source.index('[[ ! -e $stage ]] || rm')]
        for code, receipt, retained in ((0,True,False),(0,False,True),(1,True,True),
                                         (124,True,True),(137,False,True),(143,True,True)):
            with self.subTest(code=code,receipt=receipt), tempfile.TemporaryDirectory(dir=WORK) as temporary:
                root=Path(temporary)
                stage=root/'.keyboard-duration-stage'
                (stage/'fixtures/case').mkdir(parents=True)
                (stage/'fixtures/case/original').write_bytes(b'evidence')
                if receipt:(stage/'duration-cleanup-safe').write_text('sealed-terminal-cleanup-complete\n')
                prefix='set -euo pipefail\nkind=keyboard-duration\nrevision='+('a'*40)+'\nmanaged='+shlex.quote(str(root))+'\nstage='+shlex.quote(str(stage))+'\n'
                result=subprocess.run(['bash'],input=prefix+cleanup+'trap cleanup EXIT\nexit '+str(code)+'\n',
                                      text=True,capture_output=True,timeout=2)
                self.assertEqual(stage.exists(),retained)
                self.assertEqual(result.returncode, code if code else (2 if retained else 0))
                if retained:
                    self.assertEqual((stage/'fixtures/case/original').read_bytes(), b'evidence')
                    refusal=subprocess.run(['bash'],input=prefix+stale,text=True,capture_output=True,timeout=2)
                    self.assertNotEqual(refusal.returncode,0)
                    self.assertEqual((stage/'fixtures/case/original').read_bytes(),b'evidence')

    def test_symlink_and_overwrite_refuse(self):
        self.save()
        with self.assertRaises(FileExistsError):P['seal'](self.root)
        (self.root/'stderr').unlink()
        (self.root/'stderr').symlink_to(self.root/'stdout')
        with self.assertRaisesRegex(ValueError,'type/size'):self.classify()


if __name__ == '__main__':unittest.main()
