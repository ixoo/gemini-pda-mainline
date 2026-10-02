#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Keep wrapped, reset, malformed and unrelated bytes separate from receive proof."""
import importlib.util
from pathlib import Path


def main():
    source = Path(__file__).resolve().parents[1] / 'early-rx-result.py'
    spec = importlib.util.spec_from_file_location('early_rx_fixture', source)
    host = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(host)
    summary = b'one-shot passive WLAN early_rx summary: submitted=4 received=4 pending=0 atomic=0 rf_proven=0'
    def line(sample, role, value, sent, received, post=0):
        return ('one-shot passive WLAN early_rx sample: sample=%d role=%d value=%d sent_us=%d received_us=%d post_done=%d' %
                (sample, role, value, sent, received, post)).encode()
    rows = [line(0, 0, 255 << 24, 100000, 101000),
            line(0, 1, 254, 120000, 121000),
            line(1, 0, 1 << 24, 300000, 301000),
            line(1, 1, 1, 320000, 321000), summary]
    result = host.early_rx_result(rows)
    assert result['early_rx_samples_complete'] and result['early_rx_samples_before_done']
    assert result['early_rx_counter_nonzero'] and result['early_rx_counter_changed']
    assert result['early_rx_byte_change_mod256'] == {'probe_response_byte': 2, 'beacon_byte': 3}
    assert not result['early_rx_samples_atomic'] and not result['early_rx_receive_proven']
    zero = [line(0, 0, 0, 100000, 101000), line(0, 1, 0, 120000, 121000),
            line(1, 0, 0, 300000, 301000), line(1, 1, 0, 320000, 321000), summary]
    result = host.early_rx_result(zero)
    assert result['early_rx_samples_complete'] and not result['early_rx_counter_nonzero']
    assert not result['early_rx_counter_changed'] and not result['early_rx_receive_proven']
    # Other packed bytes cannot become beacon/probe receive evidence.
    unrelated = [line(0, 0, 0x00ffffff, 100000, 101000),
                 line(0, 1, 0xffffff00, 120000, 121000),
                 line(1, 0, 0x00010203, 300000, 301000),
                 line(1, 1, 0x01020300, 320000, 321000), summary]
    result = host.early_rx_result(unrelated)
    assert result['early_rx_samples_complete'] and not result['early_rx_counter_nonzero']
    assert not result['early_rx_counter_changed']
    late = rows.copy(); late[3] = line(1, 1, 40 << 8, 320000, 321000, 1)
    assert host.early_rx_result(late)['early_rx_samples_complete']
    assert not host.early_rx_result(late)['early_rx_samples_before_done']
    for bad in ([], rows[:-1], rows[1:], rows + [rows[0]],
                rows[:-1] + [summary.replace(b'pending=0', b'pending=1')],
                [line(0, 0, 5000000, 99999, 101000)] + rows[1:],
                [line(0, 0, 5000000, 100000, 200000)] + rows[1:],
                rows[:2] + [line(1, 0, 2**32, 300000, 301000)] + rows[3:],
                rows[:3] + [line(1, 0, 5000000, 320000, 321000), summary],
                rows[:3] + [line(1, 1, 40 << 8, 300500, 301500), summary],
                rows[:3] + [rows[3] + b' trailing', summary]):
        assert not host.early_rx_result(bad)['early_rx_samples_complete']
    print('early RX classification: PASS; wrap, zero, unrelated bytes and malformed limits retained')


if __name__ == '__main__':
    main()
