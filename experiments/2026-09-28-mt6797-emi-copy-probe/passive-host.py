#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Collect one bounded WLAN EMI copy and the reviewed Gemian return."""

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
ROOT = PRIVATE_REPO / 'artifacts/emi-copy-probe/session-1'
SOURCE = HERE.parent / '2026-09-28-mt6797-emi-set-probe/passive-host.py'
SPEC = importlib.util.spec_from_file_location('emi_set_host', SOURCE)
SET = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SET)
SET.HERE = HERE
SET.ROOT = ROOT
SET.PRIVATE_REPO = PRIVATE_REPO
SET.RESET.HERE = HERE
SET.RESET.ROOT = ROOT
SET.RESET.PRIVATE_REPO = PRIVATE_REPO
SET.RESET.POWERED.HERE = HERE
SET.RESET.POWERED.ROOT = ROOT
SET.RESET.POWERED.PASSIVE.HERE = HERE
SET.RESET.POWERED.PASSIVE.ROOT = ROOT
SET.RESET.POWERED.PASSIVE.DOMAIN.HERE = HERE
SET.RESET.POWERED.PASSIVE.DOMAIN.ROOT = ROOT
SET.RESET.POWERED.PASSIVE.DOMAIN.RELEASE = '7.1.3-gemini-a53-wifi-emi-copy-probe'
SET.RESET.POWERED.PASSIVE.DOMAIN.HOST.HERE = HERE
SET.RESET.POWERED.PASSIVE.DOMAIN.HOST.ROOT = ROOT
SET.RESET.POWERED.PASSIVE.DOMAIN.HOST.REPO = PRIVATE_REPO
SET.RESET.POWERED.PASSIVE.DOMAIN.HOST.__file__ = str(Path(__file__).resolve())
SET.EMI_READY = b'one-shot EMI region 18 sealed; copy=1, firmware start and DMA held'
TRANSFER = re.compile(
    rb'one-shot EMI firmware copy: status=(-?[0-9]+) completed=([0-9]+)/([0-9]+) '
    rb'bytes=([0-9]+)/([0-9]+) attempted=([01])')


def classify_copy(log, emi):
    matches = [TRANSFER.search(line) for line in log.read_bytes().splitlines()
               if b'one-shot EMI firmware copy:' in line]
    complete = len(matches) == 1 and matches[0] is not None
    values = [int(value) for value in matches[0].groups()] if complete else []
    expected = [0, 2, 2, 396688, 396688, 1]
    return {
        'accepted': bool(emi.get('accepted') and values == expected),
        'valid_timeline': bool(emi.get('valid_timeline') and len(matches) <= 1 and
                               all(match is not None for match in matches)),
        'transfer_records': len(matches),
        'transfer': dict(zip(('status', 'completed', 'planned', 'bytes',
                              'planned_bytes', 'attempted'), values)) if values else None,
        'emi': emi,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', required=True, type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    try:
        prepared = SET.RESET.POWERED.PASSIVE.DOMAIN.prepare(args.candidate)
        prepared['finish'].REPO = PRIVATE_REPO
        if not args.execute:
            print('offline-preparation=pass; device_action=none')
            return 0
        result = prepared['execute'](prepared)
        log = ROOT / 'kmsg.log'
        hif = SET.classify(log) if (result.get('preservation', {}).get('log_complete')
                                    and log.is_file()) else {
                                        'accepted': False, 'reason': 'complete log absent'}
        emi = SET.classify_emi(log, hif) if log.is_file() else {
            'accepted': False, 'valid_timeline': False,
            'reason': 'complete log absent'}
        copy = classify_copy(log, emi) if log.is_file() else {
            'accepted': False, 'valid_timeline': False,
            'reason': 'complete log absent'}
        result['wifi_emi_copy_probe'] = copy
        (ROOT / 'wifi-emi-copy-probe-result.json').write_bytes(
            SET.RESET.POWERED.PASSIVE.DOMAIN.HOST.encoded(result))
        prepared['finish'].sync_directory(ROOT)
        print(json.dumps(result, sort_keys=True))
        return 0 if (copy.get('valid_timeline') and result.get('regression_pass') and
                     result.get('preservation', {}).get('provider_probe', {}).get('registered')) else 1
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, 'Wi-Fi EMI copy host refused: ' + str(error) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
