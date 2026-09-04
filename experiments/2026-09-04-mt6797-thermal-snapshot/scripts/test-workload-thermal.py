#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fixtures preserve diagnostic attribution while rejecting thermal anomalies."""
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

spec=importlib.util.spec_from_file_location('assessment',Path(__file__).with_name('assess-workload-thermal.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def record(n,values):
    banks=(0,1,2,2,3,4,5);sensors=(0,3,1,2,1,1,1)
    maximum=max(values);winner=values.index(maximum)
    out=f'abi=1 attempt={n} error=0 complete=1 count=7 valid_mask=127 winner={winner} maximum={maximum} start_ns={n*100} end_ns={n*100+9}\n'
    return out+''.join(f'slot={i} bank={banks[i]} sensor={sensors[i]} temperature={v} valid=1\n' for i,v in enumerate(values))

values=[[35000,33000,35700,34000,35600,35700,35700],
        [35000,33200,35600,34100,35700,35700,35700],
        [35100,33100,35900,34200,35800,35800,35900]]
raw=[record(i,v) for i,v in enumerate(values,1)]
passed=m.assess(raw,35000)
assert passed['classification']=='thermal-envelope-pass'
assert passed['first_winning_slots']==[2,4,2]
assert passed['tied_maximum_slots']==[[2,5,6],[4,5,6],[2,6]]
assert passed['slots'][2]['complete_minus_waiting']==300
assert passed['overall_workload_classification']=='not-evaluated'
# A slot-specific rise remains attributable when both thermal rules reject.
anomaly=raw[:2]+[record(3,[35100,33100,41300,34200,35800,35800,35900])]
rejected=m.assess(anomaly,35000)
assert rejected['classification']=='thermal-envelope-rejected'
assert rejected['violations']==['workers-complete:baseline-rise-bound','aggregate-spread-bound']
assert rejected['slots'][2]['complete_minus_waiting']==5700
# Each thermal branch must reject, without silently losing diagnostic rows.
thermal_cases=[(raw[:2]+[record(3,[59000]*7)],35000),
               ([record(1,[-100]+[35000]*6)]+raw[1:],35000),
               (raw,42000)]
for case,initial in thermal_cases:
    out=m.assess(case,initial)
    assert out['classification']=='thermal-envelope-rejected' and len(out['slots'])==7
mutations=[raw[:2],raw+[raw[2]], [raw[0],raw[0],raw[2]],
           [raw[0].replace('winner=2','winner=0')]+raw[1:],
           [raw[0].replace('valid_mask=127','valid_mask=126')]+raw[1:],
           [raw[0].replace('complete=1','complete=0')]+raw[1:],
           [raw[0].replace('sensor=3','sensor=2')]+raw[1:],
           [raw[0][:-1]]+raw[1:],
           [raw[0],raw[1].replace('start_ns=200','start_ns=109'),raw[2]]]
for case in mutations:
    try:m.assess(case,35000)
    except ValueError:pass
    else:raise AssertionError('malformed evidence accepted')
for initial in (-1,58501,True):
    try:m.assess(raw,initial)
    except ValueError:pass
    else:raise AssertionError('initial state accepted')
with tempfile.TemporaryDirectory(prefix='gemini-thermal-assessment-',dir='/tmp') as temporary:
    paths=[Path(temporary)/f'record-{n}.txt' for n in range(3)]
    for records,expected in ((raw,0),(anomaly,3),(mutations[3],1)):
        for path,data in zip(paths,records):path.write_text(data)
        outcome=subprocess.run([sys.executable,str(Path(__file__).with_name('assess-workload-thermal.py')),'--initial','35000',*map(str,paths)],capture_output=True,text=True)
        assert outcome.returncode==expected
        if expected!=1:assert len(json.loads(outcome.stdout)['slots'])==7
print('cli_exit_cases=3 device_action=none')
print('positive_attribution_cases=1 thermal_refusal_cases=4 malformed_or_initial_refusals=12 device_action=none')
