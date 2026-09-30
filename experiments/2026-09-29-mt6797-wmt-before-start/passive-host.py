#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Collect one surviving deferred-start session and return to Gemian."""

import argparse
import importlib.util
import json
import os
from pathlib import Path


HERE = Path(__file__).resolve().parent
PRIVATE_REPO = Path(os.environ['GEMINI_PRIVATE_REPO']).resolve(strict=True)
ROOT = PRIVATE_REPO / 'artifacts/wmt-before-start/session-2'
CAPTURE = PRIVATE_REPO / 'artifacts/wmt-before-start/capture-2'
SOURCE = HERE.parent / '2026-09-29-mt6797-region19-mainline-observe/passive-host.py'
SPEC = importlib.util.spec_from_file_location('region19_passive_host', SOURCE)
HOST = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HOST)
DOMAIN = HOST.DOMAIN
DOMAIN.HERE = HERE
DOMAIN.ROOT = ROOT
DOMAIN.RELEASE = '7.1.3-gemini-a53-wifi-wmt-start'
DOMAIN.HOST.HERE = HERE
DOMAIN.HOST.ROOT = ROOT
DOMAIN.HOST.REPO = PRIVATE_REPO
DOMAIN.HOST.__file__ = str(Path(__file__).resolve())


def require(ok, why):
    if not ok:
        raise ValueError(why)


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
        wmt = json.loads((CAPTURE / 'wmt-result.json').read_text())
        start = json.loads((CAPTURE / 'start-result.json').read_text())
        candidate = json.loads((HERE / 'results/candidate-2.json').read_text())
        digest = candidate['files']['boot2-padded.img']['sha256']
        require(wmt.get('accepted') is True and
                wmt.get('candidate_boot2_sha256') == digest and
                start.get('candidate_boot2_sha256') == digest and
                start.get('boot_id') == wmt.get('boot_id') and
                start.get('one_host_start_attempt') is True and
                start.get('firmware_start_request_sent') is True,
                'capture identity or one-shot evidence changed')
        result = prepared['execute'](prepared)
        require(result.get('mainline_boot') == start['boot_id'],
                'session and deferred-start boot differ')
        log = ROOT / 'kmsg.log'
        lines = log.read_bytes().splitlines() if (
            result.get('preservation', {}).get('log_complete') and log.is_file()) else []
        markers = (
            b'one-shot WMT setup complete: clear=351232 verified, CONN held off',
            b'one-shot WLAN after WMT: prepower admission passed',
            b'one-shot WLAN START submit:',
            b'one-shot WLAN START ready:',
            b'one-shot WLAN firmware ready;',
            b'one-shot WLAN firmware stopped (',
            b'Gemini WLAN diagnostic: null workqueue pool',
        )
        counts = {marker.decode(): sum(marker in line for line in lines)
                  for marker in markers}
        result['deferred_start_records'] = {
            'capture_boot_id': start['boot_id'],
            'candidate_boot2_sha256': digest,
            'log_complete': bool(lines), 'record_counts': counts,
            'wmt_prestart_accepted': True,
        }
        (ROOT / 'deferred-start-result.json').write_bytes(DOMAIN.HOST.encoded(result))
        prepared['finish'].sync_directory(ROOT)
        print(json.dumps(result, sort_keys=True))
        return 0 if (result.get('regression_pass') and
                     result.get('preservation', {}).get('provider_probe', {}).get('registered') and
                     result.get('recovery_confirmed') and bool(lines) and
                     counts[markers[0].decode()] == 1 and
                     counts[markers[1].decode()] == 1) else 1
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, 'WMT-before-START host refused: ' + str(error) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
