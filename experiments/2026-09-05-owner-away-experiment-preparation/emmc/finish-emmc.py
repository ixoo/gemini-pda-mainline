#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""PREPARING: separately admitted eMMC log preservation and attributable recovery."""
import argparse
import json
import math
import os
from pathlib import Path
import re
import runpy
import stat
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
L = runpy.run_path(str(HERE / 'collect-emmc.py'))
C, F, S = L['C'], L['F'], L['S']
REPO, EXPERIMENT = L['REPO'], L['EXPERIMENT']
require, sha, regular, load, json_bytes = (L[name] for name in ('require', 'sha', 'regular', 'load', 'json_bytes'))
ROOT = REPO / 'artifacts/a53-authenticated/emmc-readonly/completion'
STEPS = {'preserve-log': {'log_export': 1}, 'request-recovery': {'native_reboot': 1},
         'confirm-recovery': {'known_good_probe': 1}}
LABELS = {'preserve-log': 'log-export', 'request-recovery': 'native-reboot', 'confirm-recovery': 'known-good-probe'}
LIMITS = {'preserve-log': (30, 3 * 1024 * 1024), 'request-recovery': (15, 131072), 'confirm-recovery': (15, 131072)}
ADMISSION_FIELDS = {'schema', 'experiment', 'action', 'observation_admission_id', 'observation_manifest_sha256',
    'candidate_manifest_sha256', 'boot_id', 'source_identity', 'action_budgets', 'custodian_role',
    'custody_handoff_sha256', 'custody_exclusive', 'no_other_device_operations', 'observer_transport_stopped',
    'preservation_manifest_sha256', 'native_request_manifest_sha256', 'known_good_known_hosts_sha256',
    'physical_recovery_confirmed', 'owner_console_accepted', 'recovery_mode', 'emergency_reason',
    'acknowledge_unique_ram_loss'}


def source_identity():
    return {'completion_sha256': sha(Path(__file__).read_bytes()), 'launcher': L['source_identity']()}


def inventory(directory, expected, files, directories):
    """Retain the exact bounded bytes whose hashes match the pinned manifest."""
    C['directory'](directory)
    actual, actual_dirs = set(), set()
    for parent, dirs, names in os.walk(directory, followlinks=False):
        for name in dirs:
            path = Path(parent) / name
            relative = path.relative_to(directory).as_posix()
            require(relative in directories, 'unexpected evidence directory')
            C['directory'](path)
            actual_dirs.add(relative)
        for name in names:
            path = Path(parent) / name
            relative = path.relative_to(directory).as_posix()
            info = path.lstat()
            require(relative in files and stat.S_ISREG(info.st_mode) and info.st_nlink == 1,
                    'evidence file inventory/type/links')
            actual.add(relative)
    require(actual == files and actual_dirs == directories, 'evidence inventory')
    manifest = regular(directory / 'SHA256SUMS', 16384)
    require(sha(manifest) == expected, 'evidence manifest identity')
    seen, snapshot = set(), {'SHA256SUMS': manifest}
    for line in manifest.decode('ascii').splitlines():
        match = re.fullmatch(r'([0-9a-f]{64})  ([A-Za-z0-9_./-]+)', line)
        require(match is not None, 'evidence manifest framing')
        digest, name = match.groups()
        require(name in files - {'SHA256SUMS'} and name not in seen, 'evidence member inventory')
        raw = regular(directory / name, 4 * 1024 * 1024)
        require(sha(raw) == digest, 'evidence member hash')
        snapshot[name] = raw
        seen.add(name)
    require(seen == files - {'SHA256SUMS'}, 'evidence manifest inventory')
    return snapshot


def snapshot_bytes(snapshot, name, limit):
    raw = snapshot[name]
    require(len(raw) <= limit, 'snapshot member bound')
    return raw


def snapshot_json(snapshot, name, limit=131072):
    return json.loads(snapshot_bytes(snapshot, name, limit), object_pairs_hook=L['unique'])


def process_metadata(out, err, process, seconds, limit):
    require(set(process) == {'exit_status', 'reason', 'stdin_complete', 'stdout_bytes', 'stderr_bytes', 'elapsed_seconds'},
            'process field inventory')
    require((process['exit_status'] is None or type(process['exit_status']) is int) and
            type(process['stdin_complete']) is bool and
            (process['reason'] is None or isinstance(process['reason'], str)), 'process state types')
    elapsed = process['elapsed_seconds']
    require(type(elapsed) in (int, float) and math.isfinite(elapsed) and 0 <= elapsed <= seconds + 1,
            'process elapsed bound')
    for name, value, cap in (('stdout', out, limit), ('stderr', err, 16384)):
        require(type(process[name + '_bytes']) is int and process[name + '_bytes'] == len(value) <= cap,
                'process captured count/bound')


def observation(expected):
    root = L['ATTEMPT_ROOT']
    context = L['prepare'](root / 'admission.json')
    # Handled failures produce this sealed manifest; absence never authorizes a
    # guessed boot identity or an automatic recovery from a hard interruption.
    directories = {name for name in ('pre', 'read', 'post') if (root / name).exists()}
    require(directories in ({'pre'}, {'pre', 'read'}, {'pre', 'read', 'post'}), 'observation phase order')
    files = {'claim.json', 'admission.json', 'result.json', 'SHA256SUMS'}
    for phase in directories:
        files.update(phase + '/' + name for name in ('claim.json', 'command.sh'))
        for name in ('process.json', 'stdout.txt', 'stderr.txt'):
            if (root / phase / name).exists(): files.add(phase + '/' + name)
    snapshot = inventory(root, expected, files, directories)
    require(context['admission_raw'] == snapshot_bytes(snapshot, 'admission.json', 16384),
            'observation preparation differs from pinned admission')
    require(snapshot_json(snapshot, 'claim.json') == L['session_claim'](context), 'observation claim drift')
    passed, boot, stopped, observations = [], None, False, {}
    for phase in ('pre', 'read', 'post'):
        if phase not in directories: break
        require(not stopped, 'observation continued after a failed phase')
        script = L['script_for'](context, phase, boot)
        prefix = phase + '/'
        require(snapshot_bytes(snapshot, prefix + 'command.sh', 65536) == script and
                snapshot_json(snapshot, prefix + 'claim.json') == L['phase_claim'](context, phase, boot, script),
                'phase command/claim drift')
        names = {name.removeprefix(prefix) for name in snapshot if name.startswith(prefix)}
        if not {'process.json', 'stdout.txt', 'stderr.txt'} <= names:
            stopped = True
            continue
        seconds, limit = L['PHASES'][phase]
        out, err, process = (snapshot_bytes(snapshot, prefix + 'stdout.txt', limit),
                             snapshot_bytes(snapshot, prefix + 'stderr.txt', 16384),
                             snapshot_json(snapshot, prefix + 'process.json'))
        process_metadata(out, err, process, seconds, limit)
        try:
            value = L['classify_phase'](context, phase, out, err, process, boot)
        except L['ObservationRejected'] as error:
            observations[phase] = error.observation
            stopped = True
            continue
        except ValueError:
            stopped = True
            continue
        passed.append(phase)
        observations[phase] = value
        if phase == 'pre': boot = value['boot_id']
    require(boot is not None, 'attributable preflight required; no remote completion admission')
    full = passed == ['pre', 'read', 'post'] and not stopped
    saved = snapshot_json(snapshot, 'result.json')
    require(saved.get('boot_id') == boot and saved.get('phases') == observations, 'observation result differs from raw evidence')
    if full:
        require(saved == {'classification': 'read-serviceability-only-pass', 'boot_id': boot,
            'phases': observations, 'readiness': 'preparing',
            'remaining': ['independent-log-preservation-and-continuity', 'changed-ID-known-good-recovery']},
            'observation success framing')
    else:
        classification = 'fail' if any(item['classification'] in ('fail', 'baseline-observation-rejected')
                                      for item in observations.values()) else 'inconclusive'
        require(set(saved) == {'classification', 'reason', 'boot_id', 'phases', 'budget', 'further_observations', 'next_action'} and
                saved['classification'] == classification and saved['budget'] == 'consumed' and
                saved['further_observations'] == 'none' and isinstance(saved['reason'], str) and saved['reason'],
                'failed observation framing')
    return {'context': context, 'manifest_sha256': expected, 'boot_id': boot, 'read_serviceability_pass': full,
            'classification': saved['classification']}


def target_context(context):
    return {'prepared': context['observation']['context']['dependency']['prepared'],
            'baseline': {'boot_id': context['observation']['boot_id']}}


def script(context):
    action = context['admission']['action']
    if action == 'confirm-recovery': return S['GEMIAN_PROBE']
    target = target_context(context)
    generator = S['seal_script'] if action == 'preserve-log' else S['recovery_script']
    return generator(target['prepared']['candidate'], target['baseline']['boot_id'])


def phase_claim(context):
    value = context['admission']
    return {'budget': 'consumed', 'action': value['action'], 'phase_admission_sha256': sha(context['admission_raw']),
            'observation_manifest_sha256': value['observation_manifest_sha256'],
            'candidate_manifest_sha256': value['candidate_manifest_sha256'], 'boot_id': value['boot_id'],
            'source_identity': value['source_identity'], 'action_budgets': STEPS[value['action']]}


def log_errors(log):
    # Reuse the exact observer's one reviewed POSIX-compatible byte pattern.
    source = (EXPERIMENT / 'emmc/observe.sh').read_bytes()
    patterns = re.findall(rb"^ERROR_PATTERN='([^']+)'$", source, re.MULTILINE)
    require(len(patterns) == 1, 'observer error predicate boundary changed')
    return sum(re.search(patterns[0], line, re.IGNORECASE) is not None for line in log.splitlines())


def classify_phase(context, out, err, process):
    action = context['admission']['action']
    seconds, limit = LIMITS[action]
    process_metadata(out, err, process, seconds, limit)
    boot = context['observation']['boot_id']
    if action == 'preserve-log':
        parsed = S['parse_log_export'](out, err, process)
        errors = log_errors(parsed['files']['kmsg.log']) if 'kmsg.log' in parsed['files'] else None
        result = {'classification': parsed['result']['classification'], 'boot_id': boot,
                  'export': parsed['result'], 'controller_error_count': errors}
        return result, {name: parsed['files'].get(name, b'') for name in F['EXPORT_FILES']}
    if action == 'request-recovery':
        result = S['parse_recovery_request'](out, process, boot)
        result.update({name: context['admission'][name] for name in
                       ('recovery_mode', 'emergency_reason', 'acknowledge_unique_ram_loss')})
        result['preservation_proof'] = context['proof']['preserve-log']
        return result, {}
    dependency = context['observation']['context']['dependency']
    L['process_ok'](out, err, process, seconds, limit)
    result = S['parse_gemian'](out, err, process, dependency['recovered_boot'], boot)
    require(result['boot_id'] not in (dependency['first_boot'], dependency['prepared']['recovery_id']),
            'known-good probe reuses an earlier session boot')
    proof = context['proof']
    complete = (context['observation']['read_serviceability_pass'] and
                proof['preserve-log']['classification'] == proof['request-recovery']['classification'] == 'verified' and
                proof['preserve-log'].get('preservation_complete') is True and
                proof['preserve-log'].get('complete_log') is True and
                proof['preserve-log'].get('controller_error_count') == 0 and
                proof['request-recovery'].get('recovery_mode') == 'ordinary' and
                context['admission']['owner_console_accepted'] is True)
    result.update(prior_proof=proof, experiment_classification='one-read-emmc-and-recovery-pass' if complete else
                  'recovered-with-emmc-incomplete', boot_scope=boot, requested_bytes=16777216, read_attempts=1)
    return result, {}


def verify_prior(context, action, expected):
    directory = ROOT / action
    F['verify_phase'](directory, expected, action)
    snapshot = inventory(directory, expected, F['phase_files'](action), {LABELS[action]})
    require(snapshot_json(snapshot, 'admission.json', 16384)['action'] == action, 'prior phase action')
    prior = prepare_admission(snapshot_bytes(snapshot, 'admission.json', 16384))
    require(prior['observation'] == context['observation'] and
            snapshot_json(snapshot, 'claim.json') == phase_claim(prior), 'prior phase observation/claim binding')
    prefix = LABELS[action] + '/'
    require(snapshot_bytes(snapshot, prefix + 'command.sh', 65536) == script(prior), 'prior fixed command drift')
    result, files = classify_phase(prior, snapshot_bytes(snapshot, prefix + 'stdout.txt', LIMITS[action][1]),
                                   snapshot_bytes(snapshot, prefix + 'stderr.txt', 16384),
                                   snapshot_json(snapshot, prefix + 'process.json'))
    require(snapshot_json(snapshot, 'result.json') == result, 'prior result differs from raw evidence')
    for name, raw in files.items():
        require(snapshot_bytes(snapshot, name, S['EXPORT_FILES'][name]) == raw, 'preserved file differs from raw export')
    return result


def phase_proof(context, action, expected):
    if expected is None: return {'classification': 'missing', 'manifest_sha256': None}
    try:
        result = verify_prior(context, action, expected)
        proof = {'classification': 'verified', 'manifest_sha256': expected}
        if action == 'preserve-log':
            proof.update(preservation_complete=result['export']['preservation_complete'],
                         complete_log=result['classification'] == 'complete-log-through-seal',
                         controller_error_count=result['controller_error_count'])
        else: proof['recovery_mode'] = result['recovery_mode']
        return proof
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        return {'classification': 'incomplete', 'manifest_sha256': expected, 'reason': str(error)}


def proofs(context):
    admission = context['admission']
    if admission['action'] == 'preserve-log': return {}
    result = {'preserve-log': phase_proof(context, 'preserve-log', admission['preservation_manifest_sha256'])}
    if admission['action'] == 'confirm-recovery':
        result['request-recovery'] = phase_proof(context, 'request-recovery', admission['native_request_manifest_sha256'])
    else:
        value = result['preserve-log']
        if admission['recovery_mode'] == 'ordinary':
            require(value['classification'] == 'verified' and value['preservation_complete'] is True,
                    'ordinary recovery requires verified complete local preservation')
        elif admission['emergency_reason'] == 'log-export-unavailable':
            require(value['classification'] != 'verified', 'available export contradicts emergency reason')
        elif admission['emergency_reason'] == 'log-preservation-incomplete':
            require(value['classification'] == 'verified' and value['preservation_complete'] is False,
                    'incomplete-preservation emergency needs verified partial export')
    return result


def prepare(path):
    path = Path(path).absolute()
    C['ignored'](REPO, path)
    return prepare_admission(regular(path, 16384))


def prepare_admission(raw):
    """Validate one admission byte string; prior callers supply a pinned snapshot."""
    require(len(raw) <= 16384, 'admission byte bound')
    admission = json.loads(raw, object_pairs_hook=L['unique'])
    require(set(admission) == ADMISSION_FIELDS and type(admission['schema']) is int and admission['schema'] == 1 and
            admission['experiment'] == 'a53-emmc-readonly' and admission['action'] in STEPS, 'completion admission scope')
    action = admission['action']
    for name in ('observation_admission_id', 'boot_id'):
        require(isinstance(admission[name], str) and C['UUID'].fullmatch(admission[name]), 'completion UUID')
    for name in ('observation_manifest_sha256', 'candidate_manifest_sha256', 'custody_handoff_sha256'):
        require(isinstance(admission[name], str) and C['SHA'].fullmatch(admission[name]), 'completion digest')
    for name in ('preservation_manifest_sha256', 'native_request_manifest_sha256', 'known_good_known_hosts_sha256'):
        require(admission[name] is None or isinstance(admission[name], str) and C['SHA'].fullmatch(admission[name]),
                'optional proof digest')
    require(admission['source_identity'] == source_identity(), 'completion source identity')
    require(admission['action_budgets'] == STEPS[action] and all(type(n) is int for n in admission['action_budgets'].values()),
            'completion action budget')
    require(isinstance(admission['custodian_role'], str) and
            re.fullmatch(r'[A-Za-z][A-Za-z0-9 _-]{0,63}', admission['custodian_role']) and
            all(admission[name] is True for name in ('custody_exclusive', 'no_other_device_operations', 'observer_transport_stopped')),
            'completion custody/transport quiescence')
    require(type(admission['owner_console_accepted']) is bool and type(admission['physical_recovery_confirmed']) is bool,
            'owner observation types')
    if action == 'confirm-recovery':
        require(admission['physical_recovery_confirmed'] is True and admission['known_good_known_hosts_sha256'] is not None,
                'physical recovery and known-good host pin required')
        known = regular(REPO / 'artifacts/credentials/a53-recovery-known_hosts', 16384)
        require(sha(known) == admission['known_good_known_hosts_sha256'] and len(known.decode('ascii').splitlines()) == 1 and
                known.decode('ascii').split()[0] == '192.168.1.50', 'known-good target identity')
        regular(REPO / 'artifacts/credentials/gemini_ed25519', 16384)
    else:
        require(admission['physical_recovery_confirmed'] is False and admission['known_good_known_hosts_sha256'] is None and
                admission['native_request_manifest_sha256'] is None, 'unexpected known-good evidence')
        if action == 'preserve-log': require(admission['preservation_manifest_sha256'] is None, 'preservation has no predecessor')
    if action == 'request-recovery':
        require(admission['recovery_mode'] in ('ordinary', 'emergency'), 'explicit recovery mode required')
        if admission['recovery_mode'] == 'ordinary':
            require(admission['preservation_manifest_sha256'] is not None and admission['emergency_reason'] is None and
                    admission['acknowledge_unique_ram_loss'] is None, 'ordinary recovery proof/fields')
        else:
            require(admission['emergency_reason'] in F['EMERGENCY_REASONS'] and admission['acknowledge_unique_ram_loss'] is True,
                    'emergency reason and RAM-loss acknowledgement required')
    else:
        require(all(admission[name] is None for name in ('recovery_mode', 'emergency_reason', 'acknowledge_unique_ram_loss')),
                'unexpected recovery effect fields')
    observed = observation(admission['observation_manifest_sha256'])
    require(observed['context']['admission']['admission_id'] == admission['observation_admission_id'] and
            observed['boot_id'] == admission['boot_id'] and
            observed['context']['admission']['candidate_manifest_sha256'] == admission['candidate_manifest_sha256'],
            'completion observation/candidate/boot binding')
    context = {'admission': admission, 'admission_raw': raw, 'observation': observed}
    context['proof'] = proofs(context)
    return context


def perform(context, execute=False):
    if execute: L['execution_gate']()
    action = context['admission']['action']
    if not execute:
        return {'classification': 'dry-run', 'readiness': 'preparing', 'network_access': 'none',
                'action': action, 'budgets': STEPS[action], 'prior_proof': context['proof']}
    require(source_identity() == context['admission']['source_identity'] and
            observation(context['admission']['observation_manifest_sha256']) == context['observation'] and
            proofs(context) == context['proof'], 'evidence changed after preparation')
    C['private_root'](ROOT)
    directory = ROOT / action
    directory.mkdir(mode=0o700)
    C['write_new'](directory / 'admission.json', context['admission_raw'])
    C['write_new'](directory / 'claim.json', json_bytes(phase_claim(context)))
    F['sync_directory'](directory); F['sync_directory'](ROOT); F['sync_directory'](ROOT.parent)
    try:
        target = target_context(context)
        if action == 'confirm-recovery':
            known = regular(REPO / 'artifacts/credentials/a53-recovery-known_hosts', 16384)
            require(sha(known) == context['admission']['known_good_known_hosts_sha256'], 'known-good pin changed')
            command = F['known_good_command'](target)
        else:
            prepared = target['prepared']
            require(sha(regular(prepared['keys'] / 'known_hosts', 8192)) == prepared['candidate']['known_hosts_sha256'],
                    'USB host pin changed')
            command = C['ssh_command'](prepared['keys'])
        child = directory / LABELS[action]
        child.mkdir(mode=0o700)
        remote = script(context)
        C['write_new'](child / 'command.sh', remote)
        F['sync_directory'](child); F['sync_directory'](directory)
        seconds, limit = LIMITS[action]
        process = C['run_once'](command, remote, child, seconds, stdout_limit=limit, stderr_limit=16384)
        C['write_new'](child / 'process.json', json_bytes(process))
        result, files = classify_phase(context, regular(child / 'stdout.txt', limit),
                                       regular(child / 'stderr.txt', 16384), process)
        for name, raw in files.items(): C['write_new'](directory / name, raw)
        if action == 'confirm-recovery':
            require(proofs(context) == context['proof'], 'prior evidence changed during confirmation')
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        result = {'classification': 'inconclusive', 'budget': 'consumed', 'reason': str(error),
                  'next_action': 'review retained evidence; no retry or automatic next phase'}
    C['write_new'](directory / 'result.json', json_bytes(result))
    manifest = ''.join(sha(regular(path, 4 * 1024 * 1024)) + '  ' + path.relative_to(directory).as_posix() + '\n'
                       for path in sorted(directory.rglob('*')) if path.is_file())
    C['write_new'](directory / 'SHA256SUMS', manifest.encode())
    # Match baseline finish durability: persist names as well as file contents
    # before an ordinary recovery may rely on this export of unique RAM data.
    for child in directory.iterdir():
        if child.is_dir(): F['sync_directory'](child)
    F['sync_directory'](directory)
    F['sync_directory'](ROOT)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--admission', type=Path, required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    try:
        if args.execute: L['execution_gate']()
        result = perform(prepare(args.admission), args.execute)
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        result = {'classification': 'refused', 'reason': str(error), 'readiness': 'preparing'}
    print(json.dumps(result, sort_keys=True))
    return 2 if result['classification'] in ('refused', 'inconclusive', 'log-export-inconclusive') else 0


if __name__ == '__main__':
    raise SystemExit(main())
