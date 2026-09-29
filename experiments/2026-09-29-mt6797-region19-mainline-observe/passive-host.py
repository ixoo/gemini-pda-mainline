#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Collect one passive region-19 record and the reviewed Gemian return."""

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
ROOT = PRIVATE_REPO / 'artifacts/region19-observe/session-2'
SOURCE = HERE.parent / '2026-09-28-mt6797-firmware-start-probe/passive-host.py'
SPEC = importlib.util.spec_from_file_location('firmware_start_host', SOURCE)
START = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(START)
DOMAIN = START.COPY.SET.RESET.POWERED.PASSIVE.DOMAIN
DOMAIN.HERE = HERE
DOMAIN.ROOT = ROOT
DOMAIN.RELEASE = '7.1.3-gemini-a53-wifi-region19-observe'
DOMAIN.HOST.HERE = HERE
DOMAIN.HOST.ROOT = ROOT
DOMAIN.HOST.REPO = PRIVATE_REPO
DOMAIN.HOST.__file__ = str(Path(__file__).resolve())
RECORD = re.compile(
    rb'one-shot region 19 read-only: start=0x([0-9a-f]+) bytes=(\d+) '
    rb'nonzero=(\d+) pages=(\d+) first=(-?\d+) last=(-?\d+)')


def classify(log):
    lines = log.read_bytes().splitlines()
    matches = [RECORD.search(line) for line in lines if b'one-shot region 19 read-only:' in line]
    active = [line for line in lines if any(marker in line for marker in
              (b'one-shot WLAN ', b'one-shot EMI ', b'one-shot HIF ',
               b'one-shot CONN ', b'one-shot region 19 read-only failed'))]
    if len(matches) != 1 or matches[0] is None:
        return {'accepted': False, 'reason': 'missing, duplicate or malformed region-19 record',
                'active_records': len(active)}
    start, size, nonzero, pages, first, last = matches[0].groups()
    values = [int(value) for value in (size, nonzero, pages, first, last)]
    count, nonzero, pages, first, last = values
    valid = (int(start, 16) == 0xbfa80000 and count == 524288 and
             0 <= nonzero <= count and 0 <= pages <= 128 and not active and
             ((nonzero == 0 and pages == 0 and first == last == -1) or
              (nonzero > 0 and 1 <= pages <= 128 and 0 <= first <= last < 128)))
    return {'accepted': valid, 'start': '0x' + start.decode(), 'bytes': count,
            'nonzero_bytes': nonzero, 'populated_pages': pages,
            'first_page': first, 'last_page': last, 'active_records': len(active)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', required=True, type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    try:
        prepared = DOMAIN.prepare(args.candidate)
        prepared['finish'].REPO = PRIVATE_REPO
        if not args.execute:
            print('offline-preparation=pass; device_action=none')
            return 0
        result = prepared['execute'](prepared)
        log = ROOT / 'kmsg.log'
        region = classify(log) if (result.get('preservation', {}).get('log_complete') and
                                   log.is_file()) else {
                                       'accepted': False, 'reason': 'complete log absent'}
        result['region19_observation'] = region
        (ROOT / 'region19-observation-result.json').write_bytes(DOMAIN.HOST.encoded(result))
        prepared['finish'].sync_directory(ROOT)
        print(json.dumps(result, sort_keys=True))
        return 0 if (region.get('accepted') and result.get('regression_pass') and
                     result.get('preservation', {}).get('provider_probe', {}).get('registered') and
                     result.get('recovery_confirmed')) else 1
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, 'Passive region-19 host refused: ' + str(error) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
