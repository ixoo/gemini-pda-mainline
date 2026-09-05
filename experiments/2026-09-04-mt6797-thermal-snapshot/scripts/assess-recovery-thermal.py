#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline reported-temperature response; never admits a hardware run."""
import argparse
import hashlib
import json
from pathlib import Path

from thermal_snapshot_records import parse_series, require

PARSER_SHA = '3d16447c3a213c658814a27795d6964d2c21c99424806aa51bd582f78e90da74'
ABSOLUTE_MAX = 58500
DELAY_MIN_NS = 2_000_000_000
DELAY_MAX_NS = 3_000_000_000
STAGES = ('pre-workload', 'workers-complete', 'post-completion')


def assess(raw_records, initial):
    parser = Path(__file__).with_name('thermal_snapshot_records.py')
    require(not parser.is_symlink() and
            hashlib.sha256(parser.read_bytes()).hexdigest() == PARSER_SHA,
            'parser source changed')
    require(type(initial) is int and 0 <= initial <= ABSOLUTE_MAX and
            initial % 100 == 0, 'initial temperature refusal')
    records = parse_series(raw_records)
    require(all(a['end_ns'] < b['start_ns'] for a, b in zip(records, records[1:])),
            'non-distinct scan interval')
    delay = records[2]['start_ns'] - records[1]['end_ns']
    require(DELAY_MIN_NS <= delay <= DELAY_MAX_NS, 'recovery timing refusal')
    for record in records:
        require(all(0 <= s['temperature'] <= ABSOLUTE_MAX and
                    s['temperature'] % 100 == 0 for s in record['samples']),
                'per-slot temperature refusal')
    maxima = [r['maximum'] for r in records]
    # Only the two shared boundaries have counterparts in the original run.
    # The waiting sample is absent: never manufacture it or claim full repeatability.
    violations = []
    for stage, maximum, target in zip(STAGES[:2], maxima[:2], (700, 900)):
        if abs((maximum - initial) - target) > 5000:
            violations.append(stage + ':baseline-rise-bound')
    if abs(maxima[1] - maxima[0]) > 5000:
        violations.append('shared-boundary-spread-bound')
    slots = []
    for i in range(7):
        values = [r['samples'][i]['temperature'] for r in records]
        delta = values[2] - values[1]
        slots.append({'slot': i, 'bank': records[0]['samples'][i]['bank'],
                      'sensor': records[0]['samples'][i]['sensor'],
                      'temperatures': values,
                      'complete_minus_pre': values[1] - values[0],
                      'recovery_minus_complete': delta,
                      'response': 'decreased' if delta < 0 else
                                  'increased' if delta > 0 else 'unchanged'})
    return {'classification': 'reported-temperature-response-only',
            'stages': list(STAGES), 'initial_aggregate': initial,
            'maxima': maxima, 'slots': slots, 'focus_slot': 0,
            'recovery_interval_ns': delay,
            'shared_boundary_comparison': 'rejected' if violations else 'within-bounds',
            'violations': violations,
            'full_baseline_comparison': 'not-evaluated-missing-writers-waiting-stage',
            'prior_thermal_rejection': 'unchanged',
            'conversion_age': 'unknown', 'physical_cooling': 'not-established',
            'overall_workload_classification': 'not-evaluated',
            'device_action': 'none'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--initial', required=True, type=int)
    parser.add_argument('records', nargs=3, type=Path)
    args = parser.parse_args()
    result = assess([p.read_text() for p in args.records], args.initial)
    print(json.dumps(result, indent=2, sort_keys=True))
    # Even a within-bounds response is not an admitted runtime or integrated pass.
    return 3 if result['shared_boundary_comparison'] == 'rejected' else 0


if __name__ == '__main__':
    raise SystemExit(main())
