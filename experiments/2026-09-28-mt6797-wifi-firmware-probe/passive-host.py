#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Collect one authenticated passive WLAN firmware probe and Gemian return."""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1] / 'artifacts/wifi-firmware-probe/session-1'
SOURCE = HERE.parent / '2026-09-27-mt6797-conn-domain-link-passive/passive-host.py'
SPEC = importlib.util.spec_from_file_location('conn_domain_host', SOURCE)
DOMAIN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DOMAIN)
DOMAIN.HERE = HERE
DOMAIN.ROOT = ROOT
DOMAIN.RELEASE = '7.1.3-gemini-a53-wifi-firmware-probe'
DOMAIN.HOST.HERE = HERE
DOMAIN.HOST.ROOT = ROOT
DOMAIN.HOST.__file__ = str(Path(__file__).resolve())
FIRMWARE = re.compile(rb'validated WLAN firmware: (\d+) sections, ordinary '
                      rb'(\d+)/(\d+) bytes, EMI (\d+)/(\d+) bytes; execution held')


def classify(log):
    lines = log.read_bytes().splitlines()
    owners = [line for line in lines if b'mt6797-consys' in line and
              DOMAIN.MARKER in line and b'populated passive children' in line]
    firmware = [line for line in lines if b'validated WLAN firmware:' in line]
    if len(owners) != 1 or len(firmware) != 1:
        return {'accepted': False, 'reason': 'missing or duplicate owner/firmware record'}
    match = FIRMWARE.search(firmware[0])
    if not match:
        return {'accepted': False, 'reason': 'malformed firmware record'}
    fields = tuple(int(value) for value in match.groups())
    if fields != (4, 2, 14832, 2, 396688):
        return {'accepted': False, 'reason': 'unexpected retained image plan',
                'observed': fields}
    return {'accepted': True, 'sections': fields[0],
            'ordinary_sections': fields[1], 'ordinary_bytes': fields[2],
            'emi_sections': fields[3], 'emi_bytes': fields[4]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', required=True, type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    try:
        prepared = DOMAIN.prepare(args.candidate)
        if not args.execute:
            print('offline-preparation=pass; device_action=none')
            return 0
        result = prepared['execute'](prepared)
        log = ROOT / 'kmsg.log'
        firmware = classify(log) if (result.get('preservation', {}).get('log_complete') and
                                    log.is_file()) else {
                                        'accepted': False, 'reason': 'complete log absent'}
        result['wlan_firmware_probe'] = firmware
        (ROOT / 'wifi-firmware-probe-result.json').write_bytes(DOMAIN.HOST.encoded(result))
        prepared['finish'].sync_directory(ROOT)
        print(json.dumps(result, sort_keys=True))
        return 0 if (firmware['accepted'] and result.get('regression_pass') and
                     result.get('preservation', {}).get('provider_probe', {}).get('registered')) else 1
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, 'WLAN firmware host refused: ' + str(error) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
