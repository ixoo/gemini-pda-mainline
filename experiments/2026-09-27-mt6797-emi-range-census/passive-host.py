#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Collect the authenticated EMI range census and return to Gemian."""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import re


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1] / 'artifacts/emi-range-census/session-1'
SOURCE = HERE.parent / '2026-09-27-mt6797-conn-domain-link-passive/passive-host.py'
SPEC = importlib.util.spec_from_file_location('conn_domain_host', SOURCE)
DOMAIN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DOMAIN)
DOMAIN.HERE = HERE
DOMAIN.ROOT = ROOT
DOMAIN.HOST.HERE = HERE
DOMAIN.HOST.ROOT = ROOT
DOMAIN.HOST.__file__ = str(Path(__file__).resolve())
MARKER = DOMAIN.MARKER
VCN28 = re.compile(rb'VCN28 boot control=0x([0-9a-fA-F]{4}) '
                   rb'on=([01]) source-mode=([0-7]) source-enable=([0-7])')
EMI = re.compile(rb'EMI boot region=(18|19|23) range=0x([0-9a-fA-F]{8}) '
                 rb'policy=0x([0-9a-fA-F]{8})')
CENSUS = re.compile(rb'EMI range census region=([0-9]{1,2}) raw=0x([0-9a-fA-F]{8})')


def classify_vcn28(path):
    lines = path.read_bytes().splitlines()
    owner = [line for line in lines if b'mt6797-consys' in line and MARKER in line]
    samples = [line for line in lines if b'mt6797-consys' in line and
               b'VCN28 boot control=' in line]
    if len(owner) != 1 or len(samples) != 1:
        return {'accepted': False, 'reason': 'missing or duplicate CONSYS/VCN28 record'}
    match = VCN28.search(samples[0])
    if not match:
        return {'accepted': False, 'reason': 'malformed VCN28 record'}
    raw, on, source_mode, source_enable = (int(value, 16) if i == 0 else int(value)
                                            for i, value in enumerate(match.groups()))
    if (on != ((raw >> 3) & 1) or source_mode != ((raw >> 5) & 7) or
            source_enable != ((raw >> 11) & 7)):
        return {'accepted': False, 'reason': 'VCN28 decoded fields disagree'}
    return {'accepted': True, 'raw': f'0x{raw:04x}', 'on_control': on,
            'source_mode': source_mode, 'source_enable': source_enable}


def classify_emi(path):
    lines = [line for line in path.read_bytes().splitlines()
             if b'mt6797-consys' in line and b'EMI boot region=' in line]
    if len(lines) != 3:
        return {'accepted': False, 'reason': 'expected exactly three EMI records'}
    regions = {}
    for line in lines:
        match = EMI.search(line)
        if not match:
            return {'accepted': False, 'reason': 'malformed EMI record'}
        region, range_raw, policy_raw = match.groups()
        region = int(region)
        if region in regions:
            return {'accepted': False, 'reason': 'duplicate EMI region'}
        regions[region] = {'range': '0x' + range_raw.decode().lower(),
                           'policy': '0x' + policy_raw.decode().lower()}
    if set(regions) != {18, 19, 23}:
        return {'accepted': False, 'reason': 'unexpected EMI region set'}
    if all(value == '0xffffffff' for fields in regions.values()
           for value in fields.values()):
        return {'accepted': False, 'reason': 'EMI read service unsupported signature'}
    return {'accepted': True, 'regions': regions}


def classify_census(path):
    lines = [line for line in path.read_bytes().splitlines()
             if b'mt6797-consys' in line and b'EMI range census region=' in line]
    if len(lines) != 24:
        return {'accepted': False, 'reason': 'expected exactly 24 census records'}
    regions = {}
    for line in lines:
        match = CENSUS.search(line)
        if not match:
            return {'accepted': False, 'reason': 'malformed census record'}
        region = int(match.group(1))
        if region in regions or region > 23:
            return {'accepted': False, 'reason': 'duplicate or out-of-range census region'}
        regions[region] = '0x' + match.group(2).decode().lower()
    if set(regions) != set(range(24)):
        return {'accepted': False, 'reason': 'incomplete census region set'}
    if set(regions.values()) == {'0xffffffff'}:
        return {'accepted': False, 'reason': 'uniform unsupported-service signature'}
    return {'accepted': True, 'regions': regions,
            'same_boot_positive_control': any(value != '0x00000000'
                                              for value in regions.values())}


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
        if result.get('preservation', {}).get('log_complete') and log.is_file():
            sample = classify_vcn28(log)
            emi = classify_emi(log)
            census = classify_census(log)
        else:
            sample = emi = census = {'accepted': False, 'reason': 'complete log absent'}
        result['vcn28_boot_sample'] = sample
        result['emi_boot_sample'] = emi
        result['emi_range_census'] = census
        (ROOT / 'emi-range-census-result.json').write_bytes(DOMAIN.HOST.encoded(result))
        prepared['finish'].sync_directory(ROOT)
        print(json.dumps(result, sort_keys=True))
        return 0 if (sample['accepted'] and emi['accepted'] and census['accepted'] and
                     result.get('regression_pass') and
                     result.get('preservation', {}).get('provider_probe', {}).get('registered')) else 1
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, 'EMI host refused: ' + str(error) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
