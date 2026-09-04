#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Extract only attributable timing/temperature facts from two pinned captures."""
import argparse
from decimal import Decimal
import hashlib
from pathlib import Path
import re

PINS = {
    'baseline': ('50e87880-b73a-46c2-9914-cabe34acff8c',
                 'aabc444b8336c94387a42adb771ff8aa515c6b2504bcba642624653fba34d0cc',
                 '6e32efb80f6f2ea859ebbee261b82fdf9a0ff9f443e452222446031ed2d15a0e'),
    'repeat': ('1afc43e5-d4cd-4df6-a0e1-431eeef140df',
               '5d37017b07b72784284c8b299854b3b59eb412491fe4cbb7344a715ffa156d20',
               '95b501761ad30e0b7d4cb08b828389a8abd95135dbadf9570fea0e6d08989b3e'),
}


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def single(text, key):
    values = re.findall(r'^' + re.escape(key) + r'=(\d+)$', text, re.M)
    require(len(values) == 1, 'missing-or-duplicate:' + key)
    return int(values[0])


def extract(pretrigger, runtime):
    initial = single(pretrigger, 'thermal_temperature_millicelsius')
    temperatures = [single(runtime, f'thermal_{label}_millicelsius')
                    for label in ('before', 'during', 'after')]
    matches = re.findall(
        r'^\[\s*(\d+\.\d{6})\] [^\n]*GEMINI_A72_FREQUENCY_OBSERVATION_V1 '
        r'abi=1 attempt=([123]) max_attempts=3 ', runtime, re.M)
    require([x[1] for x in matches] == ['1', '2', '3'], 'frequency-timestamp-order')
    times = [int(Decimal(value) * 1000000) for value, _ in matches]
    require(times[0] < times[1] < times[2], 'frequency-timestamp-monotonicity')
    require(len(re.findall(r'^\[.*GEMINI_A72_FREQUENCY_OBSERVATION_V1 ',
                           runtime, re.M)) == 3, 'extra-frequency-record')
    return initial, temperatures, times


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--repeat', type=Path, required=True)
    args = parser.parse_args()
    try:
        results = []
        for label, directory in (('baseline', args.baseline), ('repeat', args.repeat)):
            boot, pre_hash, runtime_hash = PINS[label]
            data = []
            for name, expected in (('pretrigger.txt', pre_hash), ('runtime.txt', runtime_hash)):
                raw = (directory / name).read_bytes()
                require(hashlib.sha256(raw).hexdigest() == expected, label + ':' + name + '-pin')
                data.append(raw.decode().replace('\r', ''))
            initial, temperatures, times = extract(*data)
            results.append((label, boot, initial, temperatures, times))
        print('audit=thermal-capture-timing-pinned')
        for label, boot, initial, temperatures, times in results:
            print(f'{label}_boot_id={boot}')
            print(f'{label}_initial_millicelsius={initial}')
            for phase, temperature, timestamp in zip(('before', 'during', 'after'), temperatures, times):
                print(f'{label}_{phase}_temperature_millicelsius={temperature}')
                print(f'{label}_{phase}_rise_millicelsius={temperature - initial}')
                print(f'{label}_{phase}_frequency_log_microseconds={timestamp}')
            print(f'{label}_frequency_window_microseconds={times[2] - times[0]}')
            print(f'{label}_during_to_after_frequency_microseconds={times[2] - times[1]}')
            print(f'{label}_temperature_spread_millicelsius={max(temperatures) - min(temperatures)}')
        print('temperature_read_timestamps=not-captured')
        print('sensor_bank_provenance=not-captured')
        print('sensor_conversion_age=not-captured')
        print('synchronized_thermal_frequency_pair=no')
        print('cross_boot_temperature_pass=not-inferred')
        print('device_access=none')
    except (OSError, UnicodeError, ValueError) as error:
        print('audit=rejected')
        print('reason=' + str(error))
        return 3
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
