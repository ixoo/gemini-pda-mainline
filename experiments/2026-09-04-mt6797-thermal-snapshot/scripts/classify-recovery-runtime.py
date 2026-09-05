#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline combined recovery classifier; never fabricates a waiting temperature."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tempfile

from thermal_snapshot_records import parse_complete, require

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RELEASE = '7.1.3-gemini-thermal-snapshot'
CLOSED_BOOTS = {'50e87880-b73a-46c2-9914-cabe34acff8c',
                '1afc43e5-d4cd-4df6-a0e1-431eeef140df',
                'ac3d28c7-69fe-4ccb-8145-cad85cbd0653',
                '056703de-bf29-4956-891e-ff69d19fdd68'}
PARENT = ROOT / 'experiments/2026-09-04-mt6797-a72-frequency-observation/scripts/classify-production-runtime.py'
PARENT_SHA = 'b186b6c1cf83d7757bbe401036d4660d950a25dd59e47aa71515dfb8b3c4f224'
ASSESS_SHA = '39b579fb99e035b53d5ecc7b0e3f97d21f7277169fdcb308b5f3c2fc1ae1683a'


def load(path, sha):
    require(not path.is_symlink() and hashlib.sha256(path.read_bytes()).hexdigest() == sha,
            'classifier dependency changed')
    spec = importlib.util.spec_from_file_location(path.stem.replace('-', '_'), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def scalar(text, key):
    values = re.findall(r'^' + re.escape(key) + r'=([^\n]*)$', text, re.M)
    require(len(values) == 1, 'missing/duplicate ' + key)
    return values[0]


def classify(raw, boot, initial):
    parent = load(PARENT, PARENT_SHA)
    assessment = load(HERE / 'assess-recovery-thermal.py', ASSESS_SHA)
    require(re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', boot)
            and boot not in CLOSED_BOOTS, 'fresh boot required')
    raw = raw.replace('\r\n', '\n')
    require(raw.count('kernel_release=' + RELEASE + '\n') == 2, 'exact kernel frames')
    require('__A72_FREQUENCY_THERMAL_REJECTED__' not in raw and
            'concurrent_result=fail' not in raw, 'device rejection')
    require('__THERMAL_ATTRIBUTION_' not in raw and
            raw.count('__THERMAL_RECOVERY_') == 6, 'snapshot inventory')
    require(not re.search(r'^thermal_during_millicelsius=', raw, re.M),
            'unobserved waiting temperature')
    records = []
    cleaned = raw
    for n, label in enumerate(('before', 'after', 'recovery'), 1):
        begin = '__THERMAL_RECOVERY_' + label + '_BEGIN__\n'
        end = '__THERMAL_RECOVERY_' + label + '_END__\n'
        data = parent.bounded(raw, begin, end)
        record = parse_complete(data, n)
        require(scalar(raw, 'thermal_' + label + '_millicelsius') == str(record['maximum']),
                'snapshot aggregate agreement')
        require(scalar(raw, 'snapshot_' + label + '_attempt') == str(n), 'snapshot attempts')
        require(raw.index(end) < raw.index('\nthermal_' + label + '_millicelsius='),
                'snapshot result ordering')
        records.append(data)
        cleaned = cleaned.replace(begin + data + end, "")
    frame = parent.bounded(cleaned, parent.OBS_BEGIN, parent.OBS_END)
    fields = parent.strict_fields(frame)
    exact = {
        'frequency_observer_count': '1', 'frequency_observer_mode': '444',
        'frequency_log_count_before': '0', 'thermal_zone_count': '1',
        'thermal_zone_type': 'soc-thermal', 'frequency_log_count': '3',
        'writer8_alive_before_observation': '1', 'writer9_alive_before_observation': '1',
        'writer8_alive_after_observation': '1', 'writer9_alive_after_observation': '1',
        'writer_start_released': '1', 'owned_workers_reaped': 'yes',
        'cancellation_file': 'absent', 'snapshot_final_attempts': '3',
        'recovery_workers_before': 'quiescent', 'recovery_workers_after': 'quiescent',
        'recovery_files_before': 'absent', 'recovery_files_after': 'absent',
        'recovery_sleep_requested_seconds': '2', 'recovery_timing': 'within-declared-window',
    }
    for key, expected in exact.items():
        require(fields.get(key) == expected and scalar(raw, key) == expected, 'field:' + key)
    for label in ('before', 'after', 'recovery'):
        for key in ('thermal_' + label + '_millicelsius', 'snapshot_' + label + '_attempt'):
            require(fields.get(key) == scalar(raw, key), 'snapshot field outside observation frame')
    observations = [parent.observation(scalar(raw, 'frequency_' + label), n)
                    for n, label in enumerate(('before', 'during', 'after'), 1)]
    for key in ('clock_generation', 'big_generation'):
        values = [o[key] for o in observations]
        require(values[0] < values[1] < values[2], 'frequency generations')
    for observation in observations:
        for key, expected in {'ll_khz': 897000, 'l_khz': 1274000,
                              'b_khz': 750000, 'cci_khz': 629500}.items():
            require(observation[key] == expected, 'baseline frequency')
    logs = re.findall(r'GEMINI_A72_FREQUENCY_OBSERVATION_V1 (abi=[^\n]+)', raw)
    require(raw.count(parent.LOG_MARKER) == 3 and
            logs == [o['raw'] for o in observations], 'frequency logs')
    # The entire order is checked; merely having a quiescence receipt somewhere
    # in an otherwise plausible transcript cannot admit the last snapshot.
    ordered = [parent.LIFECYCLE_END, parent.OBS_BEGIN, '\nfrequency_before=',
               '__THERMAL_RECOVERY_before_BEGIN__', '__THERMAL_RECOVERY_before_END__',
               '\nthermal_before_millicelsius=', '\nsnapshot_before_attempt=',
               parent.CONCURRENT_BEGIN, 'writer9_alive_before_observation=1',
               '\nfrequency_during=', 'writer8_alive_after_observation=1',
               'writer_start_released=1', 'reader9_status=0', '\nfrequency_after=',
               '__THERMAL_RECOVERY_after_BEGIN__', '__THERMAL_RECOVERY_after_END__',
               '\nthermal_after_millicelsius=', '\nsnapshot_after_attempt=',
               '\ncpu8_stat_after=', 'recovery_workers_before=quiescent',
               'recovery_files_before=absent', 'recovery_sleep_requested_seconds=2',
               'recovery_workers_after=quiescent', 'recovery_files_after=absent',
               '__THERMAL_RECOVERY_recovery_BEGIN__', '__THERMAL_RECOVERY_recovery_END__',
               '\nthermal_recovery_millicelsius=', '\nsnapshot_recovery_attempt=',
               'recovery_timing=within-declared-window', '\ncleanup_file8=absent',
               'owned_workers_reaped=yes', parent.CONCURRENT_END, parent.OBS_END]
    positions = [raw.index(marker) for marker in ordered]
    require(all(a < b for a, b in zip(positions, positions[1:])), 'recovery stage order')
    normalized = cleaned.replace('kernel_release=' + RELEASE + '\n',
                             'kernel_release=' + parent.CURRENT_RELEASE + '\n')
    with tempfile.TemporaryDirectory(prefix='gemini-recovery-classify-', dir='/tmp') as tmp:
        parent.classify_lifecycle(normalized, boot, Path(tmp))
        deltas = parent.classify_concurrent(normalized, boot, Path(tmp))
    require(all(0 < deltas[cpu] <= 10000 for cpu in (8, 9)), 'CPU accounting bounds')
    thermal = assessment.assess(records, initial)
    return {'classification': 'bounded-recovery-comparison-rejected' if
            thermal['shared_boundary_comparison'] == 'rejected' else 'bounded-recovery-observed',
            'boot_id': boot, 'kernel_release': RELEASE, 'thermal': thermal,
            'cpu8_accounting_delta': deltas[8], 'cpu9_accounting_delta': deltas[9],
            'cpu_online': '0-9', 'cpu_map': '0-3,4-7,8-9', 'restore_stage': 18,
            'frequency_records': observations, 'snapshot_requests': 3,
            'writer_checksums': '8-of-8', 'peer_reader_checksums': '8-of-8',
            'concurrent_rounds': 4, 'owned_workers_reaped': True,
            'recovery_owned_workers': 'quiescent', 'device_storage_writes': 'none',
            'full_integrated_repeatability': 'not-established',
            'device_action': 'none-offline-classification', 'host_postflight': 'not-evaluated'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--boot-id', required=True)
    parser.add_argument('--initial', type=int, required=True)
    args = parser.parse_args()
    result = classify(args.capture.read_text(), args.boot_id, args.initial)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 3 if result['classification'] == 'bounded-recovery-comparison-rejected' else 0


if __name__ == '__main__':
    raise SystemExit(main())
