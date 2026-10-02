#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Preserve one tc4-reconcile session and return to Gemian."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys


sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PRIVATE_REPO = Path(os.environ['GEMINI_PRIVATE_REPO']).resolve(strict=True)
ROOT = PRIVATE_REPO / 'artifacts/tc4-reconcile/session-1'
CAPTURE = PRIVATE_REPO / 'artifacts/tc4-reconcile/capture-1'
SOURCE = HERE.parent / '2026-10-01-mt6797-port0-successor/passive-host.py'
SPEC = importlib.util.spec_from_file_location('port0_successor_host', SOURCE)
PRIOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PRIOR)
HOST = PRIOR.PARENT.WMT
HOST.HERE = HERE
HOST.ROOT = ROOT
HOST.CAPTURE = CAPTURE
HOST.DOMAIN.HERE = HERE
HOST.DOMAIN.ROOT = ROOT
HOST.DOMAIN.RELEASE = '7.1.3-gemini-a53-wifi-tc4-reconcile'
HOST.DOMAIN.HOST.HERE = HERE
HOST.DOMAIN.HOST.ROOT = ROOT
HOST.DOMAIN.HOST.REPO = PRIVATE_REPO
HOST.DOMAIN.HOST.__file__ = str(Path(__file__).resolve())
DRAIN = re.compile(rb'one-shot WLAN boot event drain: status=(-?\d+) count=(\d+) debug=(\d+) sleepy=(\d+) post=0x([0-9a-f]{8})$')
SLEEPY = re.compile(rb'one-shot WLAN boot sleepy: status=(-?\d+) state=(\d+) WHLPCR=0x([0-9a-f]{8})$')
RECORD = re.compile(rb'one-shot WLAN private record prepare: status=(-?\d+)$')
REGULATORY = re.compile(rb'one-shot WLAN regulatory configuration: status=(-?\d+)$')

TX_STATUS = re.compile(rb'one-shot WLAN TX status: snapshot=(\d+) status=(-?\d+) valid=0x([0-9a-f]{3}) WHCR=0x([0-9a-f]{8}) WHISR=0x([0-9a-f]{8})$')
PAGE_WORD = re.compile(rb'one-shot WLAN returned pages: snapshot=(\d+) word=(\d+) value=0x([0-9a-f]{8})$')


def tx_status(lines):
    headers = [match for line in lines if (match := TX_STATUS.search(line))]
    words = [match for line in lines if (match := PAGE_WORD.search(line))]
    snapshots = []
    complete = (len(headers) == 3 and len(words) == 24 and
                [int(match[1]) for match in headers] == [0, 1, 2] and
                [(int(match[1]), int(match[2])) for match in words] ==
                [(snapshot, word) for snapshot in range(3) for word in range(8)])
    for index in range(3):
        selected = [match for match in headers if int(match[1]) == index]
        values = [match for match in words if int(match[1]) == index]
        row = {'snapshot': index, 'complete': False}
        if len(selected) == 1:
            header = selected[0]
            row.update(status=int(header[2]), valid_words=int(header[3], 16),
                       whcr=int(header[4], 16), whisr=int(header[5], 16))
            indexes = [int(match[2]) for match in values]
            row['complete'] = (row['status'] == 0 and row['valid_words'] == 0x3ff and
                               sorted(indexes) == list(range(8)))
            if row['complete']:
                row['wtqcr'] = [int(next(match[3] for match in values
                                        if int(match[2]) == word), 16)
                                for word in range(8)]
        complete = complete and row['complete']
        snapshots.append(row)
    consumption = False
    tc4_ffa = False
    if complete:
        first, second = (row['wtqcr'] for row in snapshots[1:])
        consumption = any(first) and not any(second)
        tc4_ffa = (not any(first[:7]) and 0 < (first[7] >> 16) <= 26 and
                   0 < (first[7] & 0xffff) <= 26)
    return {'complete': complete, 'header_records': len(headers),
            'word_records': len(words), 'private_snapshots': snapshots,
            'counter_consumption_witness': consumption,
            'post_tc4_ffa_observed': tc4_ffa,
            'credit_refill_enabled': False}


BOOT_RX = re.compile(rb'one-shot WLAN boot RX: attempt=(\d+) status=(-?\d+) pre_valid=([01]) pre=0x([0-9a-f]{8}) setup=([01]) complete=([01]) staging=(\d+) post_valid=([01]) post=0x([0-9a-f]{8}) len=(\d+) type=0x([0-9a-f]{4})$')
BOOT_EVENT = re.compile(rb'one-shot WLAN boot event: attempt=(\d+) id=0x([0-9a-f]{2}) seq=(\d+)$')


def boot_rx(lines):
    rows, events = [], []
    for line in lines:
        if match := BOOT_RX.search(line):
            rows.append(dict(zip(
                ('attempt', 'status', 'pre_valid', 'pre_wrplr', 'setup',
                 'complete', 'staging', 'post_valid', 'post_wrplr', 'length', 'type'),
                (int(match[i], 16 if i in (4, 9, 11) else 10)
                 for i in range(1, 12)))))
        if match := BOOT_EVENT.search(line):
            events.append({'attempt': int(match[1]), 'id': int(match[2], 16),
                           'sequence': int(match[3])})
    expected_events = [row['attempt'] for row in rows
                       if row['status'] == 0 and row['length'] >= 8 and row['type'] == 0xe000]
    complete = (0 < len(rows) <= 8 and
                [row['attempt'] for row in rows] == list(range(1, len(rows) + 1)) and
                sum(b'one-shot WLAN boot RX:' in line for line in lines) == len(rows) and
                sum(b'one-shot WLAN boot event:' in line for line in lines) == len(events) and
                [event['attempt'] for event in events] == expected_events and
                all(0 <= event['sequence'] <= 255 for event in events))
    return {'metadata_complete': complete, 'read_records': len(rows),
            'event_records': len(events), 'private_reads': rows, 'private_events': events}


def boot_sleepy(lines, drain):
    notices = [{'status': int(match[1]), 'state': int(match[2]),
                'whlpcr': int(match[3], 16)}
               for line in lines if (match := SLEEPY.search(line))]
    complete = (drain is not None and
                0 <= drain['count'] <= 8 and
                drain['count'] == drain['debug'] + drain['sleepy'] and
                len(notices) == drain['sleepy'] and
                sum(b'one-shot WLAN boot sleepy:' in line for line in lines) == len(notices) and
                all(row['status'] == 0 and 0 <= row['state'] <= 1 and
                    row['whlpcr'] & 0x100 for row in notices))
    return {'complete': complete, 'notice_records': len(notices),
            'driver_ownership_retained': bool(notices) and complete,
            'private_notices': notices}


TC4 = re.compile(rb'one-shot WLAN TC4 reconciliation: snapshot=(\d+) status=(-?\d+) released=(\d+) free=(\d+) pending_cpu=(\d+) pending_ffa=(\d+)$')


def tc4_reconciliation(lines, counters):
    rows = [dict(zip(('snapshot', 'status', 'released', 'free', 'cpu', 'ffa'),
                     (int(match[i]) for i in range(1, 7))))
            for line in lines if (match := TC4.search(line))]
    complete = (counters['complete'] and len(rows) == 3 and
                [row['snapshot'] for row in rows] == [0, 1, 2] and
                all(row['status'] == 0 for row in rows) and
                sum(b'one-shot WLAN TC4 reconciliation:' in line for line in lines) == 3)
    if complete:
        complete = (not any(counters['private_snapshots'][0]['wtqcr']) and
                    all(rows[0][key] == 0 for key in ('released', 'free', 'cpu', 'ffa')))
    if complete:
        free = rows[1]['free'] - rows[1]['released']
        cpu = ffa = 0
        complete = 0 <= free <= 26
        for row, snapshot in zip(rows[1:], counters['private_snapshots'][1:]):
            words = snapshot['wtqcr']
            cpu += words[7] >> 16
            ffa += words[7] & 0xffff
            debt = 26 - free
            released = min(cpu, ffa)
            complete = (complete and not any(words[:7]) and
                        0 <= cpu <= debt and 0 <= ffa <= debt and
                        row['released'] == released and row['free'] == free + released and
                        row['cpu'] == cpu - released and row['ffa'] == ffa - released)
            free += released
            cpu -= released
            ffa -= released
    return {'complete': complete, 'records': len(rows),
            'bounded_matched_refund_observed': complete and
                any(row['released'] > 0 for row in rows[1:]),
            'private_ledger_snapshots': rows}


def classify(log):
    raw = log.read_bytes()
    lines = raw.splitlines()
    base = PRIOR.PARENT.classify(log)
    drains = [match for line in lines if (match := DRAIN.search(line))]
    records = [match for line in lines if (match := RECORD.search(line))]
    config_sets = [match for line in lines if (match := REGULATORY.search(line))]
    drain = None
    if len(drains) == 1:
        drain = {'status': int(drains[0][1]), 'count': int(drains[0][2]),
                 'debug': int(drains[0][3]), 'sleepy': int(drains[0][4]),
                 'post_wrplr': int(drains[0][5], 16)}
    record_status = int(records[0][1]) if len(records) == 1 else None
    config_status = int(config_sets[0][1]) if len(config_sets) == 1 else None
    counters = tx_status(lines)
    counters['credit_refill_enabled'] = True
    reconciliation = tc4_reconciliation(lines, counters)
    rx_metadata = boot_rx(lines)
    sleepy_metadata = boot_sleepy(lines, drain)
    stopped = sum(b'one-shot WLAN firmware stopped (' in line for line in lines)
    accepted = (base['firmware_ready_records'] == 1 and
                base['query_status_records'] == 1 and base['query_status'] == 0 and
                base['capability_records'] == 1 and base['trace_records'] == 1 and
                base['trace']['stage'] == 11 and base['header_records'] == 1 and
                drain is not None and drain['status'] == 0 and
                0 <= drain['count'] <= 8 and drain['post_wrplr'] == 0 and
                record_status == 0 and config_status == 0 and stopped == 0 and
                counters['complete'] and rx_metadata['metadata_complete'] and
                sleepy_metadata['complete'] and reconciliation['complete'] and
                reconciliation['bounded_matched_refund_observed'])
    return {'accepted': accepted, 'boot_rx': rx_metadata, 'boot_sleepy': sleepy_metadata,
            'tc4_reconciliation': reconciliation,
            'tx_status': counters, 'capability': base['capability'],
            'query_status': base['query_status'], 'trace': base['trace'],
            'drain_records': len(drains), 'drain': drain,
            'record_prepare_records': len(records),
            'record_prepare_status': record_status,
            'regulatory_records': len(config_sets), 'regulatory_status': config_status,
            'stop_records': stopped,
            'complete_log_sha256': hashlib.sha256(raw).hexdigest(),
            'radio_or_dma_enabled': False}



# One read-only sysfs query; no interface, regulatory request or HIF access.
WIPHY_PROBE = b"""set -eu
BB=/bin/busybox
boot_before=$($BB cat /proc/sys/kernel/random/boot_id)
kernel=$($BB uname -r)
[ "$kernel" = 7.1.3-gemini-a53-wifi-tc4-reconcile ]
count=0
index=none
bound=0
for phy in /sys/class/ieee80211/phy*; do
    [ -d "$phy" ] || continue
    count=$((count + 1))
    index=$($BB cat "$phy/index")
    if [ "$($BB readlink -f "$phy/device")" = "$($BB readlink -f /sys/bus/platform/devices/10001340.consys)" ]; then
        bound=$((bound + 1))
    fi
done
boot_after=$($BB cat /proc/sys/kernel/random/boot_id)
$BB printf 'boot_before=%s\nboot_after=%s\nkernel=%s\nwiphy_count=%s\nwiphy_index=%s\nwiphy_bound=%s\n' "$boot_before" "$boot_after" "$kernel" "$count" "$index" "$bound"
"""
PREPARE = HOST.DOMAIN.prepare


def prepare_with_wiphy(candidate):
    prepared = PREPARE(candidate)
    globals_ = prepared['execute'].__globals__
    original = globals_['preserved_snapshot']
    globals_['BUDGETS']['wiphy-probe'] = (15, 8192)
    prepared['claim']['phase_budgets']['wiphy-probe'] = {
        'connections': 1, 'seconds': 15, 'stdout_bytes': 8192, 'stderr_bytes': 16384}
    prepared['claim']['wiphy_probe_script_sha256'] = hashlib.sha256(WIPHY_PROBE).hexdigest()

    def snapshot(active, boot):
        probe = {'registered': False}
        try:
            raw, err, process = globals_['invoke'](active, 'wiphy-probe', WIPHY_PROBE)
            rows = [line.split('=', 1) for line in raw.decode('ascii').splitlines()]
            fields = dict(rows)
            probe['registered'] = (
                not err and process['reason'] is None and process['exit_status'] == 0 and
                process['stdin_complete'] is True and len(fields) == len(rows) == 6 and
                fields.get('boot_before') == fields.get('boot_after') == boot and
                fields.get('kernel') == HOST.DOMAIN.RELEASE and
                fields.get('wiphy_count') == fields.get('wiphy_bound') == '1' and
                re.fullmatch(r'[0-9]+', fields.get('wiphy_index', '')) is not None)
            probe['fields'] = fields
        except (OSError, ValueError, KeyError, TypeError, UnicodeError) as error:
            probe['reason'] = str(error)
        active['collector'].write_new(ROOT / 'wiphy-probe-result.json', HOST.DOMAIN.HOST.encoded(probe))
        proof = original(active, boot)
        proof['wiphy_probe'] = probe
        return proof

    globals_['preserved_snapshot'] = snapshot
    return prepared


HOST.DOMAIN.prepare = prepare_with_wiphy

def main():
    rc = HOST.main()
    log = ROOT / 'kmsg.log'
    if not log.is_file():
        return rc
    result = classify(log)
    probe = json.loads((ROOT / 'wiphy-probe-result.json').read_text())
    result['wiphy_registered'] = probe.get('registered') is True
    result['accepted'] = result['accepted'] and result['wiphy_registered']
    result['candidate_boot2_sha256'] = (
        json.loads((HERE / 'results/candidate.json').read_text())
        ['files']['boot2-padded.img']['sha256'])
    result['kernel_release'] = HOST.DOMAIN.RELEASE
    output = ROOT / 'tc4-reconcile-result.json'
    with output.open('xb') as stream:
        stream.write((json.dumps(result, indent=2, sort_keys=True) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())
    handle = os.open(ROOT, os.O_RDONLY)
    try:
        os.fsync(handle)
    finally:
        os.close(handle)
    report = {key: value for key, value in result.items()
              if key not in ('tx_status', 'boot_rx', 'boot_sleepy', 'tc4_reconciliation')}
    report['tc4_reconciliation'] = {key: value for key, value in result['tc4_reconciliation'].items()
                                    if not key.startswith('private_')}
    report['boot_sleepy'] = {key: value for key, value in result['boot_sleepy'].items()
                             if not key.startswith('private_')}
    report['boot_rx'] = {key: value for key, value in result['boot_rx'].items()
                         if not key.startswith('private_')}
    report['tx_status'] = {key: value for key, value in result['tx_status'].items()
                           if key != 'private_snapshots'}
    print(json.dumps(report, sort_keys=True))
    return rc or (0 if result['accepted'] else 1)


if __name__ == '__main__':
    raise SystemExit(main())
