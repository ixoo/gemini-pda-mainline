#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise the actual frozen runner with fake USB and durable private files."""
import hashlib
import importlib.util
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
fixture=runpy.run_path(str(HERE/'test-observation-protocol.py'))
spec=importlib.util.spec_from_file_location('runner',HERE/'run-v4-observation.py')
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
runner.validate_sources()
pre=fixture['pre'].replace('7.1.3-gemini-thermal-snapshot','7.1.3-gemini-thermal-v4-corrected').replace(fixture['RECORD'],runner.RECORD)
deployment=fixture['deployment'].replace(fixture['CANDIDATE'],runner.CANDIDATE)
scenarios=('success','preflight-refused','preflight-timeout','read-timeout','nonzero','interrupt',
           'pause-interrupt','postflight-failure','second-hot','seal-interrupt')
with tempfile.TemporaryDirectory(prefix='gemini-v4-runner-',dir='/tmp') as name:
    root=Path(name);receipt_dir=root/'deployment';receipt_dir.mkdir(mode=0o700)
    receipt=receipt_dir/'deployment-summary.txt';receipt.write_text(deployment);receipt.chmod(0o600)
    manifest=receipt_dir/'SHA256SUMS';manifest.write_text(hashlib.sha256(deployment.encode()).hexdigest()+'  deployment-summary.txt\n');manifest.chmod(0o600)
    for scenario in scenarios:
        output=root/scenario;calls=[];syncs=[]
        original_durable=runner.durable
        def durable(path,data):
            original_durable(path,data)
            if scenario=='seal-interrupt' and path.name=='read-1.requested':raise KeyboardInterrupt()
        def syncdir(path):
            syncs.append(path)
        def sleep(seconds):
            assert seconds==1
            if scenario=='pause-interrupt':raise KeyboardInterrupt()
        def fake_run(argv,**kwargs):
            if argv[0]=='git':return subprocess.CompletedProcess(argv,0)
            if argv[0]==sys.executable:
                assert argv[1]==str(HERE/'validate-v4-candidate.py')
                return subprocess.CompletedProcess(argv,0)
            assert argv[0]=='nc' and kwargs['timeout']==20 and argv[-2:]==['10.15.19.82','2323']
            assert root in syncs, 'capture directory not persisted before transport'
            calls.append(argv);number=len(calls)
            if number==1:
                if scenario=='preflight-timeout':raise subprocess.TimeoutExpired(argv,20,output=b'partial state')
                raw=pre.replace('cpu_online=0-7','cpu_online=0-9') if scenario=='preflight-refused' else pre
            elif number==5:
                raw=pre.replace('abi=1 attempts=0 limit=3','abi=1 attempts=3 limit=3')
                if scenario=='postflight-failure':raw=raw.replace('frequency_log_count=0','frequency_log_count=1')
            else:
                attempt=number-1
                assert (output/f'read-{attempt}.requested').read_text()==f'attempt={attempt}\n'
                script=kwargs['input'].decode()
                assert runner.RECORD in script and '7.1.3-gemini-thermal-v4-corrected' in script
                if scenario=='read-timeout':raise subprocess.TimeoutExpired(argv,20,output=b'partial read')
                if scenario=='nonzero':return subprocess.CompletedProcess(argv,1,b'partial',b'failure')
                if scenario=='interrupt':raise KeyboardInterrupt()
                raw=fixture['read_frame'](attempt,59000 if scenario=='second-hot' and attempt==2 else 35000)
            return subprocess.CompletedProcess(argv,0,raw.encode(),b'')
        with patch.object(runner,'OUTPUT',output),patch.object(runner,'RECEIPT',receipt),patch.object(runner,'interface',return_value='fixture'),patch.object(runner,'durable',side_effect=durable),patch.object(runner,'syncdir',side_effect=syncdir),patch.object(runner.time,'sleep',side_effect=sleep),patch.object(runner.subprocess,'run',side_effect=fake_run),patch.object(sys,'argv',['runner','--execute']):
            try:runner.main()
            except (ValueError,KeyboardInterrupt):assert scenario!='success',scenario
            else:assert scenario=='success'
            expected={'success':5,'preflight-refused':1,'preflight-timeout':1,'read-timeout':2,'nonzero':2,'interrupt':2,'pause-interrupt':2,'postflight-failure':5,'second-hot':3,'seal-interrupt':1}[scenario]
            assert len(calls)==expected,scenario
            for line in (output/'SHA256SUMS').read_text().splitlines():
                sha,n=line.split('  ');p=output/n;assert hashlib.sha256(p.read_bytes()).hexdigest()==sha and p.stat().st_mode & 0o777==0o600
            result=json.loads((output/'classification.json').read_text())
            assert result['classification']==('corrected-v4-no-workload-observer-pass' if scenario=='success' else 'refused-or-incomplete')
            before=len(calls)
            try:runner.main()
            except FileExistsError:pass
            else:raise AssertionError('capture reopened')
            assert len(calls)==before
    # Receipt failures must happen before interface selection or any transport.
    for scenario in ('extra','manifest','mode','duplicate','candidate'):
        raw=deployment
        if scenario=='duplicate':raw+='boot_id='+fixture['deploy']+'\n'
        if scenario=='candidate':raw=raw.replace(runner.CANDIDATE,'0'*64)
        receipt.write_text(raw);receipt.chmod(0o600)
        manifest.write_text(hashlib.sha256(raw.encode()).hexdigest()+'  deployment-summary.txt\n')
        extra=receipt_dir/'extra'
        if scenario=='extra':extra.write_text('extra')
        if scenario=='manifest':manifest.write_text('invalid\n')
        if scenario=='mode':receipt.chmod(0o644)
        with patch.object(runner,'RECEIPT',receipt),patch.object(runner,'interface',side_effect=AssertionError('device access')),patch.object(sys,'argv',['runner','--execute']):
            try:runner.main()
            except ValueError:pass
            else:raise AssertionError('receipt admitted')
        extra.unlink(missing_ok=True)
old=(HERE/'remote-observation-read.sh').read_text()
new=(HERE/'remote-v4-observation-read.sh').read_text()
assert new.replace('7.1.3-gemini-thermal-v4-corrected','7.1.3-gemini-thermal-snapshot').replace(runner.RECORD,fixture['RECORD'])==old
with patch.dict(runner.PINS, {'v4_observation_protocol.py':'0'*64}):
    try: runner.validate_sources()
    except ValueError: pass
    else: raise AssertionError('source mutation admitted')
print('source_pin_refusal=pass remote_derivation=identity-only')
print('v4_runner_scenarios=10 restart_refusals=10 receipt_boundary_refusals=5 device_access=none')
