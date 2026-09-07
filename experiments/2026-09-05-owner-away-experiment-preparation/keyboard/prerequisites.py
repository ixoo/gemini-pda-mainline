#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bounded semantic verification for keyboard capture prerequisites."""
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
DURATION = HERE / 'results/duration-6d8c9b18/receipt.json'
SHA = re.compile(r'[0-9a-f]{64}')
FILES = ('observer.stdout', 'observer.stderr', 'monitor.status', 'outer-exit')


def require(value, reason):
    if not value:
        raise ValueError('keyboard prerequisite: ' + reason)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate JSON field')
        result[key] = value
    return result


def decode(raw):
    try:
        value = json.loads(raw, object_pairs_hook=unique)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError('keyboard prerequisite: invalid JSON') from error
    require(isinstance(value, dict), 'JSON object')
    return value


def object_digest(value):
    return digest((json.dumps(value, indent=2, sort_keys=True) + '\n').encode())


def duration(raw, expected, monitor_sha256):
    require(digest(raw) == expected, 'duration receipt digest')
    value = decode(raw)
    classification = value.get('classification', {})
    require(classification == {
        'classification': 'passed', 'device_action': 'none', 'failures': [],
        'keyboard_result': 'not-tested',
        'proof_sha256': 'bc165b390b04345eec23a2e6a0d2cc86bd193099b2cdb6bc64f0026e30480870',
        'schema': 'keyboard-duration-classification-v1'}, 'duration outcome')
    require(value.get('schema') == 'keyboard-duration-build-result-v1' and
            value.get('attempt_count') == 1 and value.get('retry_count') == 0 and
            value.get('dispatch_exit') == 0 and value.get('enabled_monitor_built') is False and
            value.get('production_capture_admitted') is False and
            value.get('size_build_repeated') is False, 'duration scope')
    require(value.get('source_inputs', {}).get('monitor.c') == monitor_sha256,
            'duration monitor source')
    status = value.get('monitor_status', {})
    require(status.get('schema') == 'keyboard-monitor-v1' and status.get('reason') == 'deadline' and
            status.get('reaped') == '1' and status.get('identity_lost') == '0' and
            status.get('signal') == '9' and status.get('cancel') == '0' and
            status.get('late') == '0' and status.get('stderr_bytes') == '0' and
            status.get('stdout_bytes') == status.get('forwarded_bytes'), 'duration lifecycle')
    for key, low, high in (('term_ms', 209000, 210000), ('kill_ms', 213000, 214000),
                           ('reap_ms', 213000, 215000)):
        number = status.get(key)
        require(isinstance(number, str) and number.isdigit() and low <= int(number) <= high,
                'duration ' + key)
    return value


def runtime(raw, expected, admission, candidate):
    require(digest(raw) == expected, 'runtime receipt digest')
    value = decode(raw)
    require(set(value) == {'schema', 'classification', 'admission_id', 'boot_id',
        'candidate_sha256', 'event', 'minor', 'input_path', 'capabilities_sha256',
        'resource_paths_sha256', 'logger_age_seconds', 'map_verified',
        'console_logs_separated', 'console_status_exited', 'inventory_complete'},
        'runtime inventory')
    current = admission['runtime']
    require(value['schema'] == 'keyboard-runtime-metadata-v1' and value['classification'] == 'passed' and
        value['admission_id'] == admission['id'] and value['boot_id'] == admission['boot_id'] and
        value['candidate_sha256'] == candidate['files']['boot.img'] and
        value['event'] == current['event'] and value['minor'] == current['minor'] and
        value['input_path'] == current['input_path'] and
        value['capabilities_sha256'] == object_digest(current['capabilities']) and
        value['resource_paths_sha256'] == object_digest(current['resource_paths']) and
        type(value['logger_age_seconds']) is int and 0 <= value['logger_age_seconds'] <=
            current['logger_age_limit_seconds'] and
        all(value[key] is True for key in ('map_verified', 'console_logs_separated',
             'console_status_exited', 'inventory_complete')), 'runtime outcome/bindings')
    return value


def custody(raw, expected, admission, candidate):
    require(digest(raw) == expected, 'custody receipt digest')
    value = decode(raw)
    require(set(value) == {'schema', 'classification', 'admission_id', 'boot_id',
        'candidate_sha256', 'exclusive', 'no_other_device_operations', 'stable_power',
        'physical_selection', 'screen_readable', 'owner_ready', 'continuous_reader_exclusion'},
        'custody inventory')
    requested = admission['custody']
    require(value['schema'] == 'keyboard-custody-v1' and value['classification'] == 'passed' and
        value['admission_id'] == admission['id'] and value['boot_id'] == admission['boot_id'] and
        value['candidate_sha256'] == candidate['files']['boot.img'] and
        all(value[key] is True and requested[key] is True for key in
            ('exclusive', 'no_other_device_operations', 'stable_power', 'physical_selection',
             'screen_readable', 'owner_ready')) and value['continuous_reader_exclusion'] is True,
        'custody outcome/bindings')
    return value


def disconnect(raw, expected, admission, candidate, package_pins):
    require(digest(raw) == expected, 'disconnect receipt digest')
    value = decode(raw)
    require(set(value) == {'schema', 'classification', 'admission_id', 'boot_id',
        'candidate_sha256', 'server', 'monitor', 'claim', 'transport', 'process',
        'preservation', 'reader_release'}, 'disconnect inventory')
    server, monitor = value['server'], value['monitor']
    require(server == {'binary_sha256': candidate['members']['bin/dropbear']['sha256'],
        'admin_shell_sha256': candidate['members']['bin/admin-shell']['sha256'],
        'no_pty': True, 'authentication': 'exact-candidate-ed25519'}, 'disconnect server binding')
    probe_sha256 = package_pins.get('keyboard-disconnect-probe')
    require(isinstance(probe_sha256, str) and SHA.fullmatch(probe_sha256),
            'disconnect probe package binding')
    require(monitor == {'source_sha256': digest((HERE/'monitor.c').read_bytes()),
        'package_identity': admission['package_identity'],
        'package_revision': admission['package_revision'],
        'binary_sha256': admission['monitor_sha256'],
        'probe_sha256': probe_sha256},
        'disconnect monitor binding')
    require(value['schema'] == 'keyboard-disconnect-v1' and value['classification'] == 'passed' and
        value['admission_id'] == admission['id'] and value['boot_id'] == admission['boot_id'] and
        value['candidate_sha256'] == candidate['files']['boot.img'], 'disconnect session binding')
    require(value['claim'] == {'count': 1, 'retained': True}, 'disconnect claim')
    require(value['transport'] == {'first_connection_no_pty': True,
        'deliberate_disconnect': True, 'independent_export_connection': True},
        'disconnect transport')
    require(value['process'] == {'monitor_terminal': True, 'monitor_reaped': True,
        'observer_terminal': True, 'observer_reaped': True, 'late': False},
        'disconnect terminal state')
    preservation = value['preservation']
    require(set(preservation) == {'members', 'complete_available_members', 'source_retained'} and
        set(preservation['members']) == set(FILES) and
        all(member is None or isinstance(member, str) and SHA.fullmatch(member)
            for member in preservation['members'].values()) and
        preservation['complete_available_members'] is True and
        preservation['source_retained'] is True, 'disconnect preservation')
    require(value['reader_release'] == {'monitor_absent': True, 'observer_absent': True,
        'tty1_reader_absent': True, 'input_reader_absent': True,
        'inventory_complete': True}, 'disconnect reader release')
    return value


def verify(admission, candidate, package_pins, regular, root):
    """Verify all four exact prerequisites before a claim or transport."""
    monitor_sha = digest((HERE/'monitor.c').read_bytes())
    duration_raw = regular(DURATION, 131072, private=False)
    base = Path(root) / admission['id'] / 'prerequisites'
    runtime_raw = regular(base/'runtime.json', 65536)
    custody_raw = regular(base/'custody.json', 65536)
    disconnect_raw = regular(base/'disconnect.json', 65536)
    return {'duration': duration(duration_raw, admission['full_duration_receipt_sha256'], monitor_sha),
        'runtime': runtime(runtime_raw, admission['runtime']['metadata_receipt_sha256'], admission, candidate),
        'custody': custody(custody_raw, admission['custody']['receipt_sha256'], admission, candidate),
        'disconnect': disconnect(disconnect_raw, admission['disconnect_receipt_sha256'], admission,
                                 candidate, package_pins)}
