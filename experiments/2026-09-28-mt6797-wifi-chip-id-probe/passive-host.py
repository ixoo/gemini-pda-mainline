#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Collect one authenticated powered CONSYS chip ID and Gemian return."""

import argparse
import importlib.util
import json
import os
import re
from pathlib import Path
import sys


sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PRIVATE_REPO = Path(os.environ['GEMINI_PRIVATE_REPO']).resolve(strict=True)
ROOT = PRIVATE_REPO / 'artifacts/wifi-chip-id-probe/session-1'
SOURCE = HERE.parent / '2026-09-28-mt6797-wifi-firmware-probe/passive-host.py'
SPEC = importlib.util.spec_from_file_location('passive_wlan_host', SOURCE)
PASSIVE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PASSIVE)
PASSIVE.HERE = HERE
PASSIVE.ROOT = ROOT
PASSIVE.DOMAIN.HERE = HERE
PASSIVE.DOMAIN.ROOT = ROOT
PASSIVE.DOMAIN.RELEASE = '7.1.3-gemini-a53-wifi-chip-id-probe'
PASSIVE.DOMAIN.HOST.HERE = HERE
PASSIVE.DOMAIN.HOST.ROOT = ROOT
PASSIVE.DOMAIN.HOST.REPO = PRIVATE_REPO
PASSIVE.DOMAIN.HOST.__file__ = str(Path(__file__).resolve())
POWER = b'one-shot CONN power probe: domain confirmed ON, reset held'
STOPPED = b'one-shot CONN power probe stopped ('
SKIPPED = b'one-shot CONN chip ID skipped:'
CHIP = re.compile(rb'one-shot CONN chip ID: 0x([0-9a-f]{8}), reset held')


def classify(log):
    lines = log.read_bytes().splitlines()
    power = [line for line in lines if POWER in line]
    stopped = [line for line in lines if STOPPED in line]
    skipped = [line for line in lines if SKIPPED in line]
    chip = [CHIP.search(line) for line in lines if b'one-shot CONN chip ID:' in line]
    firmware = PASSIVE.classify(log)
    value = int(chip[0].group(1), 16) if len(chip) == 1 and chip[0] else None
    return {'accepted': len(power) == 1 and not stopped and not skipped and
            len(chip) == 1 and value == 0x0279 and firmware['accepted'],
            'power_on_records': len(power), 'power_stopped_records': len(stopped),
            'chip_id_skipped_records': len(skipped), 'chip_id_records': len(chip),
            'chip_id': '0x%08x' % value if value is not None else None,
            'firmware': firmware}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', required=True, type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    try:
        prepared = PASSIVE.DOMAIN.prepare(args.candidate)
        prepared['finish'].REPO = PRIVATE_REPO
        if not args.execute:
            print('offline-preparation=pass; device_action=none')
            return 0
        result = prepared['execute'](prepared)
        log = ROOT / 'kmsg.log'
        probe = classify(log) if (result.get('preservation', {}).get('log_complete') and
                                  log.is_file()) else {
                                      'accepted': False, 'reason': 'complete log absent'}
        result['conn_chip_id_probe'] = probe
        (ROOT / 'wifi-chip-id-probe-result.json').write_bytes(PASSIVE.DOMAIN.HOST.encoded(result))
        prepared['finish'].sync_directory(ROOT)
        print(json.dumps(result, sort_keys=True))
        return 0 if (probe['accepted'] and result.get('regression_pass') and
                     result.get('preservation', {}).get('provider_probe', {}).get('registered')) else 1
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, 'CONSYS chip-ID host refused: ' + str(error) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
