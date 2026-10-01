#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Preserve one port-0 successor session and return to Gemian."""

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
ROOT = PRIVATE_REPO / 'artifacts/port0-successor/session-1'
CAPTURE = PRIVATE_REPO / 'artifacts/port0-successor/capture-1'
SOURCE = HERE.parent / '2026-10-01-mt6797-port0-header/passive-host.py'
SPEC = importlib.util.spec_from_file_location('port0_header_host', SOURCE)
PARENT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PARENT)
PARENT.WMT.HERE = HERE
PARENT.WMT.ROOT = ROOT
PARENT.WMT.CAPTURE = CAPTURE
PARENT.WMT.DOMAIN.HERE = HERE
PARENT.WMT.DOMAIN.ROOT = ROOT
PARENT.WMT.DOMAIN.RELEASE = '7.1.3-gemini-a53-wifi-port0-successor'
PARENT.WMT.DOMAIN.HOST.HERE = HERE
PARENT.WMT.DOMAIN.HOST.ROOT = ROOT
PARENT.WMT.DOMAIN.HOST.REPO = PRIVATE_REPO
PARENT.WMT.DOMAIN.HOST.__file__ = str(Path(__file__).resolve())
SUCCESSOR = re.compile(
    rb'one-shot WLAN port0 successor: status=(-?\d+) pre_valid=(\d+) '
    rb'pre=0x([0-9a-f]{8}) rx_setup=(\d+) rx_complete=(\d+) '
    rb'bytes=(\d+) post_valid=(\d+) post=0x([0-9a-f]{8}) '
    rb'len=(\d+) type=0x([0-9a-f]{4})$')
EVENT = re.compile(rb'one-shot WLAN port0 successor event: id=(\d+) seq=(\d+)$')


def classify(log):
    base = PARENT.classify(log)
    lines = log.read_bytes().splitlines()
    records = [match for line in lines if (match := SUCCESSOR.search(line))]
    events = [match for line in lines if (match := EVENT.search(line))]
    successor = None
    if len(records) == 1:
        names = ('status', 'pre_valid', 'pre_wrplr', 'rx_setup', 'rx_complete',
                 'rx_bytes', 'post_valid', 'post_wrplr', 'length', 'packet_type')
        successor = dict(zip(names,
                             (int(value, 16) if index in (2, 7, 9) else int(value)
                              for index, value in enumerate(records[0].groups()))))
    event = None
    if len(events) == 1:
        event = {'event_id': int(events[0][1]), 'sequence': int(events[0][2])}
    first = base['port0']
    prerequisite = (base['accepted'] and first is not None and
                    first['status'] == 0 and first['post_valid'] == 1 and
                    first['post_wrplr'] == 80)
    complete = (prerequisite and successor is not None and
                successor['status'] == 0 and successor['pre_valid'] == 1 and
                successor['pre_wrplr'] == 80 and successor['rx_setup'] == 1 and
                successor['rx_complete'] == 1 and successor['rx_bytes'] == 84 and
                successor['post_valid'] == 1 and successor['length'] == 80 and
                (len(events) == 1) ==
                (successor['packet_type'] == 0xe000) and len(events) <= 1)
    return {'accepted': complete, 'prerequisite_reproduced': prerequisite,
            'first_port0': first, 'first_port0_event': base['port0_event'],
            'successor_records': len(records), 'successor': successor,
            'successor_event_records': len(events), 'successor_event': event,
            'capability': base['capability'],
            'complete_log_sha256': hashlib.sha256(log.read_bytes()).hexdigest(),
            'radio_or_dma_enabled': False}


def main():
    rc = PARENT.WMT.main()
    log = ROOT / 'kmsg.log'
    if not log.is_file():
        return rc
    result = classify(log)
    result['candidate_boot2_sha256'] = (
        json.loads((HERE / 'results/candidate.json').read_text())
        ['files']['boot2-padded.img']['sha256'])
    result['kernel_release'] = PARENT.WMT.DOMAIN.RELEASE
    output = ROOT / 'successor-result.json'
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
