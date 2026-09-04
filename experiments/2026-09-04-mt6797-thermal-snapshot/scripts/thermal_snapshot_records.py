#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Strict ABI-1 record parsing; representability is not a thermal safety limit."""
import re

BANKS = (0, 1, 2, 2, 3, 4, 5)
SENSORS = (0, 3, 1, 2, 1, 1, 1)
HEADER = ('abi', 'attempt', 'error', 'complete', 'count', 'valid_mask',
          'winner', 'maximum', 'start_ns', 'end_ns')
SAMPLE = ('slot', 'bank', 'sensor', 'temperature', 'valid')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fields(line, names):
    parts = line.split(' ')
    require(len(parts) == len(names), 'record field count')
    result = {}
    for part, name in zip(parts, names):
        match = re.fullmatch(re.escape(name) + r'=(-?(?:0|[1-9][0-9]*))', part)
        require(match is not None, 'record field name or integer encoding')
        value = int(match[1])
        require(str(value) == match[1], 'noncanonical integer')
        require(-(1 << 63) <= value < (1 << 64), 'integer range')
        result[name] = value
    return result


def parse_status(raw):
    require(raw.endswith('\n') and raw.count('\n') == 1, 'status framing')
    value = fields(raw[:-1], ('abi', 'attempts', 'limit'))
    require(value['abi'] == 1 and value['limit'] == 3, 'status identity')
    require(0 <= value['attempts'] <= 3, 'status budget')
    return value


def parse_complete(raw, expected_attempt):
    require(expected_attempt in (1, 2, 3), 'requested attempt')
    require(raw.endswith('\n') and raw.count('\n') == 8, 'snapshot framing')
    lines = raw[:-1].split('\n')
    record = fields(lines[0], HEADER)
    require(record['abi'] == 1 and record['attempt'] == expected_attempt, 'snapshot identity')
    require(record['error'] == 0 and record['complete'] == 1, 'failed snapshot')
    require(record['count'] == 7 and record['valid_mask'] == 127, 'incomplete samples')
    require(0 < record['start_ns'] <= record['end_ns'], 'snapshot timing')
    samples = [fields(line, SAMPLE) for line in lines[1:]]
    for i, sample in enumerate(samples):
        require((sample['slot'], sample['bank'], sample['sensor']) ==
                (i, BANKS[i], SENSORS[i]), 'sample identity/order')
        require(sample['valid'] == 1 and -20000 <= sample['temperature'] <= 150000,
                'unrepresentable sample')
    maximum = max(sample['temperature'] for sample in samples)
    winner = next(i for i, sample in enumerate(samples) if sample['temperature'] == maximum)
    require((record['maximum'], record['winner']) == (maximum, winner), 'aggregate/winner')
    return record | {'samples': samples}


def parse_series(records):
    require(len(records) == 3, 'exact three-record series required')
    parsed = [parse_complete(raw, i) for i, raw in enumerate(records, 1)]
    require(all(a['end_ns'] <= b['start_ns'] for a, b in zip(parsed, parsed[1:])),
            'overlapping or reused scan timing')
    return parsed
