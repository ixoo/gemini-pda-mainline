#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bounded connected-data verdict; keep GTK capability/duration independent."""
import importlib.util
from pathlib import Path
import re

SPEC = importlib.util.spec_from_file_location('channel_release_budget',
                                            Path(__file__).with_name('classify-ccmp-gtk-budget.py'))
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)
SUBMIT = re.compile(rb'one-shot WLAN connected channel release: credited=0 sequence=(\d+) '
                    rb'status=(-?\d+) observed_ns=(\d+) pm_offset_ns=(\d+) debt=(\d+)$')
CREDIT = re.compile(rb'one-shot WLAN connected channel release: credited=1 sequence=(\d+) '
                    rb'observed_ns=(\d+) pm_offset_ns=(\d+) debt=0$')
CLOCK = re.compile(rb'one-shot WLAN PM credit clock: ns=(\d+)$')
GRANT = re.compile(rb'one-shot WLAN join grant: channel=40 interval_ms=(\d+)$')
TX = re.compile(rb'one-shot WLAN TX completion timing: pid=(\d+) status=(\d+) class=(\d+) '
                rb'observed_ns=(\d+) pm_offset_ns=(\d+)$')
PROBE = re.compile(rb'periodic_ping ordinal=(\d+) scheduled_offset_ns=(\d+) attempted=1 '
                   rb'start_offset_ns=(\d+) completion_offset_ns=(\d+) exit=0 '
                   rb'statistics_known=1 transmitted=1 replies=1 rtt_known=1 '
                   rb'rtt_ms=([0-9]+(?:\.[0-9]+)?) clock_resolution_ns=10000000$')


def periodic_probes(ping):
    lines = ping.splitlines()
    probes = [m for line in lines if (m := PROBE.fullmatch(line))]
    if len(probes) != 5 or sum(line.startswith(b'periodic_ping ') for line in lines) != 5 or \
            any(line.startswith(b'periodic_refused ') for line in lines):
        return []
    result = []
    for ordinal, match in enumerate(probes, 1):
        n, scheduled, start, end = map(int, match.groups()[:4])
        if n != ordinal or scheduled != ordinal * 10**10 or not scheduled <= start <= end < 60 * 10**9:
            return []
        result.append({'ordinal': n, 'scheduled_offset_ns': scheduled,
                       'start_offset_ns': start, 'completion_offset_ns': end,
                       'replies': 1, 'exit': 0, 'rtt_ms': float(match[5])})
    return result


def read_protocol(root, boot):
    result = BASE.read_protocol(root, boot)
    result['periodic_probes'] = []
    if not result.get('cycle_export_complete'):
        return result
    try:
        exported = (Path(root) / 'cycles-evidence.raw').read_bytes()
        pos = len(('__CYCLES_BEGIN__\nboot=' + boot + '\n').encode())
        # The inherited parser already validated every c1 frame/order/length.
        for name in BASE.BASE.C2['CYCLE_FILES']:
            header = re.match(rb'__FILE__ path=\S+ bytes=(\d+)\n', exported[pos:])
            if header is None:
                return result
            pos += header.end()
            size = int(header[1])
            if name == 'ping.log':
                result['periodic_probes'] = periodic_probes(exported[pos:pos + size])
            pos += size + 9
    except (OSError, ValueError, TypeError):
        result['periodic_probes'] = []
    return result


def classify(kmsg, ssh_receipt, verified_boot, protocol=None):
    result = BASE.classify(kmsg, ssh_receipt, verified_boot, protocol)
    lines = kmsg.splitlines()
    submits = [m for line in lines if (m := SUBMIT.search(line))]
    credits = [m for line in lines if (m := CREDIT.search(line))]
    clocks = [m for line in lines if (m := CLOCK.search(line))]
    grants = [m for line in lines if (m := GRANT.search(line))]
    tx = [m for line in lines if (m := TX.search(line))]
    release_ok = False
    after = []
    if len(submits) == len(credits) == len(clocks) == len(grants) == 1 and \
            sum(b'one-shot WLAN connected channel release:' in line for line in lines) == 2 and \
            sum(b'one-shot WLAN PM credit clock:' in line for line in lines) == 1 and \
            sum(b'one-shot WLAN join grant:' in line for line in lines) == 1:
        seq, status, now, offset, debt = map(int, submits[0].groups())
        cseq, cnow, coffset = map(int, credits[0].groups())
        clock = int(clocks[0][1])
        release_ok = (clock > 0 and 1 <= seq == cseq <= 253 and status == 0 and debt == 1 and
                      int(grants[0][1]) == 9000 and now - offset == cnow - coffset == clock and
                      0 <= cnow - now <= 100_000_000 and coffset < 10_000_000_000 and
                      lines.index(submits[0].string) < lines.index(credits[0].string))
        after = [int(m[5]) for m in tx if int(m[2]) == 0 and int(m[3]) == 1 and
                 1 <= int(m[1]) <= 127 and int(m[4]) - int(m[5]) == clock and
                 int(m[5]) > max(coffset, 9_000_000_000)]
    probes = (protocol or {}).get('periodic_probes') or []
    tx_ok = bool(len(tx) == sum(b'one-shot WLAN TX completion timing:' in line for line in lines) and
                 len({int(m[1]) for m in tx}) == len(tx) and
                 all(1 <= int(m[1]) <= 127 and int(m[2]) <= 255 and int(m[3]) <= 3
                     for m in tx))
    traffic_ok = bool(release_ok and tx_ok and len(probes) == 5 and
                      all(p['start_offset_ns'] > coffset for p in probes) and
                      len(after) >= 5 and max(after) >= 50_000_000_000)
    # PM credit follows the grant; PM+10 s is therefore beyond a 9 s grant.
    # A completion timestamp alone does not identify an individual ICMP frame.
    previous = result['low_traffic_60s_pass']
    result.update(inherited_low_traffic_60s_pass=previous,
                  connected_channel_release_credited=release_ok,
                  periodic_after_release_pass=traffic_ok,
                  connected_data_after_release_pass=bool(previous and traffic_ok),
                  periodic_probes=probes,
                  post_release_data_completion_offsets_ns=after,
                  low_traffic_60s_pass=bool(previous and traffic_ok),
                  provisional_ccmp_compatibility_pass=bool(previous and traffic_ok))
    return result
