#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Collect one authenticated passive CONMCU reset-handle boot."""

import argparse
import importlib.util
import json
import os
from pathlib import Path


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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', required=True, type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    try:
        prepared = HOST.prepare(args.candidate)
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
