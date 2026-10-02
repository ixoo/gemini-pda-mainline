#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check pool boundaries and observation validity independently of RF."""
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location('pool_fixture', Path(__file__).resolve().parents[1] / 'pool-result.py')
host = importlib.util.module_from_spec(spec)
spec.loader.exec_module(host)
summary = b'one-shot passive WLAN pool_sample summary: submitted=4 received=4 pending=0 atomic=0 rf_proven=0'
def line(sample, role, value, sent, received, post=0):
    return ('one-shot passive WLAN pool_sample sample: sample=%d role=%d value=%d sent_us=%d received_us=%d post_done=%d' % (sample, role, value, sent, received, post)).encode()
def rows(head=0xf007368c, count=32):
    return [line(0, 0, head, 100000, 101000), line(0, 1, count, 120000, 121000), line(1, 0, head, 300000, 301000), line(1, 1, count, 320000, 321000), summary]
for head, count, state in ((0xf0073680, 0, 'empty_at_separate_reads'), (0xf0073680, 1, 'non_atomic_disagreement'), (0xf007368c, 0, 'non_atomic_disagreement'), (0, 0, 'unexpected'), (0xf007368d, 2, 'unexpected'), (0xf0074135, 2, 'unexpected'), (0xf007368c, 33, 'unexpected'), (0xffffffff, 0xffffffff, 'unexpected')):
    result = host.pool_sample_result(rows(head, count))
    assert result['pool_sample_samples_complete'] and result['pool_sample_samples_before_done']
    assert all(p['state'] == state for p in result['pool_sample_pairs'])
    assert not result['pool_sample_receive_proven'] and not result['pool_sample_samples_atomic']
for n in range(32):
    assert host.pool_sample_result(rows(0xf007368c + n * 88, n+1))['pool_sample_pairs'][0]['state'] == 'available_at_separate_reads'
base=rows()
changed=base.copy();changed[2]=line(1,0,0xf00736e4,300000,301000)
assert host.pool_sample_result(changed)['pool_sample_values_changed']
late=base.copy();late[3]=line(1,1,32,320000,321000,1)
assert host.pool_sample_result(late)['pool_sample_samples_complete']
assert not host.pool_sample_result(late)['pool_sample_samples_before_done']
for bad in ([], base[:-1], base[1:], base + [base[0]], base + [summary], base[:-1]+[summary.replace(b'pending=0',b'pending=1')], [line(0,0,0,99999,101000)]+base[1:], [line(0,0,0,100000,200000)]+base[1:], base[:2]+[line(1,0,2**32,300000,301000)]+base[3:], base[:3]+[line(1,0,0,320000,321000),summary], base[:3]+[line(1,1,0,300500,301500),summary], base[:3]+[base[3]+b' trailing',summary]):
    result=host.pool_sample_result(bad)
    assert not result['pool_sample_samples_complete'] and not result['pool_sample_receive_proven']
print('pool classification: PASS; all object boundaries, non-atomic and malformed limits')
