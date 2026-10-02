#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Keep incomplete/non-atomic software samples separate from tuning proof."""
import importlib.util
import os
from pathlib import Path
import tempfile


def main():
    with tempfile.TemporaryDirectory(prefix='mt6797-tuning-result-') as root:
        prior = os.environ.get('GEMINI_PRIVATE_REPO')
        os.environ['GEMINI_PRIVATE_REPO'] = root
        try:
            source = Path(__file__).resolve().parents[1] / 'passive-host.py'
            spec = importlib.util.spec_from_file_location('tuning_fixture', source)
            host = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(host)
        finally:
            if prior is None:
                del os.environ['GEMINI_PRIVATE_REPO']
            else:
                os.environ['GEMINI_PRIVATE_REPO'] = prior
        summary = b'one-shot passive WLAN tuning summary: submitted=4 received=4 pending=0 atomic=0 rf_proven=0'
        def line(sample, role, value, sent, received, post=0):
            return ('one-shot passive WLAN tuning sample: sample=%d role=%d value=%d sent_us=%d received_us=%d post_done=%d' %
                    (sample, role, value, sent, received, post)).encode()
        rows = [line(0, 0, 5000000, 100000, 101000),
                line(0, 1, 40 << 8, 120000, 121000),
                line(1, 0, 5000000, 300000, 301000),
                line(1, 1, 40 << 8, 320000, 321000), summary]
        result = host.tuning_result(rows)
        assert result['tuning_samples_complete'] and result['tuning_samples_before_done']
        assert result['sampled_band_channel_matches_request']
        assert not result['tuning_samples_atomic'] and not result['rf_tuning_verified']
        stale = rows.copy(); stale[2] = line(1, 0, 2407000, 300000, 301000)
        assert host.tuning_result(stale)['tuning_samples_complete']
        assert not host.tuning_result(stale)['sampled_band_channel_matches_request']
        late = rows.copy(); late[3] = line(1, 1, 40 << 8, 320000, 321000, 1)
        assert host.tuning_result(late)['tuning_samples_complete']
        assert not host.tuning_result(late)['tuning_samples_before_done']
        for bad in ([], rows[:-1], rows[1:], rows + [rows[0]],
                    rows[:-1] + [summary.replace(b'pending=0', b'pending=1')],
                    [line(0, 0, 5000000, 99999, 101000)] + rows[1:],
                    [line(0, 0, 5000000, 100000, 200000)] + rows[1:],
                    rows[:2] + [line(1, 0, 2**32, 300000, 301000)] + rows[3:],
                    rows[:3] + [line(1, 0, 5000000, 320000, 321000), summary],
                    rows[:3] + [line(1, 1, 40 << 8, 300500, 301500), summary],
                    rows[:3] + [rows[3] + b' trailing', summary]):
            assert not host.tuning_result(bad)['tuning_samples_complete']
    print('scan tuning classification: PASS; stale, incomplete, timing and RF limits retained')


if __name__ == '__main__':
    main()
