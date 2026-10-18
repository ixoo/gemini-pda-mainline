#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""GTK3-only host verdict: finite capability and full low-traffic window."""
import importlib.util
from pathlib import Path
import re

SPEC = importlib.util.spec_from_file_location('gtk_budget_frozen_verdict',
                                            Path(__file__).with_name('classify-ccmp.py'))
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)
# This module owns its base instance; historical/default classifiers keep 512/64.
BASE.RX_MAX, BASE.NATIVE_MAX, BASE.BYTES_MAX = 4096, 1024, 2 * 1024 * 1024
read_protocol = BASE.read_protocol
COUNTER = re.compile(rb'one-shot WLAN checked GTK counters: withheld_arp=(\d+) '
                     rb'queued_ptk=(\d+) queued_gtk=(\d+) delivered_arp=(\d+)$')
GTK = re.compile(rb'one-shot WLAN checked GTK RX: first_queued=1 ethernet_bytes=(\d+)$')
START = re.compile(rb'one-shot WLAN join data phase: budget_ms=(\d+) '
                   rb'teardown_margin_ms=(\d+) inside_grant=(\d+)$')
END = re.compile(rb'one-shot WLAN join data phase end: reason=([^ ]+) elapsed_ms=(\d+) '
                 rb'rx_unicast=\d+ rx_group=\d+ rx_dropped=\d+ tx_queued=\d+ '
                 rb'tx_done=\d+ tx_failed=\d+ tx_credits=\d+$')


def classify(kmsg, ssh_receipt, verified_boot, protocol=None):
    result = BASE.classify(kmsg, ssh_receipt, verified_boot, protocol)
    finite = result['provisional_ccmp_compatibility_pass']
    lines = kmsg.splitlines()
    counters = [m for line in lines if (m := COUNTER.search(line))]
    gtk = [m for line in lines if (m := GTK.search(line))]
    starts = [m for line in lines if (m := START.search(line))]
    ends = [m for line in lines if (m := END.search(line))]
    prefixes = sum(b'one-shot WLAN checked GTK counters:' in line for line in lines)
    gtk_prefixes = sum(b'one-shot WLAN checked GTK RX:' in line for line in lines)
    start_prefixes = sum(b'one-shot WLAN join data phase:' in line for line in lines)
    end_prefixes = sum(b'one-shot WLAN join data phase end:' in line for line in lines)
    values = [int(x) for x in counters[0].groups()] if len(counters) == 1 else None
    counts_ok = bool(values is not None and prefixes == 1 and gtk_prefixes == 1 and len(gtk) == 1 and
                     14 < int(gtk[0][1]) <= BASE.HIF_RX_MAX_PACKET and
                     values[0] <= 4096 and values[1] <= 1024 and
                     1 <= values[2] <= 1024 and values[3] <= values[2] and
                     values[1] + values[2] == result['ccmp_ethernet_queued'])
    capability = bool(finite and counts_ok)
    start = tuple(map(int, starts[0].groups())) if len(starts) == 1 else None
    elapsed = int(ends[0][2]) if len(ends) == 1 else None
    reason = ends[0][1].decode('ascii') if len(ends) == 1 else None
    # Do not pass a quota-ended lifetime whose credit drain crosses 60 seconds.
    diag = [m for line in lines if (m := BASE._DIAG.search(line))]
    capacity_clear = bool(diag and result['ccmp_ethernet_queued'] is not None and
                          result['ccmp_ethernet_queued'] < 1024 and
                          int(diag[-1][3]) < 4096 and
                          int(diag[-1][5]) + 2352 <= 2 * 1024 * 1024)
    duration = bool(start_prefixes == end_prefixes == 1 and
                    start == (60000, 5000, 1) and elapsed is not None and
                    elapsed >= 60000 and reason == 'budget' and capacity_clear)
    result.update(finite_capability_pass=capability, duration_pass=duration,
                  gtk_counters_consistent=counts_ok,
                  gtk_counters=({'withheld_arp': values[0], 'queued_ptk': values[1],
                                 'queued_gtk': values[2], 'delivered_arp': values[3]}
                                if values is not None else None),
                  gtk_arp_handoff_observed=bool(counts_ok and values[3]),
                  actual_window_ms=elapsed, planned_window_ms=60000,
                  window_end_reason=reason, capacity_clear=capacity_clear,
                  sustained_ssh_proven=False,
                  arp_counter_scope='driver-to-core handoff; no stack acknowledgement or peer attribution',
                  low_traffic_60s_pass=bool(capability and duration))
    result['provisional_ccmp_compatibility_pass'] = result['low_traffic_60s_pass']
    return result
