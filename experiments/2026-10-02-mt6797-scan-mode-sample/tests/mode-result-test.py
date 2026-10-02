#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise mode decisions independently of RF and wrapped byte statistics."""
import importlib.util
from pathlib import Path

source = Path(__file__).resolve().parents[1] / 'mode-result.py'
spec = importlib.util.spec_from_file_location('mode_fixture', source)
host = importlib.util.module_from_spec(spec)
spec.loader.exec_module(host)
summary = b'one-shot passive WLAN mode_sample summary: submitted=4 received=4 pending=0 atomic=0 rf_proven=0'
def line(sample, role, value, sent, received, post=0):
    return ('one-shot passive WLAN mode_sample sample: sample=%d role=%d value=%d sent_us=%d received_us=%d post_done=%d' %
            (sample, role, value, sent, received, post)).encode()
def rows(mode0=5, mode1=5, packed0=0, packed1=0):
    return [line(0, 0, mode0, 100000, 101000), line(0, 1, packed0, 120000, 121000),
            line(1, 0, mode1, 300000, 301000), line(1, 1, packed1, 320000, 321000), summary]
for mode in (0, 1, 2, 3, 4, 5, 6, 0xffffffff):
    result = host.mode_sample_result(rows(mode, mode))
    assert result['mode_sample_samples_complete'] and result['mode_sample_samples_before_done']
    assert result['mode_sample_all_five'] == (mode == 5)
    assert result['mode_sample_any_nonfive'] == (mode != 5)
    assert not result['mode_sample_mode_changed'] and not result['mode_sample_counter_nonzero']
    assert not result['mode_sample_receive_proven'] and not result['mode_sample_samples_atomic']
result = host.mode_sample_result(rows(4, 5))
assert result['mode_sample_mode_changed'] and result['mode_sample_any_nonfive']
assert not result['mode_sample_all_five'] and not result['mode_sample_counter_changed']
result = host.mode_sample_result(rows(packed0=0xff0000fe, packed1=0x01000001))
assert result['mode_sample_byte_change_mod256'] == {'dispatcher_entry_byte': 3, 'probe_response_byte': 2}
assert result['mode_sample_counter_nonzero'] and result['mode_sample_counter_changed']
assert not result['mode_sample_receive_proven']
result = host.mode_sample_result(rows(packed0=0x00ffff00, packed1=0x00010200))
assert not result['mode_sample_counter_nonzero'] and not result['mode_sample_counter_changed']
base = rows()
late = base.copy(); late[3] = line(1, 1, 0, 320000, 321000, 1)
assert host.mode_sample_result(late)['mode_sample_samples_complete']
assert not host.mode_sample_result(late)['mode_sample_samples_before_done']
for bad in ([], base[:-1], base[1:], base + [base[0]], base + [summary],
            base[:-1] + [summary.replace(b'pending=0', b'pending=1')],
            [line(0, 0, 5, 99999, 101000)] + base[1:],
            [line(0, 0, 5, 100000, 200000)] + base[1:],
            base[:2] + [line(1, 0, 2**32, 300000, 301000)] + base[3:],
            base[:3] + [line(1, 0, 0, 320000, 321000), summary],
            base[:3] + [line(1, 1, 0, 300500, 301500), summary],
            base[:3] + [base[3] + b' trailing', summary]):
    result = host.mode_sample_result(bad)
    assert not result['mode_sample_samples_complete']
    assert not result['mode_sample_all_five'] and not result['mode_sample_receive_proven']
print('mode classification: PASS; predicate, transition, wrap and malformed limits retained')
