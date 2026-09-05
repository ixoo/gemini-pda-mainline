#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Separately admitted authentication, RAM-log preservation and recovery steps."""
import argparse
import json
import os
from pathlib import Path
import re
import runpy
import stat
import subprocess

HERE = Path(__file__).resolve().parent
C = runpy.run_path(str(HERE / 'collect-baseline.py'))
S = runpy.run_path(str(HERE / 'session_steps.py'))
REPO = C['REPO']
require, sha, regular = C['require'], C['sha'], C['regular']
STEPS = {'auth-checks': {'rejected_key': 1, 'wrong_host': 1, 'positive_probe': 1},
         'preserve-log': {'log_export': 1},
         'request-recovery': {'native_reboot': 1}, 'confirm-recovery': {'known_good_probe': 1}}
PHASE_LABELS = {'auth-checks': ('rejected-key', 'wrong-host', 'positive-probe'),
                'preserve-log': ('log-export',),
                'request-recovery': ('native-reboot',)}
EXPORT_FILES = ('kmsg.log', 'kmsg.status', 'kmsg.status.partial', 'kmsg-exit')
PRIOR_FIELDS = {'auth-checks': 'auth_checks_manifest_sha256',
                'preserve-log': 'log_export_manifest_sha256',
                'request-recovery': 'native_request_manifest_sha256'}
EMERGENCY_REASONS = {'log-export-unavailable', 'log-preservation-incomplete', 'immediate-safety-stop'}


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def load(path, limit=131072):
    return json.loads(regular(path, limit), object_pairs_hook=C['no_duplicates'])


def verified_snapshot(directory, manifest):
    """Retain bytes that individually match the already pinned manifest.

    Inventory verification alone does not bind a subsequent open of a path.
    Callers must classify this snapshot, never reopen the evidence afterward.
    """
    require(len(manifest) <= 16384, 'snapshot manifest bound')
    result = {}
    for line in manifest.decode('ascii').splitlines():
        match = re.fullmatch(r'([0-9a-f]{64})  ([A-Za-z0-9_./-]+)', line)
        require(match is not None, 'snapshot manifest framing')
        expected, name = match.groups()
        path = Path(name)
        require(not path.is_absolute() and '..' not in path.parts and path.as_posix() == name and
                name not in result and name != 'SHA256SUMS', 'snapshot manifest path/duplicate')
        raw = regular(directory / path, 4 * 1024 * 1024)
        require(sha(raw) == expected, 'snapshot member differs from pinned manifest')
        result[name] = raw
    return result


def snapshot_read(snapshot, name, limit):
    raw = snapshot[name]
    require(len(raw) <= limit, 'snapshot member exceeds parser limit')
    return raw


def snapshot_load(snapshot, name, limit=131072):
    return json.loads(snapshot_read(snapshot, name, limit), object_pairs_hook=C['no_duplicates'])


def phase_reader(directory, snapshot):
    def read(path, limit):
        if snapshot is None:
            return regular(path, limit)
        return snapshot_read(snapshot, path.relative_to(directory).as_posix(), limit)

    def parsed(path, limit=131072):
        return json.loads(read(path, limit), object_pairs_hook=C['no_duplicates'])
    return read, parsed


def verified_attempt(path):
    C['directory'](path)
    raw = regular(path / 'SHA256SUMS', 16384)
    found = set()
    for line in raw.decode().splitlines():
        match = re.fullmatch(r'([0-9a-f]{64})  ([A-Za-z0-9_.-]+)', line)
        require(match is not None, 'attempt checksum framing')
        expected, name = match.groups()
        require(name not in found and name != 'SHA256SUMS' and
                sha(regular(path / name, 2097152)) == expected, 'attempt checksum')
        found.add(name)
    require(found == {'claim.json', 'remote-observe.sh', 'admission.json', 'deployment-summary.txt',
                      'candidate.json', 'stdout.txt', 'stderr.txt', 'result.json'} and
            {p.name for p in path.iterdir()} == found | {'SHA256SUMS'}, 'attempt inventory')
    return raw


def prepare(attempt, admission_path):
    attempt, admission_path = Path(attempt).absolute(), Path(admission_path).absolute()
    require(attempt.parent == REPO / 'artifacts/a53-authenticated/attempts' and
            C['UUID'].fullmatch(attempt.name), 'baseline attempt location')
    C['ignored'](REPO, admission_path)
    manifest = verified_attempt(attempt)
    snapshot = verified_snapshot(attempt, manifest)
    prepared = C['prepare'](REPO, attempt / 'admission.json', attempt / 'deployment-summary.txt')
    require(prepared['admission_raw'] == snapshot['admission.json'] and
            prepared['deployment_raw'] == snapshot['deployment-summary.txt'] and
            prepared['candidate_raw'] == snapshot['candidate.json'], 'prepared inputs differ from pinned snapshot')
    previous = snapshot_load(snapshot, 'result.json')
    baseline = C['classify_capture'](prepared, snapshot_read(snapshot, 'stdout.txt', C['STDOUT_LIMIT']),
                                     snapshot_read(snapshot, 'stderr.txt', C['STDERR_LIMIT']), previous['process'])
    require(baseline['classification'] == previous['classification'] == 'baseline-observation-only-pass',
            'first observation must independently pass; use physical recovery if identity was inconclusive')
    claim = snapshot_load(snapshot, 'claim.json')
    require(claim['candidate_manifest_sha256'] == sha(prepared['candidate_raw']) and
            claim['admission_sha256'] == sha(prepared['admission_raw']) and
            claim['deployment_receipt_sha256'] == sha(prepared['deployment_raw']) and
            snapshot_read(snapshot, 'remote-observe.sh', 65536) == C['remote_script'](prepared), 'baseline claim drift')
    admission_raw = regular(admission_path, 16384)
    admission = json.loads(admission_raw, object_pairs_hook=C['no_duplicates'])
    required = {'schema', 'experiment', 'action', 'baseline_admission_id', 'baseline_manifest_sha256',
                'candidate_manifest_sha256', 'finish_source_sha256', 'steps_source_sha256',
                'custodian_role', 'custody_handoff_sha256', 'custody_exclusive', 'no_other_device_operations',
                'action_budgets', 'owner_console_accepted', 'physical_recovery_confirmed',
                'known_good_known_hosts_sha256', *PRIOR_FIELDS.values(),
                'recovery_mode', 'emergency_reason', 'acknowledge_unique_ram_loss'}
    require(set(admission) == required and type(admission['schema']) is int and admission['schema'] == 1 and
            admission['experiment'] == 'a53-authenticated-baseline' and admission['action'] in STEPS,
            'finish admission inventory/scope')
    require(admission['baseline_admission_id'] == attempt.name == prepared['admission']['admission_id'] and
            admission['baseline_manifest_sha256'] == sha(manifest) and
            admission['candidate_manifest_sha256'] == sha(prepared['candidate_raw']) and
            admission['finish_source_sha256'] == sha(Path(__file__).read_bytes()) and
            admission['steps_source_sha256'] == sha((HERE / 'session_steps.py').read_bytes()), 'finish source/evidence binding')
    require(C['SHA'].fullmatch(admission['custody_handoff_sha256']) and
            re.fullmatch(r'[A-Za-z][A-Za-z0-9 _-]{0,63}', admission['custodian_role']) and
            admission['custody_exclusive'] is True and admission['no_other_device_operations'] is True,
            'finish custody')
    require(admission['action_budgets'] == STEPS[admission['action']] and
            all(type(value) is int for value in admission['action_budgets'].values()), 'finish budgets')
    require(type(admission['owner_console_accepted']) is bool and type(admission['physical_recovery_confirmed']) is bool,
            'owner observations')
    if admission['action'] == 'confirm-recovery':
        require(admission['physical_recovery_confirmed'] is True and
                C['SHA'].fullmatch(admission['known_good_known_hosts_sha256']), 'physical recovery/pin unconfirmed')
        for field in PRIOR_FIELDS.values():
            require(admission[field] is None or C['SHA'].fullmatch(admission[field]), 'prior phase manifest pin')
        known = REPO / 'artifacts/credentials/a53-recovery-known_hosts'
        require(sha(regular(known, 16384)) == admission['known_good_known_hosts_sha256'], 'known-good host pin')
        text = regular(known, 16384).decode('ascii').splitlines()
        require(len(text) == 1 and text[0].split()[0] == '192.168.1.50', 'known-good target pin')
        regular(REPO / 'artifacts/credentials/gemini_ed25519', 16384)
    else:
        require(admission['known_good_known_hosts_sha256'] is None and
                admission['physical_recovery_confirmed'] is False and admission['auth_checks_manifest_sha256'] is None and
                admission['native_request_manifest_sha256'] is None, 'unexpected recovery fields')
        pin = admission['log_export_manifest_sha256']
        require((admission['action'] == 'request-recovery' and
                 (pin is None or isinstance(pin, str) and C['SHA'].fullmatch(pin))) or pin is None,
                'unexpected log export pin')
    if admission['action'] == 'request-recovery':
        require(admission['recovery_mode'] in ('ordinary', 'emergency'), 'explicit recovery mode required')
        if admission['recovery_mode'] == 'emergency':
            require(admission['emergency_reason'] in EMERGENCY_REASONS and
                    admission['acknowledge_unique_ram_loss'] is True, 'emergency reason/RAM loss acknowledgement')
        else:
            require(admission['log_export_manifest_sha256'] is not None and
                    admission['emergency_reason'] is None and admission['acknowledge_unique_ram_loss'] is None,
                    'ordinary recovery requires preserved-log pin and null emergency fields')
    else:
        require(all(admission[field] is None for field in
                    ('recovery_mode', 'emergency_reason', 'acknowledge_unique_ram_loss')), 'unexpected emergency fields')
    context = {'prepared': prepared, 'baseline': baseline, 'attempt': attempt, 'manifest': manifest,
               'admission': admission, 'admission_raw': admission_raw}
    if admission['action'] == 'confirm-recovery':
        # This classification happens before creating the consumed-budget
        # directory. Missing proof permits only the independent recovery probe.
        context['prior_proof'] = classify_prior_phases(context)
    elif admission['action'] == 'request-recovery':
        context['preservation_proof'] = recovery_preservation(context)
    return context


def invoke(context, directory, label, command, script, timeout, stdout_limit=131072):
    child = directory / label
    child.mkdir(mode=0o700)
    C['write_new'](child / 'command.sh', script)
    process = C['run_once'](command, script, child, timeout, stdout_limit=stdout_limit, stderr_limit=16384)
    C['write_new'](child / 'process.json', json_bytes(process))
    return regular(child / 'stdout.txt', stdout_limit), regular(child / 'stderr.txt', 16384), process


def authenticated_command(context):
    prepared = context['prepared']
    require(sha(regular(prepared['keys'] / 'known_hosts', 8192)) ==
            prepared['candidate']['known_hosts_sha256'], 'SSH host pin changed')
    return C['ssh_command'](prepared['keys'])


def auth_checks(context, directory):
    prepared, boot = context['prepared'], context['baseline']['boot_id']
    # Disposable keys are generated locally and removed on success/failure.
    transient = directory / '.negative-keys'
    transient.mkdir(mode=0o700)
    key = transient / 'wrong'
    try:
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', '', '-f', str(key)],
                       check=True, timeout=10, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        (transient / 'wrong.pub').chmod(0o600)
        public = regular(transient / 'wrong.pub', 8192).split()
        require(public[:1] == [b'ssh-ed25519'], 'negative fixture key')
        wrong_host = transient / 'known_hosts'
        C['write_new'](wrong_host, b'10.15.19.82 ' + b' '.join(public[:2]) + b'\n')
        probe = S['probe_script'](prepared['candidate'], boot)
        for label in ('rejected-key', 'wrong-host'):
            command = authenticated_command(context)
            if label == 'rejected-key':
                command[command.index('-i') + 1] = str(key)
                diagnostic = b'Permission denied (publickey)'
            else:
                index = next(i for i, item in enumerate(command) if item.startswith('UserKnownHostsFile='))
                command[index] = 'UserKnownHostsFile=' + str(wrong_host)
                diagnostic = b'Host key verification failed'
            out, err, process = invoke(context, directory, label, command, probe, 15)
            require(not out and process['exit_status'] == 255 and process['reason'] in (None, 'stdin-closed') and
                    diagnostic in err, label + ' did not prove the expected refusal')
        # A fresh positive command is necessary: server loss cannot count as a negative test.
        out, err, process = invoke(context, directory, 'positive-probe', authenticated_command(context), probe, 15)
        require(not err and process['exit_status'] == 0 and process['reason'] is None and process['stdin_complete'] and
                out == ('authenticated_boot_id=' + boot + '\n').encode(), 'post-negative authenticated identity')
    finally:
        # Only the exact locally created disposable names are removed.
        for name in ('wrong', 'wrong.pub', 'known_hosts'):
            path = transient / name
            if path.exists() or path.is_symlink():
                path.unlink()
        transient.rmdir()
    return {'classification': 'authentication-checks-pass', 'boot_id': boot,
            'negative_auth': 'key-and-host-refused-plus-fresh-authenticated-probe'}


def preserve_log(context, directory):
    boot = context['baseline']['boot_id']
    out, err, process = invoke(context, directory, 'log-export', authenticated_command(context),
                              S['seal_script'](context['prepared']['candidate'], boot), 30,
                              stdout_limit=3 * 1024 * 1024)
    parsed = S['parse_log_export'](out, err, process)
    require(set(parsed['files']) <= set(EXPORT_FILES), 'export file scope')
    # Fixed empty placeholders represent unavailable files only together with
    # the parser's per-file state. The original bounded streams are retained
    # even if framing is truncated or no individual file can be decoded.
    for name in EXPORT_FILES:
        C['write_new'](directory / name, parsed['files'].get(name, b''))
    return {'classification': parsed['result']['classification'], 'boot_id': boot, 'export': parsed['result']}


def known_good_command(context):
    command = C['ssh_command'](context['prepared']['keys'])
    command[command.index('-i') + 1] = str(REPO / 'artifacts/credentials/gemini_ed25519')
    for index, value in enumerate(command):
        if value.startswith('UserKnownHostsFile='):
            command[index] = 'UserKnownHostsFile=' + str(REPO / 'artifacts/credentials/a53-recovery-known_hosts')
    command[-2:] = ['gemini@192.168.1.50', '/bin/sh -s']
    return command



def phase_claim(context):
    admission = context['admission']
    return {'budget': 'consumed', 'action': admission['action'],
            'baseline_admission_id': context['attempt'].name,
            'baseline_manifest_sha256': sha(context['manifest']),
            'candidate_manifest_sha256': sha(context['prepared']['candidate_raw']),
            'phase_admission_sha256': sha(context['admission_raw']),
            'finish_source_sha256': admission['finish_source_sha256'],
            'steps_source_sha256': admission['steps_source_sha256'],
            'action_budgets': STEPS[admission['action']]}


def phase_files(action):
    require(action in PHASE_LABELS, 'unsupported prior phase')
    files = {'admission.json', 'claim.json', 'result.json', 'SHA256SUMS'}
    files.update(label + '/' + name for label in PHASE_LABELS[action]
                 for name in ('command.sh', 'process.json', 'stdout.txt', 'stderr.txt'))
    if action == 'preserve-log':
        files.update(EXPORT_FILES)
    return files


def verify_phase(directory, expected, action):
    require(isinstance(expected, str) and C['SHA'].fullmatch(expected), 'prior phase manifest pin')
    C['directory'](directory)
    wanted = phase_files(action)
    actual, directories = set(), set()
    for parent, dirs, names in os.walk(directory, followlinks=False):
        C['directory'](Path(parent))
        for name in dirs:
            child = Path(parent) / name
            relative = child.relative_to(directory).as_posix()
            require(relative in PHASE_LABELS[action], 'unexpected phase directory')
            C['directory'](child)
            directories.add(relative)
        for name in names:
            child = Path(parent) / name
            relative = child.relative_to(directory).as_posix()
            info = child.lstat()
            require(relative in wanted and stat.S_ISREG(info.st_mode) and info.st_nlink == 1,
                    'phase file inventory/type/links')
            actual.add(relative)
    require(actual == wanted and directories == set(PHASE_LABELS[action]), 'complete phase inventory')
    raw = regular(directory / 'SHA256SUMS', 16384)
    require(sha(raw) == expected, 'prior phase manifest pin')
    seen = set()
    for line in raw.decode().splitlines():
        match = re.fullmatch(r'([0-9a-f]{64})  ([A-Za-z0-9_./-]+)', line)
        require(match is not None, 'phase manifest framing')
        digest, relative = match.groups()
        path = Path(relative)
        require(relative in wanted - {'SHA256SUMS'} and path.as_posix() == relative and relative not in seen and
                sha(regular(directory / path, 4 * 1024 * 1024)) == digest, 'phase member hash/path')
        seen.add(relative)
    require(wanted == seen | {'SHA256SUMS'}, 'phase manifest inventory')


def verify_phase_commands(directory, context, action, *, snapshot=None):
    read, parsed = phase_reader(directory, snapshot)
    candidate, boot = context['prepared']['candidate'], context['baseline']['boot_id']
    probe = S['probe_script'](candidate, boot)
    commands = {'rejected-key': probe, 'wrong-host': probe, 'positive-probe': probe,
                'log-export': S['seal_script'](candidate, boot),
                'native-reboot': S['recovery_script'](candidate, boot)}
    for label in PHASE_LABELS[action]:
        child = directory / label
        require(read(child / 'command.sh', 65536) == commands[label], 'prior fixed command changed')
        process = parsed(child / 'process.json')
        require(set(process) == {'exit_status', 'reason', 'stdin_complete', 'stdout_bytes', 'stderr_bytes', 'elapsed_seconds'},
                'prior process inventory')
        require(type(process['exit_status']) is int and type(process['stdin_complete']) is bool and
                (process['reason'] is None or isinstance(process['reason'], str)) and
                type(process['elapsed_seconds']) in (int, float) and
                0 <= process['elapsed_seconds'] <= (31 if label == 'log-export' else 16), 'prior process framing/deadline')
        for name, limit in (('stdout', 3 * 1024 * 1024 if label == 'log-export' else 131072), ('stderr', 16384)):
            require(type(process[name + '_bytes']) is int and
                    process[name + '_bytes'] == len(read(child / (name + '.txt'), limit)), 'prior stream count')


def verify_prior_phase(context, action, expected):
    require(action in PHASE_LABELS, 'prior phase scope')
    directory = REPO / 'artifacts/a53-authenticated/sessions' / context['attempt'].name / action
    verify_phase(directory, expected, action)
    manifest = regular(directory / 'SHA256SUMS', 16384)
    require(sha(manifest) == expected, 'prior snapshot manifest pin')
    snapshot = verified_snapshot(directory, manifest)
    # Only request-recovery depends on preserve-log; auth/export have no
    # predecessors. The exact action check rejects recursive confirm claims.
    # Prepare independently rechecks the exact original attempt,
    # source identities, candidate, custody and this phase's admitted budgets.
    require(snapshot_load(snapshot, 'admission.json')['action'] == action, 'prior phase action binding')
    prior = prepare(context['attempt'], directory / 'admission.json')
    require(prior['admission_raw'] == snapshot['admission.json'] and
            prior['manifest'] == context['manifest'] and
            prior['prepared']['candidate_raw'] == context['prepared']['candidate_raw'] and
            prior['baseline']['boot_id'] == context['baseline']['boot_id'], 'prior baseline/candidate binding')
    require(json_bytes(snapshot_load(snapshot, 'claim.json')) == json_bytes(phase_claim(prior)), 'prior phase claim binding')
    verify_phase_commands(directory, prior, action, snapshot=snapshot)
    boot = prior['baseline']['boot_id']
    if action == 'auth-checks':
        result = recheck_auth(directory, boot, snapshot=snapshot)
    elif action == 'preserve-log':
        result = recheck_export(directory, boot, snapshot=snapshot)
    else:
        result = S['parse_recovery_request'](snapshot_read(snapshot, 'native-reboot/stdout.txt', 131072),
                                              snapshot_load(snapshot, 'native-reboot/process.json'), boot)
        result.update(recovery_context(prior))
    require(json_bytes(snapshot_load(snapshot, 'result.json')) == json_bytes(result), 'prior phase result differs from raw evidence')
    return result


def phase_proof(context, action):
    expected = context['admission'][PRIOR_FIELDS[action]]
    if expected is None:
        return {'classification': 'missing', 'manifest_sha256': None, 'reason': 'no admitted phase manifest'}
    try:
        result = verify_prior_phase(context, action, expected)
        proof = {'classification': 'verified', 'manifest_sha256': expected}
        if action == 'preserve-log':
            proof['preservation_complete'] = result['export']['preservation_complete']
            proof['complete_log'] = result['classification'] == 'complete-log-through-seal'
        if action == 'request-recovery':
            proof['recovery_mode'] = result['recovery_mode']
        return proof
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        return {'classification': 'incomplete', 'manifest_sha256': expected, 'reason': str(error)}


def recovery_preservation(context):
    proof = phase_proof(context, 'preserve-log')
    admission = context['admission']
    if admission['recovery_mode'] == 'ordinary':
        require(proof['classification'] == 'verified' and proof['preservation_complete'] is True,
                'ordinary recovery requires a complete local preservation of all bounded available RAM log evidence')
    elif admission['emergency_reason'] == 'log-export-unavailable':
        require(proof['classification'] != 'verified', 'log export is available; emergency reason does not match')
    elif admission['emergency_reason'] == 'log-preservation-incomplete':
        require(proof['classification'] == 'verified' and proof['preservation_complete'] is False,
                'incomplete preservation emergency requires its verified partial export')
    return proof


def recovery_context(context):
    return {field: context['admission'][field] for field in
            ('recovery_mode', 'emergency_reason', 'acknowledge_unique_ram_loss')} | {
                'preservation_proof': context['preservation_proof']}


def full_baseline_eligible(context, proof):
    return (all(item['classification'] == 'verified' for item in proof.values()) and
            proof['preserve-log']['complete_log'] is True and
            proof['preserve-log']['preservation_complete'] is True and
            proof['request-recovery']['recovery_mode'] == 'ordinary' and
            context['admission']['owner_console_accepted'] is True)


def classify_prior_phases(context):
    return {action: phase_proof(context, action) for action in PRIOR_FIELDS}


def recheck_auth(directory, boot, *, snapshot=None):
    read, parsed = phase_reader(directory, snapshot)
    for label, diagnostic in (('rejected-key', b'Permission denied (publickey)'),
                              ('wrong-host', b'Host key verification failed')):
        child = directory / label
        process = parsed(child / 'process.json')
        require(not read(child / 'stdout.txt', 131072) and diagnostic in read(child / 'stderr.txt', 16384) and
                process['exit_status'] == 255 and process['reason'] in (None, 'stdin-closed'), 'negative auth evidence')
    child = directory / 'positive-probe'
    process = parsed(child / 'process.json')
    require(not read(child / 'stderr.txt', 16384) and process['exit_status'] == 0 and
            process['reason'] is None and process['stdin_complete'] and
            read(child / 'stdout.txt', 131072) == ('authenticated_boot_id=' + boot + '\n').encode(),
            'positive auth evidence')
    return {'classification': 'authentication-checks-pass', 'boot_id': boot,
            'negative_auth': 'key-and-host-refused-plus-fresh-authenticated-probe'}


def recheck_export(directory, boot, *, snapshot=None):
    read, parsed_json = phase_reader(directory, snapshot)
    child = directory / 'log-export'
    parsed = S['parse_log_export'](read(child / 'stdout.txt', 3 * 1024 * 1024),
                                  read(child / 'stderr.txt', 16384), parsed_json(child / 'process.json'))
    require(set(parsed['files']) <= set(EXPORT_FILES), 'export file scope')
    for name in EXPORT_FILES:
        require(read(directory / name, S['LIMIT'] if name == 'kmsg.log' else 8192) ==
                parsed['files'].get(name, b''), 'exported raw evidence differs from captured transport')
    return {'classification': parsed['result']['classification'], 'boot_id': boot, 'export': parsed['result']}


def perform(context, execute=False):
    action = context['admission']['action']
    if not execute:
        result = {'classification': 'dry-run', 'action': action, 'network_access': 'none', 'attempt_created': False,
                  'budgets': STEPS[action], 'physical_admission': 'separate owner/custody decision'}
        if action == 'confirm-recovery':
            result['prior_proof'] = context['prior_proof']
            result['full_baseline_eligible'] = full_baseline_eligible(context, context['prior_proof'])
        elif action == 'request-recovery':
            result.update(recovery_context(context))
        return result
    root = REPO / 'artifacts/a53-authenticated/sessions' / context['attempt'].name
    C['private_root'](root)
    directory = root / action
    directory.mkdir(mode=0o700)  # One immutable attempt per phase, including interrupted failures.
    C['write_new'](directory / 'admission.json', context['admission_raw'])
    C['write_new'](directory / 'claim.json', json_bytes(phase_claim(context)))
    sync_directory(directory)
    sync_directory(root)
    sync_directory(root.parent)
    sync_directory(root.parent.parent)
    boot = context['baseline']['boot_id']
    try:
        if action == 'auth-checks':
            result = auth_checks(context, directory)
        elif action == 'preserve-log':
            result = preserve_log(context, directory)
        elif action == 'request-recovery':
            # Recheck local preservation immediately before the separately
            # admitted request. A timeout never triggers another connection.
            require(recovery_preservation(context) == context['preservation_proof'],
                    'preservation evidence changed after recovery preparation')
            out, _err, process = invoke(context, directory, 'native-reboot', authenticated_command(context),
                                       S['recovery_script'](context['prepared']['candidate'], boot), 15)
            result = S['parse_recovery_request'](out, process, boot)
            result.update(recovery_context(context))
        else:
            out, err, process = invoke(context, directory, 'known-good-probe', known_good_command(context),
                                      S['GEMIAN_PROBE'], 15)
            result = S['parse_gemian'](out, err, process, context['prepared']['recovery_id'], boot)
            # Recheck after the probe, but an incomplete prepared proof can
            # never become full admission by repairing files during execution.
            proof = classify_prior_phases(context)
            result['prior_proof'] = proof
            if proof == context['prior_proof'] and full_baseline_eligible(context, proof):
                result['baseline_classification'] = 'first-authenticated-baseline-and-recovery-pass'
            else:
                result['baseline_classification'] = 'recovered-with-baseline-incomplete'
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        result = {'classification': 'inconclusive', 'reason': str(error), 'budget': 'consumed',
                  'next_action': 'review evidence; no repeat; physical recovery if identity or USB is unavailable'}
    C['write_new'](directory / 'result.json', json_bytes(result))
    manifest = ''.join(sha(regular(path, 4 * 1024 * 1024)) + '  ' + path.relative_to(directory).as_posix() + '\n'
                       for path in sorted(directory.rglob('*')) if path.is_file())
    C['write_new'](directory / 'SHA256SUMS', manifest.encode())
    # Persist file names as well as fsynced contents before any later phase
    # can rely on this export to authorize destruction of the RAM original.
    for child in directory.iterdir():
        if child.is_dir():
            sync_directory(child)
    sync_directory(directory)
    sync_directory(root)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-attempt', type=Path, required=True)
    parser.add_argument('--admission', type=Path, required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    try:
        result = perform(prepare(args.baseline_attempt, args.admission), args.execute)
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        result = {'classification': 'refused', 'reason': str(error)}
    print(json.dumps(result, sort_keys=True))
    return 2 if result['classification'] in ('refused', 'inconclusive', 'log-export-inconclusive') else 0


if __name__ == '__main__':
    raise SystemExit(main())
