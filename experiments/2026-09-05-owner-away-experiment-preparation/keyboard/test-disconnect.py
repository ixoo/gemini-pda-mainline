#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Host-only disconnect protocol, parser and semantic-receipt fixtures."""
import argparse
import base64
import copy
import hashlib
import json
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
D = runpy.run_path(str(HERE/'disconnect.py'))
WORK = HERE.parents[2]/'artifacts/a53-authenticated/development/keyboard-disconnect-tests'

_parser = argparse.ArgumentParser(add_help=False)
_parser.add_argument('--busybox', type=Path)
_parser.add_argument('--qemu', default='qemu-aarch64-static')
_options, _remaining = _parser.parse_known_args()
sys.argv = [sys.argv[0], *_remaining]
SHELL = ['/bin/sh']
if _options.busybox is not None:
    if hashlib.sha256(_options.busybox.read_bytes()).hexdigest() != \
            '52151e7f322f926b64049cdaa1410dc3ea6485525e0624b05813791c219ae933':
        raise ValueError('exact candidate BusyBox required')
    qemu = shutil.which(_options.qemu)
    if qemu is None:
        raise ValueError('requested QEMU unavailable')
    SHELL = [qemu, str(_options.busybox), 'sh']
SHELLCHECK = shutil.which('shellcheck')
if SHELLCHECK is None:
    raise ValueError('ShellCheck required')


class DisconnectTests(unittest.TestCase):
    def setUp(self):
        WORK.mkdir(mode=0o700,parents=True,exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=WORK)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_runner_kills_one_no_pty_client_immediately_after_marker(self):
        program = ('import sys,time\n'
            'sys.stdin.buffer.read()\n'
            'sys.stdout.write("fixture-child=42\\n");sys.stdout.flush()\n'
            'time.sleep(30)\n')
        result = D['deliberate_disconnect']([sys.executable,'-c',program],b'complete\n',self.root)
        self.assertEqual({k:v for k,v in result.items() if k != 'elapsed_milliseconds' and
            not k.startswith('_')},{'schema':'keyboard-disconnect-transport-v1',
            'classification':'deliberate-client-disconnect','connections':1,'no_pty':True,
            'marker_seen':True,'stdin_complete':True,'client_signal':9})
        self.assertLessEqual(result['elapsed_milliseconds'],100)
        self.assertTrue(result['_stderr_empty'])
        self.assertTrue(result['_streams_complete'])

    def test_early_marker_retains_refusal_instead_of_raising(self):
        program = ('import sys,time\n'
            'sys.stdout.write("fixture-child=43\\n");sys.stdout.flush()\n'
            'time.sleep(30)\n')
        result = D['deliberate_disconnect']([sys.executable,'-c',program],b'x'*262144,self.root)
        self.assertTrue(result['marker_seen'])
        self.assertFalse(result['stdin_complete'])
        self.assertEqual(result['client_signal'],9)
        self.assertEqual((self.root/'stdout.txt').read_bytes(),b'fixture-child=43\n')

    def test_export_refusal_reports_stage_and_preserves_exit_status(self):
        context = {'admission': {'boot_id': '33333333-3333-3333-3333-333333333333'},
                   'candidate': {}}
        for stage, identity, ram in (
                ('identity', 'set -eu\nexit 7\n', ''),
                ('ram-guard', 'set -eu\n', 'exit 8\n'),
                ('attempt-path', 'set -eu\n', '')):
            with self.subTest(stage=stage), patch.dict(D['S'], {
                    'identity_script': lambda *a: identity,
                    'ram_guard_script': lambda: ram}):
                if stage == 'attempt-path':
                    (self.root/'real').mkdir()
                    (self.root/'absent').symlink_to(self.root/'real', target_is_directory=True)
                script = D['export_script'](context).replace(
                    b'/a53-keyboard-disconnect', str(self.root/'absent').encode())
                result = subprocess.run(SHELL + ['-s'], input=script,
                                        capture_output=True, timeout=2)
                expected = {'identity': 7, 'ram-guard': 8, 'attempt-path': 1}[stage]
                self.assertEqual(result.returncode, expected)
                self.assertEqual(result.stdout, b'')
                self.assertEqual(result.stderr,
                    f'keyboard-disconnect-export stage={stage} exit={expected}\n'.encode())

    def test_export_parser_requires_complete_ordered_members(self):
        files = {'observer.stdout':b'fixture-child=8\n','observer.stderr':b'',
            'monitor.status':b'schema=keyboard-monitor-v1\n','outer-exit':b'2\n'}
        raw = b'scan-processes=4\nscan-descriptors=9\n' + b''.join(
            ('file='+name+'\n').encode()+base64.b64encode(files[name])+b'\n'+
            ('end='+name+'\n').encode() for name in D['FILES'])
        parsed,scan = D['parse_export'](raw)
        self.assertEqual(parsed,files)
        self.assertEqual((scan['processes_scanned'],scan['descriptors_scanned'],scan['matches']),
            (4,9,[]))
        for changed in (raw+b'extra\n',raw.replace(b'scan-processes=4',b'scan-processes=513'),raw[:-4]):
            with self.assertRaises(ValueError): D['parse_export'](changed)

    def test_receipt_is_accepted_only_with_raw_lifecycle_evidence(self):
        status = (b'schema=keyboard-monitor-v1\nreason=cancelled\nreaped=1\nidentity_lost=0\n'
            b'exit=-1\nsignal=1\ncancel=1\nterm_ms=-1\nkill_ms=-1\nreap_ms=40\n'
            b'term_errno=0\nkill_errno=0\nlate=0\nstdout_bytes=17\nstderr_bytes=0\nforwarded_bytes=17\n')
        evidence = {'observer.stdout':b'fixture-child=12\n','observer.stderr':b'',
            'monitor.status':status,'outer-exit':b'2\n',
            'disconnect-process.json':D['encode']({'schema':'keyboard-disconnect-transport-v1',
                'classification':'deliberate-client-disconnect','connections':1,'no_pty':True,
                'marker_seen':True,'stdin_complete':True,'client_signal':9,'elapsed_milliseconds':1}),
            'export-process.json':D['encode']({'exit_status':0,'reason':None,'stdin_complete':True,
                'stdout_bytes':500,'stderr_bytes':0,'elapsed_seconds':1}),
            'reader-scan.json':D['encode']({'schema':'keyboard-reader-release-v1',
                'classification':'passed','admission_id':'1'*8+'-'+ '1'*4+'-'+ '1'*4+'-'+ '1'*4+'-'+ '1'*12,
                'boot_id':'2'*8+'-'+ '2'*4+'-'+ '2'*4+'-'+ '2'*4+'-'+ '2'*12,
                'processes_scanned':4,'descriptors_scanned':9,'matches':[]})}
        for name,raw in evidence.items(): (self.root/name).write_bytes(raw)
        admission_id = '11111111-1111-1111-1111-111111111111'
        boot_id = '22222222-2222-2222-2222-222222222222'
        candidate = {'files':{'boot.img':'3'*64},'members':{
            'bin/dropbear':{'sha256':'4'*64},'bin/admin-shell':{'sha256':'5'*64}}}
        admission = {'id':admission_id,'boot_id':boot_id,'package_identity':'6'*64,
            'package_revision':'revision','monitor_sha256':'7'*64,'probe_sha256':'8'*64}
        context = {'admission':admission,'candidate':candidate}
        value = D['receipt'](context,evidence); raw = D['encode'](value)
        accepted = D['P']['disconnect'](raw,D['sha'](raw),admission,candidate,
            {'keyboard-disconnect-probe':'8'*64},self.root,
            lambda path,limit:Path(path).read_bytes())
        self.assertEqual(accepted['classification'],'passed')
        forced = status.replace(b'signal=1\ncancel=1\nterm_ms=-1\nkill_ms=-1\nreap_ms=40',
            b'signal=9\ncancel=1\nterm_ms=10\nkill_ms=90\nreap_ms=100')
        evidence['monitor.status'] = forced
        (self.root/'monitor.status').write_bytes(forced)
        forced_value = D['receipt'](context,evidence); forced_raw = D['encode'](forced_value)
        forced_accepted = D['P']['disconnect'](forced_raw,D['sha'](forced_raw),admission,candidate,
            {'keyboard-disconnect-probe':'8'*64},self.root,
            lambda path,limit:Path(path).read_bytes())
        self.assertEqual(forced_accepted['process']['monitor_reaped'],True)
        evidence['monitor.status'] = forced.replace(b'reap_ms=100',b'reap_ms=600')
        (self.root/'monitor.status').write_bytes(evidence['monitor.status'])
        changed = D['receipt'](context,evidence); changed_raw = D['encode'](changed)
        with self.assertRaises(ValueError):
            D['P']['disconnect'](changed_raw,D['sha'](changed_raw),admission,candidate,
                {'keyboard-disconnect-probe':'8'*64},self.root,
                lambda path,limit:Path(path).read_bytes())

    def test_generated_first_command_never_names_evdev_or_vt(self):
        candidate = {'members':{'bin/dropbear':{'sha256':'1'*64},
            'bin/admin-shell':{'sha256':'2'*64}}}
        context = {'admission':{'boot_id':'33333333-3333-3333-3333-333333333333'},
            'candidate':candidate,'probe':b'harmless'}
        with patch.dict(D['S'],{'identity_script':lambda *a:'identity\n',
            'ram_guard_script':lambda :'ram\n'}):
            raw = D['first_script'](context)
            exported = D['export_script'](context)
        self.assertNotIn(b'/dev/input',raw)
        self.assertNotIn(b'/dev/tty',raw)
        self.assertIn(base64.b64encode(b'harmless'),raw)
        self.assertIn(b'/a53-keyboard-disconnect/probe /a53-keyboard-disconnect/run ignore',raw)
        self.assertNotIn(b'/a53-keyboard-disconnect/run wait',raw)
        self.assertIn(b'*/a53-keyboard-disconnect/probe*|*/bin/keyboard-observe*',exported)
        self.assertIn(b'/a53-keyboard-disconnect/probe\\ \\(deleted\\)',exported)
        self.assertNotIn(b'*keyboard-disconnect-probe*',exported)
        for script in (raw,exported):
            checked = subprocess.run(SHELL + ['-n'],input=script,capture_output=True)
            self.assertEqual((checked.returncode,checked.stderr),(0,b''))
            linted = subprocess.run([SHELLCHECK,'-s','sh','-e','SC2016','-'],
                input=script,capture_output=True)
            self.assertEqual((linted.returncode,linted.stdout,linted.stderr),(0,b'',b''))

    def test_execution_gate_precedes_context_claim_and_transport(self):
        admission = {name: value for name, value in {
            'schema':'keyboard-disconnect-admission-v1',
            'id':'11111111-1111-1111-1111-111111111111',
            'boot_id':'22222222-2222-2222-2222-222222222222',
            'source_identity':{
                'local_and_direct':{
                    'capture.py':'7'*64,'prerequisites.py':'8'*64,
                    'disconnect.py':'9'*64,'monitor.c':'a'*64,
                    'delivery.py':'b'*64,'classify.py':'c'*64,
                    'protocol.json':'d'*64},
                'emmc_launcher':{'launcher_sha256':'e'*64,'pins_sha256':'f'*64},
                'pinned_members':{'baseline/scripts/collect-baseline.py':'1'*64}},
            'dependency':{
                'baseline_admission_id':'33333333-3333-3333-3333-333333333333',
                'baseline_manifest_sha256':'2'*64,
                'confirmation_manifest_sha256':'3'*64,
                'candidate_manifest_sha256':'4'*64,
                'deployment_receipt_sha256':'5'*64,
                'prerequisite_selector':'reviewed-supplemental',
                'prerequisite_phase_manifests':{
                    'auth-checks':'6'*64,'preserve-log':'7'*64,
                    'request-recovery':'8'*64}},
            'package_identity':'9'*64,'package_revision':'revision-93e2b852',
            'monitor_sha256':'a'*64,'monitor_bytes':66672,
            'probe_sha256':'b'*64,'probe_bytes':66760,
            'custody':{
                'exclusive':True,'no_other_device_operations':True,
                'stable_power':True,'physical_selection':True,
                'screen_readable':True,'owner_ready':True}}.items()}
        globals_ = D['execution_gate'].__globals__

        def binding(value):
            path = self.root/'binding.json'
            path.write_bytes(value)
            return path

        def refused(value, value_admission=admission):
            with patch.dict(globals_, {'BINDING':binding(value)}):
                with self.assertRaises((OSError, ValueError, TypeError)):
                    D['execution_gate'](value_admission)

        refused(D['encode']({'schema':'keyboard-disconnect-execution-binding-v1',
            'state':'disabled','admission':None}))
        missing = self.root/'missing.json'
        with patch.dict(globals_, {'BINDING':missing}):
            with self.assertRaises(OSError): D['execution_gate'](admission)
        target = self.root/'target.json'; target.write_bytes(b'{}')
        link = self.root/'symlink.json'; link.symlink_to(target)
        with patch.dict(globals_, {'BINDING':link}):
            with self.assertRaises(ValueError): D['execution_gate'](admission)
        refused(b'{}'*8193)
        for raw in (b'not-json\n',
                    b'{"schema":"keyboard-disconnect-execution-binding-v1",'
                    b'"state":"disabled","admission":null,"extra":1}',
                    b'{"schema":"wrong","state":"disabled","admission":null}',
                    b'{"schema":"keyboard-disconnect-execution-binding-v1",'
                    b'"state":"armed","admission":null}',
                    b'{"schema":"keyboard-disconnect-execution-binding-v1",'
                    b'"state":"enabled","admission":null}',
                    b'{"schema":"keyboard-disconnect-execution-binding-v1",'
                    b'"state":"disabled","admission":null,"state":"enabled"}'):
            refused(raw)

        enabled = D['encode']({'schema':'keyboard-disconnect-execution-binding-v1',
            'state':'enabled','admission':admission})
        with patch.dict(globals_, {'BINDING':binding(enabled)}):
            with patch.dict(globals_, {'prepare':lambda *args: (_ for _ in ()).throw(
                    AssertionError('prepare'))}):
                with patch.object(D['subprocess'],'Popen',side_effect=AssertionError('transport')), \
                        patch.object(Path,'mkdir',side_effect=AssertionError('claim')):
                    with self.assertRaises(ValueError):
                        D['perform']({'admission':{},'package':self.root/'package'},True)
            self.assertEqual(D['execution_gate'](admission), D['sha'](enabled))
            prepare_calls = []
            def prepare_reached(*args):
                prepare_calls.append(args)
                raise ValueError('prepare reached')
            with patch.dict(globals_, {'prepare':prepare_reached}):
                with self.assertRaisesRegex(ValueError,'prepare reached'):
                    D['perform']({'admission':admission,'package':self.root/'package'},True)
            self.assertEqual(len(prepare_calls), 1)
            mutations = []
            for field in sorted(D['ADMISSION_FIELDS']):
                changed = copy.deepcopy(admission)
                if isinstance(changed[field], dict): changed[field]['mutation'] = True
                elif isinstance(changed[field], int): changed[field] += 1
                else: changed[field] = str(changed[field]) + '-mutation'
                mutations.append((field, changed))
            for field, changed in mutations:
                with self.subTest(field=field):
                    with self.assertRaises(ValueError): D['execution_gate'](changed)
            for field in ('exclusive','no_other_device_operations','stable_power',
                          'physical_selection','screen_readable','owner_ready'):
                changed = copy.deepcopy(admission)
                changed['custody'][field] = 1
                with self.subTest(custody=field, value=1):
                    with self.assertRaises(ValueError): D['execution_gate'](changed)

        before = D['M']['source_identity']()
        binding_path = binding(enabled)
        binding_path.write_bytes(D['encode']({'schema':'keyboard-disconnect-execution-binding-v1',
            'state':'disabled','admission':None}))
        after = D['M']['source_identity']()
        self.assertIn('disconnect.py', before['local_and_direct'])
        self.assertNotIn('disconnect-execution-binding.json', before['local_and_direct'])
        self.assertEqual(before, after)


if __name__ == '__main__': unittest.main()
