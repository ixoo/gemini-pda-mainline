#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Keep host elapsed-time classification distinct from proved RF dwell."""
import importlib.util
import os
from pathlib import Path
import tempfile

SOURCE = Path(__file__).resolve().parents[1] / 'passive-host.py'


def main():
    with tempfile.TemporaryDirectory(prefix='mt6797-dwell-result-') as root:
        prior = os.environ.get('GEMINI_PRIVATE_REPO')
        os.environ['GEMINI_PRIVATE_REPO'] = root
        try:
            spec = importlib.util.spec_from_file_location('dwell_result_fixture', SOURCE)
            host = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(host)
        finally:
            if prior is None:
                del os.environ['GEMINI_PRIVATE_REPO']
            else:
                os.environ['GEMINI_PRIVATE_REPO'] = prior
        def line(ms=500, us=520000, channels=1):
            return ('one-shot passive WLAN timing: requested_ms=%d elapsed_us=%d channels=%d' %
                    (ms, us, channels)).encode()
        normal = host.timing_result([line()])
        assert normal['timing_observation_complete']
        assert normal['nominal_dwell_timing_consistent']
        assert normal['effective_rf_dwell_verified'] is False
        short = host.timing_result([line(us=18000)])
        assert short['timing_observation_complete']
        assert not short['nominal_dwell_timing_consistent']
        assert short['effective_rf_dwell_verified'] is False
        assert host.timing_result([line(us=500000)])['nominal_dwell_timing_consistent']
        assert not host.timing_result([line(us=499999)])['nominal_dwell_timing_consistent']
        assert not host.timing_result([line(us=6000001)])['nominal_dwell_timing_consistent']
        for lines in ([], [line(), line()], [line(ms=100)], [line(channels=2)],
                      [line() + b' trailing'], [b'malformed']):
            result = host.timing_result(lines)
            assert not result['timing_observation_complete']
            assert result['effective_rf_dwell_verified'] is False
    print('dwell timing result: pass; shortening, duplicates and RF limits retained')


if __name__ == '__main__':
    main()
