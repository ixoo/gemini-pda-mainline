#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline combined attribution classifier; a thermal refusal stays a refusal."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from thermal_snapshot_records import parse_complete,require

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PARENT=ROOT/'experiments/2026-09-04-mt6797-a72-frequency-observation/scripts/classify-production-runtime.py'
PARENT_SHA='b186b6c1cf83d7757bbe401036d4660d950a25dd59e47aa71515dfb8b3c4f224'
DEPENDENCIES={'assess-workload-thermal.py': '2618bfc9d419b2e61b4f017e7fe3aff6b6bf2d9d81d2e644dd6e0abb9620a031', 'thermal_snapshot_records.py': '3d16447c3a213c658814a27795d6964d2c21c99424806aa51bd582f78e90da74'}
RELEASE='7.1.3-gemini-thermal-snapshot'
CLOSED_BOOTS={'50e87880-b73a-46c2-9914-cabe34acff8c','1afc43e5-d4cd-4df6-a0e1-431eeef140df','ac3d28c7-69fe-4ccb-8145-cad85cbd0653'}


def scalar(text,key):
    values=re.findall(r'^'+re.escape(key)+r'=([^\n]*)$',text,re.M)
    require(len(values)==1,'missing/duplicate '+key)
    return values[0]


def classify(raw,boot,initial):
    for name,sha in DEPENDENCIES.items():
        path=HERE/name
        require(not path.is_symlink() and hashlib.sha256(path.read_bytes()).hexdigest()==sha,'assessment/parser source changed')
    require(re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',boot) and boot not in CLOSED_BOOTS,'fresh boot required')
    raw=raw.replace('\r\n','\n')
    require(raw.count('kernel_release='+RELEASE+'\n')==2,'new kernel release required in both frames')
    require(scalar(raw,'owned_workers_reaped')=='yes','worker reaping')
    require(scalar(raw,'cancellation_file')=='absent','cancellation cleanup')
    require(scalar(raw,'snapshot_final_attempts')=='3','final snapshot accounting')
    require(raw.count('__THERMAL_ATTRIBUTION_')==6,'snapshot marker inventory')
    require('__A72_FREQUENCY_THERMAL_REJECTED__' not in raw and 'concurrent_result=fail' not in raw,'device failure')
    records=[];normalized=raw
    for n,label in enumerate(('before','during','after'),1):
        begin=f'__THERMAL_ATTRIBUTION_{label}_BEGIN__\n';end=f'__THERMAL_ATTRIBUTION_{label}_END__\n'
        require(raw.count(begin)==raw.count(end)==1,'snapshot frame inventory')
        start=raw.index(begin);stop=raw.index(end)
        require(start<stop,'snapshot frame order')
        data=raw[start+len(begin):stop];record=parse_complete(data,n)
        require(scalar(raw,'snapshot_'+label+'_attempt')==str(n),'stage accounting')
        require(scalar(raw,'thermal_'+label+'_millicelsius')==str(record['maximum']),'aggregate from same snapshot')
        frequency=raw.index('\nfrequency_'+label+'=')
        thermal=raw.index('\nthermal_'+label+'_millicelsius=')
        require(frequency<start<stop<thermal,'frequency/snapshot/aggregate order')
        records.append(data)
        normalized=normalized.replace(begin+data+end,'')
    require(raw.index('__THERMAL_ATTRIBUTION_before_END__')<raw.index('__GEMINI_A72_CONCURRENT_MULTILINE_BEGIN__'),'post-lifecycle stage')
    require(raw.index('writer9_alive_before_observation=1')<raw.index('__THERMAL_ATTRIBUTION_during_BEGIN__')<raw.index('__THERMAL_ATTRIBUTION_during_END__')<raw.index('writer8_alive_after_observation=1')<raw.index('writer_start_released=1'),'writers-waiting stage')
    require(raw.index('reader9_status=0')<raw.index('__THERMAL_ATTRIBUTION_after_BEGIN__')<raw.index('__THERMAL_ATTRIBUTION_after_END__')<raw.index('owned_workers_reaped=yes'),'workers-complete stage')
    require(not PARENT.is_symlink() and hashlib.sha256(PARENT.read_bytes()).hexdigest()==PARENT_SHA,'parent classifier changed')
    normalized=normalized.replace('kernel_release='+RELEASE+'\n','kernel_release=7.1.3-gemini-a72-frequency-thermal\n')
    with tempfile.TemporaryDirectory(prefix='gemini-attribution-classifier-',dir='/tmp') as tmp:
        path=Path(tmp)/'normalized.txt';path.write_text(normalized)
        result=subprocess.run([sys.executable,str(PARENT),str(path),'--boot-id',boot],capture_output=True,text=True)
    require(result.returncode==0,'inherited lifecycle/frequency/RAM classifier rejected')
    fields={}
    for line in result.stdout.splitlines():
        key,sep,value=line.partition('=');require(sep and key not in fields,'parent output inventory');fields[key]=value
    for stage in ('before','during','after'):
        for cluster,value in {'b':750000,'ll':897000,'l':1274000,'cci':629500}.items():
            require(fields.get(stage+'_'+cluster+'_khz')==str(value),'baseline frequency changed')
    for cpu in (8,9):require(0<int(fields['cpu'+str(cpu)+'_accounting_delta'])<=10000,'accounting plausibility')
    spec=importlib.util.spec_from_file_location('thermal_assessment',HERE/'assess-workload-thermal.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    assessment=module.assess(records,initial)
    return {'classification':'bounded-attribution-pass' if assessment['classification']=='thermal-envelope-pass' else 'bounded-attribution-thermal-rejected',
            'boot_id':boot,'kernel_release':RELEASE,'inherited_runtime':fields,'thermal':assessment,
            'owned_workers_reaped':True,'cancellation_file':'absent','snapshot_requests':3,'device_action':'none-offline-classification'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path)
    p.add_argument('--boot-id',required=True);p.add_argument('--initial',required=True,type=int);a=p.parse_args()
    result=classify(a.capture.read_text(),a.boot_id,a.initial)
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0 if result['classification']=='bounded-attribution-pass' else 3

if __name__=='__main__':raise SystemExit(main())
