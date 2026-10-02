#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Classify non-atomic receive pool samples; never infer RF packets."""
import re

POOL_SAMPLE = re.compile(rb'one-shot passive WLAN pool_sample sample: sample=(\d+) role=(\d+) value=(\d+) sent_us=(\d+) received_us=(\d+) post_done=([01])$')
POOL_SAMPLE_SUMMARY = re.compile(rb'one-shot passive WLAN pool_sample summary: submitted=(\d+) received=(\d+) pending=([01]) atomic=0 rf_proven=0$')


def pool_sample_result(lines):
    result = {'pool_sample_samples_complete': False,
              'pool_sample_samples_before_done': False,
              'pool_sample_samples_atomic': False,
              'pool_sample_receive_proven': False}
    matches = [m for line in lines if (m := POOL_SAMPLE.search(line))]
    summaries = [m for line in lines if (m := POOL_SAMPLE_SUMMARY.search(line))]
    if (len(matches) != 4 or len(summaries) != 1 or
            sum(b'one-shot passive WLAN pool_sample sample:' in line for line in lines) != 4 or
            sum(b'one-shot passive WLAN pool_sample summary:' in line for line in lines) != 1 or
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
        head, count = samples[index]['value'], samples[index + 1]['value']
        sentinel = head == 0xf0073680
        member = (0xf007368c <= head <= 0xf0074134 and
                  (head - 0xf007368c) % 88 == 0)
        state = 'unexpected'
        if count <= 32:
            if sentinel and count == 0:
                state = 'empty_at_separate_reads'
            elif member and count > 0:
                state = 'available_at_separate_reads'
            elif sentinel or member:
                state = 'non_atomic_disagreement'
        pairs.append({'head': head, 'free_count': count,
                      'head_is_empty_sentinel': sentinel,
                      'head_is_pool_member': member, 'state': state})
    result.update(pool_sample_samples_complete=True, pool_sample_samples=samples,
                  pool_sample_pairs=pairs,
                  pool_sample_samples_before_done=not any(s['post_done'] for s in samples),
                  pool_sample_values_changed=any(samples[i]['value'] != samples[i+2]['value'] for i in (0, 1)))
    return result
