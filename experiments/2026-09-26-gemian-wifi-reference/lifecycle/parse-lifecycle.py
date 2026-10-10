#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Turn a private /dev/kmsg stream of one gemini-wifi-ref-v10 cycle into the sanitized ledger.

The ledger is the only publishable product. It holds, in kernel-log order, every
`gwref10` record with its kernel sequence number, monotonic microseconds, record
number, category, subtype and fields, plus the arm, cap and seal markers and two
completeness verdicts: `stream_intact` (one arm, one seal, contiguous kernel
sequence between them, record numbers contiguous from 1, seal counts equal to the
records parsed, every record valid against the schema) and `complete`, which also
requires zero suppressed and zero truncated records, so a capped category never
passes as a full lifecycle.

Every record is validated against the observer's schema: an allow-listed subtype
per category and, per subtype, an allow-listed field set with a type (unsigned
integer, hexadecimal word, address class or transmit class). Anything else is a
problem named by field name only; values never appear in problem strings.

Input lines are /dev/kmsg records: "<prio>,<seq>,<usec>,<flags>;<message>".
"""
import argparse
import json
import re
import sys

LINE = re.compile(r'^(\d+),(\d+),(\d+),([^;]*);(.*)$')
RECORD = re.compile(r'^gwref10 (cmd|event|credit|rxd|txd|state): n=(\d+)( .*)?$')
ARM = re.compile(r'^gwref10 arm: deadline_s=(\d+) caps=(\d+)/(\d+)/(\d+)/(\d+)/(\d+)/(\d+)$')
SEAL = re.compile(r'^gwref10 seal: reason=(explicit|deadline) records=(\d+) truncated=(\d+) '
                  r'cmd=(\d+)/(\d+)/(\d+) event=(\d+)/(\d+)/(\d+) credit=(\d+)/(\d+)/(\d+) '
                  r'rxd=(\d+)/(\d+)/(\d+) txd=(\d+)/(\d+)/(\d+) state=(\d+)/(\d+)/(\d+)$')
CAP = re.compile(r'^gwref10 cap: (cmd|event|credit|rxd|txd|state) records=(\d+)$')
TOKEN = re.compile(r'^([a-z][a-z_0-9]{0,15})=([0-9a-z]{1,24})$')
WORD = re.compile(r'^[a-z]{1,12}$')
CATEGORIES = ('cmd', 'event', 'credit', 'rxd', 'txd', 'state')
CLASSES = ('bss', 'own', 'bcast', 'zero', 'group', 'other')
TXCLASSES = ('eapol', 'mgmt', 'data')
U, H, C, T = 'uint', 'hex', 'class', 'txclass'

# (category, subtype or None) -> {field: type}; a record must use exactly one allowed shape.
SCHEMA = {
    ('cmd', None): [{'cid': H, 'seq': U, 'set': U, 'len': U, 'bss': U, 'type': U},
                    {'type': U, 'frame': U, 'len': U, 'bss': U, 'sta': U},
                    {'type': U, 'short': U, 'len': U, 'bss': U},
                    {'trunc': U}],
    ('cmd', 'key'): [{'seq': U, 'addremove': U, 'tx': U, 'keytype': U, 'auth': U, 'bss': U, 'alg': U, 'keyid': U,
                      'keylen': U, 'wlan': U, 'peer': C}],
    ('cmd', 'bss'): [{'seq': U, 'bss': U, 'active': U, 'nettype': U, 'ownmac': U, 'bmcwlan': U}],
    ('cmd', 'sta'): [{'seq': U, 'sta': U, 'statype': U, 'bss': U, 'state': U, 'qos': U, 'aid': U, 'wlan': U,
                      'bmcwlan': U, 'resp': U}],
    ('cmd', 'starm'): [{'seq': U, 'action': U, 'sta': U, 'bss': U}],
    ('cmd', 'bssinfo'): [{'seq': U, 'bss': U, 'connstate': U, 'opmode': U, 'qbss': U, 'staofap': U, 'authmode': U,
                          'encstatus': U, 'physet': U, 'bmcwlan': U}],
    ('event', None): [{'eid': H, 'seq': U, 'len': U, 'hif': U}, {'eid': H, 'seq': U, 'badlen': U}, {'shorthdr': U, 'hif': U},
                      {'trunc': U}],
    ('event', 'keydone'): [{'seq': U, 'bss': U, 'sta': C}],
    ('event', 'txdone'): [{'seq': U, 'pid': U, 'status': U, 'sn': U, 'wlan': U, 'count': U, 'rate': U, 'flag': U}],
    ('event', 'starec'): [{'seq': U, 'sta': U, 'bss': U, 'peer': C}],
    ('event', 'linkq'): [{'seq': U, 'rdy': U, 'speed': U, 'busy': U}],
    ('event', 'scandone'): [{'seq': U, 'scanseq': U, 'sparse': U}],
    ('event', 'chpriv'): [{'seq': U, 'bss': U, 'token': U, 'status': U, 'channel': U, 'band': U, 'width': U,
                           'reqtype': U, 'grant_ms': U}],
    ('event', 'bcntimeout'): [{'seq': U, 'bss': U, 'reason': U}],
    ('event', 'aging'): [{'seq': U, 'sta': U}],
    ('event', 'addba'): [{'seq': U, 'sta': U, 'token': U, 'param': H, 'timeout': U, 'ssn': H}],
    ('event', 'delba'): [{'seq': U, 'sta': U, 'tid': U}],
    ('event', 'bubble'): [{'seq': U, 'sta': U, 'tid': U}],
    ('event', 'absence'): [{'seq': U, 'bss': U, 'absent': U, 'quota': U}],
    ('event', 'psmode'): [{'seq': U, 'sta': U, 'inps': U, 'mode': U, 'quota': U}],
    ('event', 'quota'): [{'seq': U, 'sta': U, 'mode': U, 'quota': U}],
    ('credit', None): [{'rel0': U, 'rel1': U, 'rel2': U, 'rel3': U, 'rel4': U, 'rel5': U,
                        'free0': U, 'free1': U, 'free2': U, 'free3': U, 'free4': U, 'free5': U}, {'trunc': U}],
    ('rxd', None): [{'type': U, 'len': U, 'span': U, 'off': U, 'hdrlen': U, 'pad': U, 'trans': U, 'bssid': U, 'wlan': U,
                     'tid': U, 'sec': U, 'status': H, 'mismatch': U, 'fmt': U, 'uc2me': U, 'mc': U, 'bc': U, 'grp': U, 'fc': H,
                     'havefc': U, 'eth': H},
                    {'shortdesc': U, 'hif': U}, {'badlen': U, 'declared': U, 'hif': U}, {'badhdr': U, 'declared': U, 'hif': U},
                    {'trunc': U}],
    ('txd', None): [{'cls': T, 'pid': U, 'wlan': U, 'bss': U, 'sta': U, 'len': U, 'fmt': U, 'tid': U, 'prot': U,
                     'is80211': U, 'tc': U}, {'trunc': U}],
    ('state', 'stastate'): [{'sta': U, 'wlan': U, 'bss': U, 'from': U, 'to': U}],
    ('state', 'stafree'): [{'sta': U, 'wlan': U, 'bss': U, 'state': U}],
    ('state', 'bssdeact'): [{'bss': U}],
}
# Accepted data, conservatively: the data path's own test (nic_rx.c nicRxProcessDataPacket, nic_rx.h
# RXS_DW2_RX_nERR_BITMAP 0x07f8: cipher length, ICV, TKIP MIC, length mismatch, de-AMSDU, exceed length,
# LLC mismatch, UDF) plus the FCS error (bit 1) and cipher mismatch (bit 2) flags, which the driver
# handles separately and which never describe correctly decrypted data; non-data (0x3000 == 0x2000) and
# fragments (0x3800 == 0x0800) are not whole accepted data frames either.
RX_ERROR_MASK = 0x07fe
RX_NON_DATA = (0x3000, 0x2000)
RX_FRAGMENT = (0x3800, 0x0800)


def accepted_data(fields):
    status = fields.get('status', RX_ERROR_MASK)
    return (fields.get('type') == 2 and (status & RX_ERROR_MASK) == 0 and
            (status & RX_NON_DATA[0]) != RX_NON_DATA[1] and (status & RX_FRAGMENT[0]) != RX_FRAGMENT[1])


def typed(value, kind):
    if kind == U:
        return int(value) if re.fullmatch(r'\d{1,10}', value) else None
    if kind == H:
        return int(value, 16) if re.fullmatch(r'0x[0-9a-f]{1,8}', value) else None
    if kind == C:
        return value if value in CLASSES else None
    if kind == T:
        return value if value in TXCLASSES else None
    return None


def parse_record(category, text):
    """Return (subtype, fields, problems) for one record body; problems name fields only."""
    problems = []
    tokens = text.split()
    subtype = None
    if tokens and '=' not in tokens[0]:
        subtype = tokens.pop(0)
        if not WORD.match(subtype) or (category, subtype) not in SCHEMA:
            return None, {}, ['unexpected subtype']
    shapes = SCHEMA.get((category, subtype))
    if shapes is None:
        return None, {}, ['unexpected record shape']
    raw = {}
    for token in tokens:
        match = TOKEN.match(token)
        if not match:
            return subtype, {}, ['unparsable field']
        key, value = match.groups()
        if key in raw:
            return subtype, {}, ['duplicate field ' + key]
        raw[key] = value
    if 'trunc' in raw:
        problems.append('truncated record')
    for shape in shapes:
        if set(shape) == set(raw):
            fields = {}
            for key, kind in shape.items():
                value = typed(raw[key], kind)
                if value is None:
                    return subtype, {}, problems + ['field type mismatch ' + key]
                fields[key] = value
            return subtype, fields, problems
    if 'trunc' in raw:
        return subtype, {}, problems
    unexpected = sorted(set(raw) - set().union(*[set(s) for s in shapes]))
    missing = all(set(raw) < set(s) or not set(raw) <= set(s) for s in shapes)
    if unexpected:
        return subtype, {}, problems + ['unexpected field ' + ' '.join(unexpected)]
    return subtype, {}, problems + ['incomplete record' if missing else 'unexpected record shape']


def parse(lines):
    ledger = {'arm': None, 'seal': None, 'caps': [], 'records': [], 'problems': [], 'length_refusals': 0}
    expected_seq = None
    seen = dict.fromkeys(CATEGORIES, 0)
    numbers = []
    for raw in lines:
        match = LINE.match(raw.rstrip('\n'))
        if not match:
            if raw.startswith(' '):
                continue  # kmsg continuation line of some other message
            ledger['problems'].append('unparsable kmsg line')
            continue
        prio, seq, usec, _flags, message = match.groups()
        seq, usec, prio = int(seq), int(usec), int(prio)
        if ledger['arm'] is not None and ledger['seal'] is None:
            if expected_seq is not None and seq != expected_seq:
                ledger['problems'].append('kmsg sequence gap: expected %d saw %d' % (expected_seq, seq))
            expected_seq = seq + 1
        if not message.startswith('gwref10 '):
            continue
        arm = ARM.match(message)
        if arm:
            if ledger['arm'] is not None:
                ledger['problems'].append('second arm line')
                continue
            ledger['arm'] = {'seq': seq, 'usec': usec, 'deadline_s': int(arm.group(1)),
                             'caps': dict(zip(CATEGORIES, (int(arm.group(i)) for i in range(2, 8))))}
            expected_seq = seq + 1
            continue
        seal = SEAL.match(message)
        if seal:
            if ledger['seal'] is not None:
                ledger['problems'].append('second seal line')
                continue
            if ledger['arm'] is None:
                ledger['problems'].append('seal before arm')
            counts = {}
            values = [int(v) for v in seal.groups()[3:]]
            for i, category in enumerate(CATEGORIES):
                counts[category] = {'recorded': values[3 * i], 'suppressed': values[3 * i + 1],
                                    'filtered': values[3 * i + 2]}
            ledger['seal'] = {'seq': seq, 'usec': usec, 'reason': seal.group(1),
                              'records': int(seal.group(2)), 'truncated': int(seal.group(3)), 'counts': counts}
            continue
        cap = CAP.match(message)
        if cap:
            ledger['caps'].append({'seq': seq, 'usec': usec, 'category': cap.group(1), 'records': int(cap.group(2))})
            continue
        record = RECORD.match(message)
        if not record:
            ledger['problems'].append('unknown gwref10 line')
            continue
        category, number, rest = record.group(1), int(record.group(2)), record.group(3) or ''
        if ledger['arm'] is None or ledger['seal'] is not None:
            ledger['problems'].append('record outside the armed window: n=%d' % number)
        if prio & 7 != 7:
            ledger['problems'].append('record not KERN_DEBUG: n=%d' % number)
        subtype, fields, problems = parse_record(category, rest.strip())
        numbers.append(number)
        seen[category] += 1
        if problems:
            ledger['problems'].extend('record n=%d: %s' % (number, p) for p in problems)
            continue
        if any(k in fields for k in ('badlen', 'shorthdr', 'shortdesc', 'badhdr')):
            ledger['length_refusals'] += 1
        entry = {'seq': seq, 'usec': usec, 'n': number, 'category': category, 'fields': fields}
        if subtype:
            entry['subtype'] = subtype
        ledger['records'].append(entry)
    if ledger['arm'] is None:
        ledger['problems'].append('no arm line')
    if ledger['seal'] is None:
        ledger['problems'].append('no seal line')
    else:
        if ledger['seal']['records'] != len(numbers):
            ledger['problems'].append('seal records=%d but %d records parsed' % (ledger['seal']['records'], len(numbers)))
        for category in CATEGORIES:
            if ledger['seal']['counts'][category]['recorded'] != seen[category]:
                ledger['problems'].append('seal %s recorded=%d but %d parsed' % (
                    category, ledger['seal']['counts'][category]['recorded'], seen[category]))
    if numbers != list(range(1, len(numbers) + 1)):
        ledger['problems'].append('record numbers not contiguous from 1')
    ledger['stream_intact'] = not ledger['problems']
    suppressed = sum(c['suppressed'] for c in ledger['seal']['counts'].values()) if ledger['seal'] else 0
    truncated = ledger['seal']['truncated'] if ledger['seal'] else 0
    ledger['suppressed'] = suppressed
    ledger['truncated'] = truncated
    ledger['complete'] = ledger['stream_intact'] and suppressed == 0 and truncated == 0
    return ledger


def summarize(ledger):
    """Counts the analysis starts from, with attribution and classification limits stated."""
    records = ledger['records']

    def by(category, subtype=None):
        return [r for r in records if r['category'] == category and (subtype is None or r.get('subtype') == subtype)]

    def header_only(category):
        return [r for r in by(category) if 'subtype' not in r]

    rxd = [r for r in by('rxd') if 'type' in r['fields']]
    data = [r for r in rxd if accepted_data(r['fields']) and r['fields']['sec'] != 0]
    protected_unicast = [r for r in data if r['fields']['grp'] == 0 and r['fields']['uc2me'] == 1
                         and r['fields']['mc'] == 0 and r['fields']['bc'] == 0]
    protected_group = [r for r in data if r['fields']['grp'] == 1 and (r['fields']['mc'] == 1 or r['fields']['bc'] == 1)]
    inconsistent = [r for r in rxd if r['fields']['sec'] != 0 and r not in protected_unicast and r not in protected_group]
    errored = [r for r in rxd if (r['fields']['status'] & RX_ERROR_MASK) != 0]
    keys = by('cmd', 'key')
    return {
        'commands': len(header_only('cmd')),
        'events': len(header_only('event')),
        'key_commands': [{'seq': k['fields']['seq'], 'addremove': k['fields']['addremove'],
                          'keytype': k['fields']['keytype'], 'keyid': k['fields']['keyid'],
                          'peer': k['fields']['peer']} for k in keys],
        'keydone_events': [{'seq': r['fields']['seq'], 'bss': r['fields']['bss'], 'sta': r['fields']['sta']}
                           for r in by('event', 'keydone')],
        'keydone_attribution': 'by order only: the ADD_PKEY_DONE payload names no key type, key index or command sequence',
        'txdone_events': len(by('event', 'txdone')),
        'credits': len(by('credit')),
        'rxd_records': len(rxd),
        'rxd_protected_unicast': len(protected_unicast),
        'rxd_protected_group': len(protected_group),
        'rxd_security_metadata_unclassified': len(inconsistent),
        'rxd_error_status': len(errored),
        'rxd_classification': 'protected means an accepted data frame (no error bit in status 0x07fe: the data '
                              'path\'s 0x07f8 test plus FCS and cipher mismatch; not non-data, not a fragment), security '
                              'mode nonzero and consistent unicast or group match flags; other security metadata is '
                              'counted separately',
        'txd_records': len(by('txd')),
        'txd_protected': len([r for r in by('txd') if r['fields'].get('prot', 0)]),
        'state_records': [r.get('subtype') for r in by('state')],
        'group_downlink_evidence': 'observed' if protected_group else 'missing',
        'complete': ledger['complete'],
        'stream_intact': ledger['stream_intact'],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('kmsg', help='private kmsg-cycle.log')
    parser.add_argument('--ledger', help='write the sanitized ledger JSON here')
    args = parser.parse_args()
    with open(args.kmsg, encoding='utf-8', errors='replace') as handle:
        ledger = parse(handle)
    ledger['summary'] = summarize(ledger)
    text = json.dumps(ledger, indent=2, sort_keys=True) + '\n'
    if args.ledger:
        with open(args.ledger, 'w', encoding='utf-8') as handle:
            handle.write(text)
    else:
        sys.stdout.write(text)
    return 0 if ledger['complete'] else 1


if __name__ == '__main__':
    sys.exit(main())
