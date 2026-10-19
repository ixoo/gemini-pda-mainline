#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""I50: grade the 50-second window, idle measurement and cleanup separately."""
import importlib.util
from pathlib import Path
import re

SPEC = importlib.util.spec_from_file_location('i50_release', Path(__file__).with_name('classify-ccmp-channel-release.py'))
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)


def periodic_probes(ping):
    lines = ping.splitlines()
    matches = [m for line in lines if (m := BASE.PROBE.fullmatch(line))]
    if len(matches) != 4 or sum(line.startswith(b'periodic_ping ') for line in lines) != 4 or any(
            line.startswith(b'periodic_refused ') for line in lines):
        return []
    probes = []
    for ordinal, m in enumerate(matches, 1):
        n, scheduled, start, end = map(int, m.groups()[:4])
        if n != ordinal or scheduled != ordinal * 10**10 or not scheduled <= start <= end < 50 * 10**9:
            return []
        probes.append({'ordinal': n, 'scheduled_offset_ns': scheduled, 'start_offset_ns': start,
                       'completion_offset_ns': end, 'replies': 1, 'exit': 0, 'rtt_ms': float(m[5])})
    return probes


BASE.periodic_probes = periodic_probes
read_protocol = BASE.read_protocol
RECORD = re.compile(rb'^\d+,\d+,(\d+),[^;]*;(.*)$')
DEAUTH = re.compile(rb'one-shot WLAN join TX: subtype=12 pid=(\d+) pages=1$')


def classify(kmsg, ssh_receipt, verified_boot, protocol=None):
    result = BASE.classify(kmsg, ssh_receipt, verified_boot, protocol)
    lines = kmsg.splitlines()
    starts = [m for line in lines if (m := BASE.BASE.START.search(line))]
    ends = [m for line in lines if (m := BASE.BASE.END.search(line))]
    duration = bool(len(starts) == len(ends) == 1 and
                    sum(b'one-shot WLAN join data phase:' in line for line in lines) == 1 and
                    sum(b'one-shot WLAN join data phase end:' in line for line in lines) == 1 and
                    tuple(map(int, starts[0].groups())) == (50000, 5000, 1) and
                    ends[0][1] == b'budget' and int(ends[0][2]) >= 50000 and result['capacity_clear'])
    probes = (protocol or {}).get('periodic_probes') or []
    tx = [m for line in lines if (m := BASE.TX.search(line))]
    tx_ok = bool(len(tx) == sum(b'one-shot WLAN TX completion timing:' in line for line in lines) and
                 len({int(m[1]) for m in tx}) == len(tx) and
                 all(1 <= int(m[1]) <= 127 and int(m[2]) <= 255 and int(m[3]) <= 3 for m in tx))
    traffic = bool(result['connected_channel_release_credited'] and tx_ok and len(probes) == 4 and
                   all(p['start_offset_ns'] > 9_000_000_000 for p in probes) and
                   result['post_release_data_completion_offsets_ns'])
    records = [(int(m[1]), m[2]) for line in lines if (m := RECORD.fullmatch(line))]
    deauth = [(stamp, m) for stamp, text in records if (m := DEAUTH.search(text))]
    completed = [(stamp, m) for stamp, text in records if (m := BASE.TX.search(text)) and
                 int(m[2]) == 0 and int(m[3]) == 1]
    gap = None
    last_offset = None
    valid_idle = False
    if len(deauth) == 1:
        prior = [(stamp, m) for stamp, m in completed if stamp < deauth[0][0]]
        if prior:
            stamp, last = prior[-1]
            gap = deauth[0][0] - stamp
            last_offset = int(last[5])
            valid_idle = 9_000_000 <= gap <= 11_000_000 and 40_000_000_000 <= last_offset <= 41_000_000_000
    # Missing sequence/timestamp/shape or unplanned late TX cannot establish the
    # idle comparison. It remains separate from a successful network/cleanup.
    clocks_ok = len(records) == sum(bool(re.match(rb'^\d+,\d+,', line)) for line in lines) and all(
        a[0] <= b[0] for a, b in zip(records, records[1:]))
    measured = bool(result['authenticated'] and duration and traffic and valid_idle and clocks_ok)
    ack = bool(result['healthy_cleanup'] and sum(b'cleanup: stage=3 credits=returned slots=retired deauth=1' in line for line in lines) == 1)
    result.update(planned_window_ms=50000, duration_pass=duration,
                  full_60s_budget_pass_claimed=False, periodic_after_release_pass=traffic,
                  connected_data_after_release_pass=False,
                  low_traffic_60s_pass=False, low_traffic_50s_pass=bool(duration and traffic and result['finite_capability_pass']),
                  idle_tail_comparison_measured=measured, deauth_acked=ack,
                  idle_tail={'valid': valid_idle, 'last_successful_data_pm_offset_ns': last_offset,
                             'completion_log_to_deauth_submission_us': gap,
                             'required_idle_us': [9_000_000, 11_000_000],
                             'required_last_data_pm_offset_ns': [40_000_000_000, 41_000_000_000],
                             'scope': 'same-domain kernel log timestamps; no packet attribution or mechanism claim'},
                  provisional_ccmp_compatibility_pass=bool(measured and result['healthy_cleanup']))
    return result
