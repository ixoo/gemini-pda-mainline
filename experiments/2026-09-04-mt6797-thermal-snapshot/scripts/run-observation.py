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
from observation_protocol import run, receipt

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
OUTPUT=REPO/'artifacts/runtime-captures/thermal-snapshot-no-workload-1'
# Frozen dependencies: any source change refuses before device access.
PINS={'observation_protocol.py': 'ac8067307a46bc80478697bd30dddab78459f298a408b4de48dd8fd649a7bf6c', 'observation_state.py': '217b176e5825cfb1423a51b0b4b99a443b5d00d3a7149ad7c9f7e06c77c628dc', 'thermal_snapshot_records.py': '3d16447c3a213c658814a27795d6964d2c21c99424806aa51bd582f78e90da74', 'remote-observation-state.sh': 'bada6f961efaf2ee3be8d43647942143381ecfadb0b00f4be329d8fd5ad5c9ae', 'remote-observation-read.sh': 'a5b3324738f20ed283437e9cf685ab0fda9917477ec359f84cf9938fbabda4d7'}


def validate_sources():
    if not PINS: raise ValueError('runner is not frozen')
    for name,sha in PINS.items():
        p=HERE/name
        if not p.is_file() or p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest()!=sha:
            raise ValueError('protocol source identity changed: '+name)


def interface():
    names=subprocess.check_output(['/sbin/ifconfig','-l'],text=True).split()
    found=[]
    for name in names:
        data=subprocess.check_output(['/sbin/ifconfig',name],text=True)
        if re.search(r'ether (?:42:00:15:19:82:00|42:00:15:19:84:00)\b',data.lower()) and re.search(r'\binet 10\.15\.19\.1\b',data):
            found.append(name)
    if len(found)!=1: raise ValueError('exact Gemini USB interface is absent or ambiguous')
    return found[0]


def durable(path,data):
    with path.open('x',encoding='utf-8') as stream:
        stream.write(data);stream.flush();os.fsync(stream.fileno())
    path.chmod(0o600)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt',type=Path,required=True)
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    validate_sources()
    if args.receipt.is_symlink() or not args.receipt.is_file(): raise ValueError('unsafe receipt')
    deployment=args.receipt.read_text();receipt(deployment)
    if not args.execute:
        print('receipt=pass protocol=frozen device_action=none');return
    link=interface()
    parent=OUTPUT.parent
    if parent.is_symlink() or not parent.is_dir() or (parent.stat().st_mode & 0o777)!=0o700:
        raise ValueError('private runtime capture root is unsafe')
    subprocess.run(['git','-C',str(REPO),'check-ignore','-q',str(OUTPUT)],check=True)
    # Existing captures and interrupted attempts are never reopened or retried.
    OUTPUT.mkdir(mode=0o700)
    durable(OUTPUT/'deployment-summary.txt',deployment)
    durable(OUTPUT/'started.json',json.dumps({'transport':'direct-usb-netcat','interface':link,'started_ns':time.time_ns()})+'\n')
    sessions=0
    def save(name,data):durable(OUTPUT/name,data)
    def request(attempt):
        durable(OUTPUT/f'read-{attempt}.requested',f'attempt={attempt}\n')
        fd=os.open(OUTPUT,os.O_RDONLY)
        try:os.fsync(fd)
        finally:os.close(fd)
    def transport(kind,boot,attempt):
        nonlocal sessions
        sessions+=1
        script=(HERE/('remote-observation-state.sh' if kind=='state' else 'remote-observation-read.sh')).read_text()
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
        result=run(transport,save,request,time.sleep,deployment)
        result['transport_sessions']=sessions
        save('classification.json',json.dumps(result,indent=2,sort_keys=True)+'\n')
    except Exception as error:
        save('classification.json',json.dumps({'classification':'refused-or-incomplete','reason':str(error),'transport_sessions':sessions,'retry':'forbidden'})+'\n')
        raise
    finally:
        entries=sorted(p for p in OUTPUT.iterdir() if p.is_file())
        save('SHA256SUMS',''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in entries))
    print('classification=no-workload-observer-pass snapshots=3 storage_writes=none')

if __name__=='__main__':main()
