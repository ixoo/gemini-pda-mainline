#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline thermal assessment only; never admits or executes a device workload."""
import argparse
import json
from pathlib import Path
from thermal_snapshot_records import parse_series, require

STAGES=('post-lifecycle', 'writers-waiting', 'workers-complete')
BASELINE_RISE=(700,700,900)
ABSOLUTE_MAX=58500
RISE_ALLOWANCE=5000
SPREAD_MAX=5000


def assess(raw_records, initial):
    require(type(initial) is int and 0<=initial<=ABSOLUTE_MAX,'initial temperature refusal')
    records=parse_series(raw_records)
    require(all(a['end_ns']<b['start_ns'] for a,b in zip(records,records[1:])), 'reused scan interval')
    maxima=[r['maximum'] for r in records]
    rises=[value-initial for value in maxima]
    violations=[]
    for stage,record,rise,baseline in zip(STAGES,records,rises,BASELINE_RISE):
        if any(not 0<=s['temperature']<=ABSOLUTE_MAX for s in record['samples']):
            violations.append(stage+':per-slot-absolute-bound')
        if abs(rise-baseline)>RISE_ALLOWANCE:
            violations.append(stage+':baseline-rise-bound')
    spread=max(maxima)-min(maxima)
    if spread>SPREAD_MAX:violations.append('aggregate-spread-bound')
    slots=[]
    for index in range(7):
        samples=[r['samples'][index] for r in records]
        values=[s['temperature'] for s in samples]
        slots.append({'slot':index,'bank':samples[0]['bank'],'sensor':samples[0]['sensor'],
                      'temperatures':values,'waiting_minus_post_lifecycle':values[1]-values[0],
                      'complete_minus_waiting':values[2]-values[1],
                      'complete_minus_post_lifecycle':values[2]-values[0]})
    return {'classification':'thermal-envelope-pass' if not violations else 'thermal-envelope-rejected',
            'violations':violations,'stages':list(STAGES),'initial_aggregate':initial,
            'maxima':maxima,'rises_from_initial_aggregate':rises,'aggregate_spread':spread,
            'first_winning_slots':[r['winner'] for r in records],
            'tied_maximum_slots':[[s['slot'] for s in r['samples'] if s['temperature']==r['maximum']] for r in records],
            'scan_duration_ns':[r['end_ns']-r['start_ns'] for r in records],
            'start_intervals_ns':[records[i+1]['start_ns']-records[i]['start_ns'] for i in range(2)],
            'slots':slots,'conversion_age':'unknown','device_action':'none',
            'overall_workload_classification':'not-evaluated'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--initial',required=True,type=int)
    p.add_argument('records',nargs=3,type=Path,help='ABI records in the three documented stage slots')
    a=p.parse_args()
    result=assess([f.read_text() for f in a.records],a.initial)
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0 if result['classification']=='thermal-envelope-pass' else 3

if __name__=='__main__':raise SystemExit(main())
