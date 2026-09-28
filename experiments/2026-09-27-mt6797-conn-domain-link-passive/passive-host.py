#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Collect the authenticated passive CONN-domain-link boot and return to Gemian."""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import runpy


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1] / 'artifacts/conn-domain-link/session-1'
SOURCE = HERE.parent / '2026-09-27-mt6797-consys-rails-passive/passive-host.py'
SPEC = importlib.util.spec_from_file_location('consys_rails_host', SOURCE)
HOST = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HOST)
HOST.HERE = HERE
HOST.ROOT = ROOT
HOST.__file__ = str(Path(__file__).resolve())
MARKER = b'bound boot CONSYS reserve, remap, VCN, CONMCU reset and checked-OFF CONN domain'
RETURN_V2 = HERE.parent / '2026-09-09-standard-kernel-package/a53-ram-return-v2.py'
RETURN_V2_SHA = '4ef45cd11071a9de2e0c0b6cefbc9dfb1b5f75b6ca2b68f264bcf6f7e3522fe6'
RELEASE = '7.1.3-gemini-a53-consys-owner-passive'
PROBE = r'''set -eu
BB=/bin/busybox
export LC_ALL=C
$BB printf '__CONN_PROVIDER_BEGIN__\n'
boot_before=$($BB cat /proc/sys/kernel/random/boot_id)
$BB printf 'boot_before=%s\n' "$boot_before"
$BB printf 'kernel=%s\n' "$($BB uname -r)"
count=0
bound=0
for device in /sys/bus/platform/devices/*; do
    [ -r "$device/of_node/compatible" ] || continue
    compatible=$($BB tr '\000' '\n' < "$device/of_node/compatible")
    [ "$compatible" = 'mediatek,mt6797-power-controller' ] || continue
    count=$((count + 1))
    if [ -L "$device/driver" ]; then
        driver=$($BB readlink "$device/driver")
        case "$driver" in */mtk-power-controller) bound=$((bound + 1));; esac
    fi
done
$BB printf 'provider_count=%s\nprovider_bound=%s\n' "$count" "$bound"
boot_after=$($BB cat /proc/sys/kernel/random/boot_id)
$BB printf 'boot_after=%s\n__CONN_PROVIDER_END__\n' "$boot_after"
'''.encode('ascii')


def classify_probe(raw, err, process, boot):
    if (err or process['exit_status'] != 0 or process['reason'] is not None or
            not process['stdin_complete'] or process['stdout_bytes'] != len(raw) or
            process['stderr_bytes'] != len(err)):
        return {'registered': False, 'reason': 'incomplete provider probe transport'}
    try:
        lines = raw.decode('ascii').splitlines()
        if len(lines) != 7 or lines[0] != '__CONN_PROVIDER_BEGIN__' or \
                lines[-1] != '__CONN_PROVIDER_END__':
            raise ValueError('provider probe framing')
        fields = {}
        for line in lines[1:-1]:
            key, sep, value = line.partition('=')
            if not sep or key in fields:
                raise ValueError('provider probe fields')
            fields[key] = value
        if fields.keys() != {'boot_before', 'boot_after', 'kernel',
                             'provider_count', 'provider_bound'} or \
                fields['boot_before'] != boot or fields['boot_after'] != boot or \
                fields['kernel'] != RELEASE or \
                not re.fullmatch(r'[0-9]+', fields['provider_count']) or \
                not re.fullmatch(r'[0-9]+', fields['provider_bound']):
            raise ValueError('provider probe identity')
        registered = fields['provider_count'] == fields['provider_bound'] == '1'
        return {'registered': registered, 'provider_count': int(fields['provider_count']),
                'provider_bound': int(fields['provider_bound']), 'boot_id': boot}
    except (UnicodeError, ValueError):
        return {'registered': False, 'reason': 'invalid provider probe result'}


def prepare(candidate):
    if RETURN_V2.is_symlink() or hashlib.sha256(RETURN_V2.read_bytes()).hexdigest() != RETURN_V2_SHA:
        raise ValueError('Gemian return v2 source changed')
    prepared = HOST.prepare(candidate)
    returning = runpy.run_path(str(RETURN_V2))
    if returning['TRUST_SHA'] != 'd43262bd1f9c76d02eb633900f5e5502e2342d6c1b41586a2d7e524a2293768f':
        raise ValueError('Gemian return v2 trust changed')
    prepared['returning'].watch = returning['watch']
    prepared['claim']['gemian_return_v2_sha256'] = RETURN_V2_SHA
    globals_ = prepared['execute'].__globals__
    original_snapshot = globals_['preserved_snapshot']
    globals_['BUDGETS']['provider-probe'] = (15, 8192)
    prepared['claim']['phase_budgets']['provider-probe'] = {
        'connections': 1, 'seconds': 15, 'stdout_bytes': 8192, 'stderr_bytes': 16384}
    prepared['claim']['provider_probe_script_sha256'] = hashlib.sha256(PROBE).hexdigest()

    def snapshot_with_probe(active, boot):
        try:
            raw, err, process = globals_['invoke'](active, 'provider-probe', PROBE)
            probe = classify_probe(raw, err, process, boot)
        except (OSError, ValueError, KeyError, TypeError) as error:
            probe = {'registered': False, 'reason': str(error)}
        active['collector'].write_new(ROOT / 'provider-probe-result.json', HOST.encoded(probe))
        proof = original_snapshot(active, boot)
        proof['provider_probe'] = probe
        return proof

    globals_['preserved_snapshot'] = snapshot_with_probe
    return prepared


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', required=True, type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    try:
        prepared = prepare(args.candidate)
        if not args.execute:
            print('offline-preparation=pass; device_action=none')
            return 0
        result = prepared['execute'](prepared)
        log = ROOT / 'kmsg.log'
        if result.get('preservation', {}).get('log_complete') and log.is_file():
            lines = [line for line in log.read_bytes().splitlines()
                     if b'mt6797-consys' in line and MARKER in line]
            if len(lines) == 1:
                result['consys_reset_bound'] = True
                result['consys_reset_record'] = lines[0].decode('ascii', errors='replace')
        (ROOT / 'conn-domain-link-result.json').write_bytes(HOST.encoded(result))
        prepared['finish'].sync_directory(ROOT)
        print(json.dumps(result, sort_keys=True))
        return 0 if (result.get('consys_reset_bound') and result.get('regression_pass') and
                     result.get('preservation', {}).get('provider_probe', {}).get('registered')) else 1
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, 'CONN domain-link host refused: ' + str(error) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
