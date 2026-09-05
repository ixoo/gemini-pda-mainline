#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline-testable corrected-V4 orchestration; no transport or device CLI."""
import hashlib
import importlib.util
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
PINS = {
    'observation_state': '217b176e5825cfb1423a51b0b4b99a443b5d00d3a7149ad7c9f7e06c77c628dc',
    'observation_protocol': 'ac8067307a46bc80478697bd30dddab78459f298a408b4de48dd8fd649a7bf6c',
    'thermal_snapshot_records': '3d16447c3a213c658814a27795d6964d2c21c99424806aa51bd582f78e90da74',
}
RELEASE = '7.1.3-gemini-thermal-v4-corrected'
CLOSED_BOOTS = {
    '50e87880-b73a-46c2-9914-cabe34acff8c', '1afc43e5-d4cd-4df6-a0e1-431eeef140df',
    'ac3d28c7-69fe-4ccb-8145-cad85cbd0653', '056703de-bf29-4956-891e-ff69d19fdd68',
    '6bd8ef2e-d7b1-4b4f-95a7-c97e13992a4c', '5d45171e-6c70-4fe4-99b6-715ac22ca826',
}
OLD_IDENTITIES = {
    '666961b636b21b8598a64999e9dbf72af280ad99f07a6b745045320f24ca361b',
    '7d67a19b3ae40ae1521293d7ffc834e6d06ae14a2d55de693ee9c815bdaee552',
    'b8f0a5652c431acbc60ae38d569be15e860dcf1d1a259949a9d2b0a4f19358c6',
}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def module(name):
    for dependency, expected in PINS.items():
        path = HERE / (dependency + '.py')
        require(not path.is_symlink() and hashlib.sha256(path.read_bytes()).hexdigest() == expected,
                'inherited source identity changed')
    spec = importlib.util.spec_from_file_location('v4_private_' + name, HERE / (name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class Protocol:
    """The eventual frozen runner must supply validated candidate/record identities."""

    def __init__(self, candidate, record):
        for value in (candidate, record):
            require(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value)
                    and int(value, 16) and value not in OLD_IDENTITIES, 'new exact identity required')
        require(candidate != record, 'distinct image and record identities required')
        self.candidate, self.record = candidate, record
        self.state = module('observation_state')
        self.state.FIXED = {**self.state.FIXED, 'kernel_release': RELEASE}
        self.state.CONSUMED_BOOTS = self.state.CONSUMED_BOOTS | CLOSED_BOOTS
        self.parent = module('observation_protocol')
        self.parent.CANDIDATE = candidate

    def state_gate(self, raw, deployment_boot, attempts=0, expected_boot=None):
        values = self.state.validate_state(raw, record_identity=self.record,
                                          deployment_boot=deployment_boot, attempts=attempts,
                                          expected_boot=expected_boot)
        require(values['thermal_snapshot_path'] == self.parent.PATH, 'exact thermal device')
        require(int(values['thermal_temperature_millicelsius']) % 100 == 0, 'aggregate precision')
        return values

    def run(self, transport, save, request, pause, deployment):
        deployment_boot = self.parent.receipt(deployment)
        raw = transport('state', None, None)
        save('preflight.txt', raw)
        pre = self.state_gate(raw, deployment_boot)
        late = self.state.bounded(raw.replace('\r\n', '\n'), self.state.LATE_BEGIN, self.state.LATE_END)
        boot = pre['boot_id']
        records = []
        for attempt in (1, 2, 3):
            if attempt > 1:
                pause(1)
            request(attempt)  # Frozen host must fsync this before consuming transport.
            raw = transport('read', boot, attempt)
            save(f'read-{attempt}.txt', raw)
            current = self.parent.reading(raw, boot, attempt)
            require(all(s['temperature'] % 100 == 0 for s in current['samples']), 'slot precision')
            require(not records or current['start_ns'] > records[-1]['end_ns'], 'scan order')
            records.append(current)
            maxima = [r['maximum'] for r in records]
            require(max(maxima) - min(maxima) <= 5000, 'aggregate spread')
        raw = transport('state', None, None)
        save('postflight.txt', raw)
        self.state_gate(raw, deployment_boot, 3, boot)
        require(self.state.bounded(raw.replace('\r\n', '\n'), self.state.LATE_BEGIN, self.state.LATE_END)
                == late, 'late-profile evidence changed')
        return {'classification': 'corrected-v4-no-workload-observer-pass',
                'candidate_sha256': self.candidate, 'record_identity': self.record,
                'kernel_release': RELEASE, 'boot_id': boot, 'records': records,
                'cpu_online': '0-7', 'cpu_offline': '8-9', 'lifecycle': 'unchanged-pristine',
                'snapshot_requests': 3, 'ordinary_thermal_reads': 2,
                'frequency_observation_requests': 0, 'cpu_admission_requests': 0,
                'cpu_off_requests': 0, 'retries': 0, 'reboot_requests': 0,
                'device_storage_reads': 'none', 'device_storage_writes': 'none',
                'device_temporary_files': 'none', 'cleanup': 'transport-shells-exited',
                'conversion_age': 'unknown', 'calibrated_accuracy': 'not-established',
                'integrated_thermal_repeatability': 'not-established'}
