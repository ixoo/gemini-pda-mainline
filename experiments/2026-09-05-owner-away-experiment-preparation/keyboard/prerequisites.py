#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bounded semantic verification for keyboard capture prerequisites."""
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
DURATION = HERE / 'results/duration-daaa4529/receipt.json'
SHA = re.compile(r'[0-9a-f]{64}')
FILES = ('observer.stdout', 'observer.stderr', 'monitor.status', 'outer-exit')
EVIDENCE = FILES + ('disconnect-process.json', 'export-process.json', 'reader-scan.json')


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


def fields(raw):
    result = {}
    try:
        lines = raw.decode('ascii').splitlines()
    except UnicodeDecodeError as error:
        raise ValueError('keyboard prerequisite: non-ASCII status') from error
    for line in lines:
        key, separator, value = line.partition('=')
        require(separator and key and key not in result and value == value.strip(),
                'status framing')
        result[key] = value
    return result


def duration(raw, expected, monitor_sha256):
    require(digest(raw) == expected, 'duration receipt digest')
    value = decode(raw)
    classification = value.get('classification', {})
    require(classification == {
        'classification': 'passed', 'device_action': 'none', 'failures': [],
        'keyboard_result': 'not-tested',
        'proof_sha256': 'bfff5b5917d1dd936851e64591f6de90ecebb294b34f4a4f78e4b620e44cf586',
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


def disconnect(raw, expected, admission, candidate, package_pins, evidence_root, regular):
    require(digest(raw) == expected, 'disconnect receipt digest')
    value = decode(raw)
    require(set(value) == {'schema', 'classification', 'admission_id', 'boot_id',
        'candidate_sha256', 'server', 'monitor', 'claim', 'transport', 'process',
        'preservation', 'reader_release', 'evidence'}, 'disconnect inventory')
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
    evidence = {}
    for name in EVIDENCE:
        evidence[name] = regular(Path(evidence_root)/name, 98304 if name.startswith('observer.') else 16384)
    require(value['evidence'] == {name: digest(raw) for name, raw in evidence.items()},
            'disconnect evidence inventory/digests')
    preservation = value['preservation']
    require(set(preservation) == {'members', 'complete_available_members', 'source_retained'} and
        set(preservation['members']) == set(FILES) and
        all(preservation['members'][name] == digest(evidence[name]) for name in FILES) and
        preservation['complete_available_members'] is True and
        preservation['source_retained'] is True, 'disconnect preservation')
    require(re.fullmatch(rb'fixture-child=[1-9][0-9]*\n', evidence['observer.stdout']) is not None and
            evidence['observer.stderr'] == b'' and evidence['outer-exit'] == b'2\n',
            'disconnect retained members')
    status = fields(evidence['monitor.status'])
    require(set(status) == {'schema', 'reason', 'reaped', 'identity_lost', 'exit', 'signal',
        'cancel', 'term_ms', 'kill_ms', 'reap_ms', 'term_errno', 'kill_errno', 'late',
        'stdout_bytes', 'stderr_bytes', 'forwarded_bytes'}, 'disconnect status inventory')
    numeric = {}
    for key in ('term_ms', 'kill_ms', 'reap_ms', 'stdout_bytes', 'stderr_bytes', 'forwarded_bytes'):
        require(re.fullmatch(r'-1|0|[1-9][0-9]*', status[key]) is not None,
                'disconnect status numeric field')
        numeric[key] = int(status[key])
    reason_cancel = ((status['reason'] == 'cancelled' and status['cancel'] == '1') or
                     (status['reason'] == 'forward-close-or-stall' and status['cancel'] == '0'))
    if status['signal'] == '1':
        timing = numeric['term_ms'] == numeric['kill_ms'] == -1 and 0 <= numeric['reap_ms'] <= 500
    else:
        timing = (status['signal'] == '9' and 0 <= numeric['term_ms'] <= 300 and
                  numeric['term_ms'] <= numeric['kill_ms'] <= 380 and
                  numeric['kill_ms'] <= numeric['reap_ms'] <= 500)
    require(status['schema'] == 'keyboard-monitor-v1' and reason_cancel and timing and
        status['reason'] in ('cancelled', 'forward-close-or-stall') and
        status['reaped'] == '1' and status['identity_lost'] == '0' and
        status['exit'] == '-1' and status['signal'] in ('1', '9') and
        status['cancel'] in ('0', '1') and status['term_errno'] == '0' and
        status['kill_errno'] == '0' and status['late'] == '0' and
        numeric['stderr_bytes'] == 0 and numeric['stdout_bytes'] == len(evidence['observer.stdout']) and
        0 <= numeric['forwarded_bytes'] <= len(evidence['observer.stdout']),
        'disconnect parsed lifecycle')
    transport = decode(evidence['disconnect-process.json'])
    require(transport == {'schema': 'keyboard-disconnect-transport-v1',
        'classification': 'deliberate-client-disconnect', 'connections': 1, 'no_pty': True,
        'marker_seen': True, 'stdin_complete': True, 'client_signal': 9,
        'elapsed_milliseconds': transport.get('elapsed_milliseconds')} and
        type(transport['elapsed_milliseconds']) is int and
        0 <= transport['elapsed_milliseconds'] <= 100, 'disconnect transport process')
    exported = decode(evidence['export-process.json'])
    require(set(exported) == {'exit_status', 'reason', 'stdin_complete', 'stdout_bytes',
        'stderr_bytes', 'elapsed_seconds'} and exported['exit_status'] == 0 and
        exported['reason'] is None and exported['stdin_complete'] is True and
        type(exported['elapsed_seconds']) in (int, float) and
        0 <= exported['elapsed_seconds'] <= 30 and exported['stderr_bytes'] == 0,
        'disconnect export process')
    scan = decode(evidence['reader-scan.json'])
    require(scan == {'schema': 'keyboard-reader-release-v1', 'classification': 'passed',
        'admission_id': admission['id'], 'boot_id': admission['boot_id'],
        'processes_scanned': scan.get('processes_scanned'),
        'descriptors_scanned': scan.get('descriptors_scanned'), 'matches': []} and
        type(scan['processes_scanned']) is int and 0 <= scan['processes_scanned'] <= 512 and
        type(scan['descriptors_scanned']) is int and 0 <= scan['descriptors_scanned'] <= 4096,
        'disconnect reader scan')
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
    disconnect_root = base/'disconnect'
    disconnect_raw = regular(disconnect_root/'receipt.json', 65536)
    return {'duration': duration(duration_raw, admission['full_duration_receipt_sha256'], monitor_sha),
        'runtime': runtime(runtime_raw, admission['runtime']['metadata_receipt_sha256'], admission, candidate),
        'custody': custody(custody_raw, admission['custody']['receipt_sha256'], admission, candidate),
        'disconnect': disconnect(disconnect_raw, admission['disconnect_receipt_sha256'], admission,
                                 candidate, package_pins, disconnect_root, regular)}
