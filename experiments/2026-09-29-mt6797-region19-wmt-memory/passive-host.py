#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Collect the WMT memory session after one private setup attempt."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys


HERE = Path(__file__).resolve().parent
PRIVATE_REPO = Path(os.environ['GEMINI_PRIVATE_REPO']).resolve(strict=True)
ROOT = PRIVATE_REPO / 'artifacts/region19-wmt-memory/session-1'
CAPTURE = PRIVATE_REPO / 'artifacts/region19-wmt-memory/capture-1'
SOURCE = HERE.parent / '2026-09-29-mt6797-region19-mainline-observe/passive-host.py'
SPEC = importlib.util.spec_from_file_location('region19_passive_host', SOURCE)
HOST = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HOST)
HOST.HERE = HERE
HOST.ROOT = ROOT
HOST.DOMAIN.HERE = HERE
HOST.DOMAIN.ROOT = ROOT
HOST.DOMAIN.RELEASE = '7.1.3-gemini-a53-wifi-region19-wmtmem'
HOST.DOMAIN.HOST.HERE = HERE
HOST.DOMAIN.HOST.ROOT = ROOT
HOST.DOMAIN.HOST.REPO = PRIVATE_REPO
HOST.DOMAIN.HOST.__file__ = str(Path(__file__).resolve())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


WMT_RECORDS = (
    b'one-shot WMT before: remap=0x180e0000 region1=0x44604460 '
    b'region18=0x00000000/0x00000000',
    b'one-shot WMT before: region19=0x00000000/0x00000000 '
    b'region23=0x00000000/0x00000000 CONN=off',
    b'one-shot WMT region19: status=0 range=0xbfa8bfaf policy=0x00b6da28',
    b'one-shot WMT remap: before=0x180e0000 after=0x180e1bfa '
    b'expected=0x180e1bfa',
    b'one-shot WMT setup complete: clear=351232 verified, CONN held off',
)


def main():
    if '--execute' not in sys.argv:
        return HOST.main()
    receipt = json.loads((CAPTURE / 'receipt.json').read_text())
    candidate = json.loads((HERE / 'results/candidate.json').read_text())
    if (receipt.get('status') != 'private-one-shot-wmt-memory-captured' or
            receipt.get('candidate_boot2_sha256') !=
            candidate['files']['boot2-padded.img']['sha256'] or
            receipt.get('kernel_release') != '7.1.3-gemini-a53-wifi-region19-wmtmem' or
            receipt.get('bytes_per_read') != 524288 or
            receipt.get('clear_bytes') != 351232 or
            receipt.get('pre_equal') is not True or
            receipt.get('cleared_prefix_zero') is not True or
            receipt.get('untouched_suffix_equal') is not True or
            receipt.get('trigger_transport_complete') is not True or
            sha(CAPTURE / 'read-1/stdout.txt') != receipt.get('read_1_sha256') or
            sha(CAPTURE / 'read-2/stdout.txt') != receipt.get('read_2_sha256') or
            sha(CAPTURE / 'read-after/stdout.txt') != receipt.get('read_after_sha256')):
        raise SystemExit('private capture identity or integrity changed')
    rc = HOST.main()
    result = json.loads((ROOT / 'session-result.json').read_text())
    if result.get('mainline_boot') != receipt.get('mainline_boot_id'):
        raise SystemExit('mainline session boot differs from private capture')
    log = (ROOT / 'kmsg.log').read_bytes().splitlines()
    counts = [sum(pattern in line for line in log) for pattern in WMT_RECORDS]
    stopped = sum(b'one-shot WMT setup stopped' in line for line in log)
    active = sum(bool(re.search(rb'one-shot (?:WLAN|EMI|HIF|CONN) ', line))
                 for line in log)
    accepted = counts == [1] * len(WMT_RECORDS) and stopped == active == 0
    check = {'accepted': accepted, 'mainline_boot_id': receipt['mainline_boot_id'],
             'expected_record_counts': counts, 'stopped_records': stopped,
             'other_active_records': active, 'session_collector_exit': rc}
    (ROOT / 'wmt-record-result.json').write_text(json.dumps(check, indent=2) + '\n')
    return 0 if rc == 0 and accepted else 1


if __name__ == '__main__':
    raise SystemExit(main())
