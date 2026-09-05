#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise the generated host installer with an inert transport and metadata."""
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

sys.dont_write_bytecode = True
from installer import BASE, DERIVER, HERE, PINS, REPO, RECEIPT_NAME, STAGE_LIBRARY, derive, pinned_sources
from deployment_receipt import receipt

BOOT = '11111111-1111-4111-8111-111111111111'

SSH = r'''#!/usr/bin/env python3
import json, os, pathlib, signal, sys
root=pathlib.Path(os.environ['FIXTURE'])
case=os.environ['CASE']
command=sys.argv[-1]
candidate=root/'candidate-bytes'
sha=os.environ['CANDIDATE_SHA']
boot='11111111-1111-4111-8111-111111111111'
def action(name):
    with (root/'actions').open('a') as stream: stream.write(name+'\n')
def refuse(): raise SystemExit(2)
if command == 'command -v systemctl >/dev/null && sudo -n true':
    action('preflight')
    if case=='ssh-refused': refuse()
elif command == 'sudo -n cat /proc/sys/kernel/random/boot_id':
    action('boot-id'); print(boot if case!='bad-boot' else 'bad')
elif 'GATE_MODE=' in command:
    import re
    mode=re.search("GATE_MODE='([^']+)'",command).group(1)
    remote=sys.stdin.read()
    if 'boot2_device_guard "$target" "$majmin" "$root_major_minor"' not in remote: refuse()
    if 'a53_no_swap' not in remote: refuse()
    action('gate-'+mode)
    if case==mode+'-refused': refuse()
    if mode=='write':
        action('write-attempt')
        if case=='write-signal': os.kill(os.getppid(),signal.SIGTERM); refuse()
    current=case=='already-current' or mode!='probe'
    value=sha if current else 'a'*64
    fields={'boot2_device_guard':'passed','target_device':'/dev/mmcblk0p31',
        'target_major_minor':'179:31','root_device':'/dev/mmcblk0p29','root_major_minor':'179:29',
        'gate':'passed','mode':mode,'target':'/dev/mmcblk0p31','root':'/dev/mmcblk0p29',
        'boot_id':boot,'power':'1|100|Good|0','target_sha256':value,'already_current':'yes' if current else 'no'}
    for key,value in fields.items(): print(key+'='+value)
    if case=='duplicate-probe' and mode=='probe': print('target_sha256='+'b'*64)
elif 'STAGE_ACTION=' in command:
    import re
    mode=re.search("STAGE_ACTION='([^']+)'",command).group(1)
    remote=sys.stdin.read()
    if 'a53_tmpfs_mount' not in remote or 'a53_no_swap' not in remote: refuse()
    if not command.startswith('sudo -n env ') or '"$owner" == 0' not in remote: refuse()
    action('stage-'+mode)
    if mode=='prepare':
        if case=='stage-refused': refuse()
        (root/'stage').write_bytes(b'')
        print('/dev/shm/.gemini-a53-'+sha+'.abcd1234')
    elif mode=='cleanup':
        if case=='cleanup-refused': refuse()
        (root/'stage').unlink()
    else: refuse()
elif command.startswith('sudo -n /bin/bash -c ') and 'a53-upload' in command:
    action('upload')
    data=sys.stdin.buffer.read()
    if data!=candidate.read_bytes(): refuse()
    (root/'stage').write_bytes(data)
    if case in ('upload-term','upload-int','upload-hup'):
        os.kill(os.getppid(),{'upload-term':signal.SIGTERM,'upload-int':signal.SIGINT,'upload-hup':signal.SIGHUP}[case])
        refuse()
    if case=='upload-refused': refuse()
elif command=="sudo -n dd if='/dev/mmcblk0p31' bs=4M iflag=fullblock count=4 status=none":
    action('readback')
    data=candidate.read_bytes()
    if case=='readback-short': data=data[:512]
    if case=='readback-corrupt': data=b'x'+data[1:]
    if case=='readback-signal': data=data[:512]
    sys.stdout.buffer.write(data);sys.stdout.buffer.flush()
    if case=='readback-signal': os.kill(os.getppid(),signal.SIGTERM); refuse()
elif command=='sudo -n systemctl poweroff':
    action('poweroff')
    if case=='poweroff-refused': refuse()
    if case=='poweroff-disconnect': raise SystemExit(255)
elif command=='true':
    action('reachability')
    if case!='still-reachable': raise SystemExit(255)
else:
    action('UNEXPECTED-TRANSPORT')
    refuse()
'''

VALIDATOR = r'''import os,pathlib
root=pathlib.Path(os.environ['FIXTURE'])
with (root/'actions').open('a') as f:f.write('validate\n')
raise SystemExit(2 if os.environ['CASE']=='validator-refused' else 0)
'''


class InstallerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = pinned_sources()
        cls.temp = tempfile.TemporaryDirectory(prefix='a53-installer-test-', dir='/private/tmp' if Path('/private/tmp').is_dir() else '/tmp')
        cls.root = Path(cls.temp.name)
        cls.repo = cls.root / 'repo'
        cls.tools = cls.repo / HERE.relative_to(REPO)
        cls.tools.mkdir(parents=True)
        cls.candidate = cls.root / ('candidate-' + '1' * 64)
        cls.candidate.mkdir()
        cls.image = cls.candidate / 'boot2-padded.img'
        cls.image.write_bytes(bytes(16777216))
        cls.manifest = cls.candidate / 'candidate.json'
        cls.manifest.write_text('{"fixture":"no private key or real kernel"}\n')
        cls.sha = hashlib.sha256(cls.image.read_bytes()).hexdigest()
        cls.manifest_sha = hashlib.sha256(cls.manifest.read_bytes()).hexdigest()
        # The transport streams this synthetic image, never a device read.
        (cls.root / 'candidate-bytes').symlink_to(cls.image)
        (cls.tools / 'validate-candidate.py').write_text(VALIDATOR)
        shutil.copyfile(HERE / 'deployment_receipt.py', cls.tools / 'deployment_receipt.py')
        old_parser = Path('experiments/2026-09-04-mt6797-thermal-snapshot/scripts/v4_deployment_receipt.py')
        (cls.repo / old_parser).parent.mkdir(parents=True)
        shutil.copyfile(REPO / old_parser, cls.repo / old_parser)
        key = cls.repo / 'artifacts/credentials/gemini_ed25519'
        key.parent.mkdir(parents=True)
        key.write_text('inert test identity; never used by SSH\n')
        key.chmod(0o600)
        cls.trust = key.parent / 'a53-recovery-known_hosts'
        cls.trust.write_text('inert pinned trust fixture; no real host identity\n')
        cls.trust.chmod(0o600)
        cls.evidence_root = cls.repo / 'artifacts/device-install-evidence'
        cls.evidence_root.mkdir()
        cls.evidence = cls.evidence_root / RECEIPT_NAME
        cls.bin = cls.root / 'bin'
        cls.bin.mkdir()
        for name, source in {'ssh': SSH, 'git': '#!/bin/sh\nexit 0\n',
                             'sleep': '#!/bin/sh\nexit 0\n', 'sync': '#!/bin/sh\nexit 0\n'}.items():
            path = cls.bin / name
            path.write_text(source)
            path.chmod(0o700)
        cls.source = derive(cls.sources, cls.repo, cls.candidate, cls.candidate, cls.candidate)
        cls.source = cls.source.replace('d43262bd1f9c76d02eb633900f5e5502e2342d6c1b41586a2d7e524a2293768f', hashlib.sha256(cls.trust.read_bytes()).hexdigest())
        cls.script = cls.root / 'install.sh'
        cls.script.write_text(cls.source)
        subprocess.run(['bash', '-n', str(cls.script)], check=True)
        subprocess.run(['shellcheck', str(cls.script)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_case(self, case, extra=()):
        if self.evidence.is_symlink():
            self.evidence.unlink()
        elif self.evidence.exists():
            shutil.rmtree(self.evidence)
        (self.root / 'actions').write_text('')
        (self.root / 'stage').unlink(missing_ok=True)
        if case == 'existing-evidence':
            self.evidence.mkdir()
        if case == 'symlink-evidence':
            self.evidence.symlink_to(self.evidence_root)
        env = dict(os.environ, FIXTURE=str(self.root), CASE=case, CANDIDATE_SHA=self.sha,
                   PATH=str(self.bin) + os.pathsep + os.environ['PATH'], PYTHONDONTWRITEBYTECODE='1')
        result = subprocess.run(['bash', str(self.script), '--target', 'gemini@192.168.1.50',
                                 '--candidate-dir', str(self.candidate), '--evidence-dir', str(self.evidence), *extra],
                                env=env, text=True, capture_output=True, timeout=20)
        actions = (self.root / 'actions').read_text().splitlines()
        self.assertNotIn('UNEXPECTED-TRANSPORT', actions)
        return result, actions

    def test_explicit_trust_and_root_stage_contract(self):
        for option in ('-F /dev/null', 'StrictHostKeyChecking=yes',
                       'UserKnownHostsFile=$recovery_trust', 'GlobalKnownHostsFile=/dev/null',
                       'UpdateHostKeys=no'):
            self.assertIn(option, self.source)
        self.assertIn('"$owner" == 0', STAGE_LIBRARY)
        self.assertNotIn('id -u gemini', STAGE_LIBRARY)

    def test_host_success_and_skip(self):
        for case in ('pass', 'already-current', 'poweroff-disconnect'):
            with self.subTest(case=case):
                result, actions = self.run_case(case)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(actions.count('write-attempt'), 0 if case == 'already-current' else 1)
                self.assertEqual(actions.count('upload'), 0 if case == 'already-current' else 1)
                self.assertLess(actions.index('readback'), actions.index('poweroff'))
                self.assertFalse((self.root / 'stage').exists())
                self.assertFalse((self.evidence / '.boot2-readback.partial').exists())
                raw = (self.evidence / 'deployment-summary.txt').read_text()
                self.assertEqual(receipt(raw, self.sha, self.manifest_sha), BOOT)

    def test_host_failures_and_interruptions(self):
        cases = ('validator-refused', 'existing-evidence', 'symlink-evidence', 'ssh-refused', 'bad-boot',
                 'probe-refused', 'duplicate-probe', 'stage-refused', 'upload-refused',
                 'upload-term', 'upload-int', 'upload-hup', 'write-refused', 'write-signal',
                 'cleanup-refused', 'post-refused', 'readback-short', 'readback-corrupt',
                 'readback-signal', 'poweroff-refused', 'still-reachable')
        for case in cases:
            with self.subTest(case=case):
                result, actions = self.run_case(case)
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertLessEqual(actions.count('write-attempt'), 1)
                if case not in ('poweroff-refused', 'still-reachable'):
                    self.assertNotIn('poweroff', actions)
                if case in ('validator-refused', 'existing-evidence', 'symlink-evidence'):
                    self.assertNotIn('preflight', actions)
                if case != 'cleanup-refused':
                    self.assertFalse((self.root / 'stage').exists())
                self.assertFalse((self.evidence / '.boot2-readback.partial').exists())
                summary = self.evidence / 'deployment-summary.txt'
                if summary.is_file():
                    with self.assertRaises(ValueError):
                        receipt(summary.read_text(), self.sha, self.manifest_sha)

    def test_bad_arguments(self):
        result, actions = self.run_case('duplicate-target', ('--target', 'other'))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(actions, [])

    def test_local_identity_refusals_precede_transport(self):
        key = self.repo / 'artifacts/credentials/gemini_ed25519'
        for path, kind in ((self.image, 'byte'), (self.manifest, 'byte'),
                           (self.tools / 'validate-candidate.py', 'byte'), (self.trust, 'byte'), (key, 'mode')):
            with self.subTest(path=path.name, kind=kind):
                if kind == 'byte':
                    with path.open('r+b') as stream:
                        saved = stream.read(1)
                        stream.seek(0)
                        stream.write(bytes([saved[0] ^ 1]))
                else:
                    path.chmod(0o644)
                try:
                    result, actions = self.run_case('local-identity-refusal')
                    self.assertNotEqual(result.returncode, 0)
                    self.assertNotIn('preflight', actions)
                finally:
                    if kind == 'byte':
                        with path.open('r+b') as stream:
                            stream.write(saved)
                    else:
                        path.chmod(0o600)

    def test_exact_derivation_pins(self):
        for path in PINS:
            with self.subTest(path=path):
                altered = dict(self.sources)
                altered[path] += b'\n'
                with self.assertRaises(ValueError):
                    derive(altered, self.repo, self.candidate, self.candidate, self.candidate)

    def test_receipt_binding_mutations(self):
        result, _ = self.run_case('pass')
        self.assertEqual(result.returncode, 0, result.stderr)
        raw = (self.evidence / 'deployment-summary.txt').read_text()
        for key in ('experiment', 'candidate_manifest_sha256', 'candidate_sha256', 'readback_sha256',
                    'target_major_minor', 'root_major_minor', 'post_shutdown_reachability'):
            lines = raw.splitlines()
            entry = next(line for line in lines if line.startswith(key + '='))
            for mutation in ('\n'.join(line for line in lines if line != entry), raw + entry + '\n', raw.replace(entry, key + '=wrong')):
                with self.subTest(key=key, mutation=mutation[:20]):
                    with self.assertRaises(ValueError):
                        receipt(mutation, self.sha, self.manifest_sha)
        with self.assertRaises(ValueError):
            receipt(raw, self.sha, 'f' * 64)

    def test_cli_never_defaults_to_transport(self):
        env = dict(os.environ, FIXTURE=str(self.root), CASE='pass', CANDIDATE_SHA=self.sha,
                   PATH=str(self.bin) + os.pathsep + os.environ['PATH'], PYTHONDONTWRITEBYTECODE='1')
        (self.root / 'actions').write_text('')
        command = [sys.executable, str(HERE / 'install-boot2.py'), '--candidate', str(self.candidate),
                   '--foundation', str(self.candidate), '--userspace', str(self.candidate)]
        for extra in ([], ['--execute'], ['--execute', '--target', 'other']):
            result = subprocess.run(command + extra, env=env, capture_output=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual((self.root / 'actions').read_text(), '')

    def test_cli_forwards_signals_and_reaps_transport(self):
        for number in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM):
            with self.subTest(signal=number):
                ready = self.root / 'child-ready'
                stopped = self.root / 'child-stopped'
                ready.unlink(missing_ok=True)
                stopped.unlink(missing_ok=True)
                child = 'import os,pathlib,signal,sys,time\n' + \
                    'def stop(n,f):\n pathlib.Path(sys.argv[2]).write_text(str(n));sys.exit(128+n)\n' + \
                    'for n in (signal.SIGHUP,signal.SIGINT,signal.SIGTERM):signal.signal(n,stop)\n' + \
                    'pathlib.Path(sys.argv[1]).write_text(str(os.getpid()))\ntime.sleep(10)\n'
                runner = 'import runpy,sys; sys.path.insert(0,' + repr(str(HERE)) + '); ' + \
                    'runpy.run_path(' + repr(str(HERE / 'install-boot2.py')) + ')["run_installer"](' + \
                    repr([sys.executable, '-c', child, str(ready), str(stopped)]) + ')'
                process = subprocess.Popen([sys.executable, '-B', '-c', runner], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                           start_new_session=True)
                try:
                    deadline = time.monotonic() + 5
                    while not ready.exists() and process.poll() is None and time.monotonic() < deadline:
                        time.sleep(0.01)
                    self.assertTrue(ready.exists(), 'transport child never started')
                    os.kill(process.pid, number)
                    output, error = process.communicate(timeout=5)
                    self.assertNotEqual(process.returncode, 0, output)
                    self.assertIn(b'deployment interrupted', error)
                    self.assertEqual(stopped.read_text(), str(number))
                    with self.assertRaises(ProcessLookupError):
                        os.kill(int(ready.read_text()), 0)
                finally:
                    if process.poll() is None:
                        process.kill()
                    process.communicate()


if __name__ == '__main__':
    unittest.main(verbosity=2)
