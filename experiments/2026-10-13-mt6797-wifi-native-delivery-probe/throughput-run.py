#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Validate prepared measurement inputs; execute only after physical boot2 selection."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import socket
import subprocess
import sys
import time


def write_new(path, value):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'w') as out:
        json.dump(value,out,indent=2);out.write('\n');out.flush();os.fsync(out.fileno())


def validate(runtime):
    env={**os.environ,**json.loads((runtime/'environment.json').read_text())}
    plan=json.loads((runtime/'measurement-plan.json').read_text())
    if plan['run']!='PIO-throughput-baseline-2' or (runtime/'execution-claim.json').exists():
        raise ValueError('measurement namespace already consumed or mismatched')
    for field,key in [('TP_HELPER','helper_sha256'),('TP_REVIEWED_LEAF','leaf_sha256'),('GEMINI_JOIN_SCRIPT','private_leaf_sha256')]:
        if hashlib.sha256(Path(env[field]).read_bytes()).hexdigest()!=plan[key]:
            raise ValueError('prepared measurement input changed: '+key)
    here=Path(__file__).resolve().parent
    manifest=json.loads((runtime/'validated-source-inputs.json').read_text())
    for name,digest in manifest.items():
        if hashlib.sha256((here/name).read_bytes()).hexdigest()!=digest:
            raise ValueError('measurement source changed: '+name)
    candidate=Path(env['TP_CANDIDATE'])
    receipt=json.loads((candidate/'candidate.json').read_text())
    if hashlib.sha256((candidate/'candidate.json').read_bytes()).hexdigest()!='8eb12232ddbb2a00027f926a2c72c5e8213a3dbffadf6269c10beeed6bdceab3':
        raise ValueError('installed-image receipt changed')
    for name,identity in receipt['files'].items():
        if hashlib.sha256((candidate/name).read_bytes()).hexdigest()!=identity['sha256']:
            raise ValueError('installed-image input changed: '+name)
    return env,receipt


def execute(runtime,env,protocol):
    write_new(runtime/'execution-claim.json',{'run':'PIO-throughput-baseline-2','one_attempt':True,'retry':False,'image_changed':False})
    cohort=Path(env['TP_SOURCE_ROOT'])
    old=runpy.run_path(str(cohort/'experiments/2026-10-13-mt6797-wifi-native-delivery-probe/laptop-run-ccmp-p2e.py'))
    collector=runpy.run_path(str(Path(env['GEMINI_SESSION_SOURCE_ROOT'])/'experiments/2026-09-05-owner-away-experiment-preparation/baseline/scripts/collect-baseline.py'))
    state={'runtime':runtime,'protocol':protocol,'keys':Path(env['GEMINI_WIFI_SSH_KEYS']),
           'previous_boot':'1c5d22fe-aa8f-4f51-8250-c20790761b9f','collector':collector}
    # A readiness wait is read-only and finite, never a boot or radio retry.
    ssh=collector['ssh_command'](state['keys'])
    endpoint=ssh[-2].removeprefix('root@')
    port=int(ssh[ssh.index('-p')+1]) if '-p' in ssh else 22
    deadline=time.monotonic()+180
    while True:
        try:
            with socket.create_connection((endpoint,port),timeout=0.5):
                break
        except OSError:
            if time.monotonic()>=deadline:
                raise TimeoutError('USB readiness deadline; no capture attempted')
            time.sleep(0.5)
    live=old['identity'](state)
    env['GEMINI_WIFI_SSH_BOOT']=live['boot_id']
    results={'run':'PIO-throughput-baseline-2','boot_id':live['boot_id'],'boot_allowance_consumed':True,
             'kernel_build_commit':protocol['kernel_build_commit'],'new_image':False}
    adapter=Path(env['TP_ADAPTER'])
    for phase in ('capture','session'):
        with (runtime/(phase+'-execute.log')).open('xb') as log:
            result=subprocess.run([sys.executable,str(adapter),phase,'--execute'],env=env,stdout=log,stderr=subprocess.STDOUT)
        results[phase+'_exit']=result.returncode
        if phase=='capture':
            preflight=runtime/'ccmp-stable-monitor/capture-throughput-2/preflight.json'
            if preflight.is_file():
                observed=json.loads(preflight.read_text())
                if observed['boot_id']!=live['boot_id'] or observed['release']!=protocol['kernel_release']:
                    raise ValueError('capture changed boot or release; no join admitted')
            elif result.returncode==0:
                raise ValueError('successful capture missing boot identity')
        # A failed firmware capture still enters the original failure-session
        # preservation/quiescence/recovery path exactly once; no capture retry.
    write_new(runtime/'measurement-controller-result.json',results)
    return 0 if results.get('capture_exit')==results.get('session_exit')==0 else 1


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('runtime',type=Path)
    p.add_argument('--execute',action='store_true')
    a=p.parse_args();os.umask(0o077)
    env,protocol=validate(a.runtime.resolve(strict=True))
    if a.execute:
        raise SystemExit(execute(a.runtime.resolve(),env,protocol))
    print('prepared_measurement_inputs=verified; device_action=none; physical_boot2_selection_required=yes')
