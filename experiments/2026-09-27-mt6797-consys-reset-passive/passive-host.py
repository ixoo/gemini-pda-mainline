#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Collect one authenticated passive CONMCU reset-handle boot."""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import runpy


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1] / 'artifacts/consys-reset/session-1'
SOURCE = HERE.parent / '2026-09-27-mt6797-consys-rails-passive/passive-host.py'
SPEC = importlib.util.spec_from_file_location('consys_rails_host', SOURCE)
HOST = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HOST)
HOST.HERE = HERE
HOST.ROOT = ROOT
HOST.__file__ = str(Path(__file__).resolve())
MARKER = b'bound boot CONSYS reserve, remap, VCN and CONMCU reset handles'
RETURN_V2 = HERE.parent / '2026-09-09-standard-kernel-package/a53-ram-return-v2.py'
RETURN_V2_SHA = '4ef45cd11071a9de2e0c0b6cefbc9dfb1b5f75b6ca2b68f264bcf6f7e3522fe6'


def prepare(candidate):
    if RETURN_V2.is_symlink() or hashlib.sha256(RETURN_V2.read_bytes()).hexdigest() != RETURN_V2_SHA:
        raise ValueError('Gemian return v2 source changed')
    prepared = HOST.prepare(candidate)
    returning = runpy.run_path(str(RETURN_V2))
    if returning['TRUST_SHA'] != 'd43262bd1f9c76d02eb633900f5e5502e2342d6c1b41586a2d7e524a2293768f':
        raise ValueError('Gemian return v2 trust changed')
    prepared['returning'].watch = returning['watch']
    prepared['claim']['gemian_return_v2_sha256'] = RETURN_V2_SHA
    return prepared


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', required=True, type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    try:
        prepared = prepare(args.candidate)
        if not args.execute:
            print('offline-preparation=pass; device_action=none')
            return 0
        result = prepared['execute'](prepared)
        log = ROOT / 'kmsg.log'
        if result.get('preservation', {}).get('log_complete') and log.is_file():
            lines = [line for line in log.read_bytes().splitlines()
                     if b'mt6797-consys' in line and MARKER in line]
            if len(lines) == 1:
                result['consys_reset_bound'] = True
                result['consys_reset_record'] = lines[0].decode('ascii', errors='replace')
        (ROOT / 'consys-reset-result.json').write_bytes(HOST.encoded(result))
        prepared['finish'].sync_directory(ROOT)
        print(json.dumps(result, sort_keys=True))
        return 0 if result.get('consys_reset_bound') and result.get('regression_pass') else 1
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, 'CONSYS reset host refused: ' + str(error) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
