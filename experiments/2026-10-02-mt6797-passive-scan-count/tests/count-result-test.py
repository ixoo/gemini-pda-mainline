#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Distinguish firmware processing evidence from host reception and RF dwell."""
import importlib.util
import os
from pathlib import Path
import tempfile

SOURCE = Path(__file__).resolve().parents[1] / 'passive-host.py'


def main():
    with tempfile.TemporaryDirectory(prefix='mt6797-count-result-') as root:
        prior = os.environ.get('GEMINI_PRIVATE_REPO')
        os.environ['GEMINI_PRIVATE_REPO'] = root
        try:
            spec = importlib.util.spec_from_file_location('count_result_fixture', SOURCE)
            host = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(host)
        finally:
            if prior is None:
                del os.environ['GEMINI_PRIVATE_REPO']
            else:
                os.environ['GEMINI_PRIVATE_REPO'] = prior
        def line(version=3, count=5, pno=0):
            return ('one-shot passive WLAN firmware scan count: version=%d management=%d pno=%d' %
                    (version, count, pno)).encode()
        positive = host.count_result([line()])
        assert positive['firmware_count_observation_complete']
        assert positive['firmware_management_processing_seen']
        assert positive['firmware_management_processing_count'] == 5
        zero = host.count_result([line(count=0)])
        assert zero['firmware_count_observation_complete']
        assert not zero['firmware_management_processing_seen']
        for lines in ([], [line(), line()], [line(version=2)], [line(version=256)],
                      [line(count=4294967296)], [line(pno=2)],
                      [line() + b' trailing'], [b'malformed']):
            assert not host.count_result(lines)['firmware_count_observation_complete']
        boundary = host.count_result([line(count=4294967295, pno=1)])
        assert boundary['firmware_count_observation_complete']
        assert boundary['firmware_management_processing_seen']
        timing = host.timing_result([
            b'one-shot passive WLAN timing: requested_ms=500 elapsed_us=513501 channels=1'])
        assert timing['effective_rf_dwell_verified'] is False
    print('firmware scan counter result: pass; zero, duplicates, versions and RF limits retained')


if __name__ == '__main__':
    main()
