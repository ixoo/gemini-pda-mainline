#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""One-shot orchestration, independent of transport for offline failure tests."""
import re
from observation_state import validate_state, bounded
from thermal_snapshot_records import parse_complete, require

CANDIDATE='666961b636b21b8598a64999e9dbf72af280ad99f07a6b745045320f24ca361b'
RECORD='7d67a19b3ae40ae1521293d7ffc834e6d06ae14a2d55de693ee9c815bdaee552'
PATH='/sys/bus/platform/devices/1100b000.thermal/mt6797_temperature_snapshot'


def receipt(raw):
    d={}
    for line in raw.splitlines():
        key,sep,value=line.partition('=')
        require(sep and key not in d,'receipt duplicate or malformed field')
        d[key]=value
    fixed={'experiment':'2026-09-04-mt6797-thermal-snapshot','target_logical_name':'boot2',
           'root':'/dev/mmcblk0p29','fresh_predecessor_backup':'no','candidate_sha256':CANDIDATE,
           'readback_sha256':CANDIDATE,'temporary_readback_removed':'yes',
           'shutdown':'requested-after-evidence-flush','post_shutdown_reachability':'unreachable',
           'reboot':'no','next_action':'owner-physically-selects-boot2'}
    require(d.keys()==fixed.keys() | {'result','target','predecessor_sha256','boot_id','power','poweroff_ssh_rc'},'receipt inventory')
    require(all(d[k]==v for k,v in fixed.items()),'receipt invariant')
    require(d['result'] in ('write-synced-flushed-full-readback-verified','skipped-already-matching'),'receipt write result')
    require(re.fullmatch(r'/dev/mmcblk0p[0-9]+',d['target']) and d['target']!=d['root'],'receipt inactive target')
    require(re.fullmatch(r'[0-9a-f]{64}',d['predecessor_sha256']),'receipt predecessor')
    require(re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',d['boot_id']),'receipt boot')
    require(d['poweroff_ssh_rc'] in ('0','255'),'receipt shutdown status')
    power=d['power'].split('|')
    require(len(power)==4 and power[0]=='1' and power[2]=='Good' and power[1].isdigit() and power[3].isdigit(),'receipt power')
    capacity,external=int(power[1]),int(power[3])
    require(0<=capacity<=100 and (capacity>=80 or (capacity>=40 and external>=1)),'receipt stable power')
    if d['result']=='skipped-already-matching': require(d['predecessor_sha256']==CANDIDATE,'receipt skip identity')
    return d['boot_id']


def reading(raw,boot,attempt):
    frame=bounded(raw.replace('\r\n','\n'),'__THERMAL_SNAPSHOT_READ_BEGIN__','__THERMAL_SNAPSHOT_READ_END__')
    data=bounded(frame,'__THERMAL_SNAPSHOT_RECORD_BEGIN__','__THERMAL_SNAPSHOT_RECORD_END__')
    rest=frame.replace('__THERMAL_SNAPSHOT_RECORD_BEGIN__\n'+data+'__THERMAL_SNAPSHOT_RECORD_END__\n','')
    expected={'boot_id':boot,'requested_attempt':str(attempt),'observer_status':f'abi=1 attempts={attempt} limit=3','boot_id_after':boot}
    values={}
    for line in rest.splitlines():
        key,sep,value=line.partition('=');require(sep and key not in values,'read frame fields');values[key]=value
    require(values==expected,'read identity/accounting')
    parsed=parse_complete(data,attempt)
    require(all(0<=s['temperature']<=58500 for s in parsed['samples']),'per-bank thermal refusal')
    return parsed


def run(transport, save, request, pause, deployment):
    """Callbacks save evidence and durably seal each request before transport."""
    deployment_boot=receipt(deployment)
    raw=transport('state',None,None);save('preflight.txt',raw)
    pre=validate_state(raw,record_identity=RECORD,deployment_boot=deployment_boot)
    require(pre['thermal_snapshot_path']==PATH,'exact thermal device')
    boot=pre['boot_id']; records=[]
    for attempt in (1,2,3):
        if attempt>1: pause(1)
        request(attempt)  # Must be durable before any possibly consuming call.
        raw=transport('read',boot,attempt);save(f'read-{attempt}.txt',raw)
        current=reading(raw,boot,attempt)
        require(not records or current['start_ns']>records[-1]['end_ns'],'scan timing order')
        records.append(current)
        values=[r['maximum'] for r in records]
        require(max(values)-min(values)<=5000,'aggregate spread refusal')
    raw=transport('state',None,None);save('postflight.txt',raw)
    post=validate_state(raw,record_identity=RECORD,deployment_boot=deployment_boot,attempts=3,expected_boot=boot)
    require(post['thermal_snapshot_path']==pre['thermal_snapshot_path'],'thermal device changed')
    return {'classification':'no-workload-observer-pass','candidate_sha256':CANDIDATE,'record_identity':RECORD,
            'boot_id':boot,'records':records,'cpu_online':'0-7','cpu_offline':'8-9',
            'lifecycle':'unchanged-pristine','frequency_observation_requests':0,'snapshot_requests':3,
            'ordinary_thermal_reads':2,'device_storage_reads':'none','device_storage_writes':'none',
            'cpu_admission_requests':0,'cpu_off_requests':0,'retries':0,'device_temporary_files':'none',
            'cleanup':'transport-shells-exited','reboot_requests':0}
