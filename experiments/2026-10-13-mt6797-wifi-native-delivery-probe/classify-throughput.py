#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Measurement verdict separate from the consumed ten-minute stream verdict."""
import os
from pathlib import Path
import re
import runpy

base = runpy.run_path(str(Path(os.environ['TP_SOURCE_ROOT'])/'experiments/2026-10-13-mt6797-wifi-native-delivery-probe/classify-ccmp-connected-p2.py'))
read_protocol = base['read_protocol']


def classify(kmsg, receipt, verified_boot, protocol=None):
    value = base['classify'](kmsg,receipt,verified_boot,protocol)
    measurement = (receipt or {}).get('throughput_measurement',{})
    for label, direction in measurement.get('directions',{}).items():
        start, end = direction.get('device_start_ns'), direction.get('device_end_ns')
        if start is None or end is None:
            continue
        records = []
        for line in kmsg.splitlines():
            m = re.match(rb'^\d+,\d+,(\d+),[^;]*;(.*)',line)
            if m and start <= int(m[1])*1000 < end:
                records.append(m[2])
        done = [m for line in records if (m:=re.search(rb'one-shot WLAN join TX done: pid=\d+ status=(\d+)',line))]
        direction['device_clock_resolution_ns'] = 10000000
        direction['completion_interval'] = 'start-inclusive, end-exclusive; boundary uncertainty one device clock tick'
        direction['device_tx_status_completions'] = len(done)
        direction['device_tx_status_nonzero'] = sum(int(m[1]) != 0 for m in done)
    directions = measurement.get('directions',{})
    timing = bool(len(directions)==2 and all(59e9<=d.get('elapsed_ns',0)<=63e9 for d in directions.values()))
    passed = bool(verified_boot and receipt and receipt.get('all_pass') and timing and
                  value.get('healthy_cleanup') and value.get('counts_ok') and
                  value.get('sequence_ok') and value.get('gtk_counters_consistent') and not value.get('fault'))
    value.update(throughput_measurement=measurement,throughput_baseline_pass=passed,
                 provisional_ccmp_compatibility_pass=passed,ten_minute_ssh_proven=False,
                 same_boot_reconnect_proven=False,maintained_wifi_support=False,
                 measurement_censored=not timing)
    return value
