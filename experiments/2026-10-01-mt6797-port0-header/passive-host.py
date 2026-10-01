#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Preserve one port-0 header session, return to Gemian, and classify it."""

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
ROOT = PRIVATE_REPO / 'artifacts/port0-header/session-1'
CAPTURE = PRIVATE_REPO / 'artifacts/port0-header/capture-1'
SOURCE = HERE.parent / '2026-09-29-mt6797-wmt-before-start/passive-host.py'
SPEC = importlib.util.spec_from_file_location('wmt_start_host', SOURCE)
WMT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WMT)
WMT.HERE = HERE
WMT.ROOT = ROOT
WMT.CAPTURE = CAPTURE
WMT.DOMAIN.HERE = HERE
WMT.DOMAIN.ROOT = ROOT
WMT.DOMAIN.RELEASE = '7.1.3-gemini-a53-wifi-port0-header'
WMT.DOMAIN.HOST.HERE = HERE
WMT.DOMAIN.HOST.ROOT = ROOT
WMT.DOMAIN.HOST.REPO = PRIVATE_REPO
WMT.DOMAIN.HOST.__file__ = str(Path(__file__).resolve())
QUERY = re.compile(rb'one-shot WLAN capability query: status=(-?\d+)$')
TRACE = re.compile(
    rb'one-shot WLAN capability trace: stage=(\d+) pre_valid=(\d+) '
    rb'pre=0x([0-9a-f]{8}) tx_setup=(\d+) tx_complete=(\d+) '
    rb'tx_bytes=(\d+) post_valid=(\d+) post=0x([0-9a-f]{8}) '
    rb'rx_setup=(\d+) rx_complete=(\d+) rx_bytes=(\d+)$')
HEADER = re.compile(
    rb'one-shot WLAN capability event header: len=(\d+) '
    rb'type=0x([0-9a-f]{4}) id=(\d+) seq=(\d+)$')
DETAIL = re.compile(
    rb'one-shot WLAN capability: product=0x([0-9a-f]{4}) '
    rb'own=0x([0-9a-f]{4}) peer=0x([0-9a-f]{4}) '
    rb'5g_disabled=(\d+) eeprom_used=(\d+) rf_fail=(\d+) bb_fail=(\d+)$')
PORT0 = re.compile(
    rb'one-shot WLAN port0: status=(-?\d+) pre_valid=(\d+) '
    rb'pre=0x([0-9a-f]{8}) rx_setup=(\d+) rx_complete=(\d+) '
    rb'rx_bytes=(\d+) header_valid=(\d+) length=(\d+) '
    rb'type=0x([0-9a-f]{4}) kind=(\d+) post_valid=(\d+) '
    rb'post=0x([0-9a-f]{8})$')
PORT0_EVENT = re.compile(rb'one-shot WLAN port0 event: id=(\d+) seq=(\d+)$')


def classify(log):
    raw = log.read_bytes()
    lines = raw.splitlines()
    queries = [match for line in lines if (match := QUERY.search(line))]
    details = [match for line in lines if (match := DETAIL.search(line))]
    traces = [match for line in lines if (match := TRACE.search(line))]
    headers = [match for line in lines if (match := HEADER.search(line))]
    port0_matches = [match for line in lines if (match := PORT0.search(line))]
    port0_events = [match for line in lines if (match := PORT0_EVENT.search(line))]
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
    trace = None
    if len(traces) == 1:
        names = ('stage', 'pre_valid', 'pre_wrplr', 'tx_setup',
                 'tx_complete', 'tx_bytes', 'post_valid', 'post_wrplr',
                 'rx_setup', 'rx_complete', 'rx_bytes')
        trace = dict(zip(names,
                         (int(value, 16) if index in (2, 7) else int(value)
                          for index, value in enumerate(traces[0].groups()))))
    header = None
    if len(headers) == 1:
        header = dict(zip(('length', 'packet_type', 'event_id', 'sequence'),
                          (int(value, 16) if index == 1 else int(value)
                           for index, value in enumerate(headers[0].groups()))))
    port0 = None
    if len(port0_matches) == 1:
        names = ('status', 'pre_valid', 'pre_wrplr', 'rx_setup',
                 'rx_complete', 'rx_bytes', 'header_valid', 'length',
                 'packet_type', 'kind', 'post_valid', 'post_wrplr')
        port0 = dict(zip(names,
                         (int(value, 16) if index in (2, 8, 11) else int(value)
                          for index, value in enumerate(port0_matches[0].groups()))))
    port0_event = None
    if len(port0_events) == 1:
        port0_event = {'event_id': int(port0_events[0][1]),
                       'sequence': int(port0_events[0][2])}
    accepted = (ready == 1 and status == 0 and fields is not None and
                trace is not None and trace['stage'] == 11 and
                trace['rx_complete'] == 1 and header is not None and
                port0 is not None and
                (port0['status'] != 0 or
                 (port0['rx_complete'] == 1 and port0['header_valid'] == 1 and
                  port0['rx_bytes'] == 96 and port0['length'] == 89)) and
                (len(port0_events) == 1) == (port0['kind'] == 1))
    return {'accepted': accepted, 'firmware_ready_records': ready,
            'query_status_records': len(queries), 'query_status': status,
            'capability_records': len(details), 'capability': fields,
            'trace_records': len(traces), 'trace': trace,
            'header_records': len(headers), 'header': header,
            'port0_records': len(port0_matches), 'port0': port0,
            'port0_event_records': len(port0_events),
            'port0_event': port0_event,
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
    output = ROOT / 'port0-result.json'
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
