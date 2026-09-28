#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Collect one gated MT6797 HIF startup result and reviewed Gemian return."""

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
ROOT = PRIVATE_REPO / 'artifacts/wifi-hif-probe/session-1'
SOURCE = HERE.parent / '2026-09-28-mt6797-wifi-reset-release/passive-host.py'
SPEC = importlib.util.spec_from_file_location('reset_release_host', SOURCE)
RESET = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RESET)
RESET.HERE = HERE
RESET.ROOT = ROOT
RESET.PRIVATE_REPO = PRIVATE_REPO
RESET.POWERED.HERE = HERE
RESET.POWERED.ROOT = ROOT
RESET.POWERED.PASSIVE.HERE = HERE
RESET.POWERED.PASSIVE.ROOT = ROOT
RESET.POWERED.PASSIVE.DOMAIN.HERE = HERE
RESET.POWERED.PASSIVE.DOMAIN.ROOT = ROOT
RESET.POWERED.PASSIVE.DOMAIN.RELEASE = '7.1.3-gemini-a53-wifi-hif-probe'
RESET.POWERED.PASSIVE.DOMAIN.HOST.HERE = HERE
RESET.POWERED.PASSIVE.DOMAIN.HOST.ROOT = ROOT
RESET.POWERED.PASSIVE.DOMAIN.HOST.REPO = PRIVATE_REPO
RESET.POWERED.PASSIVE.DOMAIN.HOST.__file__ = str(Path(__file__).resolve())

VCN33 = re.compile(rb'one-shot HIF VCN33 before: BT=0x([0-9a-f]{4}) WiFi=0x([0-9a-f]{4})')
BEFORE = re.compile(rb'one-shot HIF before enable: IOEx=0x([0-9a-f]{2}) IORx=0x([0-9a-f]{2})')
AFTER = re.compile(rb'one-shot HIF after enable: IOEx=0x([0-9a-f]{2}) IORx=0x([0-9a-f]{2})')
WCIR = re.compile(rb'one-shot HIF WCIR=0x([0-9a-f]{8})')
READY = b'one-shot HIF function ready; firmware and DMA held'
STOPPED = b'one-shot HIF stopped ('


def classify(log):
    reset = RESET.classify(log)
    lines = log.read_bytes().splitlines()

    def capture(marker, pattern):
        found = [pattern.search(line) for line in lines if marker in line]
        return found, [int(group, 16) for group in found[0].groups()] if len(found) == 1 and found[0] else []

    vcn33, vcn33_values = capture(b'one-shot HIF VCN33 before:', VCN33)
    before, before_values = capture(b'one-shot HIF before enable:', BEFORE)
    after, after_values = capture(b'one-shot HIF after enable:', AFTER)
    wcir, wcir_values = capture(b'one-shot HIF WCIR=', WCIR)
    ready = [line for line in lines if READY in line]
    stopped = [line for line in lines if STOPPED in line]
    count_ok = (all(len(found) <= 1 and all(match is not None for match in found)
                    for found in (vcn33, before, after, wcir)) and
                len(ready) <= 1 and len(stopped) <= 1 and
                not (ready and stopped))
    valid = (reset['valid_timeline'] and count_ok and
             (bool(ready) or bool(stopped) if reset['accepted'] else
              not any((vcn33, before, after, wcir, ready, stopped))))
    accepted = (valid and reset['accepted'] and len(ready) == 1 and
                len(vcn33_values) == 2 and len(before_values) == 2 and
                len(after_values) == 2 and len(wcir_values) == 1 and
                ((vcn33_values[0] | vcn33_values[1]) & 0x000a) == 0 and
                before_values == [0, 0] and after_values == [2, 2] and
                (wcir_values[0] & 0xffff) == 0x0279)
    return {'accepted': accepted, 'valid_timeline': valid,
            'vcn33_before': ['0x%04x' % value for value in vcn33_values],
            'hif_before': ['0x%02x' % value for value in before_values],
            'hif_after': ['0x%02x' % value for value in after_values],
            'wcir': '0x%08x' % wcir_values[0] if wcir_values else None,
            'ready_records': len(ready), 'stopped_records': len(stopped),
            'reset_release': reset}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', required=True, type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    try:
        prepared = RESET.POWERED.PASSIVE.DOMAIN.prepare(args.candidate)
        prepared['finish'].REPO = PRIVATE_REPO
        if not args.execute:
            print('offline-preparation=pass; device_action=none')
            return 0
        result = prepared['execute'](prepared)
        log = ROOT / 'kmsg.log'
        probe = classify(log) if (result.get('preservation', {}).get('log_complete') and
                                  log.is_file()) else {
                                      'accepted': False, 'reason': 'complete log absent'}
        result['wifi_hif_probe'] = probe
        (ROOT / 'wifi-hif-probe-result.json').write_bytes(
            RESET.POWERED.PASSIVE.DOMAIN.HOST.encoded(result))
        prepared['finish'].sync_directory(ROOT)
        print(json.dumps(result, sort_keys=True))
        return 0 if (probe.get('valid_timeline') and result.get('regression_pass') and
                     result.get('preservation', {}).get('provider_probe', {}).get('registered')) else 1
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, 'Wi-Fi HIF host refused: ' + str(error) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
