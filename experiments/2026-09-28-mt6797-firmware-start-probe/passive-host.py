#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Collect one bounded WLAN firmware start and reviewed Gemian return."""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import sys


sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PRIVATE_REPO = Path(os.environ['GEMINI_PRIVATE_REPO']).resolve(strict=True)
ROOT = PRIVATE_REPO / 'artifacts/firmware-start-probe/session-1'
SOURCE = HERE.parent / '2026-09-28-mt6797-emi-copy-probe/passive-host.py'
SPEC = importlib.util.spec_from_file_location('emi_copy_host', SOURCE)
COPY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COPY)
COPY.HERE = HERE
COPY.ROOT = ROOT
COPY.PRIVATE_REPO = PRIVATE_REPO
COPY.SET.HERE = HERE
COPY.SET.ROOT = ROOT
COPY.SET.PRIVATE_REPO = PRIVATE_REPO
COPY.SET.EMI_READY = b'one-shot EMI region 18 sealed; copy=1, firmware start gated and DMA held'
COPY.SET.RESET.HERE = HERE
COPY.SET.RESET.ROOT = ROOT
COPY.SET.RESET.PRIVATE_REPO = PRIVATE_REPO
COPY.SET.RESET.POWERED.HERE = HERE
COPY.SET.RESET.POWERED.ROOT = ROOT
COPY.SET.RESET.POWERED.PASSIVE.HERE = HERE
COPY.SET.RESET.POWERED.PASSIVE.ROOT = ROOT
COPY.SET.RESET.POWERED.PASSIVE.DOMAIN.HERE = HERE
COPY.SET.RESET.POWERED.PASSIVE.DOMAIN.ROOT = ROOT
COPY.SET.RESET.POWERED.PASSIVE.DOMAIN.RELEASE = '7.1.3-gemini-a53-wifi-firmware-start-probe'
COPY.SET.RESET.POWERED.PASSIVE.DOMAIN.HOST.HERE = HERE
COPY.SET.RESET.POWERED.PASSIVE.DOMAIN.HOST.ROOT = ROOT
COPY.SET.RESET.POWERED.PASSIVE.DOMAIN.HOST.REPO = PRIVATE_REPO
COPY.SET.RESET.POWERED.PASSIVE.DOMAIN.HOST.__file__ = str(Path(__file__).resolve())

PATTERNS = {
    'ownership_before': rb'one-shot WLAN HIF ownership before: WHLPCR=0x([0-9a-f]{8})',
    'ownership_after': rb'one-shot WLAN HIF ownership after: WHLPCR=0x([0-9a-f]{8}) requested=([01])',
    'init_before': rb'one-shot WLAN INIT before: WRPLR=0x([0-9a-f]{8}) WCIR=0x([0-9a-f]{8})',
    'ordinary': rb'one-shot WLAN ordinary transfer: status=(-?[0-9]+) completed=([0-9]+)/2 bytes=([0-9]+)/14832 failed_index=([0-9]+) firmware_status=([0-9]+) partial=([0-9]+)',
    'start_submit': rb'one-shot WLAN START submit: status=(-?[0-9]+)',
    'start_ready': rb'one-shot WLAN START ready: status=(-?[0-9]+) WCIR=0x([0-9a-f]{8})',
    'ready': rb'one-shot WLAN firmware ready; radio commands and DMA held',
    'stopped': rb'one-shot WLAN firmware stopped \((-?[0-9]+)\); ordinary=([0-9]+)/2 start=([01]), state retained',
}


def classify_start(log, copy):
    lines = log.read_bytes().splitlines()
    events = {}
    positions = {}
    syntax = True
    for name, expression in PATTERNS.items():
        marker = b'one-shot WLAN ' + (b'HIF ownership before:' if name == 'ownership_before'
                                      else b'HIF ownership after:' if name == 'ownership_after'
                                      else b'INIT before:' if name == 'init_before'
                                      else b'ordinary transfer:' if name == 'ordinary'
                                      else b'START submit:' if name == 'start_submit'
                                      else b'START ready:' if name == 'start_ready'
                                      else b'firmware ready;' if name == 'ready'
                                      else b'firmware stopped (')
        hits = [(i, re.search(expression, line)) for i, line in enumerate(lines)
                if marker in line]
        syntax &= len(hits) <= 1 and all(match is not None for _, match in hits)
        if hits and hits[0][1]:
            positions[name] = hits[0][0]
            events[name] = [part.decode() for part in hits[0][1].groups()]
    terminal = ('ready' in events) + ('stopped' in events)
    ordered = (not positions or list(positions.values()) == sorted(positions.values()))
    valid = bool(copy.get('valid_timeline') and syntax and ordered and
                 (terminal == 1 if copy.get('accepted') else terminal == 0 and not events))
    ordinary = events.get('ordinary')
    complete = ordinary is not None and ordinary[:3] == ['0', '2', '14832']
    initial = events.get('init_before')
    owned = events.get('ownership_after')
    final = events.get('start_ready')
    ready = bool(valid and copy.get('accepted') and complete and
                 ordinary[3:] == ['2', '0', '0'] and
                 owned and int(owned[0], 16) & (1 << 8) and
                 initial and int(initial[0], 16) == 0 and
                 int(initial[1], 16) & 0xffff == 0x0279 and
                 not int(initial[1], 16) & (1 << 21) and
                 events.get('start_submit') == ['0'] and
                 final and final[0] == '0' and
                 int(final[1], 16) & 0xffff == 0x0279 and
                 int(final[1], 16) & (1 << 21) and
                 'ready' in events and 'stopped' not in events)
    return {'accepted': ready, 'valid_timeline': valid,
            'events': events, 'copy': copy}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', required=True, type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    try:
        prepared = COPY.SET.RESET.POWERED.PASSIVE.DOMAIN.prepare(args.candidate)
        prepared['finish'].REPO = PRIVATE_REPO
        if not args.execute:
            print('offline-preparation=pass; device_action=none')
            return 0
        result = prepared['execute'](prepared)
        log = ROOT / 'kmsg.log'
        hif = COPY.SET.classify(log) if (result.get('preservation', {}).get('log_complete')
                                         and log.is_file()) else {
                                             'accepted': False, 'reason': 'complete log absent'}
        emi = COPY.SET.classify_emi(log, hif) if log.is_file() else {
            'accepted': False, 'valid_timeline': False,
            'reason': 'complete log absent'}
        copy = COPY.classify_copy(log, emi) if log.is_file() else {
            'accepted': False, 'valid_timeline': False,
            'reason': 'complete log absent'}
        start = classify_start(log, copy) if log.is_file() else {
            'accepted': False, 'valid_timeline': False,
            'reason': 'complete log absent'}
        result['wifi_firmware_start_probe'] = start
        (ROOT / 'wifi-firmware-start-probe-result.json').write_bytes(
            COPY.SET.RESET.POWERED.PASSIVE.DOMAIN.HOST.encoded(result))
        prepared['finish'].sync_directory(ROOT)
        print(json.dumps(result, sort_keys=True))
        return 0 if (start.get('valid_timeline') and result.get('regression_pass') and
                     result.get('preservation', {}).get('provider_probe', {}).get('registered')) else 1
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, 'Wi-Fi firmware start host refused: ' + str(error) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
