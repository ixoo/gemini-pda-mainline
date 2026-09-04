#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
from pathlib import Path
import hashlib
from observation_state import BEGIN, END, LATE_BEGIN, LATE_END, READY, FIXED, STATUS_SHA256, validate_state

record='1'*64
deployment='11111111-1111-4111-8111-111111111111'
boot='22222222-2222-4222-8222-222222222222'
status=(Path(__file__).resolve().parent.parent/'results/pristine-lifecycle-status.txt').read_text()
assert hashlib.sha256(status.encode()).hexdigest()==STATUS_SHA256
values=FIXED | {'boot_id':boot,'record_identity':record,'sysfs_options':'ro,nosuid,nodev,noexec,relatime',
    'live_status':status.rstrip('\n'),'thermal_temperature_millicelsius':'35000',
    'thermal_snapshot_status':'abi=1 attempts=0 limit=3',
    'thermal_snapshot_path':'/sys/bus/platform/devices/1100b000.thermal/mt6797_temperature_snapshot'}
raw=BEGIN+'\n'+''.join(k+'='+v+'\n' for k,v in values.items())+LATE_BEGIN+'\n[ 1.0] '+READY+'\n'+LATE_END+'\n'+END+'\n'
kwargs=dict(record_identity=record,deployment_boot=deployment)
assert validate_state(raw,**kwargs)['boot_id']==boot
mutations={
    'used-boot':raw.replace(boot,'1afc43e5-d4cd-4df6-a0e1-431eeef140df'),
    'deployment-boot':raw.replace(boot,deployment),
    'wrong-record':raw.replace(record,'2'*64),
    'missing-field':raw.replace('cpu_online=0-7\n',''),
    'extra-field':raw.replace(END,'unknown=1\n'+END),
    'duplicate':raw.replace('cpu_online=0-7\n','cpu_online=0-7\ncpu_online=0-7\n'),
    'lifecycle-budget':raw.replace('cpu_requests=0','cpu_requests=1',1),
    'lifecycle-missing':raw.replace(' checkpoint_errno=0','',1),
    'already-observed':raw.replace('abi=1 attempts=0 limit=3','abi=1 attempts=1 limit=3'),
    'frequency-used':raw.replace('frequency_log_count=0','frequency_log_count=1'),
    'hot':raw.replace('millicelsius=35000','millicelsius=58501'),
    'cold-negative':raw.replace('millicelsius=35000','millicelsius=-1'),
    'writeable':raw.replace('sysfs_options=ro,','sysfs_options=rw,'),
    'observer-mode':raw.replace('thermal_snapshot_mode=400','thermal_snapshot_mode=444'),
    'multiple-observers':raw.replace('thermal_snapshot_count=1','thermal_snapshot_count=2'),
    'path-traversal':raw.replace('1100b000.thermal/','../'),
    'not-ready':raw.replace(READY,'arm64-late-cpu-profile: blocked'),
    'second-frame':raw+raw,
}
for name,mutant in mutations.items():
    try: validate_state(mutant,**kwargs)
    except ValueError: pass
    else: raise AssertionError(name)
try: validate_state(raw,expected_boot=deployment,**kwargs)
except ValueError: pass
else: raise AssertionError('changed-boot')
print('positive_cases=1 mutations_rejected=19')
