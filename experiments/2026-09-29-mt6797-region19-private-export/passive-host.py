#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Collect the passive A53 session after private region-19 capture."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
PRIVATE_REPO = Path(os.environ['GEMINI_PRIVATE_REPO']).resolve(strict=True)
ROOT = PRIVATE_REPO / 'artifacts/region19-export/session-1'
CAPTURE = PRIVATE_REPO / 'artifacts/region19-export/capture-1'
SOURCE = HERE.parent / '2026-09-29-mt6797-region19-mainline-observe/passive-host.py'
SPEC = importlib.util.spec_from_file_location('region19_passive_host', SOURCE)
HOST = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HOST)
HOST.HERE = HERE
HOST.ROOT = ROOT
HOST.DOMAIN.HERE = HERE
HOST.DOMAIN.ROOT = ROOT
HOST.DOMAIN.RELEASE = '7.1.3-gemini-a53-wifi-region19-export'
HOST.DOMAIN.HOST.HERE = HERE
HOST.DOMAIN.HOST.ROOT = ROOT
HOST.DOMAIN.HOST.REPO = PRIVATE_REPO
HOST.DOMAIN.HOST.__file__ = str(Path(__file__).resolve())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if '--execute' not in sys.argv:
        return HOST.main()
    receipt = json.loads((CAPTURE / 'receipt.json').read_text())
    candidate = json.loads((HERE / 'results/candidate.json').read_text())
    if (receipt.get('status') != 'private-read-only-mainline-region19-captured' or
            receipt.get('candidate_boot2_sha256') !=
            candidate['files']['boot2-padded.img']['sha256'] or
            receipt.get('kernel_release') != '7.1.3-gemini-a53-wifi-region19-export' or
            receipt.get('bytes_per_read') != 524288 or
            sha(CAPTURE / 'read-1/stdout.txt') != receipt.get('read_1_sha256') or
            sha(CAPTURE / 'read-2/stdout.txt') != receipt.get('read_2_sha256')):
        raise SystemExit('private capture identity or integrity changed')
    rc = HOST.main()
    result = json.loads((ROOT / 'session-result.json').read_text())
    if result.get('mainline_boot') != receipt.get('mainline_boot_id'):
        raise SystemExit('mainline session boot differs from private capture')
    return rc if receipt.get('equal') is True else 1


if __name__ == '__main__':
    raise SystemExit(main())
