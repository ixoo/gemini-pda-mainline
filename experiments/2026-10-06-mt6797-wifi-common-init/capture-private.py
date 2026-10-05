#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Preserve WMT evidence, run one Phase A trigger and classify its kernel log."""

import importlib.util
import json
import os
from pathlib import Path
import re
import sys


sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PRIVATE_REPO = Path(os.environ['GEMINI_PRIVATE_REPO']).resolve(strict=True)
ROOT = PRIVATE_REPO / 'artifacts/wifi-phase-a'
SOURCE = HERE.parent / '2026-09-29-mt6797-wmt-before-start/capture-private.py'
SPEC = importlib.util.spec_from_file_location('wmt_start_capture', SOURCE)
WMT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WMT)
RELEASE = '7.1.3-gemini-a53-wifi-phase-a'
# Slot filled from the committed results/candidate.json after composition.
MANIFEST_SHA = None
START_TIMEOUT_S = 120
WMT.HERE = HERE
WMT.ROOT = ROOT
WMT.CAPTURE_DIR = ROOT / 'capture-1'
WMT.RELEASE = RELEASE
WMT.START_TRIGGER = '/sys/bus/platform/devices/10001340.consys/wmt_negotiate'
WMT.CAPTURE.HERE = HERE
WMT.CAPTURE.ROOT = ROOT
WMT.CAPTURE.CAPTURE = WMT.CAPTURE_DIR
WMT.CAPTURE.DEPLOYMENT = ROOT / 'session-1/deployment-summary.txt'
WMT.CAPTURE.RECEIPT = HERE / 'results/candidate.json'
WMT.CAPTURE.MANIFEST_SHA = MANIFEST_SHA
WMT.CAPTURE.RELEASE = RELEASE

COMMON = re.compile(rb'one-shot WMT common init: result=(-?\d+) completed=(\d+)/285 '
                    rb'bt-rail=([01]) wifi-rail=([01]) link=(\d+)/(\d+)/(\d+)/(\d+)$')
NEGOTIATION = re.compile(rb'one-shot WMT negotiation: result=(-?\d+) phase=(\d+) clocks-held=([01])$')
CALIBRATION = re.compile(rb'WMT common init calibration RX: [0-9a-f]+: ((?:[0-9a-f]{2} ?)+)$')
WLAN_READY = (
    b'one-shot WLAN private record prepare: status=0',
    b'one-shot WLAN regulatory configuration: status=0',
    b'one-shot WLAN TC4 reconciliation: snapshot=2 status=0 ',
)


CONTINUE = b'WMT common init complete; continuing to WLAN HIF'


def ordered(lines):
    """Each prerequisite exactly once, in protocol order."""
    patterns = [NEGOTIATION, COMMON, re.compile(re.escape(CONTINUE))] + [
        re.compile(re.escape(line)) for line in WLAN_READY]
    positions = []
    for pattern in patterns:
        found = [i for i, line in enumerate(lines) if pattern.search(line)]
        if len(found) != 1:
            return False
        positions.append(found[0])
    return positions == sorted(positions)


def classify(log):
    """Phase A kernel-log result; raw calibration bytes stay in the private log."""
    lines = log.splitlines()
    negotiation = [m for line in lines if (m := NEGOTIATION.search(line))]
    common = [m for line in lines if (m := COMMON.search(line))]
    calibration = [m for line in lines if (m := CALIBRATION.search(line))]
    status = calibration[0][1].split() if len(calibration) == 1 else []
    result = {
        'negotiation_passed': len(negotiation) == 1 and negotiation[0][1] == b'0',
        'common_init_lines': len(common),
        'common_init_result': int(common[0][1]) if len(common) == 1 else None,
        'common_init_completed': int(common[0][2]) if len(common) == 1 else None,
        'pa_rails_off_after': len(common) == 1 and common[0][3] == b'0' and common[0][4] == b'0',
        'calibration_reply_bytes': len(status),
        'calibration_status_vendor_expected': status == [b'02', b'14', b'02', b'00', b'00', b'01'],
        'continued_to_wlan': sum(CONTINUE in line for line in lines) == 1,
        'prerequisites_in_order': ordered(lines),
        'wlan_ready_lines': {line.decode(): sum(line in raw for raw in lines) == 1
                             for line in WLAN_READY},
        'wlan_firmware_stopped': any(b'one-shot WLAN firmware stopped (' in line
                                     for line in lines),
        'bt_h1_absent': not any(b'one-shot BT H1' in line for line in lines),
    }
    result['common_init_passed'] = (result['common_init_result'] == 0 and
                                     result['common_init_completed'] == 285 and
                                     result['pa_rails_off_after'])
    result['ready_for_scan'] = (result['negotiation_passed'] and result['common_init_passed'] and
                                result['continued_to_wlan'] and
                                result['prerequisites_in_order'] and
                                all(result['wlan_ready_lines'].values()) and
                                not result['wlan_firmware_stopped'] and result['bt_h1_absent'])
    return result


_record_attempt = WMT.record_attempt


def record_attempt(collector, command, name, script, timeout=30):
    # Negotiation, up to 60 s of common init and WLAN start run in this write.
    if name == 'firmware-start-once':
        timeout = START_TIMEOUT_S
    return _record_attempt(collector, command, name, script, timeout)


WMT.record_attempt = record_attempt


def prepare(candidate):
    WMT.require(MANIFEST_SHA is not None, 'Phase A receipt slot not filled')
    published = WMT.CAPTURE.RECEIPT.read_bytes()
    WMT.require(WMT.sha(published) == MANIFEST_SHA, 'published candidate changed')
    expected = json.loads(published)
    WMT.require(expected['kernel_release'] == RELEASE, 'candidate release changed')
    WMT.require(not candidate.is_symlink(), 'candidate path is a symlink')
    candidate = candidate.resolve(strict=True)
    WMT.require(candidate.is_dir() and
                candidate.name == 'candidate-' + expected['files']['boot.img']['sha256'] and
                json.loads((candidate / 'candidate.json').read_bytes()) == expected and
                {p.name for p in candidate.iterdir()} == set(expected['files']) | {'candidate.json'},
                'private candidate identity changed')
    for name, identity in expected['files'].items():
        path = candidate / name
        WMT.require(path.is_file() and not path.is_symlink() and
                    path.stat().st_size == identity['bytes'] and
                    WMT.sha(path.read_bytes()) == identity['sha256'],
                    'candidate member changed: ' + name)
    rows = [line.split('=', 1) for line in WMT.CAPTURE.DEPLOYMENT.read_text().splitlines()]
    WMT.require(all(len(row) == 2 for row in rows) and
                len({row[0] for row in rows}) == len(rows), 'deployment malformed')
    fields = dict(rows)
    WMT.require(fields.get('experiment') == 'mt6797-wifi-phase-a' and
                fields.get('candidate_manifest_sha256') == MANIFEST_SHA and
                fields.get('target_logical_name') == 'boot2' and
                fields.get('result') in ('write-synced-flushed-full-readback-verified',
                                         'skipped-already-matching') and
                fields.get('candidate_sha256') == expected['files']['boot2-padded.img']['sha256'] and
                fields.get('readback_sha256') == fields['candidate_sha256'] and
                fields.get('reboot') == 'no', 'deployment not admitted')
    return expected


WMT.prepare = prepare


def main():
    rc = WMT.main()
    log = WMT.CAPTURE_DIR / 'log-after-start/stdout.txt'
    if rc or not log.is_file():
        return rc or 1
    result = classify(log.read_bytes())
    path = WMT.CAPTURE_DIR / 'phase-a-result.json'
    with path.open('x') as stream:
        stream.write(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps(result, sort_keys=True))
    return 0 if result['ready_for_scan'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
