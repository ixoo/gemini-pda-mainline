#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Raw export/assessment fixtures; no transport or device access."""
import base64
import json
from pathlib import Path
import runpy
import subprocess
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
M = runpy.run_path(str(HERE/'capture.py'))
FIXTURE = runpy.run_path(str(HERE/'test_packet.py'))['fixture']
WORK = HERE.parents[2]/'artifacts/a53-authenticated/development/keyboard-capture-tests'

def frame(files):
    return b''.join(('file='+name+'\n').encode()+
        (b'missing\n' if files[name] is None else base64.b64encode(files[name])+b'\n')+
        ('end='+name+'\n').encode() for name in M['FILES'])

class CaptureTests(unittest.TestCase):
    def setUp(self):
        WORK.mkdir(mode=0o700,parents=True,exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=WORK)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        expected,receipt,self.capture = FIXTURE()
        self.admission = {'id':receipt['boot_id_before'],'boot_id':receipt['boot_id_before'],
            'expected':expected,'dependency':{'deployment_receipt_sha256':'2'*64,'confirmation_manifest_sha256':'3'*64},
            'runtime':{'event':'event0','minor':64}}
        self.context = {'admission':self.admission,'package':self.root,
            'dependency':{'recovered_boot':receipt['known_good_boot_id']}}
        self.owner = {'admission_id':self.admission['id'],'sequence_complete':True,'screen_readable':True,'source':'synthetic owner fixture'}
        status = {'schema':'keyboard-monitor-v1','reason':'normal-lifecycle-only','reaped':'1','identity_lost':'0',
            'exit':'0','signal':'0','cancel':'0','term_ms':'-1','kill_ms':'-1','reap_ms':'202001',
            'term_errno':'0','kill_errno':'0','late':'0','stdout_bytes':str(len(self.capture)),
            'stderr_bytes':'0','forwarded_bytes':str(len(self.capture))}
        self.files = {'observer.stdout':self.capture,'observer.stderr':b'',
            'monitor.status':''.join(k+'='+v+'\n' for k,v in status.items()).encode(),'outer-exit':b'0\n'}

    def store(self,files=None,diagnostic=b''):
        files = self.files if files is None else files
        self.session = self.root/self.admission['id'];self.session.mkdir(mode=0o700)
        for action,out in [('capture',self.capture+b'__KEYBOARD_POSTFLIGHT_PASS__\n'),('export',frame(files))]:
            path=self.session/action;path.mkdir(mode=0o700)
            values={'admission.json':M['encode'](self.admission),'command.sh':action.encode(),
                'stdout.txt':out,'stderr.txt':diagnostic if action=='capture' else b'',
                'process.json':M['encode']({'exit_status':0,'reason':None,'stdin_complete':True,'stdout_bytes':len(out),
                    'stderr_bytes':len(diagnostic) if action=='capture' else 0,'elapsed_seconds':203 if action=='capture' else 1})}
            for name,raw in values.items():M['C']['write_new'](path/name,raw)

    def assess(self):
        with patch.dict(M['assess'].__globals__,{'ROOT':self.root,'prepare':lambda *a:self.context,
            'capture_script':lambda c:b'capture','export_script':lambda c:b'export'}):
            return M['assess'](self.context,self.owner)

    def test_retry_paths_keep_original_attempt_and_reject_unsafe_ids(self):
        original = M['attempt_root'](self.admission)
        retry = '1c573500-ae1d-4e51-aa18-5d69b627f48a'
        self.admission['runtime']['retry_id'] = retry
        self.assertEqual(M['attempt_root'](self.admission), original/'retries'/retry)
        for value in ('../capture', '', 'retry', 1):
            self.admission['runtime']['retry_id'] = value
            with self.assertRaisesRegex(ValueError, 'retry identity'):
                M['attempt_root'](self.admission)

    def test_restarted_clock_age_identity_and_malformed_records(self):
        boot = 'e3a29c80-4948-4ef8-893a-cfbef0cd4918'
        with tempfile.TemporaryDirectory() as work:
            clock, uptime = Path(work)/'clock', Path(work)/'uptime'
            command = 'set -eu\nBB=\npid=42\n' + M['logger_clock_guard'](boot, 240)
            command = command.replace('/run/a53/keyboard-logger-clock', str(clock))
            command = command.replace('/proc/uptime', str(uptime))
            # Model stat for portability; these cases test clock data and arithmetic.
            command = command.replace('$($BB stat -c %u:%a '+str(clock)+')', '0:600')
            command = command.replace('$($BB stat -c %s '+str(clock)+')', '64')
            cases = [(f'{boot} 42 1000.25\n', '1000.25 0\n', True),
                     (f'{boot} 42 1000.25\n', '1239.99 0\n', True),
                     (f'{boot} 42 1000.25\n', '1240.25 0\n', False),
                     (f'{boot} 42 1000.25\n', '999 0\n', False),
                     (f'{boot} 43 1000.25\n', '1001 0\n', False),
                     ('bad 42 1000.25\n', '1001 0\n', False),
                     (f'{boot} 42 nan\n', '1001 0\n', False),
                     ('', '1001 0\n', False),
                     (f'{boot} 42 1000.25\nextra\n', '1001 0\n', False)]
            for record, now, passed in cases:
                with self.subTest(record=record, now=now):
                    clock.write_text(record); uptime.write_text(now)
                    result = subprocess.run(['sh'], input=command.encode(), capture_output=True)
                    self.assertEqual(result.returncode == 0, passed, result.stderr)

    def test_complete_export_rejoins_classifier_without_hardware_claim(self):
        self.store();result=self.assess()
        self.assertEqual(result['classification'],'pass')
        self.assertEqual(len(result['cases']),20)
        self.assertFalse(json.loads((self.session/'preserved-keyboard-files/result.json').read_text())['final_keyboard_acceptance'])

    def test_missing_status_preserves_other_private_files_but_refuses(self):
        self.store({**self.files,'monitor.status':None})
        with self.assertRaisesRegex(ValueError,'partial keyboard'):self.assess()
        self.assertEqual((self.session/'preserved-keyboard-files/observer.stdout').read_bytes(),self.capture)

    def test_diagnostics_cannot_become_capture_success(self):
        self.store(diagnostic=b'diagnostic')
        with self.assertRaisesRegex(ValueError,'transport'):self.assess()

    def test_extra_duplicate_and_truncated_exports_refuse(self):
        raw=frame(self.files)
        for value in (raw+b'extra\n',raw+raw,raw[:-5]):
            with self.assertRaises(ValueError):M['parse_export'](value)

    def test_execution_gate_precedes_all_context_and_io(self):
        path = self.root/'disabled-binding.json'
        path.write_bytes(M['encode']({'schema':'keyboard-capture-execution-binding-v1',
                                     'state':'disabled', 'admission':None}))
        with patch.dict(M['execution_binding'].__globals__, {'BINDING':path}), \
                patch('subprocess.Popen',side_effect=AssertionError('transport')), \
                patch.object(Path,'mkdir',side_effect=AssertionError('claim')):
            for action in ('delivery','capture','export'):
                with self.assertRaisesRegex(ValueError,'disabled'):M['perform'](None,action,True)

    def test_binding_rejects_cross_session_and_changed_admissions(self):
        admission = dict.fromkeys(M['ADMISSION_FIELDS'], 'fixture')
        binding = {'schema':'keyboard-capture-execution-binding-v1',
            'state':'enabled', 'admission':admission}
        path = self.root/'binding.json'
        path.write_bytes(M['encode'](binding))
        with patch.dict(M['execution_binding'].__globals__, {'BINDING':path}):
            self.assertEqual(M['execution_gate'](admission), M['sha'](path.read_bytes()))
            with patch('subprocess.Popen', side_effect=AssertionError('transport')), \
                    patch.object(Path, 'mkdir', side_effect=AssertionError('claim')):
                with self.assertRaisesRegex(ValueError, 'admission mismatch'):
                    M['perform']({'admission':{**admission, 'boot_id':'changed'}}, 'capture', True)
            for field in M['ADMISSION_FIELDS']:
                with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'admission mismatch'):
                    M['execution_gate']({**admission, field:'changed'})
            for malformed in (
                    {**binding, 'state':'unknown'},
                    {**binding, 'state':'disabled'},
                    {**binding, 'admission':{}},
                    {**binding, 'extra':True}):
                path.write_bytes(M['encode'](malformed))
                with self.assertRaises(ValueError):M['execution_gate'](admission)
            path.write_text('{"state":"enabled","state":"disabled"}')
            with self.assertRaises(ValueError):M['execution_gate'](admission)

    def test_imported_helper_drift_refuses_before_effect(self):
        identity = M['source_identity']()
        context = {'admission':{'source_identity':identity}}
        original = M['C']['regular']
        helper = (HERE/'../emmc/mainline_host.py').resolve()
        def changed(path, *args, **kwargs):
            raw = original(path,*args,**kwargs)
            return raw+b'\n# changed helper\n' if Path(path).resolve()==helper else raw
        with patch.dict(M['C'],{'regular':changed}), \
                patch.dict(M['perform'].__globals__,{'execution_gate':lambda a:None}), \
                patch.object(Path,'mkdir',side_effect=AssertionError('claim')), \
                patch('subprocess.Popen',side_effect=AssertionError('transport')):
            with self.assertRaisesRegex(ValueError,'^imported closure drift$'):
                M['perform'](context,'capture',True)

if __name__ == '__main__':unittest.main()
