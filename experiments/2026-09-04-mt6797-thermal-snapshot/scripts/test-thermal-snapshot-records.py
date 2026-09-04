#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Mutation fixtures for future host admission's strict snapshot parser."""
from thermal_snapshot_records import BANKS, SENSORS, parse_complete, parse_series, parse_status


def make(attempt=1):
    return (f'abi=1 attempt={attempt} error=0 complete=1 count=7 valid_mask=127 '
            f'winner=6 maximum=35600 start_ns={attempt * 10} end_ns={attempt * 10 + 1}\n' +
            ''.join(f'slot={i} bank={bank} sensor={sensor} temperature={35000+i*100} valid=1\n'
                    for i, (bank, sensor) in enumerate(zip(BANKS, SENSORS))))


raw = make()
assert parse_complete(raw, 1)['maximum'] == 35600
assert len(parse_series([make(i) for i in (1, 2, 3)])) == 3
assert parse_status('abi=1 attempts=0 limit=3\n')['attempts'] == 0
mutations = [
    raw.replace('abi=1', 'abi=2'), raw.replace('attempt=1', 'attempt=2'),
    raw.replace('error=0', 'error=-5'), raw.replace('complete=1', 'complete=0'),
    raw.replace('count=7', 'count=6'), raw.replace('valid_mask=127', 'valid_mask=126'),
    raw.replace('winner=6', 'winner=5'), raw.replace('maximum=35600', 'maximum=35500'),
    raw.replace('start_ns=10', 'start_ns=12'), raw.replace('start_ns=10', 'start_ns=0'),
    raw.replace('slot=0 bank=0', 'slot=0 bank=1'), raw.replace('sensor=3', 'sensor=2'),
    raw.replace('valid=1', 'valid=0', 1), raw.replace('temperature=35000', 'temperature=150001'),
    raw.replace('abi=1', 'abi=01'), raw.replace('error=0', 'error=-0'),
    raw.replace('count=7', 'count=7 count=7'), raw + 'unexpected=1\n', raw.rstrip('\n'),
    raw.replace('end_ns=11', 'end_ns=18446744073709551616'),
]
for mutant in mutations:
    try:
        parse_complete(mutant, 1)
    except ValueError:
        pass
    else:
        raise AssertionError(mutant)
for records in ([make(1), make(2)], [make(1), make(1), make(3)],
                [make(1), make(2).replace('start_ns=20', 'start_ns=10'), make(3)]):
    try:
        parse_series(records)
    except ValueError:
        pass
    else:
        raise AssertionError(records)
for status in ('abi=1 attempts=4 limit=3\n', 'abi=1 attempts=0 limit=4\n',
               'abi=1 attempts=0 limit=3\nabi=1 attempts=0 limit=3\n'):
    try:
        parse_status(status)
    except ValueError:
        pass
    else:
        raise AssertionError(status)
print('positive_cases=3 record_mutations_rejected=20 series_mutations_rejected=3 status_mutations_rejected=3')
