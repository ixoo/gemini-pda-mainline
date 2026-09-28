#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Collect one powered CONN EMI snapshot and reviewed Gemian return."""

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
ROOT = PRIVATE_REPO / 'artifacts/wifi-powered-emi/session-1'
SOURCE = HERE.parent / '2026-09-28-mt6797-wifi-firmware-probe/passive-host.py'
SPEC = importlib.util.spec_from_file_location('passive_wlan_host', SOURCE)
PASSIVE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PASSIVE)
PASSIVE.HERE = HERE
PASSIVE.ROOT = ROOT
PASSIVE.DOMAIN.HERE = HERE
PASSIVE.DOMAIN.ROOT = ROOT
PASSIVE.DOMAIN.RELEASE = '7.1.3-gemini-a53-wifi-powered-emi'
PASSIVE.DOMAIN.HOST.HERE = HERE
PASSIVE.DOMAIN.HOST.ROOT = ROOT
PASSIVE.DOMAIN.HOST.REPO = PRIVATE_REPO
PASSIVE.DOMAIN.HOST.__file__ = str(Path(__file__).resolve())
POWER = b'one-shot CONN power probe: domain confirmed ON, reset held'
STOPPED = b'one-shot CONN power probe stopped ('
SKIPPED = b'one-shot CONN chip ID skipped:'
CHIP = re.compile(rb'one-shot CONN chip ID: 0x([0-9a-f]{8}), reset held')
DELAYED = re.compile(rb'one-shot CONN chip ID after (20|40) ms: 0x([0-9a-f]{8}), reset held')
EMI_CONTROL = re.compile(
    rb'one-shot CONN EMI powered: control1=0x([0-9a-f]{8}) '
    rb'region23-before=0x([0-9a-f]{8}) region23-after=0x([0-9a-f]{8})')
EMI_REGIONS = re.compile(
    rb'one-shot CONN EMI powered: region18=0x([0-9a-f]{8}) '
    rb'policy18=0x([0-9a-f]{8}) region19=0x([0-9a-f]{8}) '
    rb'policy19=0x([0-9a-f]{8}) policy23=0x([0-9a-f]{8})')
EMI_SKIPPED = b'one-shot CONN EMI powered skipped:'


def classify(log):
    lines = log.read_bytes().splitlines()
    power = [line for line in lines if POWER in line]
    stopped = [line for line in lines if STOPPED in line]
    skipped = [line for line in lines if SKIPPED in line]
    chip = [CHIP.search(line) for line in lines if b'one-shot CONN chip ID:' in line]
    delayed = [DELAYED.search(line) for line in lines
               if b'one-shot CONN chip ID after ' in line]
    emi_control = [EMI_CONTROL.search(line) for line in lines
                   if b'one-shot CONN EMI powered: control1=' in line]
    emi_regions = [EMI_REGIONS.search(line) for line in lines
                   if b'one-shot CONN EMI powered: region18=' in line]
    emi_skipped = [line for line in lines if EMI_SKIPPED in line]
    firmware = PASSIVE.classify(log)
    value = int(chip[0].group(1), 16) if len(chip) == 1 and chip[0] else None
    samples = [{'after_ms': 0, 'chip_id': '0x%08x' % value}] if value is not None else []
    for match in delayed:
        if match:
            samples.append({'after_ms': int(match.group(1)),
                            'chip_id': '0x%08x' % int(match.group(2), 16)})
    times = [sample['after_ms'] for sample in samples]
    values = [sample['chip_id'] for sample in samples]
    expected_times = ([0] if value == 0x0279 else
                      [0, 20] if len(values) >= 2 and values[1] == '0x00000279' else
                      [0, 20, 40])
    valid = (len(power) == 1 and not stopped and not skipped and
             len(chip) == 1 and chip[0] is not None and
             all(match is not None for match in delayed) and
             times == expected_times and firmware['accepted'])
    chip_ready = valid and values[-1] == '0x00000279'
    snapshot = (len(emi_control) == 1 and emi_control[0] is not None and
                len(emi_regions) == 1 and emi_regions[0] is not None and
                not emi_skipped)
    if chip_ready:
        valid = valid and (snapshot or
                           (len(emi_skipped) == 1 and not emi_control and
                            not emi_regions))
    else:
        valid = valid and not emi_skipped and not emi_control and not emi_regions
    control = ([int(group, 16) for group in emi_control[0].groups()]
               if snapshot else [])
    regions = ([int(group, 16) for group in emi_regions[0].groups()]
               if snapshot else [])
    empty_ranges = (valid and snapshot and control[0] not in (0, 0xffffffff) and
                    control[1] == control[2] == 0 and
                    regions[0] == regions[2] == 0)
    return {'accepted': valid and snapshot,
            'valid_timeline': valid, 'chip_id_0279': chip_ready,
            'emi_snapshot_complete': snapshot,
            'empty_ranges_with_control': empty_ranges,
            'emi_skipped_records': len(emi_skipped),
            'emi_control': {
                'region1': '0x%08x' % control[0],
                'region23_before': '0x%08x' % control[1],
                'region23_after': '0x%08x' % control[2],
            } if snapshot else {},
            'emi_regions': {
                'region18_range': '0x%08x' % regions[0],
                'region18_policy': '0x%08x' % regions[1],
                'region19_range': '0x%08x' % regions[2],
                'region19_policy': '0x%08x' % regions[3],
                'region23_policy_cached': '0x%08x' % regions[4],
            } if snapshot else {},
            'power_on_records': len(power), 'power_stopped_records': len(stopped),
            'chip_id_skipped_records': len(skipped), 'chip_id_records': len(chip),
            'delayed_chip_id_records': len(delayed), 'samples': samples,
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
        result['conn_powered_emi_probe'] = probe
        (ROOT / 'wifi-powered-emi-result.json').write_bytes(PASSIVE.DOMAIN.HOST.encoded(result))
        prepared['finish'].sync_directory(ROOT)
        print(json.dumps(result, sort_keys=True))
        return 0 if (probe.get('valid_timeline') and result.get('regression_pass') and
                     result.get('preservation', {}).get('provider_probe', {}).get('registered')) else 1
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, 'CONSYS powered EMI host refused: ' + str(error) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
