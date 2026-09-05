#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Summarize two immutable published traces offline; never admit a device run."""
import hashlib
import json
from pathlib import Path

RESULTS = Path(__file__).resolve().parent.parent / 'results'
INPUTS = {
    'attribution': ('attribution-runtime-thermal-rejected.json',
                    '4e4bc2b635e9f3a8b4ae908725dff5ac52bfedc3cc2b766d9bb4ee2622a3ad8f'),
    'recovery': ('recovery-runtime-thermal-rejected.json',
                 'be16e9df7420a9f1e59678867478bd2535f4f0c4d85573ffa03e3767933e7ccc'),
}


def summarize():
    output = {'device_access': 'none', 'units': 'millicelsius', 'traces': {}}
    for label, (name, expected) in INPUTS.items():
        path = RESULTS / name
        raw = path.read_bytes()
        if path.is_symlink() or hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError('published input identity changed: ' + name)
        data = json.loads(raw)
        thermal = data['thermal']
        slots = thermal['slots']
        stages = thermal['stages']
        maxima = [max(s['temperatures'][i] for s in slots) for i in range(3)]
        if maxima != thermal['maxima']:
            raise ValueError('aggregate disagrees with slots')
        repeated = [s for s in slots if s['sensor'] == 1]
        output['traces'][label] = {
            'input_sha256': expected, 'boot_id': data['boot_id'], 'stages': stages,
            'maxima': maxima,
            'winning_slots': [[s['slot'] for s in slots if s['temperatures'][i] == maxima[i]]
                              for i in range(3)],
            'same_sensor_1_bank_spread': [
                max(s['temperatures'][i] for s in repeated)
                - min(s['temperatures'][i] for s in repeated) for i in range(3)],
            'first_to_last_delta_by_slot': [s['temperatures'][2] - s['temperatures'][0]
                                            for s in slots],
            'last_interval_delta_by_slot': [s['temperatures'][2] - s['temperatures'][1]
                                            for s in slots],
        }
    return output


if __name__ == '__main__':
    print(json.dumps(summarize(), indent=2, sort_keys=True))
