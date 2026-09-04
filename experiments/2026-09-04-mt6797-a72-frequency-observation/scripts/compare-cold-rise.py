#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare one pristine cold-cycle workload using temperature rise and fixed ceilings."""
import argparse
import hashlib
import importlib.util
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 'results/cold-repeat-baseline-classification.txt'
RECEIPT = HERE.parent / 'results/cold-repeat-shutdown.txt'
BASE_SHA = '6fdd283f07774f7c274065f853d37d18942c6db4e910d71e0e17a0826fa0aae4'
OLD_BOOT = '50e87880-b73a-46c2-9914-cabe34acff8c'
TARGET_BOOT = '1afc43e5-d4cd-4df6-a0e1-431eeef140df'
BASELINE_PRE_MILLICELSIUS = 52800
RECOVERY_BOOT = 'a59a6e44-5ff2-453e-a78b-4bbba106ed53'
PINS = {
    'validate-production-pretrigger.py': '39fba1bc82080068ccfa90b9a7188e7beb78881b97ab3a5d01f700023feb186c',
    'classify-production-runtime.py': 'b186b6c1cf83d7757bbe401036d4660d950a25dd59e47aa71515dfb8b3c4f224',
    'build-production-runtime.sh': '241854bde76396d2713a7cc5a75ea53f7e56fa1b143a3a2278c3b7f64fff52eb',
}


def require(ok, why):
    if not ok:
        raise ValueError(why)


def fields(text):
    result = {}
    for line in text.splitlines():
        require('=' in line, 'malformed-summary')
        key, value = line.split('=', 1)
        require(key not in result, 'duplicate:' + key)
        result[key] = value
    return result


def compare(baseline, current, initial_temperature):
    require(set(current) == set(baseline), 'summary-field-set')
    require(bool(re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', current['boot_id'])), 'boot-id-shape')
    require(current['boot_id'] != baseline['boot_id'], 'reused-boot-id')
    require(current['boot_id'] == TARGET_BOOT, 'unselected-boot-id')
    require(0 <= initial_temperature <= 58500, 'initial-temperature-range')
    for key, expected in baseline.items():
        value = current[key]
        if key == 'boot_id':
            continue
        if key.endswith('_accounting_delta'):
            require(value.isdecimal() and 0 < int(value) <= 10000,
                    'accounting:' + key)
        elif key.endswith('_temperature_millicelsius'):
            require(value.isdecimal() and 0 <= int(value) <= int(expected) + 5000,
                    'thermal-absolute-ceiling:' + key)
            observed_rise = int(value) - initial_temperature
            baseline_rise = int(expected) - BASELINE_PRE_MILLICELSIUS
            require(abs(observed_rise - baseline_rise) <= 5000,
                    'thermal-rise-envelope:' + key)
        else:
            require(value == expected, 'baseline-mismatch:' + key)
    temperatures = [int(current[f'{label}_temperature_millicelsius'])
                    for label in ('before', 'during', 'after')]
    require(max(temperatures) - min(temperatures) <= 5000, 'thermal-spread')


def gate(capture):
    for name, expected in PINS.items():
        require(hashlib.sha256((HERE / name).read_bytes()).hexdigest() == expected,
                'source-pin:' + name)
    require(hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA,
            'baseline-pin')
    spec = importlib.util.spec_from_file_location(
        'pristine', HERE / 'validate-production-pretrigger.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    deployment = module.validate_deployment((capture / 'deployment-summary.txt').read_text())
    raw = (capture / 'pretrigger.txt').read_text()
    boot = module.validate_capture(raw, deployment)
    require(boot not in (OLD_BOOT, RECOVERY_BOOT), 'reused-baseline-or-recovery-boot')
    require(boot == TARGET_BOOT, 'unselected-boot-id')
    parsed = module.fields(module.bounded(raw.replace('\r', ''), module.BEGIN, module.END))
    initial_temperature = int(parsed['thermal_temperature_millicelsius'])
    require(0 <= initial_temperature <= 58500,
            'pretrigger-temperature-range')
    receipt = fields(RECEIPT.read_text())
    require(receipt == {'boot_id': RECOVERY_BOOT, 'kernel_release': '3.18.41+',
                       'shutdown_requested': 'yes', 'ssh_disconnect_observed': 'yes',
                       'boot2_sha256': module.CANDIDATE,
                       'partition_write': 'none', 'backup_created': 'no',
                       'reboot_requested': 'no'},
            'cold-cycle-shutdown-receipt')
    return boot, initial_temperature


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('gate', 'compare'))
    parser.add_argument('--capture', type=Path, required=True)
    args = parser.parse_args()
    try:
        boot, initial_temperature = gate(args.capture)
        if args.mode == 'compare':
            result = subprocess.run(
                [sys.executable, str(HERE / 'classify-production-runtime.py'),
                 str(args.capture / 'runtime.txt'), '--boot-id', boot],
                text=True, capture_output=True, check=False)
            require(result.returncode == 0, 'raw-runtime-rejected:' + result.stdout)
            baseline = fields(BASE.read_text())
            current = fields(result.stdout)
            compare(baseline, current, initial_temperature)
            events = fields((args.capture / 'runtime-events.txt').read_text())
            for key, value in {'boot_id': boot, 'netcat_sessions': '1', 'retries': '0',
                               'classification': 'pass', 'native_reboot_command_sent': 'no',
                               'device_left_running': 'yes'}.items():
                require(events.get(key) == value, 'host-budget:' + key)
            print('comparison=cold-cycle-rise-bounded-repeat-pass')
            print('pretrigger_temperature_millicelsius=' + str(initial_temperature))
            print('baseline_pretrigger_temperature_millicelsius=' + str(BASELINE_PRE_MILLICELSIUS))
            for label in ('before', 'during', 'after'):
                key = f'{label}_temperature_millicelsius'
                print(f'{label}_rise_millicelsius={int(current[key]) - initial_temperature}')
                print(f'{label}_baseline_rise_millicelsius={int(baseline[key]) - BASELINE_PRE_MILLICELSIUS}')
            print('baseline_boot_id=' + OLD_BOOT)
            print('baseline_classification_sha256=' + BASE_SHA)
            print(result.stdout, end='')
        else:
            print('cold_rise_gate=exact-pristine-unspent-cold-cycle-ready')
            print('boot_id=' + boot)
    except (OSError, ValueError, KeyError) as error:
        print('cold_rise=rejected')
        print('reason=' + str(error))
        return 3
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
