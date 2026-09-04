#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reject incomplete, duplicate and unordered timing facts."""
import importlib.util
from pathlib import Path

p = Path(__file__).with_name('audit-thermal-capture-timing.py')
spec = importlib.util.spec_from_file_location('audit', p)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
pre = 'thermal_temperature_millicelsius=35000\n'
raw = '\n'.join(f'thermal_{key}_millicelsius={value}' for key, value in
                zip(('before', 'during', 'after'), (35600, 35700, 41300))) + '\n'
raw += '\n'.join(f'[ {value}] driver: GEMINI_A72_FREQUENCY_OBSERVATION_V1 '
                 f'abi=1 attempt={index} max_attempts=3 remaining={3-index}'
                 for index, value in enumerate(('630.126402', '630.232672', '630.896266'), 1)) + '\n'
initial, temperatures, times = m.extract(pre, raw)
assert initial == 35000 and temperatures == [35600, 35700, 41300]
assert times[-1] - times[0] == 769864
cases = [(pre + pre, raw), ('', raw), (pre, raw + raw),
         (pre, raw.replace('attempt=2', 'attempt=1')),
         (pre, raw.replace('630.232672', '630.126402')),
         (pre, raw.replace('630.232672', '630.996266')),
         (pre, raw.replace('thermal_after_millicelsius=41300\n', '')),
         (pre, raw.replace('630.232672', '630.232'))]
for a, b in cases:
    try:
        m.extract(a, b)
    except ValueError:
        continue
    raise SystemExit('unsafe timing mutation accepted')
print('timing_mutations_rejected=8')
print('result=pass')
