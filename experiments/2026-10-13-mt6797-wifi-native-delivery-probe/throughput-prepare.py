#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare a new measurement namespace for the exact rebuilt pump image."""
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys


def prepare(repo, runtime):
    here = Path(__file__).resolve().parent
    cohort = repo/'artifacts/wifi-p2ed2-host-cohort-1'
    source = cohort/'experiments/2026-10-13-mt6797-wifi-native-delivery-probe'
    candidate = repo/'artifacts/wifi-tx-pump-candidate-1/candidate-08bab27ae571e6e8e59e6d2112e9b30736148b750b28950861cdd7a4e03fe038'
    for name, expected in [('P2ED_BINDING.json','16fb1a8c26c913cf4da756a01dca59240abb031af794b8385910afb25ddcdb7a'),('P2ED2_BINDING.json','6da7efd1a6f31f5c744006a2745bf3934265f91841ad52442c9d2f1e13545690')]:
        if hashlib.sha256((cohort/name).read_bytes()).hexdigest() != expected:
            raise ValueError('retained cohort binding changed')
    runtime.mkdir(mode=0o700)
    retained = (source/'join-ccmp-p2.sh').read_bytes()
    private = (repo/'artifacts/wifi-p2ed-private-join-1/join-admitted.sh').read_bytes()
    if not private.endswith(retained):
        raise ValueError('retained private leaf does not wrap exact reviewed body')
    old = b'    pc_result=0; periodic_data_checks "$cyc" || pc_result=$?'
    if retained.count(old) != 1:
        raise ValueError('periodic leaf anchor changed')
    # No periodic ping traffic during either measurement. Admission, initial
    # DHCP/three pings, ACK, standard disconnect and teardown stay unchanged.
    leaf = retained.replace(old,b'    pc_result=0 # throughput: no periodic probes during measurement')
    reviewed = runtime/'reviewed-leaf.sh'
    bound = runtime/'join-private.sh'
    reviewed.write_bytes(leaf)
    bound.write_bytes(private[:-len(retained)]+leaf)
    bound.chmod(0o600)
    plan = {'schema':1,'seconds_per_chunk':1,'byte_cap_per_chunk':1048576,'chunks_each':5,'gap_seconds':0.1,'data_path':'plain nc TCP; SSH control/progress only','run':'PIO-throughput-pump-1','image_changed':True,'boot_allowance_consumed':False,
            'helper_sha256':hashlib.sha256((here/'throughput-helper.py').read_bytes()).hexdigest(),
            'leaf_sha256':hashlib.sha256(leaf).hexdigest(),
            'private_leaf_sha256':hashlib.sha256(bound.read_bytes()).hexdigest(),
            'boot2_sha256':'e33c85f94b1217918ffe4bb886195fa469c564a49684b4f9c3fc62234540970d'}
    inputs = ('throughput-helper.py','throughput-session-adapter.py','classify-throughput.py','throughput-run.py','throughput-prepare.py','validate-tx-pump-candidate.py')
    (runtime/'validated-source-inputs.json').write_text(json.dumps({name:hashlib.sha256((here/name).read_bytes()).hexdigest() for name in inputs},indent=2)+'\n')
    plan_path = runtime/'measurement-plan.json'
    plan_path.write_text(json.dumps(plan,indent=2)+'\n')
    env = {**os.environ,'GEMINI_PRIVATE_REPO':str(repo),'GEMINI_RUNTIME_ROOT':str(runtime),
           'GEMINI_JOIN_SCRIPT':str(bound),'GEMINI_SESSION_SOURCE_ROOT':str(repo/'artifacts/wifi-snapshot-c2-session-sources'),
           'GEMINI_INSTALLER_SOURCE_ROOT':str(repo/'artifacts/wifi-ccmp6-installer-sources'),
           'GEMINI_WIFI_SSH_KEYS':str(repo/'artifacts/credentials/a53-auth'),
           'GEMINI_WIFI_SSH_BOOT':'5044c0d9-617b-4030-8e59-1ba3b1147a72',
           'TP_SOURCE_ROOT':str(cohort),'TP_CANDIDATE':str(candidate),'TP_PLAN':str(plan_path),
           'TP_REVIEWED_LEAF':str(reviewed),'TP_HELPER':str(here/'throughput-helper.py'),
           'TP_ADAPTER':str(here/'throughput-session-adapter.py'),
           'TP_CLASSIFIER':str(here/'classify-throughput.py')}
    (runtime/'environment.json').write_text(json.dumps({k:v for k,v in env.items() if k.startswith(('TP_','GEMINI_'))},indent=2)+'\n')
    # Create only fresh namespace bindings. This invokes no device operation.
    old = runpy.run_path
    def authority(path,*args,**kwargs):
        if Path(path).name=='deployment-authority.py':
            return {'path':lambda:candidate/'candidate.json','read':lambda:json.loads((candidate/'candidate.json').read_text())}
        return old(path,*args,**kwargs)
    original_env = dict(os.environ)
    os.environ.update(env)
    runpy.run_path=authority
    try:
        prepared = old(str(source/'prepare-ccmp.py'))
        g=prepared['main'].__globals__
        g.update(RECEIPT=candidate/'candidate.json',MANIFEST_SHA='16eb08d56be896e0d607b12142aaee6e52e95a1332a7f669932fe1e529d5ac9f',
                 CAPTURE='capture-throughput-pump-1',SESSION='session-throughput-pump-1',REVIEWED_JOIN_SCRIPT=reviewed)
        prepared['main']()
    finally:
        runpy.run_path=old
        os.environ.clear();os.environ.update(original_env)
    # New image: an actual guarded installation must populate deployment evidence
    # before execution. Never copy a prior image's receipt as current evidence.
    for phase in ('capture','session'):
        with (runtime/(phase+'-offline-prepare.log')).open('xb') as log:
            result=subprocess.run([sys.executable,str(here/'throughput-session-adapter.py'),phase],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=60)
        if result.returncode:
            raise ValueError('offline '+phase+' constructor refused; see retained log')
    return plan


if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('usage: throughput-prepare.py <fresh ignored runtime root>')
    os.umask(0o077)
    print(json.dumps(prepare(Path(__file__).resolve().parents[2],Path(sys.argv[1]).resolve()),indent=2))
