#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Preserve one regulatory-config session and return to Gemian."""

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
ROOT = PRIVATE_REPO / 'artifacts/regulatory-config/session-1'
CAPTURE = PRIVATE_REPO / 'artifacts/regulatory-config/capture-1'
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
HOST.DOMAIN.RELEASE = '7.1.3-gemini-a53-wifi-regulatory-config'
HOST.DOMAIN.HOST.HERE = HERE
HOST.DOMAIN.HOST.ROOT = ROOT
HOST.DOMAIN.HOST.REPO = PRIVATE_REPO
HOST.DOMAIN.HOST.__file__ = str(Path(__file__).resolve())
DRAIN = re.compile(rb'one-shot WLAN boot debug drain: status=(-?\d+) count=(\d+) post=0x([0-9a-f]{8})$')
RECORD = re.compile(rb'one-shot WLAN private record prepare: status=(-?\d+)$')
REGULATORY = re.compile(rb'one-shot WLAN regulatory configuration: status=(-?\d+)$')


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
                 'post_wrplr': int(drains[0][3], 16)}
    record_status = int(records[0][1]) if len(records) == 1 else None
    config_status = int(config_sets[0][1]) if len(config_sets) == 1 else None
    stopped = sum(b'one-shot WLAN firmware stopped (' in line for line in lines)
    accepted = (base['firmware_ready_records'] == 1 and
                base['query_status_records'] == 1 and base['query_status'] == 0 and
                base['capability_records'] == 1 and base['trace_records'] == 1 and
                base['trace']['stage'] == 11 and base['header_records'] == 1 and
                drain is not None and drain['status'] == 0 and
                0 <= drain['count'] <= 8 and drain['post_wrplr'] == 0 and
                record_status == 0 and config_status == 0 and stopped == 0)
    return {'accepted': accepted, 'capability': base['capability'],
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
[ "$kernel" = 7.1.3-gemini-a53-wifi-regulatory-config ]
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
    output = ROOT / 'regulatory-config-result.json'
    with output.open('xb') as stream:
        stream.write((json.dumps(result, indent=2, sort_keys=True) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())
    handle = os.open(ROOT, os.O_RDONLY)
    try:
        os.fsync(handle)
    finally:
        os.close(handle)
    print(json.dumps(result, sort_keys=True))
    return rc or (0 if result['accepted'] else 1)


if __name__ == '__main__':
    raise SystemExit(main())
