#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Read-only aggregate verification of retained first-baseline/recovery evidence.

No candidate image or credential is opened. The caller supplies independently
trusted artifact/manifest identities. No reviewed prepare/perform/network path
is called. A successful archive verification never admits dependent execution.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys
from types import MappingProxyType

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
BASELINE = 'experiments/2026-09-05-owner-away-experiment-preparation/baseline/scripts/'
# Resolve only an enclosing checkout, never a path supplied by the evidence or
# environment. This also permits ignored private staging inside that checkout.
REPO = next((path for path in HERE.parents
             if (path / 'kernel/manifest.json').is_file() and
             (path / BASELINE / 'collect-baseline.py').is_file()), None)
SHA = re.compile(r'[0-9a-f]{64}')
UUID = re.compile(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}')
SOURCE_PINS = MappingProxyType({
    BASELINE + 'collect-baseline.py': 'efbca1e464e04005d3b7d503742b426eb9f642140ec289c40bc43563852208cf',
    BASELINE + 'finish-baseline.py': 'f6fc5cf6a73518385af714b4f8566e32e4b231338cf231b0204d0b5aa96564a0',
    BASELINE + 'session_steps.py': '762616bb386647e0a25addd36ad9dba2f6384ebde4858f89a806a32678fc60fc',
    BASELINE + 'deployment_receipt.py': 'a2dc643ddedf5c9c93ede43598208cafd17242fccbb45db6ddaf078f30ae6f23',
    'experiments/2026-09-04-mt6797-pwrap-reset-serviceability/scripts/remote_observe.sh':
        'bfa7b11a355263f181285b12d99a07c1ca71ac6b8f13570730da7783937e9fe4',
    'experiments/2026-09-04-mt6797-pwrap-reset-serviceability/scripts/classify_observation.py':
        'f628143d6a70fdda8c6da5171c69e91647a51eb3cb65fa1577d2487540cb1ca6',
    'experiments/2026-09-04-mt6797-thermal-snapshot/scripts/v4_deployment_receipt.py':
        '2ef4fc09a11207e2f43cce9c1d328905b636d618c72f3ab76325ef766201c5b7',
})


class Refused(ValueError):
    """The archive or independently pinned verifier inputs did not verify."""


def need(value, reason):
    if not value:
        raise Refused(reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode()


def pairs(items):
    result = {}
    for key, value in items:
        need(key not in result, 'duplicate-json-key')
        result[key] = value
    return result


def fields(value, keys, label):
    need(type(value) is dict and set(value) == set(keys), label + '-inventory')


def safe_read(path, limit=65536, *, private=False):
    path = Path(path).absolute()
    for part in (path, *path.parents):
        need(not part.is_symlink(), 'symlink-input')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        need(stat.S_ISREG(info.st_mode) and info.st_size <= limit, 'input-type-or-size')
        if private:
            need(info.st_nlink == 1 and stat.S_IMODE(info.st_mode) == 0o600 and
                 info.st_uid == os.getuid(), 'archive-file-permissions-or-links')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            data = stream.read(limit + 1)
        need(len(data) <= limit, 'input-grew')
        return data
    finally:
        os.close(fd)


def private_dir(path):
    for part in (path, *path.parents):
        need(not part.is_symlink(), 'symlink-directory')
    info = path.stat()
    need(stat.S_ISDIR(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o700 and
         info.st_uid == os.getuid(), 'private-directory')


def module(name, path):
    spec = importlib.util.spec_from_file_location('verified_baseline_' + name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def sources():
    """Verify the complete seven-file production closure before any imports."""
    need(REPO is not None, 'enclosing-source-checkout-missing')
    for name, expected in SOURCE_PINS.items():
        need(digest(safe_read(REPO / name, 262144)) == expected, 'changed-source:' + name)


def tools():
    sources()
    collector = module('collector', REPO / BASELINE / 'collect-baseline.py')
    finish = module('finish', REPO / BASELINE / 'finish-baseline.py')
    receipt = module('receipt', REPO / BASELINE / 'deployment_receipt.py')
    return collector, finish, receipt


def read(path, limit=65536):
    return safe_read(path, limit, private=True)


def load(path, limit=65536):
    return json.loads(read(path, limit), object_pairs_hook=pairs)


def valid_hash(value):
    return type(value) is str and SHA.fullmatch(value)



def private_snapshot(directory, manifest, F):
    """Retain manifest-bound bytes from descriptors enforcing archive privacy."""
    verified = F.verified_snapshot(directory, manifest)
    snapshot = {}
    for name, expected in verified.items():
        raw = read(directory / name, 4 * 1024 * 1024)
        need(raw == expected, 'snapshot-private-read-drift')
        snapshot[name] = raw
    return MappingProxyType(snapshot)


def process_value(value, stdout, stderr, seconds):
    # The original collector embeds its process record in result.json.
    fields(value, ('reason', 'exit_status', 'stdin_complete', 'stdout_bytes', 'stderr_bytes', 'elapsed_seconds'), 'process')
    need(type(value['exit_status']) is int and type(value['stdin_complete']) is bool and
         (value['reason'] is None or type(value['reason']) is str) and
         type(value['elapsed_seconds']) in (int, float) and 0 <= value['elapsed_seconds'] <= seconds,
         'process-framing-or-time-budget')
    for name, raw in (('stdout', stdout), ('stderr', stderr)):
        need(type(value[name + '_bytes']) is int and value[name + '_bytes'] == len(raw), 'process-byte-count')
    return value


def original(attempt, bindings, C, F, D):
    manifest = F.verified_attempt(attempt)
    need(digest(manifest) == bindings['baseline_manifest_sha256'], 'baseline-manifest-pin')
    # Supplement the reviewed original inventory with nlink/permission checks.
    for path in attempt.iterdir():
        read(path, 2097152)
    snapshot = private_snapshot(attempt, manifest, F)
    raw_member = lambda name, limit=65536: F.snapshot_read(snapshot, name, limit)
    parsed_member = lambda name, limit=65536: F.snapshot_load(snapshot, name, limit)
    admission_raw = raw_member('admission.json', 16384)
    admission = json.loads(admission_raw, object_pairs_hook=pairs)
    fields(admission, ('schema', 'experiment', 'action', 'admission_id', 'candidate_sha256',
                        'candidate_manifest_sha256', 'deployment_receipt_sha256', 'collector_sha256',
                        'custodian_role', 'custody_handoff_sha256', 'custody_exclusive',
                        'physical_selection_confirmed', 'no_other_device_operations', 'observation_budget'), 'baseline-admission')
    need(type(admission['schema']) is int and admission['schema'] == 1 and
         admission['experiment'] == 'a53-authenticated-baseline' and admission['action'] == 'first-baseline-observation' and
         admission['admission_id'] == bindings['admission_id'] == attempt.name, 'baseline-admission-scope')
    need(admission['candidate_sha256'] == bindings['candidate_sha256'] and
         admission['candidate_manifest_sha256'] == bindings['candidate_manifest_sha256'] and
         admission['collector_sha256'] == digest(safe_read(REPO / BASELINE / 'collect-baseline.py', 131072)), 'baseline-admission-binding')
    need(valid_hash(admission['deployment_receipt_sha256']) and valid_hash(admission['custody_handoff_sha256']) and
         type(admission['custodian_role']) is str and re.fullmatch(r'[A-Za-z][A-Za-z0-9 _-]{0,63}', admission['custodian_role']) and
         all(admission[k] is True for k in ('custody_exclusive', 'physical_selection_confirmed', 'no_other_device_operations')) and
         type(admission['observation_budget']) is int and admission['observation_budget'] == 1, 'baseline-custody-budget')
    candidate_raw = raw_member('candidate.json', 2097152)
    need(digest(candidate_raw) == bindings['candidate_manifest_sha256'], 'candidate-manifest-pin')
    candidate = json.loads(candidate_raw, object_pairs_hook=pairs)
    need(type(candidate.get('schema')) is int and candidate['schema'] == 1 and
         candidate.get('experiment') == 'a53-authenticated-baseline' and candidate.get('secret_bearing') is True,
         'candidate-scope')
    need(candidate['files']['boot.img'] == bindings['candidate_sha256'], 'candidate-boot-binding')
    for key in ('boot.img', 'boot2-padded.img', 'kernel.config'):
        need(valid_hash(candidate['files'][key]), 'candidate-file-hash')
    need(valid_hash(candidate['known_hosts_sha256']), 'candidate-host-pin')
    for member in C.MEMBERS.values():
        item = candidate['members'][member]
        need(valid_hash(item['sha256']) and type(item['size']) is int and 0 < item['size'] <= 16777216 and
             type(item['mode']) is str and stat.S_ISREG(int(item['mode'], 8)), 'candidate-member-record')
    need(candidate['members']['etc/gemini-us.bkeymap']['sha256'] == C.MAP_SHA, 'candidate-map')
    deployment = raw_member('deployment-summary.txt', 16384)
    need(digest(deployment) == admission['deployment_receipt_sha256'], 'deployment-binding')
    old = D.receipt(deployment.decode('ascii'), candidate['files']['boot2-padded.img'], digest(candidate_raw))
    prepared = {'candidate': candidate, 'candidate_raw': candidate_raw, 'admission': admission,
                'admission_raw': admission_raw, 'deployment_raw': deployment, 'recovery_id': old}
    script = C.remote_script(prepared)
    need(raw_member('remote-observe.sh') == script, 'original-command-drift')
    base = {'candidate_sha256': bindings['candidate_sha256'], 'remote_script_sha256': digest(script),
            'outer_timeout_seconds': C.TOTAL_SECONDS, 'stdout_limit_bytes': C.STDOUT_LIMIT, 'stderr_limit_bytes': C.STDERR_LIMIT}
    claim = {**base, 'budget': 'consumed', 'ssh_attempts_max': 1, 'admission_id': admission['admission_id'],
             'admission_sha256': digest(admission_raw), 'deployment_receipt_sha256': digest(deployment),
             'candidate_manifest_sha256': digest(candidate_raw),
             'deployment_parser_sha256': digest(safe_read(REPO / BASELINE / 'deployment_receipt.py')),
             'historical_sources': {str(p.relative_to(C.REPO)): d for p, d in C.SOURCE_PINS.items()}}
    need(encoded(parsed_member('claim.json')) == encoded(claim), 'original-claim-drift')
    stored_raw = raw_member('result.json')
    stored = json.loads(stored_raw, object_pairs_hook=pairs)
    out, err = raw_member('stdout.txt', C.STDOUT_LIMIT), raw_member('stderr.txt', C.STDERR_LIMIT)
    proc = process_value(stored['process'], out, err, C.TOTAL_SECONDS)
    result = C.classify_capture(prepared, out, err, proc)
    need(result['classification'] == 'baseline-observation-only-pass' and
         encoded(stored) == encoded({**base, **result, 'process': proc}), 'original-observation-not-independent-pass')
    return {'attempt': attempt, 'manifest': manifest, 'prepared': prepared, 'baseline': result,
            'baseline_result_sha256': digest(stored_raw)}


def finish_admission(directory, action, context, pins, F, snapshot):
    raw = F.snapshot_read(snapshot, 'admission.json', 16384)
    value = json.loads(raw, object_pairs_hook=pairs)
    fields(value, ('schema', 'experiment', 'action', 'baseline_admission_id', 'baseline_manifest_sha256',
                    'candidate_manifest_sha256', 'finish_source_sha256', 'steps_source_sha256',
                    'custodian_role', 'custody_handoff_sha256', 'custody_exclusive', 'no_other_device_operations',
                    'action_budgets', 'owner_console_accepted', 'physical_recovery_confirmed',
                    'known_good_known_hosts_sha256', *F.PRIOR_FIELDS.values(),
                    'recovery_mode', 'emergency_reason', 'acknowledge_unique_ram_loss'), 'phase-admission')
    need(type(value['schema']) is int and value['schema'] == 1 and
         value['experiment'] == 'a53-authenticated-baseline' and value['action'] == action, 'phase-scope')
    need(value['baseline_admission_id'] == context['attempt'].name and
         value['baseline_manifest_sha256'] == digest(context['manifest']) and
         value['candidate_manifest_sha256'] == digest(context['prepared']['candidate_raw']) and
         value['finish_source_sha256'] == digest(safe_read(REPO / BASELINE / 'finish-baseline.py', 131072)) and
         value['steps_source_sha256'] == digest(safe_read(REPO / BASELINE / 'session_steps.py', 131072)), 'phase-source-or-baseline-drift')
    need(valid_hash(value['custody_handoff_sha256']) and type(value['custodian_role']) is str and
         re.fullmatch(r'[A-Za-z][A-Za-z0-9 _-]{0,63}', value['custodian_role']) and
         value['custody_exclusive'] is True and value['no_other_device_operations'] is True, 'phase-custody')
    need(encoded(value['action_budgets']) == encoded(F.STEPS[action]) and
         type(value['owner_console_accepted']) is bool and type(value['physical_recovery_confirmed']) is bool,
         'phase-budgets-or-owner-types')
    if action == 'confirm-recovery':
        need(value['physical_recovery_confirmed'] is True and value['owner_console_accepted'] is True and
             valid_hash(value['known_good_known_hosts_sha256']), 'recovery-owner-and-host-pin')
        need(all(value[field] == pins[phase] for phase, field in F.PRIOR_FIELDS.items()), 'confirmation-prior-manifests')
    else:
        need(value['known_good_known_hosts_sha256'] is None and value['physical_recovery_confirmed'] is False and
             value['auth_checks_manifest_sha256'] is None and value['native_request_manifest_sha256'] is None,
             'nonconfirm-recovery-fields')
        need(value['log_export_manifest_sha256'] == (pins['preserve-log'] if action == 'request-recovery' else None),
             'recovery-preservation-manifest')
    if action == 'request-recovery':
        need(value['recovery_mode'] == 'ordinary' and value['emergency_reason'] is None and
             value['acknowledge_unique_ram_loss'] is None, 'emergency-chain-not-baseline-acceptance')
    else:
        need(all(value[field] is None for field in ('recovery_mode', 'emergency_reason', 'acknowledge_unique_ram_loss')),
             'unexpected-emergency-fields')
    result = {**context, 'admission': value, 'admission_raw': raw}
    need(encoded(F.snapshot_load(snapshot, 'claim.json')) == encoded(F.phase_claim(result)), 'phase-claim-drift')
    return result


def confirm_inventory(directory, pin, F):
    """The reviewed finish verifier intentionally handles prior phases only."""
    private_dir(directory)
    child = directory / 'known-good-probe'
    private_dir(child)
    need({p.name for p in directory.iterdir()} == {'admission.json', 'claim.json', 'result.json', 'SHA256SUMS', 'known-good-probe'} and
         {p.name for p in child.iterdir()} == {'command.sh', 'process.json', 'stdout.txt', 'stderr.txt'}, 'confirm-inventory')
    wanted = {'admission.json', 'claim.json', 'result.json'} | {'known-good-probe/' + name for name in
             ('command.sh', 'process.json', 'stdout.txt', 'stderr.txt')}
    raw = read(directory / 'SHA256SUMS', 16384)
    need(digest(raw) == pin, 'confirm-manifest-pin')
    seen = set()
    for line in raw.decode('ascii').splitlines():
        match = re.fullmatch(r'([0-9a-f]{64})  ([A-Za-z0-9_./-]+)', line)
        need(match is not None, 'confirm-manifest-framing')
        value, name = match.groups()
        need(name in wanted and name not in seen and digest(read(directory / name, 131072)) == value,
             'confirm-member-binding')
        seen.add(name)
    need(seen == wanted, 'confirm-manifest-inventory')
    return private_snapshot(directory, raw, F)


def verify(evidence_root, bindings):
    """Return acceptance only after all raw phases and final recovery reparse.

    evidence_root contains attempts/<UUID> and sessions/<UUID>. It may be an
    offline copy; all required files must be private, single-link regular files.
    Bindings must come from the reviewed caller, never from the archive itself.
    """
    fields(bindings, ('admission_id', 'candidate_sha256', 'candidate_manifest_sha256',
                       'baseline_manifest_sha256', 'confirmation_manifest_sha256'), 'aggregate-bindings')
    need(type(bindings['admission_id']) is str and UUID.fullmatch(bindings['admission_id']), 'aggregate-admission-id')
    need(all(valid_hash(bindings[key]) for key in bindings if key != 'admission_id'), 'aggregate-hash-binding')
    root = Path(evidence_root).absolute()
    for part in (root, *root.parents):
        need(not part.is_symlink(), 'aggregate-symlink-root')
    C, F, D = tools()
    attempt = root / 'attempts' / bindings['admission_id']
    sessions = root / 'sessions' / bindings['admission_id']
    private_dir(sessions)
    need({p.name for p in sessions.iterdir()} == set(F.STEPS), 'session-inventory')
    context = original(attempt, bindings, C, F, D)
    confirmation = sessions / 'confirm-recovery'
    confirmation_snapshot = confirm_inventory(confirmation, bindings['confirmation_manifest_sha256'], F)
    confirm = F.snapshot_load(confirmation_snapshot, 'admission.json')
    pins = {phase: confirm[field] for phase, field in F.PRIOR_FIELDS.items()}
    need(all(valid_hash(pin) for pin in pins.values()), 'missing-prior-manifest')
    proof = {}
    for action in ('auth-checks', 'preserve-log', 'request-recovery'):
        directory = sessions / action
        F.verify_phase(directory, pins[action], action)
        phase_manifest = read(directory / 'SHA256SUMS', 16384)
        need(digest(phase_manifest) == pins[action], 'phase-snapshot-manifest-pin')
        snapshot = private_snapshot(directory, phase_manifest, F)
        prior = finish_admission(directory, action, context, pins, F, snapshot)
        F.verify_phase_commands(directory, prior, action, snapshot=snapshot)
        # Supplement all reviewed prior file checks with one common privacy rule.
        for parent, _dirs, files in os.walk(directory):
            for name in files:
                read(Path(parent) / name, 4 * 1024 * 1024)
        boot = context['baseline']['boot_id']
        if action == 'auth-checks':
            result = F.recheck_auth(directory, boot, snapshot=snapshot)
        elif action == 'preserve-log':
            result = F.recheck_export(directory, boot, snapshot=snapshot)
            need(result['classification'] == 'complete-log-through-seal' and
                 result['export']['preservation_complete'] is True, 'incomplete-baseline-log')
        else:
            result = F.S['parse_recovery_request'](F.snapshot_read(snapshot, 'native-reboot/stdout.txt', 131072),
                                                  F.snapshot_load(snapshot, 'native-reboot/process.json'), boot)
            prior['preservation_proof'] = proof['preserve-log']
            result.update(F.recovery_context(prior))
        need(encoded(F.snapshot_load(snapshot, 'result.json')) == encoded(result), 'prior-result-not-reparsed')
        item = {'classification': 'verified', 'manifest_sha256': pins[action]}
        if action == 'preserve-log':
            item.update(preservation_complete=True, complete_log=True)
        if action == 'request-recovery':
            item['recovery_mode'] = 'ordinary'
        proof[action] = item
    final_context = finish_admission(confirmation, 'confirm-recovery', context, pins, F, confirmation_snapshot)
    need(F.full_baseline_eligible(final_context, proof), 'baseline-full-eligibility')
    need(F.snapshot_read(confirmation_snapshot, 'known-good-probe/command.sh', 65536) == F.S['GEMIAN_PROBE'], 'changed-gemian-probe')
    out = F.snapshot_read(confirmation_snapshot, 'known-good-probe/stdout.txt', 131072)
    err = F.snapshot_read(confirmation_snapshot, 'known-good-probe/stderr.txt', 16384)
    proc = process_value(F.snapshot_load(confirmation_snapshot, 'known-good-probe/process.json'), out, err, 16)
    result = F.S['parse_gemian'](out, err, proc, context['prepared']['recovery_id'], context['baseline']['boot_id'])
    result['prior_proof'] = proof
    result['baseline_classification'] = 'first-authenticated-baseline-and-recovery-pass'
    confirmation_result_raw = F.snapshot_read(confirmation_snapshot, 'result.json', 65536)
    need(encoded(json.loads(confirmation_result_raw, object_pairs_hook=pairs)) == encoded(result), 'final-result-not-reparsed')
    # Refuse evidence or source mutation during the aggregate read.
    need(F.verified_attempt(attempt) == context['manifest'], 'baseline-changed-during-read')
    for action, pin in pins.items():
        F.verify_phase(sessions / action, pin, action)
    confirm_inventory(confirmation, bindings['confirmation_manifest_sha256'], F)
    sources()
    return {'classification': 'verified-first-authenticated-baseline-and-recovery',
            'candidate_sha256': bindings['candidate_sha256'], 'candidate_manifest_sha256': bindings['candidate_manifest_sha256'],
            'baseline_boot_id': context['baseline']['boot_id'], 'original_known_good_boot_id': context['prepared']['recovery_id'],
            'recovered_boot_id': result['boot_id'], 'baseline_manifest_sha256': bindings['baseline_manifest_sha256'],
            'confirmation_manifest_sha256': bindings['confirmation_manifest_sha256'],
            'baseline_admission_sha256': digest(context['prepared']['admission_raw']),
            'deployment_receipt_sha256': digest(context['prepared']['deployment_raw']),
            'baseline_first_boot_result_sha256': context['baseline_result_sha256'],
            'baseline_recovery_result_sha256': digest(confirmation_result_raw),
            'phase_manifests': pins, 'dependency_scope': 'one-first-baseline-plus-recovery',
            'network_access': 'none', 'dependent_admission': False}
