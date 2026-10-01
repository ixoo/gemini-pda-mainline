#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Preserve one private-record probe session and return to Gemian."""

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
ROOT = PRIVATE_REPO / 'artifacts/record-runtime/session-1'
CAPTURE = PRIVATE_REPO / 'artifacts/record-runtime/capture-1'
SOURCE = HERE.parent / '2026-10-01-mt6797-port0-successor/passive-host.py'
SPEC = importlib.util.spec_from_file_location('port0_successor_host', SOURCE)
PRIOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PRIOR)
HOST = PRIOR.PARENT.WMT
HOST.HERE = HERE
HOST.ROOT = ROOT
HOST.CAPTURE = CAPTURE
HOST.DOMAIN.HERE = HERE
HOST.DOMAIN.ROOT = ROOT
HOST.DOMAIN.RELEASE = '7.1.3-gemini-a53-wifi-record-runtime'
HOST.DOMAIN.HOST.HERE = HERE
HOST.DOMAIN.HOST.ROOT = ROOT
HOST.DOMAIN.HOST.REPO = PRIVATE_REPO
HOST.DOMAIN.HOST.__file__ = str(Path(__file__).resolve())
DRAIN = re.compile(rb'one-shot WLAN boot debug drain: status=(-?\d+) count=(\d+) post=0x([0-9a-f]{8})$')
RECORD = re.compile(rb'one-shot WLAN private record prepare: status=(-?\d+)$')


def classify(log):
    raw = log.read_bytes()
    lines = raw.splitlines()
    base = PRIOR.PARENT.classify(log)
    drains = [match for line in lines if (match := DRAIN.search(line))]
    records = [match for line in lines if (match := RECORD.search(line))]
    drain = None
    if len(drains) == 1:
        drain = {'status': int(drains[0][1]), 'count': int(drains[0][2]),
                 'post_wrplr': int(drains[0][3], 16)}
    record_status = int(records[0][1]) if len(records) == 1 else None
    stopped = sum(b'one-shot WLAN firmware stopped (' in line for line in lines)
    accepted = (base['firmware_ready_records'] == 1 and
                base['query_status_records'] == 1 and base['query_status'] == 0 and
                base['capability_records'] == 1 and base['trace_records'] == 1 and
                base['trace']['stage'] == 11 and base['header_records'] == 1 and
                drain is not None and drain['status'] == 0 and
                1 <= drain['count'] <= 8 and drain['post_wrplr'] == 0 and
                record_status == 0 and stopped == 0)
    return {'accepted': accepted, 'capability': base['capability'],
            'query_status': base['query_status'], 'trace': base['trace'],
            'drain_records': len(drains), 'drain': drain,
            'record_prepare_records': len(records),
            'record_prepare_status': record_status, 'stop_records': stopped,
            'complete_log_sha256': hashlib.sha256(raw).hexdigest(),
            'radio_or_dma_enabled': False}


def main():
    rc = HOST.main()
    log = ROOT / 'kmsg.log'
    if not log.is_file():
        return rc
    result = classify(log)
    result['candidate_boot2_sha256'] = (
        json.loads((HERE / 'results/candidate.json').read_text())
        ['files']['boot2-padded.img']['sha256'])
    result['kernel_release'] = HOST.DOMAIN.RELEASE
    output = ROOT / 'record-result.json'
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
