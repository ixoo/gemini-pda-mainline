#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Inspect focused capture framing and input/VT evidence; never certify a session."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import runpy

HERE = Path(__file__).resolve().parent
V1 = runpy.run_path(str(HERE/'classify.py'))
require, Refusal = V1['require'], V1['Refusal']
EXPECTED = [([[2, 1], [2, 0]], '31'),
            (V1['PROTOCOL']['steps'][0]['key_edges'], V1['PROTOCOL']['steps'][0]['vt_hex'])]


def analyze(data, *, coverage=False):
    duration = 10000 if coverage else 15000
    expected = [(s["key_edges"], s["vt_hex"]) for s in V1["PROTOCOL"]["steps"]] if coverage else EXPECTED
    byte_limit = 1048576 if coverage else 98304
    result = {'hardware_claim': False, 'session_receipt_verified': False,
              'capture_sha256': hashlib.sha256(data).hexdigest()}
    try:
        require(len(data) <= byte_limit, 'capture-byte-limit')
        require(data.endswith(b'\n'), 'unterminated-capture')
        lines = iter(data.decode('ascii').splitlines())

        def exact(wanted):
            require(next(lines, None) == wanted, 'incomplete-or-unexpected-frame')

        exact('keyboard-coverage version=1' if coverage else 'keyboard-diagnostic version=1')
        repeat = re.fullmatch(r'repeat delay_ms=([0-9]+) period_ms=([0-9]+) planned_events=([0-9]+) limit=1024',
                              next(lines, ''))
        require(repeat is not None, 'missing-repeat-settings')
        delay, period, planned = map(int, repeat.groups())
        require(0 <= delay <= 60000 and 0 < period <= 60000, 'repeat-settings')
        require(planned == 64 + 2 * ((duration + period - 1) // period) and planned <= 1024,
                'repeat-capacity')
        identity = re.fullmatch(r'device event=(event[0-9]+) major=13 minor=([0-9]+) name=keyboard-matrix',
                                next(lines, ''))
        require(identity is not None, 'missing-input-identity')
        result['reported_input'] = {'event': identity[1], 'minor': int(identity[2])}
        idle = re.fullmatch(r'window elapsed_ms=([0-9]+) events=0 bytes=0 held=0', next(lines, ''))
        require(idle is not None and int(idle[1]) >= 2000, 'idle-preflight')
        exact('preflight state=pass vt=1 unicode=1 held=0 functions=exact')
        cases = []
        for index, (expected_edges, expected_vt) in enumerate(expected):
            exact(f'step begin index={index}')
            edges, scans, vt = [], [], bytearray()
            held = set()
            pending_scan, frame, last_ms, count, repeats = None, None, -1, 0, 0
            while True:
                line = next(lines, None)
                require(line is not None, 'truncated-step')
                require(not line.startswith(('overflow ', 'incomplete ')), 'collection-incomplete')
                end = re.fullmatch(r'window elapsed_ms=([0-9]+) events=([0-9]+) bytes=([0-9]+) held=0', line)
                if end:
                    require(int(end[1]) >= duration and int(end[2]) == count and int(end[3]) == len(vt),
                            'window-time-or-counters')
                    require(pending_scan is None and frame is None and not held, 'unfinished-frame-or-held-key')
                    break
                event = re.fullmatch(r'event ([0-9]+) ([0-9]+) ([0-9]+) (-?[0-9]+)', line)
                tty = re.fullmatch(r'tty hex=([0-9a-f]+)', line)
                if event:
                    elapsed, kind, code, value = map(int, event.groups())
                    count += 1
                    require(count <= 1024 and last_ms <= elapsed < duration, 'event-budget-or-time')
                    last_ms = elapsed
                    if kind == 4:
                        require(code == 4 and 0 <= value <= 63 and pending_scan is None and frame != 'repeat',
                                'malformed-scan')
                        pending_scan, frame = value, 'edge'
                    elif kind == 1:
                        require(code in V1['SCANS'], 'unexpected-key')
                        if value == 2:
                            require(code in held and pending_scan is None and frame is None,
                                    'repeat-without-held-key-or-mixed-frame')
                            repeats += 1
                            frame = 'repeat'
                        else:
                            require(value in (0, 1) and pending_scan is not None and frame == 'edge',
                                    'key-without-scan-or-malformed-value')
                            require((code in held) == (value == 0), 'duplicate-press-or-unmatched-release')
                            held.add(code) if value else held.remove(code)
                            edges.append([code, value])
                            scans.append(pending_scan)
                            pending_scan = None
                    elif kind == 0:
                        require(code == 0 and pending_scan is None and frame is not None,
                                'dropped-or-empty-sync')
                        require(value == (1 if frame == 'repeat' else 0), 'unexpected-sync-value')
                        frame = None
                    else:
                        raise Refusal('unexpected-event-type')
                elif tty:
                    require(len(tty[1]) % 2 == 0, 'malformed-tty-hex')
                    vt.extend(bytes.fromhex(tty[1]))
                    require(len(vt) <= 128, 'tty-byte-limit')
                else:
                    raise Refusal('unexpected-record')
            exact(f'step end index={index}')
            input_match = edges == expected_edges and scans == [V1['SCANS'][code] for code, _ in expected_edges]
            cases.append({'index': index, 'input': 'match' if input_match else 'mismatch',
                          'vt': 'match' if vt.hex() == expected_vt else 'mismatch',
                          'physical_edges': len(edges), 'repeat_events': repeats})
        exact(f'complete steps={len(expected)} restored=1')
        require(next(lines, None) is None, 'trailing-record')
        result.update(outcome='observations-complete', cases=cases)
    except (Refusal, UnicodeError, ValueError) as exc:
        result.update(outcome='inconclusive', reason=str(exc))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--coverage', action='store_true')
    args = parser.parse_args()
    require(args.capture.is_file() and not args.capture.is_symlink(), 'capture-not-regular')
    with args.capture.open('rb') as stream:
        data = stream.read(1048577 if args.coverage else 98305)
    result = analyze(data, coverage=args.coverage)
    print(json.dumps(result, indent=2))
    return 0 if result['outcome'] == 'observations-complete' else 2


if __name__ == '__main__':
    raise SystemExit(main())
