#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Classify bounded byte samples without claiming RF reception or packet counts."""
import re


EARLY_RX = re.compile(rb'one-shot passive WLAN early_rx sample: sample=(\d+) role=(\d+) value=(\d+) sent_us=(\d+) received_us=(\d+) post_done=([01])$')
EARLY_RX_SUMMARY = re.compile(rb'one-shot passive WLAN early_rx summary: submitted=(\d+) received=(\d+) pending=([01]) atomic=0 rf_proven=0$')


def early_rx_result(lines):
    result = {'early_rx_samples_complete': False,
              'early_rx_samples_before_done': False,
              'early_rx_counter_nonzero': False,
              'early_rx_counter_changed': False,
              'early_rx_samples_atomic': False, 'early_rx_receive_proven': False}
    matches = [m for line in lines if (m := EARLY_RX.search(line))]
    summaries = [m for line in lines if (m := EARLY_RX_SUMMARY.search(line))]
    if (len(matches) != 4 or len(summaries) != 1 or
            sum(b'one-shot passive WLAN early_rx sample:' in line for line in lines) != 4 or
            sum(b'one-shot passive WLAN early_rx summary:' in line for line in lines) != 1 or
            tuple(int(v) for v in summaries[0].groups()) != (4, 4, 0)):
        return result
    samples = []
    prior_received = 0
    for index, match in enumerate(matches):
        sample, role, value, sent, received, post_done = (int(v) for v in match.groups())
        if (sample != index // 2 or role != index % 2 or value > 0xffffffff or
                sent < (100000 if sample == 0 else 300000) or
                sent < prior_received or not sent <= received < sent + 100000 or
                received >= 5000000):
            return result
        samples.append({'sample': sample, 'role': role, 'value': value,
                        'sent_us': sent, 'received_us': received,
                        'post_done': bool(post_done)})
        prior_received = received
    pairs = []
    for index in (0, 2):
        probe, beacon = samples[index]['value'], samples[index + 1]['value']
        pairs.append({'probe_response_byte': (probe >> 24) & 255,
                      'beacon_byte': beacon & 255})
    changes = {key: (pairs[1][key] - pairs[0][key]) & 255 for key in pairs[0]}
    result.update(early_rx_samples_complete=True, early_rx_samples=samples,
                  early_rx_byte_pairs=pairs,
                  early_rx_samples_before_done=not any(s['post_done'] for s in samples),
                  early_rx_counter_nonzero=any(v for p in pairs for v in p.values()),
                  early_rx_counter_changed=pairs[0] != pairs[1],
                  early_rx_byte_change_mod256=changes)
    return result
