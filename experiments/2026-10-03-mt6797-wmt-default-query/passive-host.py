#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Collect one surviving WMT query session and return to Gemian."""

import argparse
import importlib.util
import json
import os
from pathlib import Path


HERE = Path(__file__).resolve().parent
PRIVATE_REPO = Path(os.environ['GEMINI_PRIVATE_REPO']).resolve(strict=True)
ROOT = PRIVATE_REPO / 'artifacts/wmt-default-query/session-1'
CAPTURE = PRIVATE_REPO / 'artifacts/wmt-default-query/capture-1'
SOURCE = HERE.parent / '2026-09-29-mt6797-region19-mainline-observe/passive-host.py'
SPEC = importlib.util.spec_from_file_location('region19_passive_host', SOURCE)
HOST = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HOST)
DOMAIN = HOST.DOMAIN
DOMAIN.HERE = HERE
DOMAIN.ROOT = ROOT
DOMAIN.RELEASE = '7.1.3-gemini-a53-wmt-query'
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
        result = prepared['execute'](prepared)
        log = ROOT / 'kmsg.log'
        complete = result.get('preservation', {}).get('log_complete') and log.is_file()
        capture = importlib.util.spec_from_file_location('query_capture', HERE / 'capture-private.py')
        module = importlib.util.module_from_spec(capture)
        capture.loader.exec_module(module)
        result['wmt_query'] = module.query_result(log.read_bytes()) if complete else {
            'matched_response': False, 'reason': 'complete sealed log absent'}
        (ROOT / 'wmt-query-session-result.json').write_bytes(DOMAIN.HOST.encoded(result))
        prepared['finish'].sync_directory(ROOT)
        print(json.dumps(result, sort_keys=True))
        return 0 if (result.get('regression_pass') and result.get('recovery_confirmed') and
                     complete and result['wmt_query'].get('matched_response')) else 1
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, 'WMT query host refused: ' + str(error) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
