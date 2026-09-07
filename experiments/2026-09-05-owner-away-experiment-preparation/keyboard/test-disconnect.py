#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Host-only disconnect protocol, parser and semantic-receipt fixtures."""
import base64
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
D = runpy.run_path(str(HERE/'disconnect.py'))
WORK = HERE.parents[2]/'artifacts/a53-authenticated/development/keyboard-disconnect-tests'


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
            checked = subprocess.run(['/bin/sh','-n'],input=script,capture_output=True)
            self.assertEqual((checked.returncode,checked.stderr),(0,b''))
            linted = subprocess.run(['/opt/homebrew/bin/shellcheck','-s','sh','-e','SC2016','-'],
                input=script,capture_output=True)
            self.assertEqual((linted.returncode,linted.stdout,linted.stderr),(0,b'',b''))

    def test_execution_gate_precedes_context_claim_and_transport(self):
        with patch('subprocess.Popen',side_effect=AssertionError('transport')), \
                patch.object(Path,'mkdir',side_effect=AssertionError('claim')):
            with self.assertRaisesRegex(ValueError,'disabled'):
                D['perform'](None,True)


if __name__ == '__main__': unittest.main()
