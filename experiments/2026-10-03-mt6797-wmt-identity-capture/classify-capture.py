#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Account for private raw chip-capture evidence; accept no WMT identity."""
import hashlib
import re

COMMAND = bytes.fromhex('8040140001081000020100010800008000000000ffff00000000')
PREFIX = b'WMT identity capture '


def classify(log):
    result = {'capture_complete': False, 'identity_accepted': False,
              'radio_action': False}
    lines = [line for line in log.splitlines() if b'one-shot WMT identity capture:' in line]
    pattern = rb'one-shot WMT identity capture: result=(-?\d+) tx=(\d+) rx=(\d+) services=(\d+) terminal=([01]) clocks-held=([01])$'
    records = [m for line in lines if (m := re.search(pattern, line))]
    if len(lines) != 1 or len(records) != 1:
        result['reason'] = 'missing, duplicate or malformed terminal record'
        return result
    status, tx, rx, services, terminal, held = map(int, records[0].groups())
    result.update(status=status, tx=tx, rx=rx, services=services,
                  terminal=bool(terminal), clocks_held=bool(held))
    wire = {'TX': bytearray(), 'RX': bytearray()}
    for line in log.splitlines():
        if PREFIX not in line:
            continue
        suffix = line.split(PREFIX, 1)[1]
        match = re.fullmatch(rb'(TX|RX): ([0-9a-f]{8}): ((?:[0-9a-f]{2}(?: |$))+)', suffix)
        if not match:
            result['reason'] = 'malformed or unknown wire record'
            return result
        name = match[1].decode()
        data = wire[name]
        chunk = bytes.fromhex(match[3].decode())
        if (int(match[2], 16) != len(data) or len(data) % 16 or
                not 1 <= len(chunk) <= 16 or len(data) + len(chunk) > {'TX': 26, 'RX': 32}[name]):
            result['reason'] = 'duplicate, discontinuous or oversized wire record'
            return result
        data.extend(chunk)
    checks = {
        'bounded_counts': 0 <= tx <= 26 and 0 <= rx <= 32 and 0 <= services <= 64,
        'exact_logged_counts': tx == len(wire['TX']) and rx == len(wire['RX']),
        'command_prefix': wire['TX'] == COMMAND[:tx],
        'terminal_retained': terminal == 1 and held == 1,
        'no_other_transport_or_WLAN': not any(marker in log for marker in
            (b'one-shot WMT negotiation:', b'WMT negotiation ', b'one-shot WLAN ',
             b'one-shot EMI ', b'one-shot HIF ')),
    }
    result['checks'] = checks
    result['evidence_consistent'] = all(checks.values())
    result['capture_complete'] = result['evidence_consistent'] and status == -110 and tx == 26 and services >= 1
    result['rx_sha256'] = hashlib.sha256(wire['RX']).hexdigest()
    result['next_action'] = ('review captured encoding privately' if result['capture_complete'] and rx
                             else 'diagnose finite capture result; no automatic retry')
    return result
