#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise durable request seals and restart refusal with fake USB transport."""
import hashlib
import importlib.util
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
fixture=runpy.run_path(str(HERE/'test-observation-protocol.py'))
spec=importlib.util.spec_from_file_location('runner',HERE/'run-observation.py')
runner=importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
runner.validate_sources()
with tempfile.TemporaryDirectory(prefix='gemini-observer-runner-',dir='/tmp') as temporary:
    root=Path(temporary)
    receipt=root/'receipt.txt';receipt.write_text(fixture['deployment'])
    for scenario in ('timeout','nonzero','interrupt','success'):
        output=root/scenario
        calls=[]
        def fake_run(argv,**kwargs):
            if argv[0]=='git':return subprocess.CompletedProcess(argv,0)
            assert argv[0]=='nc' and kwargs['timeout']==20
            calls.append(argv)
            number=len(calls)
            if number==1:raw=fixture['pre']
            elif number==5:raw=fixture['pre'].replace('abi=1 attempts=0 limit=3','abi=1 attempts=3 limit=3')
            else:
                attempt=number-1
                assert (output/f'read-{attempt}.requested').read_text()==f'attempt={attempt}\n'
                if scenario=='timeout':raise subprocess.TimeoutExpired(argv,20,output=b'partial record')
                if scenario=='nonzero':return subprocess.CompletedProcess(argv,1,b'partial record',b'error')
                if scenario=='interrupt':raise KeyboardInterrupt()
                raw=fixture['read_frame'](attempt)
            return subprocess.CompletedProcess(argv,0,raw.encode(),b'')
        with patch.object(runner,'OUTPUT',output), patch.object(runner,'interface',return_value='fixture'), patch.object(runner.subprocess,'run',side_effect=fake_run), patch.object(runner.time,'sleep'), patch.object(sys,'argv',['runner','--receipt',str(receipt),'--execute']):
            try:runner.main()
            except (ValueError,KeyboardInterrupt):assert scenario!='success'
            else:assert scenario=='success'
            assert len(calls)==(5 if scenario=='success' else 2)
            assert (output/'read-1.requested').stat().st_mode & 0o777==0o600
            for line in (output/'SHA256SUMS').read_text().splitlines():
                sha,name=line.split('  ')
                assert hashlib.sha256((output/name).read_bytes()).hexdigest()==sha
            count=len(calls)
            try:runner.main()
            except FileExistsError:pass
            else:raise AssertionError('existing capture was reopened')
            assert len(calls)==count
print('runner_scenarios=4 durable_request_seals=pass restart_refusals=4 device_action=none')
