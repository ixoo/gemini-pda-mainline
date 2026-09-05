#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Execute pinned remote scripts on synthetic files under the candidate shell."""
import hashlib
import json
import os
import re
from pathlib import Path
import shlex
import subprocess
import tempfile
from v4_observation_protocol import Protocol, RELEASE

HERE=Path(__file__).resolve().parent
CANDIDATE='b007af3d7025b804b34c6f1e717b2eca5e9fecf09b0ff731cede2a12116d993c'
RECORD='6972913af84c5b651848516456d1c6744015f3fc02a9d18596441a6c82d97ad3'
BOOT='22222222-2222-4222-8222-222222222222'
DEPLOY='11111111-1111-4111-8111-111111111111'
SNAP='/sys/bus/platform/devices/1100b000.thermal/mt6797_temperature_snapshot'
GROUP='/sys/bus/platform/devices/a72-admission-controller/gemini_admission'
PINS={
 'remote-observation-state.sh':'bada6f961efaf2ee3be8d43647942143381ecfadb0b00f4be329d8fd5ad5c9ae',
 'remote-v4-observation-read.sh':'5fd20ca9077e3c5fe08a9369485bc07dfa101f73545791efc54e2749ae401a4f',
}


def main():
    shell=json.loads(os.environ['GEMINI_TEST_SHELL'])
    busybox=os.environ['GEMINI_TEST_BUSYBOX']
    scripts={}
    for name,sha in PINS.items():
        p=HERE/name
        if p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest()!=sha:
            raise ValueError('remote script identity changed')
        scripts[name]=p.read_text()
    protocol=Protocol(CANDIDATE,RECORD)
    read_cases=['pass-1','pass-2','pass-3','old-release','wrong-boot','old-record','cpu-online',
                'cpu-offline','sysfs-rw','lifecycle-used','wrong-count','wrong-limit','snapshot-mode',
                'status-mode','duplicate-observer','missing-observer','read-error','after-boot-change']
    state_cases=['state-pass','state-used-frequency','state-ambiguous-zone','state-used-lifecycle','state-precision','state-post']
    with tempfile.TemporaryDirectory(prefix='gemini-v4-shell-',dir='/tmp') as tmp:
        for case in read_cases+state_cases:
            root=Path(tmp)/case;root.mkdir()
            def put(path,data,mode=0o600):
                p=root/path.lstrip('/');p.parent.mkdir(parents=True,exist_ok=True)
                if p.exists():p.chmod(0o600)
                p.write_bytes(data if isinstance(data,bytes) else data.encode());p.chmod(mode);return p
            attempt=int(case[-1]) if case.startswith('pass-') else 1
            put('/release',RELEASE+'\n');put('/proc/sys/kernel/random/boot_id',BOOT+'\n')
            put('/proc/mounts','sysfs /sys sysfs ro,nosuid,nodev,noexec,relatime 0 0\n')
            for n,v in {'possible':'0-9','present':'0-9','online':'0-7','offline':'8-9'}.items():put('/sys/devices/system/cpu/'+n,v+'\n')
            put('/sys/firmware/devicetree/base/chosen/gemini-late-cpu-provenance/record-identity',bytes.fromhex(RECORD))
            status=(HERE.parent/'results/pristine-lifecycle-status.txt').read_text()
            put(GROUP+'/status',status,0o444);put(GROUP+'/trigger','',0o200)
            for d in ('a72-binder','10222000.a72-platform-state'):(root/'sys/bus/platform/devices'/d).mkdir()
            put('/sys/bus/platform/devices/10200000.clock/a72_frequency_observation','',0o444)
            put('/sys/class/thermal/thermal_zone0/type','soc-thermal\n')
            put('/sys/class/thermal/thermal_zone0/temp','35000\n')
            put('/log','[ 1.0] arm64-late-cpu-profile: mt6797-a53-a72-a41-v7 ready\n')
            record=f'abi=1 attempt={attempt} error=0 complete=1 count=7 valid_mask=127 winner=6 maximum=35600 start_ns={attempt*10} end_ns={attempt*10+1}\n'
            record+=''.join(f'slot={i} bank={b} sensor={s} temperature={35000+i*100} valid=1\n' for i,(b,s) in enumerate(zip((0,1,2,2,3,4,5),(0,3,1,2,1,1,1))))
            put(SNAP,record,0o400);put(SNAP+'_status',f'abi=1 attempts={attempt-1} limit=3\n',0o400)
            put('/consumed','');put('/temperature-reads','')
            if case=='old-release':put('/release','7.1.3-gemini-thermal-snapshot\n')
            if case=='wrong-boot':put('/proc/sys/kernel/random/boot_id',DEPLOY+'\n')
            if case=='old-record':put('/sys/firmware/devicetree/base/chosen/gemini-late-cpu-provenance/record-identity',bytes(32))
            if case=='cpu-online':put('/sys/devices/system/cpu/online','0-9\n')
            if case=='cpu-offline':put('/sys/devices/system/cpu/offline','\n')
            if case=='sysfs-rw':put('/proc/mounts','sysfs /sys sysfs rw 0 0\n')
            if case in ('lifecycle-used','state-used-lifecycle'):put(GROUP+'/status',status.replace('cpu_requests=0','cpu_requests=1',1),0o444)
            if case=='wrong-count':put(SNAP+'_status','abi=1 attempts=1 limit=3\n',0o400)
            if case=='wrong-limit':put(SNAP+'_status','abi=1 attempts=0 limit=4\n',0o400)
            if case=='snapshot-mode':(root/SNAP.lstrip('/')).chmod(0o444)
            if case=='status-mode':(root/(SNAP+'_status').lstrip('/')).chmod(0o444)
            if case=='duplicate-observer':put('/sys/bus/platform/devices/duplicate/mt6797_temperature_snapshot',record,0o400)
            if case=='missing-observer':(root/SNAP.lstrip('/')).unlink()
            if case=='state-used-frequency':put('/log','[ 1.0] arm64-late-cpu-profile: mt6797-a53-a72-a41-v7 ready\nGEMINI_A72_FREQUENCY_OBSERVATION_V1\n')
            if case=='state-ambiguous-zone':put('/sys/class/thermal/thermal_zone1/type','soc-thermal\n');put('/sys/class/thermal/thermal_zone1/temp','35000\n')
            if case=='state-precision':put('/sys/class/thermal/thermal_zone0/temp','35001\n')
            if case=='state-post':put(SNAP+'_status','abi=1 attempts=3 limit=3\n',0o400)
            # Only IO targets and hardware-dependent applets are adapted. All
            # shell tests, pipelines, globbing and parser applets execute intact.
            read_failure = 'return 1' if case == 'read-error' else ':'
            boot_change = ('"$BB_REAL" printf "' + DEPLOY + '\\n" > "$BB_FIXTURE/proc/sys/kernel/random/boot_id"'
                           if case == 'after-boot-change' else ':')
            prefix=f'''BB_FIXTURE={shlex.quote(str(root))}
BB_REAL={shlex.quote(busybox)}
bb() {{
 case "$1" in
 uname) if [ "$2" = -r ]; then "$BB_REAL" cat "$BB_FIXTURE/release"; else "$BB_REAL" printf 'aarch64\\n'; fi ;;
 dmesg) "$BB_REAL" cat "$BB_FIXTURE/log" ;;
 cat)
  if [ "$2" = "$BB_FIXTURE{SNAP}" ]; then
   "$BB_REAL" printf 'read\\n' >> "$BB_FIXTURE/consumed"
   "$BB_REAL" chmod 600 "$BB_FIXTURE{SNAP}_status"
   "$BB_REAL" printf 'abi=1 attempts={attempt} limit=3\\n' > "$BB_FIXTURE{SNAP}_status"
   "$BB_REAL" chmod 400 "$BB_FIXTURE{SNAP}_status"
   {read_failure}
   {boot_change}
  fi
  case "$2" in */thermal_zone*/temp) "$BB_REAL" printf 'read\\n' >> "$BB_FIXTURE/temperature-reads" ;; esac
  "$BB_REAL" "$@" ;;
 *) "$BB_REAL" "$@" ;;
 esac
}}
'''
            state=case.startswith('state-')
            script=scripts['remote-observation-state.sh' if state else 'remote-v4-observation-read.sh']
            if script.count('BB=/bin/busybox')!=1:raise ValueError('BB adapter anchor')
            script=script.replace('BB=/bin/busybox','BB=bb')
            script=re.sub(r'(?<![A-Za-z0-9_/])/(sys|proc)/', lambda m: str(root)+m[0], script)
            target=root/'script.sh';target.write_text(prefix+script)
            result=subprocess.run(shell+[str(target)]+([] if state else [BOOT,str(attempt)]),text=True,capture_output=True,timeout=30)
            reads=(root/'consumed').read_text().splitlines()
            raw=result.stdout.replace(str(root),'')
            if state:
                if result.returncode:raise ValueError(result.stderr)
                if reads:raise ValueError('state probe consumed snapshot')
                try:protocol.state_gate(raw,DEPLOY,3 if case=='state-post' else 0)
                except ValueError:
                    if case in ('state-pass','state-post'):raise
                else:
                    if case not in ('state-pass','state-post'):raise ValueError('state mutation admitted: '+case)
                temperatures=(root/'temperature-reads').read_text().splitlines()
                if len(temperatures)!=(0 if case=='state-ambiguous-zone' else 1):raise ValueError('ordinary read budget')
            elif case.startswith('pass-') or case=='after-boot-change':
                if result.returncode or len(reads)!=1:raise ValueError('read success shape: '+case+' '+result.stderr)
                try:protocol.parent.reading(raw,BOOT,attempt)
                except ValueError:
                    if case!='after-boot-change':raise
                else:
                    if case=='after-boot-change':raise ValueError('boot change admitted')
            else:
                if result.returncode==0 or len(reads)!=(1 if case=='read-error' else 0):raise ValueError('remote refusal failed: '+case)
    print('remote_read_cases=18 state_cases=6 consuming_read_budget=pass synthetic_adapter_only=yes')


if __name__=='__main__':main()
