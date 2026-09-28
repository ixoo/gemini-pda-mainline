#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Collect one gated CONMCU reset-release result and reviewed Gemian return."""

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
ROOT = PRIVATE_REPO / 'artifacts/wifi-reset-release/session-1'
SOURCE = HERE.parent / '2026-09-28-mt6797-wifi-powered-emi/passive-host.py'
SPEC = importlib.util.spec_from_file_location('powered_emi_host', SOURCE)
POWERED = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(POWERED)
POWERED.HERE = HERE
POWERED.ROOT = ROOT
POWERED.PASSIVE.HERE = HERE
POWERED.PASSIVE.ROOT = ROOT
POWERED.PASSIVE.DOMAIN.HERE = HERE
POWERED.PASSIVE.DOMAIN.ROOT = ROOT
POWERED.PASSIVE.DOMAIN.RELEASE = '7.1.3-gemini-a53-wifi-reset-release'
POWERED.PASSIVE.DOMAIN.HOST.HERE = HERE
POWERED.PASSIVE.DOMAIN.HOST.ROOT = ROOT
POWERED.PASSIVE.DOMAIN.HOST.REPO = PRIVATE_REPO
POWERED.PASSIVE.DOMAIN.HOST.__file__ = str(Path(__file__).resolve())
ACR = re.compile(rb'one-shot CONN MCU ACR: before=0x([0-9a-f]{8}) after=0x([0-9a-f]{8})')
RELEASED = re.compile(rb'one-shot CONN MCU reset released: chip-id=0x([0-9a-f]{8}), domain ON')
STOPPED = b'one-shot CONN MCU reset release stopped ('
SKIPPED = b'one-shot CONN MCU reset release skipped: EMI gate'
UNEXPECTED = b'one-shot CONN MCU reset release: unexpected chip ID; state retained'


def classify(log):
    powered = POWERED.classify(log)
    lines = log.read_bytes().splitlines()
    acr = [ACR.search(line) for line in lines if b'one-shot CONN MCU ACR:' in line]
    released = [RELEASED.search(line) for line in lines
                if b'one-shot CONN MCU reset released:' in line]
    stopped = [line for line in lines if STOPPED in line]
    skipped = [line for line in lines if SKIPPED in line]
    unexpected = [line for line in lines if UNEXPECTED in line]
    gate = (powered['chip_id_0279'] and powered['emi_snapshot_complete'] and
            powered['emi_control'].get('region1') == '0x44604460' and
            powered['emi_control'].get('region23_before') == '0x00000000' and
            powered['emi_control'].get('region23_after') == '0x00000000' and
            all(powered['emi_regions'].get(key) == '0x00000000' for key in
                ('region18_range', 'region18_policy',
                 'region19_range', 'region19_policy')))
    acr_pair = ([int(group, 16) for group in acr[0].groups()]
                if len(acr) == 1 and acr[0] else [])
    released_id = (int(released[0].group(1), 16)
                   if len(released) == 1 and released[0] else None)
    records_valid = (powered['valid_timeline'] and len(acr) <= 1 and
                     all(match is not None for match in acr) and
                     len(released) <= 1 and all(match is not None for match in released) and
                     (not released or bool(acr)) and
                     len(stopped) <= 1 and len(skipped) <= 1 and
                     len(unexpected) <= 1 and
                     (bool(skipped) == (powered['chip_id_0279'] and not gate)) and
                     (not acr and not released and not stopped if not gate else
                      not skipped and bool(released) != bool(stopped)))
    accepted = (records_valid and gate and len(acr_pair) == 2 and
                acr_pair[1] == (acr_pair[0] | (1 << 18)) and
                released_id == 0x0279 and not unexpected)
    return {'accepted': accepted, 'valid_timeline': records_valid,
            'same_boot_gate_passed': gate,
            'acr_before': '0x%08x' % acr_pair[0] if acr_pair else None,
            'acr_after': '0x%08x' % acr_pair[1] if acr_pair else None,
            'released_chip_id': '0x%08x' % released_id if released_id is not None else None,
            'reset_release_stopped_records': len(stopped),
            'reset_release_skipped_records': len(skipped),
            'unexpected_chip_id_records': len(unexpected),
            'powered_emi': powered}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', required=True, type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    try:
        prepared = POWERED.PASSIVE.DOMAIN.prepare(args.candidate)
        prepared['finish'].REPO = PRIVATE_REPO
        if not args.execute:
            print('offline-preparation=pass; device_action=none')
            return 0
        result = prepared['execute'](prepared)
        log = ROOT / 'kmsg.log'
        probe = classify(log) if (result.get('preservation', {}).get('log_complete') and
                                  log.is_file()) else {
                                      'accepted': False, 'reason': 'complete log absent'}
        result['conn_reset_release_probe'] = probe
        (ROOT / 'wifi-reset-release-result.json').write_bytes(
            POWERED.PASSIVE.DOMAIN.HOST.encoded(result))
        prepared['finish'].sync_directory(ROOT)
        print(json.dumps(result, sort_keys=True))
        return 0 if (probe.get('valid_timeline') and result.get('regression_pass') and
                     result.get('preservation', {}).get('provider_probe', {}).get('registered')) else 1
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, 'CONSYS reset-release host refused: ' + str(error) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
