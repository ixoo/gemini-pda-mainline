#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare a new measurement namespace against the unchanged installed image."""
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
    candidate = repo/'artifacts/wifi-p2ed-composition-1/candidate-68b9d143f46f9ff390515f40535da4f8bf8a67e032a3951bd61383dfa1ab2f0d'
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
    plan = {'schema':1,'run':'PIO-throughput-baseline-2','image_changed':False,'boot_allowance_consumed':False,
            'helper_sha256':hashlib.sha256((here/'throughput-helper.py').read_bytes()).hexdigest(),
            'leaf_sha256':hashlib.sha256(leaf).hexdigest(),
            'private_leaf_sha256':hashlib.sha256(bound.read_bytes()).hexdigest(),
            'boot2_sha256':'5f63e2d32fc0b921b4fc60d5a50baeb045d1155598ad4108fb0afe6629bfefdd'}
    inputs = ('throughput-helper.py','throughput-session-adapter.py','classify-throughput.py','throughput-run.py','throughput-prepare.py')
    (runtime/'validated-source-inputs.json').write_text(json.dumps({name:hashlib.sha256((here/name).read_bytes()).hexdigest() for name in inputs},indent=2)+'\n')
    plan_path = runtime/'measurement-plan.json'
    plan_path.write_text(json.dumps(plan,indent=2)+'\n')
    env = {**os.environ,'GEMINI_PRIVATE_REPO':str(repo),'GEMINI_RUNTIME_ROOT':str(runtime),
           'GEMINI_JOIN_SCRIPT':str(bound),'GEMINI_SESSION_SOURCE_ROOT':str(repo/'artifacts/wifi-snapshot-c2-session-sources'),
           'GEMINI_INSTALLER_SOURCE_ROOT':str(repo/'artifacts/wifi-ccmp6-installer-sources'),
           'GEMINI_WIFI_SSH_KEYS':str(repo/'artifacts/credentials/a53-auth'),
           'GEMINI_WIFI_SSH_BOOT':'1c5d22fe-aa8f-4f51-8250-c20790761b9f',
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
        g.update(RECEIPT=candidate/'candidate.json',MANIFEST_SHA='8eb12232ddbb2a00027f926a2c72c5e8213a3dbffadf6269c10beeed6bdceab3',
                 CAPTURE='capture-throughput-2',SESSION='session-throughput-2',REVIEWED_JOIN_SCRIPT=reviewed)
        prepared['main']()
    finally:
        runpy.run_path=old
        os.environ.clear();os.environ.update(original_env)
    # Preserve the actual prior install receipt as prior-install evidence;
    # no new installation or partition action is represented by this copy.
    deployment=repo/'artifacts/device-install-evidence/mt6797-wifi-ccmp-stable-monitor-deployment-p2ed1/deployment-summary.txt'
    shutil.copyfile(deployment,runtime/'ccmp-stable-monitor/session-throughput-2/deployment-summary.txt')
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
