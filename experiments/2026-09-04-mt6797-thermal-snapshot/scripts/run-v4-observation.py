#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Execute the frozen no-workload protocol once over direct, interface-bound USB."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

CANDIDATE="b007af3d7025b804b34c6f1e717b2eca5e9fecf09b0ff731cede2a12116d993c"
RECORD="6972913af84c5b651848516456d1c6744015f3fc02a9d18596441a6c82d97ad3"

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
OUTPUT=REPO/'artifacts/runtime-captures/thermal-v4-no-workload-1'
RECEIPT=REPO/'artifacts/device-install-evidence/thermal-v4-deployment-1/deployment-summary.txt'
# Frozen dependencies: any source change refuses before device access.
PINS={'v4_observation_protocol.py': '893a5aacd667d0cfde56b7cc1bf127798a7206b2e8c87a2c25dd736c08846fe1', 'observation_protocol.py': 'ac8067307a46bc80478697bd30dddab78459f298a408b4de48dd8fd649a7bf6c', 'observation_state.py': '217b176e5825cfb1423a51b0b4b99a443b5d00d3a7149ad7c9f7e06c77c628dc', 'thermal_snapshot_records.py': '3d16447c3a213c658814a27795d6964d2c21c99424806aa51bd582f78e90da74', 'remote-observation-state.sh': 'bada6f961efaf2ee3be8d43647942143381ecfadb0b00f4be329d8fd5ad5c9ae', 'remote-v4-observation-read.sh': '5fd20ca9077e3c5fe08a9369485bc07dfa101f73545791efc54e2749ae401a4f', 'validate-v4-candidate.py': '6c542e7d5182f87c400003c92f55982ccbe576ec840a4874c6f0414ddac1f99a', 'run-observation.py': '6f87d631cab6626d8ffe54c008ac327b515cf79a46b98117a6d4c72d2b8e11e1'}

def validate_sources():
    if not PINS: raise ValueError('runner is not frozen')
    for name,sha in PINS.items():
        p=HERE/name
        if not p.is_file() or p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest()!=sha:
            raise ValueError('protocol source identity changed: '+name)


def interface():
    import runpy
    return runpy.run_path(str(HERE/'run-observation.py'))['interface']()


def durable(path,data):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w',encoding='utf-8') as stream:
        stream.write(data);stream.flush();os.fsync(stream.fileno())


def syncdir(path):
    fd=os.open(path,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt',type=Path,default=RECEIPT)
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    validate_sources()
    from v4_observation_protocol import Protocol
    protocol=Protocol(CANDIDATE, RECORD)
    run,receipt=protocol.run,protocol.receipt
    if args.receipt.absolute()!=RECEIPT.absolute(): raise ValueError('unexpected deployment receipt path')
    directory=RECEIPT.parent
    if directory.is_symlink() or not directory.is_dir() or directory.stat().st_mode & 0o777!=0o700:
        raise ValueError('unsafe deployment directory')
    if {p.name for p in directory.iterdir()}!={'deployment-summary.txt','SHA256SUMS'}:
        raise ValueError('deployment receipt inventory')
    for p in directory.iterdir():
        if p.is_symlink() or not p.is_file() or p.stat().st_mode & 0o777!=0o600:
            raise ValueError('unsafe deployment receipt file')
    deployment=RECEIPT.read_text()
    if (directory/'SHA256SUMS').read_text()!=hashlib.sha256(deployment.encode()).hexdigest()+'  deployment-summary.txt\n':
        raise ValueError('deployment manifest disagreement')
    receipt(deployment)
    subprocess.run([sys.executable,str(HERE/'validate-v4-candidate.py'),'--candidate',
                    str(REPO/'artifacts/thermal-snapshot-composition/candidate-v4-ba906730')],
                   check=True,capture_output=True)
    if not args.execute:
        print('receipt=pass protocol=frozen device_action=none');return
    link=interface()
    parent=OUTPUT.parent
    if parent.is_symlink() or not parent.is_dir() or (parent.stat().st_mode & 0o777)!=0o700:
        raise ValueError('private runtime capture root is unsafe')
    subprocess.run(['git','-C',str(REPO),'check-ignore','-q',str(OUTPUT)],check=True)
    # Existing captures and interrupted attempts are never reopened or retried.
    OUTPUT.mkdir(mode=0o700)
    syncdir(parent)
    sessions=0
    def save(name,data):durable(OUTPUT/name,data)
    def request(attempt):
        durable(OUTPUT/f'read-{attempt}.requested',f'attempt={attempt}\n')
        fd=os.open(OUTPUT,os.O_RDONLY)
        try:os.fsync(fd)
        finally:os.close(fd)
    def transport(kind,boot,attempt):
        nonlocal sessions
        if sessions>=5: raise ValueError("transport budget exhausted")
        sessions+=1
        script=(HERE/('remote-observation-state.sh' if kind=='state' else 'remote-v4-observation-read.sh')).read_text()
        args_text=''
        if kind=='read':
            if not re.fullmatch(r'[0-9a-f-]{36}',boot) or attempt not in (1,2,3):raise ValueError('unsafe read arguments')
            args_text=f' {boot} {attempt}'
        marker='__THERMAL_SNAPSHOT_HOST_SCRIPT__'
        if marker in script:raise ValueError('heredoc collision')
        command=f"/bin/busybox sh -s --{args_text} <<'{marker}'\n{script}\n{marker}\nexit\n"
        nc=['nc','-4','-b',link,'-s','10.15.19.1','-G','5','-w','15','10.15.19.82','2323']
        try: result=subprocess.run(nc,input=command.encode(),capture_output=True,timeout=20)
        except subprocess.TimeoutExpired as error:
            save(f'transport-failure-{sessions}.txt',(error.stdout or b'').decode('utf-8','replace'))
            raise ValueError('transport timed out; request remains spent') from error
        raw=result.stdout.decode('utf-8','replace')
        if result.returncode:
            save(f'transport-failure-{sessions}.txt',raw+result.stderr.decode('utf-8','replace'))
            raise ValueError('transport failed; no retry')
        return raw
    try:
        save('deployment-summary.txt',deployment)
        save('started.json',json.dumps({'transport':'direct-usb-netcat','interface':link,'started_ns':time.time_ns()})+'\n')
        result=run(transport,save,request,time.sleep,deployment)
        result['transport_sessions']=sessions
        save('classification.json',json.dumps(result,indent=2,sort_keys=True)+'\n')
    except BaseException as error:
        save('classification.json',json.dumps({'classification':'refused-or-incomplete','reason':str(error),'transport_sessions':sessions,'retry':'forbidden'})+'\n')
        raise
    finally:
        entries=sorted(p for p in OUTPUT.iterdir() if p.is_file())
        save('SHA256SUMS',''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in entries))
        syncdir(OUTPUT)
    print('classification=corrected-v4-no-workload-observer-pass snapshots=3 storage_writes=none')

if __name__=='__main__':main()
