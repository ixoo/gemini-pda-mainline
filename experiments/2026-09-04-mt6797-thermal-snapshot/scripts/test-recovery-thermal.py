#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Synthetic offline response and refusal cases, without device access."""
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    'recovery', Path(__file__).with_name('assess-recovery-thermal.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
BANKS = (0, 1, 2, 2, 3, 4, 5)
SENSORS = (0, 3, 1, 2, 1, 1, 1)


def record(attempt, values, start):
    maximum = max(values)
    header = (f'abi=1 attempt={attempt} error=0 complete=1 count=7 valid_mask=127 '
              f'winner={values.index(maximum)} maximum={maximum} '
              f'start_ns={start} end_ns={start + 10000}\n')
    return header + ''.join(
        f'slot={i} bank={BANKS[i]} sensor={SENSORS[i]} temperature={v} valid=1\n'
        for i, v in enumerate(values))


def fixture(final=37500, delay=2_000_000_000):
    return [record(1, [36300] * 7, 1_000_000_000),
            record(2, [41900, 32400, 37600, 33200, 37900, 37900, 37600], 2_000_000_000),
            record(3, [final, 32400, 37000, 33200, 37500, 37500, 37000],
                   2_000_010_000 + delay)]


def main():
    for final, response in ((37500, 'decreased'), (41900, 'unchanged'), (42000, 'increased')):
        result = module.assess(fixture(final), 35100)
        assert result['slots'][0]['response'] == response
        assert result['shared_boundary_comparison'] == 'rejected'
        assert result['prior_thermal_rejection'] == 'unchanged'
        assert result['overall_workload_classification'] == 'not-evaluated'
        assert result['physical_cooling'] == 'not-established'
    for delay in (2_000_000_000, 3_000_000_000):
        module.assess(fixture(delay=delay), 35100)
    # A fall in the zone maximum must not be assigned to the wrong slot.
    swapped = fixture()
    swapped[1] = record(2, [37000, 41900, 37600, 33200, 37900, 37900, 37600], 2_000_000_000)
    swapped[2] = record(3, [37500, 38000, 37000, 33200, 37500, 37500, 37000], 4_000_010_000)
    result = module.assess(swapped, 35100)
    assert result['slots'][0]['response'] == 'increased'
    assert result['maxima'][2] < result['maxima'][1]
    bounded = fixture()
    bounded[1] = record(2, [36000] * 7, 2_000_000_000)
    result = module.assess(bounded, 35100)
    assert result['shared_boundary_comparison'] == 'within-bounds'
    assert result['prior_thermal_rejection'] == 'unchanged'
    assert result['overall_workload_classification'] == 'not-evaluated'
    mutations = [
        (fixture(delay=1_999_999_999), 35100),
        (fixture(delay=3_000_000_001), 35100),
        (fixture(58600), 35100), (fixture(-100), 35100),
        (fixture(37501), 35100), (fixture(), True),
        (fixture(), 58501), (fixture(), -100),
        (fixture()[:2], 35100), (fixture() + [fixture()[2]], 35100),
    ]
    for old, new in [('attempt=3', 'attempt=2'), ('valid_mask=127', 'valid_mask=126'),
                     ('sensor=0', 'sensor=1'), ('complete=1', 'complete=0'),
                     ('error=0', 'error=-1'), ('maximum=37500', 'maximum=37600'),
                     ('winner=0', 'winner=4'), ('start_ns=4000010000', 'start_ns=2000010000')]:
        records = fixture(); assert old in records[2]
        records[2] = records[2].replace(old, new, 1)
        mutations.append((records, 35100))
    for records, initial in mutations:
        try:
            module.assess(records, initial)
        except ValueError:
            continue
        raise AssertionError('mutation accepted')
    with tempfile.TemporaryDirectory(prefix='gemini-recovery-thermal-', dir='/tmp') as temporary:
        paths = [Path(temporary) / f'record-{i}.txt' for i in range(3)]
        for records, expected in ((fixture(), 3), (bounded, 0), (fixture(delay=1), 1)):
            for path, raw in zip(paths, records):
                path.write_text(raw)
            child = subprocess.run([sys.executable, str(Path(__file__).with_name(
                'assess-recovery-thermal.py')), '--initial', '35100',
                *map(str, paths)], capture_output=True, text=True)
            assert child.returncode == expected, child.stderr
            if expected != 1:
                assert json.loads(child.stdout)['overall_workload_classification'] == 'not-evaluated'
    print(f'validation=recovery-thermal-assessment response_cases=3 timing_edges=2 '
          f'slot_identity_cases=1 within_bounds_nonpromotion_cases=1 mutations_rejected={len(mutations)} cli_cases=3 device_action=none')


if __name__ == '__main__':
    main()
