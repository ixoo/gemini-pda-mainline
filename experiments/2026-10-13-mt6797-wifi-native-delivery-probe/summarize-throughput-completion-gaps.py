#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Summarize existing TX-status timing inside measured chunks; no device I/O."""
import argparse
from bisect import bisect_right
import hashlib
import json
from pathlib import Path
import re

LIMITS_NS = tuple(ms * 1_000_000 for ms in (1, 2, 3, 4, 5, 10, 20, 25,
                                            28, 30, 32, 40, 60, 100, 200))


def completion_records(kmsg):
    records = []
    for line in kmsg.splitlines():
        framed = re.fullmatch(rb'\d+,\d+,(\d+),[^;]*;(.*)', line)
        if not framed:
            continue
        done = re.search(rb'one-shot WLAN join TX done: pid=(\d+) status=(\d+) advanced=[01] count=\d+$', framed[2])
        if done and 1 <= int(done[1]) <= 126:
            records.append({'pid': int(done[1]), 'status': int(done[2]),
                            'observed_ns': int(framed[1]) * 1000})
    return records


def gaps(records):
    values = [b['observed_ns'] - a['observed_ns'] for a, b in zip(records, records[1:])]
    if any(value < 0 for value in values):
        raise ValueError('TX timing observations are not monotonic')
    return values


def histogram(values):
    counts = [0] * (len(LIMITS_NS) + 1)
    for value in values:
        counts[bisect_right(LIMITS_NS, value)] += 1
    return {'gap_count': len(values), 'maximum_gap_ns': max(values, default=None),
            'bins': [{'lower_inclusive_ns': lower, 'upper_exclusive_ns': upper, 'count': count}
                     for lower, upper, count in zip((0, *LIMITS_NS), (*LIMITS_NS, None), counts)]}


def chunk_windows(raw, label):
    prefix = rb'^TP2_PROGRESS direction=' + label.encode() + rb' chunk=([1-5]) '
    starts, ends = {}, {}
    for phase, target, pattern in (
        ('start', starts, rb'phase=start ns=([0-9]+)\r?$'),
        ('end', ends, rb'phase=end rc=[0-9]+ bytes=(?:unknown|[0-9]+) ns=([0-9]+)\r?$'),
    ):
        for match in re.finditer(prefix + pattern, raw, re.M):
            ordinal = int(match[1])
            if ordinal in target:
                raise ValueError('duplicate chunk ' + phase)
            target[ordinal] = int(match[2])
    if set(starts) != set(ends) or set(starts) != set(range(1, 6)):
        raise ValueError('five attributable chunk intervals are required')
    windows = [(starts[i], ends[i]) for i in range(1, 6)]
    if any(start >= end for start, end in windows) or any(
            a[1] > b[0] for a, b in zip(windows, windows[1:])):
        raise ValueError('chunk intervals overlap or have nonpositive duration')
    return windows


def summarize(result, raw, kmsg):
    value = result['ccmp_compatibility']
    trace = value['pid_ownership']
    if not trace['trace_valid'] or not trace['whole_after_cleanup']:
        raise ValueError('a verified whole PID ledger is required')
    records = completion_records(kmsg)
    if len(records) != trace['ordinary_completions']:
        raise ValueError('ordinary TX-status count disagrees with the whole ledger')
    gaps(records)  # Validate time ordering before selecting separate intervals.
    directions = {}
    for label in ('TX', 'RX'):
        windows = chunk_windows(raw, label)
        chunks, pooled = [], []
        for ordinal, (start, end) in enumerate(windows, 1):
            selected = [row for row in records if start <= row['observed_ns'] < end]
            within = gaps(selected)
            pooled.extend(within)
            chunks.append({'ordinal': ordinal, 'completion_count': len(selected),
                           'nonzero_status_count': sum(row['status'] != 0 for row in selected),
                           **histogram(within)})
        direction = value['throughput_measurement']['directions'][label]
        start, end = direction['device_start_ns'], direction['device_end_ns']
        if not start <= windows[0][0] < windows[-1][1] <= end:
            raise ValueError('chunk intervals extend outside direction interval')
        full = [row for row in records if start <= row['observed_ns'] < end]
        directions[label] = {'device_interval_ns': [start, end], 'chunks': chunks,
                             'within_chunks': histogram(pooled),
                             'full_window_including_chunk_gaps': histogram(gaps(full))}
    return {'schema': 1, 'boot_id': result['verified_boot'],
            'scope': 'ordinary PID 1..126 join TX done records; all statuses; no PID deduplication',
            'clock': 'kmsg header timestamp_us times 1000; not the separate completion timing observed_ns field',
            'interval': 'start-inclusive, end-exclusive; device progress clock resolution 10000000 ns',
            'within_chunks': 'pooled adjacent observations within each chunk; intentional chunk gaps excluded',
            'measurement_censored': value.get('measurement_censored'), 'directions': directions}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('session', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    inputs = {name: (args.session/name).read_bytes() for name in (
        'ccmp-session-result.json', 'ssh-client-observation/stdout.bin', 'kmsg.log')}
    value = summarize(json.loads(inputs['ccmp-session-result.json']),
                      inputs['ssh-client-observation/stdout.bin'], inputs['kmsg.log'])
    value['input_sha256'] = {name: hashlib.sha256(raw).hexdigest() for name, raw in inputs.items()}
    encoded = json.dumps(value, indent=2) + '\n'
    if args.output:
        with args.output.open('x') as output:
            output.write(encoded)
    else:
        print(encoded, end='')


if __name__ == '__main__':
    main()
