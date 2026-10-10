#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Turn a private /dev/kmsg stream of one gemini-wifi-ref-v10 cycle into the sanitized ledger.

The ledger is the only publishable product. It holds, in kernel-log order, every
`gwref10` record with its kernel sequence number, monotonic microseconds, record
number, category and the key=value fields the observer formatted, plus the arm and
seal markers and completeness checks: the kernel sequence must be contiguous from
the arm line to the seal line (a gap is a drop), the seal counts must equal the
records seen, and every record field value must be a bare integer or one of the
observer's class words, so no address or name can pass through.

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
FIELD = re.compile(r'^([a-z_0-9]+)=(0x[0-9a-f]{1,8}|\d{1,10}|bss|own|bcast|zero|group|other|eapol|mgmt|data)$')
CATEGORIES = ('cmd', 'event', 'credit', 'rxd', 'txd', 'state')


def parse_fields(text):
    """Return the record's fields; the first bare word (if any) is its subtype."""
    fields = {}
    subtype = None
    for token in text.split():
        if '=' not in token:
            if subtype is not None or not re.fullmatch(r'[a-z]+', token):
                raise ValueError('unexpected token ' + token)
            subtype = token
            continue
        match = FIELD.fullmatch(token)
        if not match:
            raise ValueError('field not sanitizable: ' + token.split('=')[0])
        key, value = match.groups()
        fields[key] = int(value, 0) if value[0].isdigit() else value
    return subtype, fields


def parse(lines):
    ledger = {'arm': None, 'seal': None, 'caps': [], 'records': [], 'problems': []}
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
        arm = ARM.match(message)
        if arm:
            if ledger['arm'] is not None:
                ledger['problems'].append('second arm line')
            ledger['arm'] = {'seq': seq, 'usec': usec, 'deadline_s': int(arm.group(1)),
                             'caps': dict(zip(CATEGORIES, (int(arm.group(i)) for i in range(2, 8))))}
            expected_seq = seq + 1
            continue
        seal = SEAL.match(message)
        if seal:
            if ledger['arm'] is None:
                ledger['problems'].append('seal before arm')
            counts = {}
            values = [int(v) for v in seal.groups()[3:]]
            for i, category in enumerate(CATEGORIES):
                counts[category] = {'recorded': values[3 * i], 'suppressed': values[3 * i + 1],
                                    'filtered': values[3 * i + 2]}
            ledger['seal'] = {'seq': seq, 'usec': usec, 'reason': seal.group(1),
                              'records': int(seal.group(2)), 'truncated': int(seal.group(3)), 'counts': counts}
            if ledger['seal']['truncated']:
                ledger['problems'].append('%d truncated records' % ledger['seal']['truncated'])
            continue
        cap = CAP.match(message)
        if cap:
            ledger['caps'].append({'seq': seq, 'usec': usec, 'category': cap.group(1),
                                   'records': int(cap.group(2))})
            continue
        record = RECORD.match(message)
        if not record:
            continue
        if ledger['arm'] is None or ledger['seal'] is not None:
            ledger['problems'].append('record outside the armed window: n=%s' % record.group(2))
        if prio & 7 != 7:
            ledger['problems'].append('record not KERN_DEBUG: n=%s' % record.group(2))
        category, number, rest = record.group(1), int(record.group(2)), record.group(3) or ''
        try:
            subtype, fields = parse_fields(rest)
        except ValueError as error:
            ledger['problems'].append('record n=%d: %s' % (number, error))
            continue
        if fields.get('trunc') == 1:
            ledger['problems'].append('record n=%d truncated' % number)
        if fields.get('badlen') == 1 or fields.get('shorthdr') == 1 or fields.get('shortdesc') == 1:
            ledger.setdefault('length_refusals', 0)
            ledger['length_refusals'] += 1
        numbers.append(number)
        seen[category] += 1
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
    ledger['complete'] = not ledger['problems']
    return ledger


def summarize(ledger):
    """Counts the analysis starts from; attribution limits stated with them."""
    records = ledger['records']
    by = lambda category, subtype=None: [r for r in records if r['category'] == category and
                                          (subtype is None or r.get('subtype') == subtype)]
    keys = by('cmd', 'key')
    return {
        'commands': len(by('cmd')),
        'events': len([r for r in by('event') if 'subtype' not in r]),
        'key_commands': [{'seq': k['fields']['seq'], 'addremove': k['fields']['addremove'],
                          'keytype': k['fields']['keytype'], 'keyid': k['fields']['keyid'],
                          'peer': k['fields']['peer']} for k in keys],
        'keydone_events': [{'seq': r['fields']['seq'], 'bss': r['fields']['bss'], 'sta': r['fields']['sta']}
                           for r in by('event', 'keydone')],
        'keydone_attribution': 'by order only: the ADD_PKEY_DONE payload names no key type, key index or command sequence',
        'txdone_events': len(by('event', 'txdone')),
        'credits': len(by('credit')),
        'rxd_records': len(by('rxd')),
        'rxd_protected_unicast': len([r for r in by('rxd') if r['fields'].get('sec', 0) and not r['fields'].get('grp', 0)
                                      and not r['fields'].get('mismatch', 1)]),
        'rxd_protected_group': len([r for r in by('rxd') if r['fields'].get('sec', 0) and r['fields'].get('grp', 0)]),
        'txd_records': len(by('txd')),
        'txd_protected': len([r for r in by('txd') if r['fields'].get('prot', 0)]),
        'state_records': [r.get('subtype') for r in by('state')],
        'group_downlink_evidence': 'observed' if any(r['fields'].get('sec', 0) and r['fields'].get('grp', 0)
                                                     for r in by('rxd')) else 'missing',
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
