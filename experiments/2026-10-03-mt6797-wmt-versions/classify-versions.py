#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Validate sealed version-read logs independently of the host printf result."""
import hashlib
import re


def classify(log):
    result = {'identity_accepted': False, 'radio_action': False, 'reads': []}
    owner_lines = [line for line in log.splitlines() if b'one-shot WMT versions:' in line]
    owner = [m for line in owner_lines if (m := re.search(
        rb'one-shot WMT versions: result=(-?\d+) completed=([0-3]) clocks-held=([01])$', line))]
    if len(owner_lines) != 1 or len(owner) != 1:
        result['reason'] = 'missing, duplicate or malformed owner record'
        return result
    status, completed, held = map(int, owner[0].groups())
    result.update(status=status, completed=completed, clocks_held=bool(held))
    reads = {}
    wire = {(ordinal, name): bytearray() for ordinal in range(3) for name in ('TX', 'RX')}
    for line in log.splitlines():
        if b'WMT version ' not in line:
            continue
        suffix = line.split(b'WMT version ', 1)[1]
        record = re.fullmatch(rb'([0-2]): result=(-?\d+) tx=(\d+) rx=(\d+) services=(\d+) terminal=([01])', suffix)
        chunk = re.fullmatch(rb'([0-2]) (TX|RX): ([0-9a-f]{8}): ((?:[0-9a-f]{2}(?: |$))+)', suffix)
        if record:
            ordinal, ret, tx, rx, services, terminal = map(int, record.groups())
            if ordinal != len(reads):
                result['reason'] = 'duplicate read record'
                return result
            reads[ordinal] = dict(ordinal=ordinal, status=ret, tx=tx, rx=rx,
                                  services=services, terminal=bool(terminal))
        elif chunk:
            ordinal = int(chunk[1]); name = chunk[2].decode()
            data = wire[ordinal, name]; part = bytes.fromhex(chunk[4].decode())
            if (ordinal not in reads or int(chunk[3], 16) != len(data) or len(data) % 16 or
                    not 1 <= len(part) <= 16 or len(data) + len(part) > {'TX': 26, 'RX': 22}[name]):
                result['reason'] = 'duplicate, discontinuous or oversized wire record'
                return result
            data.extend(part)
        else:
            result['reason'] = 'malformed or unknown read/wire record'
            return result
    consistent = sorted(reads) == list(range(len(reads)))
    successes = 0
    for ordinal in range(3):
        if ordinal not in reads:
            consistent &= not wire[ordinal, 'TX'] and not wire[ordinal, 'RX']
            continue
        read = reads[ordinal]
        command = bytearray.fromhex('8040140001081000020100010800008000000000ffff00000000')
        command[12] = (8, 0, 4)[ordinal]
        reply = bytearray.fromhex('8040100002080c000000000108000080790200000000')
        reply[12] = (8, 0, 4)[ordinal]
        reply[16:18] = (b'\x79\x02', b'\x00\x8a', b'\x00\x8a')[ordinal]
        tx, rx = wire[ordinal, 'TX'], wire[ordinal, 'RX']
        read['rx_sha256'] = hashlib.sha256(rx).hexdigest()
        read['checked_reply'] = rx == reply
        read['bounded'] = (read['terminal'] and 0 <= read['tx'] <= 26 and
                           0 <= read['rx'] <= 22 and 0 <= read['services'] <= 64 and
                           len(tx) == read['tx'] and len(rx) == read['rx'] and tx == command[:len(tx)])
        if read['status'] == 0:
            consistent &= (successes == ordinal and read['bounded'] and
                           read['tx'] == 26 and read['services'] >= 1 and read['checked_reply'])
            successes += 1
        else:
            consistent &= read['bounded'] and ordinal == len(reads) - 1 and ordinal == successes
        result['reads'].append(read)
    forbidden = (b'one-shot WMT negotiation:', b'WMT negotiation ', b'one-shot WLAN ',
                 b'one-shot EMI ', b'one-shot HIF ')
    result['no_continuation'] = not any(marker in log for marker in forbidden)
    result['evidence_consistent'] = bool(consistent and held == 1 and
        completed == successes and result['no_continuation'] and
        (not reads or reads[len(reads)-1]['status'] == 0 or status == reads[len(reads)-1]['status']) and
        ((status == 0 and completed == 3) or (status != 0 and completed < 3)))
    result['identity_accepted'] = result['evidence_consistent'] and status == 0 and completed == 3
    result['reason'] = ('checked tuple 0279/8a00/8a00' if result['identity_accepted'] else
                        'preserve first unknown or incomplete reply; no automatic retry')
    return result
