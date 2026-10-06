#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Classify sanitized join stage records; raw captures remain private."""

import re


def classify(raw):
    patterns = {
        'tx': rb'TX: subtype=(\d+) pid=(\d+) pages=(\d+)',
        'done': rb'TX done: pid=(\d+) status=(\d+) advanced=([01]) count=(\d+)',
        'rx': rb'RX: subtype=(\d+) status=(\d+)',
        'credit': rb'credit: pages=(\d+) remaining=(\d+)',
        'activation': rb'activation: sequence=(\d+) state=3',
        'cleanup': rb'cleanup: stage=3 credits=returned slots=retired deauth=([01])',
        'cleanup_submission': rb'cleanup submission: stage=(\d+)',
        'peer': rb'peer: ready=1 sequence=(\d+)',
        'grant': rb'grant: channel=40 interval_ms=(\d+)',
    }
    rows = {name: [] for name in patterns}
    malformed = False
    stopped = False
    for index, line in enumerate(raw.splitlines()):
        prefix = b'one-shot WLAN join '
        if prefix not in line:
            continue
        body = line.split(prefix, 1)[1]
        if body.startswith(b'stopped:'):
            stopped = True
            continue
        for name, pattern in patterns.items():
            if match := re.fullmatch(pattern, body):
                rows[name].append((index, *(int(v) for v in match.groups())))
                break
        else:
            malformed = True
    tx, done, rx = rows['tx'], rows['done'], rows['rx']
    association = [row for row in rx if row[1] == 1]
    auth = [row for row in rx if row[1] == 11]
    accepted = len(association) == 1 and association[0][2] == 0
    expected = [11, 0, 12] if accepted else [11, 0]
    sequence_ok = ([row[1] for row in tx] == expected and
                   len({row[2] for row in tx}) == len(tx) and
                   all(1 <= row[2] <= 127 and 1 <= row[3] <= 19 for row in tx))
    acknowledged = (len(done) == len(tx) and
                    {row[1] for row in done} == {row[2] for row in tx} and
                    all(row[2] == 0 for row in done) and
                    all(len([d for d in done if d[1] == t[2] and d[0] > t[0]]) == 1
                        for t in tx))
    exchange = (sequence_ok and acknowledged and len(auth) == 1 and auth[0][2] == 0 and
                len(association) == 1 and tx[0][0] < auth[0][0] < tx[1][0] < association[0][0])
    credits = rows['credit']
    expected_pages = 7 + (3 if accepted else 0) + sum(row[3] for row in tx)
    credit_ok = (bool(credits) and all(row[1] > 0 and row[2] <= 19 for row in credits) and
                 sum(row[1] for row in credits) == expected_pages and credits[-1][2] == 0)
    cleanup_ok = (len(rows['cleanup']) == 1 and
                  rows['cleanup'][0][1] == int(accepted) and
                  [row[1] for row in rows['cleanup_submission']] == [0, 1, 2] and
                  rows['cleanup'][-1][0] > rows['cleanup_submission'][-1][0] and credit_ok)
    activation_ok = (len(rows['activation']) == int(accepted) and
                     (not accepted or association[0][0] < rows['activation'][0][0] < tx[-1][0]))
    healthy = (not malformed and not stopped and len(rows['peer']) == 1 and
               len(rows['grant']) == 1 and 0 < rows['grant'][0][1] <= 9000)
    result = {
        'association_response_status': association[0][2] if len(association) == 1 else None,
        'host_management_submissions': len(tx),
        'unique_tx_acknowledgements': acknowledged,
        'management_exchange_demonstrated': bool(exchange),
        'associated_station_activation_demonstrated': bool(exchange and accepted and activation_ok),
        'healthy_cleanup_demonstrated': bool(healthy and cleanup_ok and activation_ok),
        'malformed_stage_record': malformed,
        'terminal_failure_recorded': stopped,
        'wifi_operational': False,
    }
    result['bounded_join_pass'] = bool(exchange and healthy and cleanup_ok and activation_ok)
    return result
