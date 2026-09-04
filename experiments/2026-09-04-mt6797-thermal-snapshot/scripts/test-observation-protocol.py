#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline end-to-end orchestration and receipt mutation fixtures."""
from pathlib import Path
import runpy
from observation_protocol import CANDIDATE, RECORD, receipt, run

fixture=runpy.run_path(str(Path(__file__).with_name('test-observation-state.py')))
pre=fixture['raw'].replace('record_identity='+fixture['record'],'record_identity='+RECORD)
boot=fixture['boot']; deploy=fixture['deployment']
receipt_fields={
 'experiment':'2026-09-04-mt6797-thermal-snapshot','result':'write-synced-flushed-full-readback-verified',
 'target_logical_name':'boot2','target':'/dev/mmcblk0p30','root':'/dev/mmcblk0p29',
 'predecessor_sha256':'a'*64,'fresh_predecessor_backup':'no','candidate_sha256':CANDIDATE,
 'readback_sha256':CANDIDATE,'boot_id':deploy,'power':'1|100|Good|1',
 'temporary_readback_removed':'yes','shutdown':'requested-after-evidence-flush','poweroff_ssh_rc':'0',
 'post_shutdown_reachability':'unreachable','reboot':'no','next_action':'owner-physically-selects-boot2'}
deployment=''.join(k+'='+v+'\n' for k,v in receipt_fields.items())
assert receipt(deployment)==deploy
for key,bad in [('target_logical_name','boot'),('target','/dev/mmcblk0p29'),('candidate_sha256','0'*64),
                ('readback_sha256','0'*64),('fresh_predecessor_backup','yes'),('power','1|20|Good|0'),
                ('shutdown','none'),('post_shutdown_reachability','reachable'),('reboot','yes'),('poweroff_ssh_rc','1')]:
    try:receipt(deployment.replace(key+'='+receipt_fields[key],key+'='+bad))
    except ValueError:pass
    else:raise AssertionError(key)
try:receipt(deployment+'boot_id='+deploy+'\n')
except ValueError:pass
else:raise AssertionError('duplicate receipt')

def read_frame(n,base=35000):
    banks=(0,1,2,2,3,4,5);sensors=(0,3,1,2,1,1,1)
    record=f'abi=1 attempt={n} error=0 complete=1 count=7 valid_mask=127 winner=6 maximum={base+600} start_ns={n*10} end_ns={n*10+1}\n'
    record+=''.join(f'slot={i} bank={b} sensor={s} temperature={base+i*100} valid=1\n' for i,(b,s) in enumerate(zip(banks,sensors)))
    return ('__THERMAL_SNAPSHOT_READ_BEGIN__\n'+f'boot_id={boot}\nrequested_attempt={n}\n'+
            '__THERMAL_SNAPSHOT_RECORD_BEGIN__\n'+record+'__THERMAL_SNAPSHOT_RECORD_END__\n'+
            f'observer_status=abi=1 attempts={n} limit=3\nboot_id_after={boot}\n__THERMAL_SNAPSHOT_READ_END__\n')

scenarios={'pass':3,'preflight':0,'timeout':1,'first-truncated':1,'second-heat':2,
           'second-duplicate':2,'third-spread':3,'wrong-count':1,'post-boot':3,'post-missing':3}
for scenario,expected_requests in scenarios.items():
    calls=[];requests=[];saved={};pauses=[]
    def transport(kind,current_boot,n):
        calls.append(kind)
        if kind=='state':
            if len(calls)==1:
                return pre.replace('cpu_online=0-7','cpu_online=0-8') if scenario=='preflight' else pre
            post=pre.replace('abi=1 attempts=0 limit=3','abi=1 attempts=3 limit=3')
            if scenario=='post-boot':post=post.replace(boot,deploy)
            if scenario=='post-missing':post=post.replace('cpu_online=0-7\n','')
            return post
        assert current_boot==boot and requests==list(range(1,n+1))
        if scenario=='timeout' and n==1:raise TimeoutError('injected transport interruption')
        data=read_frame(n,59000 if scenario=='second-heat' and n==2 else 42000 if scenario=='third-spread' and n==3 else 35000)
        if scenario=='first-truncated' and n==1:data=data[:-40]
        if scenario=='second-duplicate' and n==2:data+=data
        if scenario=='wrong-count' and n==1:data=data.replace('observer_status=abi=1 attempts=1','observer_status=abi=1 attempts=2')
        return data
    try:
        result=run(transport,lambda name,data:saved.setdefault(name,data),requests.append,pauses.append,deployment)
    except (ValueError,TimeoutError):
        assert scenario!='pass',scenario
    else:
        assert scenario=='pass' and result['snapshot_requests']==3 and result['cpu_admission_requests']==0
        assert calls==['state','read','read','read','state']
    assert requests==list(range(1,expected_requests+1)),scenario
    assert len(calls)<=5 and all(n==1 for n in pauses)
print('protocol_scenarios=10 receipt_mutations_rejected=11 retries=0 device_action=none')
