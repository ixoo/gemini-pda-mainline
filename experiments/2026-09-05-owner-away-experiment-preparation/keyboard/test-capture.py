#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Raw export/assessment fixtures; no transport or device access."""
import base64
import json
from pathlib import Path
import runpy
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
        with patch('subprocess.Popen',side_effect=AssertionError('transport')),patch.object(Path,'mkdir',side_effect=AssertionError('claim')):
            for action in ('delivery','capture','export'):
                with self.assertRaisesRegex(ValueError,'disabled'):M['perform'](None,action,True)

    def test_imported_helper_drift_refuses_before_effect(self):
        identity = M['source_identity']()
        context = {'admission':{'source_identity':identity}}
        original = M['C']['regular']
        helper = (HERE/'../emmc/mainline_host.py').resolve()
        def changed(path, *args, **kwargs):
            raw = original(path,*args,**kwargs)
            return raw+b'\n# changed helper\n' if Path(path).resolve()==helper else raw
        with patch.dict(M['C'],{'regular':changed}), \
                patch.dict(M['perform'].__globals__,{'execution_gate':lambda:None}), \
                patch.object(Path,'mkdir',side_effect=AssertionError('claim')), \
                patch('subprocess.Popen',side_effect=AssertionError('transport')):
            with self.assertRaisesRegex(ValueError,'source changed'):
                M['perform'](context,'capture',True)

if __name__ == '__main__':unittest.main()
