#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Classify bounded mode and byte samples without claiming RF reception or packet counts."""
import re


MODE_SAMPLE = re.compile(rb'one-shot passive WLAN mode_sample sample: sample=(\d+) role=(\d+) value=(\d+) sent_us=(\d+) received_us=(\d+) post_done=([01])$')
MODE_SAMPLE_SUMMARY = re.compile(rb'one-shot passive WLAN mode_sample summary: submitted=(\d+) received=(\d+) pending=([01]) atomic=0 rf_proven=0$')


def mode_sample_result(lines):
    result = {'mode_sample_samples_complete': False,
              'mode_sample_samples_before_done': False,
              'mode_sample_counter_nonzero': False,
              'mode_sample_all_five': False, 'mode_sample_any_nonfive': False,
              'mode_sample_mode_changed': False,
              'mode_sample_counter_changed': False,
              'mode_sample_samples_atomic': False, 'mode_sample_receive_proven': False}
    matches = [m for line in lines if (m := MODE_SAMPLE.search(line))]
    summaries = [m for line in lines if (m := MODE_SAMPLE_SUMMARY.search(line))]
    if (len(matches) != 4 or len(summaries) != 1 or
            sum(b'one-shot passive WLAN mode_sample sample:' in line for line in lines) != 4 or
            sum(b'one-shot passive WLAN mode_sample summary:' in line for line in lines) != 1 or
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
        mode, packed = samples[index]['value'], samples[index + 1]['value']
        pairs.append({'receive_mode': mode,
                      'dispatcher_entry_byte': packed & 255,
                      'probe_response_byte': (packed >> 24) & 255})
    changes = {key: (pairs[1][key] - pairs[0][key]) & 255 for key in ('dispatcher_entry_byte', 'probe_response_byte')}
    result.update(mode_sample_samples_complete=True, mode_sample_samples=samples,
                  mode_sample_pairs=pairs,
                  mode_sample_all_five=all(p['receive_mode'] == 5 for p in pairs),
                  mode_sample_any_nonfive=any(p['receive_mode'] != 5 for p in pairs),
                  mode_sample_mode_changed=pairs[0]['receive_mode'] != pairs[1]['receive_mode'],
                  mode_sample_samples_before_done=not any(s['post_done'] for s in samples),
                  mode_sample_counter_nonzero=any(p[k] for p in pairs for k in changes),
                  mode_sample_counter_changed=any(changes.values()),
                  mode_sample_byte_change_mod256=changes)
    return result
