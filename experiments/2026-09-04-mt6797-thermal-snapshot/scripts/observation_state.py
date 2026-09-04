#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Strict no-workload state gate; candidate identity must be frozen by the runner."""
import hashlib
import re
from thermal_snapshot_records import parse_status, require

BEGIN = '__THERMAL_SNAPSHOT_STATE_BEGIN__'
END = '__THERMAL_SNAPSHOT_STATE_END__'
LATE_BEGIN = '__THERMAL_SNAPSHOT_LATE_PROFILE_BEGIN__'
LATE_END = '__THERMAL_SNAPSHOT_LATE_PROFILE_END__'
RELEASE = '7.1.3-gemini-thermal-snapshot'
READY = 'arm64-late-cpu-profile: mt6797-a53-a72-a41-v7 ready'
CONSUMED_BOOTS = {'50e87880-b73a-46c2-9914-cabe34acff8c',
                  '1afc43e5-d4cd-4df6-a0e1-431eeef140df'}
STATUS_SHA256 = '6a5fd459cd5b7ed4e309dd4942e116428980f6229c9ee434240c4c70396d43eb'
FIXED = {
    'kernel_release': RELEASE, 'architecture': 'aarch64',
    'cpu_possible': '0-9', 'cpu_present': '0-9', 'cpu_online': '0-7', 'cpu_offline': '8-9',
    'controller_bound': '1', 'binder_bound': '1', 'platform_state_bound': '1',
    'status_mode': '444', 'trigger_mode': '200',
    'frequency_observer_count': '1', 'frequency_observer_mode': '444', 'frequency_log_count': '0',
    'thermal_zone_count': '1', 'thermal_zone_type': 'soc-thermal',
    'thermal_snapshot_count': '1', 'thermal_snapshot_mode': '400', 'thermal_snapshot_status_mode': '400',
    **{k: 'none' for k in ('device_storage_reads', 'device_storage_writes',
                          'frequency_observation_request', 'sysfs_write_request',
                          'cpu_admission_request', 'cpu_off_request', 'retry_request', 'reboot_request')},
}
VARIABLE = {'boot_id', 'record_identity', 'sysfs_options', 'live_status',
            'thermal_temperature_millicelsius', 'thermal_snapshot_status', 'thermal_snapshot_path'}


def bounded(text, begin, end):
    require(text.count(begin) == text.count(end) == 1, 'frame count')
    start = text.index(begin) + len(begin)
    stop = text.index(end)
    require(start < stop, 'frame order')
    require(text[start:stop].startswith('\n') and text[start:stop].endswith('\n'), 'frame lines')
    return text[start + 1:stop]


def validate_state(raw, *, record_identity, deployment_boot, attempts=0, expected_boot=None):
    require(re.fullmatch(r'[0-9a-f]{64}', record_identity) and int(record_identity, 16), 'expected record identity')
    uuid = r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}'
    require(re.fullmatch(uuid, deployment_boot) is not None, 'deployment boot identity')
    require(attempts in (0, 1, 2, 3), 'expected observer budget')
    frame = bounded(raw.replace('\r\n', '\n'), BEGIN, END)
    late = bounded(frame, LATE_BEGIN, LATE_END)
    require(late.count(READY) == 1 and not any(w in late.lower() for w in ('blocked', 'proof mask', 'proof_mask')), 'late profile readiness')
    frame = frame.replace(LATE_BEGIN + '\n' + late + LATE_END + '\n', '')
    values = {}
    for line in frame.splitlines():
        key, separator, value = line.partition('=')
        require(separator and key in FIXED.keys() | VARIABLE and key not in values, 'missing/duplicate/unknown state field')
        values[key] = value
    require(values.keys() == FIXED.keys() | VARIABLE, 'state field inventory')
    require(all(values[k] == v for k, v in FIXED.items()), 'state invariant')
    require(values['record_identity'] == record_identity, 'runtime record identity')
    boot = values['boot_id']
    require(re.fullmatch(uuid, boot) is not None and boot not in CONSUMED_BOOTS | {deployment_boot}, 'fresh boot identity')
    require(expected_boot is None or boot == expected_boot, 'boot changed during observation')
    options = values['sysfs_options'].split(',')
    require('ro' in options and 'rw' not in options and len(options) == len(set(options)), 'sysfs readonly')
    require(hashlib.sha256((values['live_status']+'\n').encode()).hexdigest() == STATUS_SHA256, 'lifecycle not exact pristine baseline')
    require(re.fullmatch(r'/sys/bus/platform/devices/[a-z0-9][a-z0-9.-]*/mt6797_temperature_snapshot', values['thermal_snapshot_path']) is not None, 'observer path')
    status = parse_status(values['thermal_snapshot_status']+'\n')
    require(status['attempts'] == attempts, 'observer not pristine or unexpected accounting')
    temperature = values['thermal_temperature_millicelsius']
    require(re.fullmatch(r'0|[1-9][0-9]*', temperature) is not None and int(temperature) <= 58500, 'aggregate temperature refusal')
    return values
