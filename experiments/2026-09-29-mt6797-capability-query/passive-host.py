#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Preserve one capability session, return to Gemian, and classify its reply."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys


sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PRIVATE_REPO = Path(os.environ['GEMINI_PRIVATE_REPO']).resolve(strict=True)
ROOT = PRIVATE_REPO / 'artifacts/capability-query/session-1'
CAPTURE = PRIVATE_REPO / 'artifacts/capability-query/capture-1'
SOURCE = HERE.parent / '2026-09-29-mt6797-wmt-before-start/passive-host.py'
SPEC = importlib.util.spec_from_file_location('wmt_start_host', SOURCE)
WMT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WMT)
WMT.HERE = HERE
WMT.ROOT = ROOT
WMT.CAPTURE = CAPTURE
WMT.DOMAIN.HERE = HERE
WMT.DOMAIN.ROOT = ROOT
WMT.DOMAIN.RELEASE = '7.1.3-gemini-a53-wifi-capability'
WMT.DOMAIN.HOST.HERE = HERE
WMT.DOMAIN.HOST.ROOT = ROOT
WMT.DOMAIN.HOST.REPO = PRIVATE_REPO
WMT.DOMAIN.HOST.__file__ = str(Path(__file__).resolve())
QUERY = re.compile(rb'one-shot WLAN capability query: status=(-?\d+)$')
DETAIL = re.compile(
    rb'one-shot WLAN capability: product=0x([0-9a-f]{4}) '
    rb'own=0x([0-9a-f]{4}) peer=0x([0-9a-f]{4}) '
    rb'5g_disabled=(\d+) eeprom_used=(\d+) rf_fail=(\d+) bb_fail=(\d+)$')


def classify(log):
    raw = log.read_bytes()
    lines = raw.splitlines()
    queries = [match for line in lines if (match := QUERY.search(line))]
    details = [match for line in lines if (match := DETAIL.search(line))]
    ready = sum(b'one-shot WLAN firmware ready;' in line for line in lines)
    status = int(queries[0][1]) if len(queries) == 1 else None
    fields = None
    if status == 0 and len(details) == 1:
        data = details[0].groups()
        fields = dict(zip(('product', 'firmware_own', 'firmware_peer',
                           'hw_5g_disabled', 'eeprom_used', 'rf_cal_fail',
                           'bb_cal_fail'),
                          (int(value, 16) if index < 3 else int(value)
                           for index, value in enumerate(data))))
    accepted = ready == 1 and status == 0 and fields is not None
    return {'accepted': accepted, 'firmware_ready_records': ready,
            'query_status_records': len(queries), 'query_status': status,
            'capability_records': len(details), 'capability': fields,
            'complete_log_sha256': hashlib.sha256(raw).hexdigest(),
            'radio_or_dma_enabled': False}


def main():
    rc = WMT.main()
    log = ROOT / 'kmsg.log'
    if not log.is_file():
        return rc
    result = classify(log)
    result['candidate_boot2_sha256'] = (
        json.loads((HERE / 'results/candidate.json').read_text())
        ['files']['boot2-padded.img']['sha256'])
    result['kernel_release'] = WMT.DOMAIN.RELEASE
    output = ROOT / 'capability-result.json'
    with output.open('xb') as stream:
        stream.write((json.dumps(result, indent=2, sort_keys=True) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())
    handle = os.open(ROOT, os.O_RDONLY)
    try:
        os.fsync(handle)
    finally:
        os.close(handle)
    print(json.dumps(result, sort_keys=True))
    return rc or (0 if result['accepted'] else 1)


if __name__ == '__main__':
    raise SystemExit(main())
