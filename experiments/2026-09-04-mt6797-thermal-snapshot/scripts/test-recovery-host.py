#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise actual one-shot host entrypoints using fake USB and durable files."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import os
import runpy
import shutil
import subprocess
import sys
import tempfile
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('host',HERE/'run-recovery.py')
host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
host.sources()
subprocess.run(json.loads(os.environ.get('GEMINI_TEST_SHELL','["sh"]'))+['-n',str(HERE/'remote-recovery-shutdown.sh')],check=True)
subprocess.run(['shellcheck',str(HERE/'remote-recovery-shutdown.sh')],check=True)
fixture=runpy.run_path(str(HERE/'test-recovery-runtime.py'))
state_fixture=runpy.run_path(str(HERE/'test-observation-state.py'))
pre=state_fixture['raw'].replace('record_identity='+state_fixture['record'],'record_identity='+host.shutdown_fields()['record_identity']).replace(state_fixture['boot'],fixture['BOOT'])
deployment=HERE.parent/'results/no-workload-deployment.txt'
assert hashlib.sha256(deployment.read_bytes()).hexdigest()==host.DEPLOYMENT_SHA
shutdown='__THERMAL_RECOVERY_SHUTDOWN_BEGIN__\n'+''.join(k+'='+v+'\n' for k,v in host.shutdown_fields().items())+'__THERMAL_RECOVERY_SHUTDOWN_END__\n'
real_run=subprocess.run
real_module=host.module
base=host.module('run-observation')
base.interface=lambda:'fixture'
def modules(name):return base if name=='run-observation' else real_module(name)

with tempfile.TemporaryDirectory(prefix='gemini-recovery-host-',dir='/tmp') as tmp:
    root=Path(tmp);root.chmod(0o700)
    # Exercise expected disconnect, receipt construction and bounded reachability.
    for scenario in ('complete','truncated','reachable','timeout-complete'):
        case=root/('cycle-'+scenario);case.mkdir(mode=0o700)
        calls=[]
        def fake_run(args,**kwargs):
            if args[0]=='git' and 'check-ignore' in args:return subprocess.CompletedProcess(args,0)
            if args[0]!='nc':return real_run(args,**kwargs)
            calls.append(args)
            if '-z' in args:return subprocess.CompletedProcess(args,0 if scenario=='reachable' else 1,b'',b'')
            assert (case/'cycle/shutdown.requested').read_text()=='requested=yes\n'
            if scenario=='timeout-complete':raise subprocess.TimeoutExpired(args,20,output=shutdown.encode())
            return subprocess.CompletedProcess(args,1,(shutdown[:30] if scenario=='truncated' else shutdown).encode(),b'')
        with patch.object(host,'CYCLE',case/'cycle'),patch.object(host,'DEPLOYMENT',deployment),patch.object(host,'module',side_effect=modules),patch.object(subprocess,'run',side_effect=fake_run),patch.object(host.time,'sleep'),patch.object(sys,'argv',['runner','prepare-cycle','--execute']):
            try:result=host.main()
            except ValueError:assert scenario in ('truncated','reachable')
            else:
                assert scenario in ('complete','timeout-complete') and result==0
                assert host.validate_cycle(host.read_cycle())==host.cycle_expected()
            assert len(calls)<=11
            count=len(calls)
            try:host.main()
            except FileExistsError:pass
            else:raise AssertionError('cycle restarted')
            assert len(calls)==count
    template=root/'cycle-complete/cycle'
    # A changed receipt or missing seal cannot supply a fresh-cycle proof.
    for key in host.cycle_expected():
        value=host.cycle_expected();value[key]='wrong'
        try:host.validate_cycle(json.dumps(value))
        except ValueError:pass
        else:raise AssertionError(key)
    try:host.validate_cycle('{"protocol":"x","protocol":"y"}')
    except ValueError:pass
    else:raise AssertionError('duplicate receipt')
    changed=root/'tampered';shutil.copytree(template,changed)
    (changed/'shutdown.requested').write_text('requested=no\n')
    with patch.object(host,'CYCLE',changed):
        try:host.read_cycle()
        except ValueError:pass
        else:raise AssertionError('changed cycle manifest admitted')
    # Re-seal mutated files to exercise semantics beyond digest mismatch.
    for scenario in ('extra-file','source-evidence','metadata-shape','metadata-duplicate'):
        changed=root/('semantic-'+scenario);shutil.copytree(template,changed)
        if scenario=='extra-file':(changed/'unexpected').write_text('extra')
        if scenario=='source-evidence':(changed/'source-runtime-classification.json').write_text('{}\n')
        if scenario=='metadata-shape':(changed/'transport-1-meta.json').write_text('{"timeout":true,"returncode":0}\n')
        if scenario=='metadata-duplicate':(changed/'transport-1-meta.json').write_text('{"timeout":false,"timeout":false,"returncode":0}\n')
        (changed/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in sorted(changed.iterdir()) if p.name!='SHA256SUMS'))
        with patch.object(host,'CYCLE',changed):
            try:host.read_cycle()
            except ValueError:pass
            else:raise AssertionError('changed cycle semantics admitted')
    scenarios=('pass','thermal-reject','pre-hot','pre-consumed','runtime-timeout','runtime-nonzero',
               'runtime-truncated','interrupt','post-timeout','post-boot','post-missing','post-hot','post-accounting')
    for scenario in scenarios:
        case=root/scenario;case.mkdir(mode=0o700);shutil.copytree(template,case/'cycle')
        calls=[]
        runtime=fixture['capture'](41300 if scenario=='thermal-reject' else 36500)
        terminal=host.module('classify-recovery-runtime').scalar(runtime,'post_status')
        def fake_run(args,**kwargs):
            if args[0]=='git' and 'check-ignore' in args:return subprocess.CompletedProcess(args,0)
            if args[0]!='nc':return real_run(args,**kwargs)
            calls.append(args);n=len(calls)
            if n==1:
                raw=pre
                if scenario=='pre-hot':raw=re.sub(r'thermal_temperature_millicelsius=[0-9]+','thermal_temperature_millicelsius=59000',raw)
                if scenario=='pre-consumed':raw=raw.replace(fixture['BOOT'],host.SOURCE_BOOT)
            elif n==2:
                assert (case/'run/workload.requested').read_text()=='requested=yes\n'
                assert kwargs['timeout']==125
                if scenario=='runtime-timeout':raise subprocess.TimeoutExpired(args,125,output=b'partial runtime')
                if scenario=='interrupt':raise KeyboardInterrupt()
                if scenario=='runtime-nonzero':return subprocess.CompletedProcess(args,1,b'partial runtime',b'')
                raw=runtime[:100] if scenario=='runtime-truncated' else runtime
            else:
                assert n==3
                if scenario=='post-timeout':raise subprocess.TimeoutExpired(args,20,output=b'partial postflight')
                raw=pre
                for key,value in {'cpu_online':'0-9','cpu_offline':'','frequency_log_count':'3','live_status':terminal,'thermal_snapshot_status':'abi=1 attempts=3 limit=3'}.items():
                    raw=re.sub(r'^'+key+r'=.*$',key+'='+value,raw,flags=re.M)
                if scenario=='post-boot':raw=raw.replace(fixture['BOOT'],host.SOURCE_BOOT)
                if scenario=='post-missing':raw=raw.replace('cpu_present=0-9\n','')
                if scenario=='post-hot':raw=re.sub(r'thermal_temperature_millicelsius=[0-9]+','thermal_temperature_millicelsius=59000',raw)
                if scenario=='post-accounting':raw=raw.replace('frequency_log_count=3','frequency_log_count=2')
            return subprocess.CompletedProcess(args,0,raw.encode(),b'')
        with patch.object(host,'CYCLE',case/'cycle'),patch.object(host,'RUN',case/'run'),patch.object(host,'DEPLOYMENT',deployment),patch.object(host,'module',side_effect=modules),patch.object(subprocess,'run',side_effect=fake_run),patch.object(sys,'argv',['runner','run','--execute']):
            try:result=host.main()
            except (ValueError,KeyboardInterrupt):assert scenario not in ('pass','thermal-reject'),scenario
            else:assert result==(3 if scenario=='thermal-reject' else 0) and scenario in ('pass','thermal-reject'),scenario
            assert len(calls)<=3
            assert (case/'run/workload.requested').exists()==(not scenario.startswith('pre-'))
            for line in (case/'run/SHA256SUMS').read_text().splitlines():
                sha,name=line.split('  ');assert hashlib.sha256((case/'run'/name).read_bytes()).hexdigest()==sha
            count=len(calls)
            try:host.main()
            except FileExistsError:pass
            else:raise AssertionError('workload capture restarted')
            assert len(calls)==count
print('cycle_scenarios=4 workload_scenarios=13 restart_refusals=17 receipt_field_mutations='+str(len(host.cycle_expected()))+' receipt_duplicate_refusals=1 manifest_tamper_refusals=1 resealed_semantic_mutations=4 device_action=none')
