#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""PREPARING: one authenticated eMMC read; completion is separately admitted."""
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import runpy
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = next(parent for parent in HERE.parents if (parent / 'AGENTS.md').is_file())
EXPERIMENT = REPO / 'experiments/2026-09-05-owner-away-experiment-preparation'
SOURCE_NAMES = {'baseline/scripts/collect-baseline.py', 'baseline/scripts/finish-baseline.py',
                'baseline/scripts/session_steps.py', 'baseline/scripts/verified_baseline.py',
                'emmc/observe.sh', 'emmc/classify.py', 'emmc/guarded_observation.py',
                'baseline/scripts/supplemental_recovery.py', 'emmc/prerequisite.py',
                'emmc/recovery_v2.py', 'emmc/execution_gate.py', 'emmc/live_window.py',
                'emmc/mainline_host.py', 'emmc/session.py'}
GUARD_NAME = 'emmc/guarded_observation.py'
VERIFIER_NAME = 'baseline/scripts/verified_baseline.py'


def require(value, reason):
    if not value:
        raise ValueError(reason)


class ObservationRejected(ValueError):
    def __init__(self, observation):
        self.observation = observation
        super().__init__('observation did not pass: ' + observation.get('reason', observation['classification']))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate JSON field')
        result[key] = value
    return result


def source_path(name):
    path = EXPERIMENT / name
    require(path.is_file() and all(not item.is_symlink() for item in (path, *path.parents)),
            'source missing or symlinked')
    return path


def source_identity():
    raw = (HERE / 'source-pins.json').read_bytes()
    pins = json.loads(raw, object_pairs_hook=unique)
    require(set(pins) == SOURCE_NAMES, 'source pin inventory')
    for name, value in pins.items():
        require(isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value) and
                sha(source_path(name).read_bytes()) == value, 'reviewed source changed')
    return {'launcher_sha256': sha(Path(__file__).read_bytes()), 'pins_sha256': sha(raw)}


source_identity()  # Refuse source drift before importing the shared contracts.
# Share the process-local receipt type across separately loaded adapters.
_window_name = '_gemini_emmc_live_window'
if _window_name not in sys.modules:
    _spec = importlib.util.spec_from_file_location(_window_name, HERE / 'live_window.py')
    _module = importlib.util.module_from_spec(_spec)
    sys.modules[_window_name] = _module
    _spec.loader.exec_module(_module)
LiveWindow = sys.modules[_window_name].LiveWindow

C = runpy.run_path(str(EXPERIMENT / 'baseline/scripts/collect-baseline.py'))
F = runpy.run_path(str(EXPERIMENT / 'baseline/scripts/finish-baseline.py'))
S = runpy.run_path(str(EXPERIMENT / 'baseline/scripts/session_steps.py'))
S['parse_recovery_request'] = runpy.run_path(str(HERE / 'recovery_v2.py'))['parse_recovery_request']
P = runpy.run_path(str(HERE / 'prerequisite.py'))
execution_gate = runpy.run_path(str(HERE / 'execution_gate.py'))['require_enabled']
V = runpy.run_path(str(source_path(VERIFIER_NAME)))
O = runpy.run_path(str(source_path(GUARD_NAME)))
E = runpy.run_path(str(EXPERIMENT / 'emmc/classify.py'))
regular = C['regular']
BUDGETS = {'pre_observations': 1, 'read_attempts': 1, 'post_observations': 1,
           'requested_bytes': 16777216, 'read_seconds': 20, 'outer_read_seconds': 40,
           'pre_seconds': 45, 'post_seconds': 45, 'retries': 0}
PHASES = {'pre': (45, 131072), 'read': (40, 8192), 'post': (45, 131072)}
ATTEMPT_ROOT = REPO / 'artifacts/a53-authenticated/emmc-readonly/attempt'
FIELDS = {'schema', 'experiment', 'action', 'admission_id', 'baseline_admission_id',
          'baseline_manifest_sha256', 'confirmation_manifest_sha256', 'candidate_manifest_sha256',
          'deployment_receipt_sha256', 'source_identity', 'action_budgets', 'custodian_role',
          'custody_handoff_sha256', 'custody_exclusive', 'physical_selection_confirmed',
          'no_other_device_operations', 'stable_power_confirmed', 'prerequisite_selector', 'prerequisite_phase_manifests'}


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def load(path, limit=131072):
    return json.loads(regular(path, limit), object_pairs_hook=unique)


def process_ok(out, err, process, seconds, limit):
    require(set(process) == {'exit_status', 'reason', 'stdin_complete', 'stdout_bytes',
                             'stderr_bytes', 'elapsed_seconds'}, 'process inventory')
    elapsed = process['elapsed_seconds']
    require(type(elapsed) in (int, float) and math.isfinite(elapsed) and 0 <= elapsed <= seconds + 1,
            'process elapsed bound')
    require(type(process['exit_status']) is int and process['exit_status'] == 0 and
            process['reason'] is None and process['stdin_complete'] is True and not err,
            'transport incomplete or interrupted')
    for label, raw, cap in (('stdout', out, limit), ('stderr', err, 16384)):
        require(type(process[label + '_bytes']) is int and process[label + '_bytes'] == len(raw)
                and len(raw) <= cap, 'process stream count or bound')


def candidate_inputs(admission):
    """Separate local candidate/image/key boundary; this does not accept an archive."""
    attempt = REPO / 'artifacts/a53-authenticated/attempts' / admission['baseline_admission_id']
    prepared = C['prepare'](REPO, attempt / 'admission.json', attempt / 'deployment-summary.txt')
    require(prepared['admission']['admission_id'] == admission['baseline_admission_id'] and
            sha(prepared['candidate_raw']) == admission['candidate_manifest_sha256'] and
            sha(prepared['deployment_raw']) == admission['deployment_receipt_sha256'], 'dependency identity')
    observer = (EXPERIMENT / 'emmc/observe.sh').read_bytes()
    require(prepared['candidate']['members']['bin/emmc-observe'] ==
            {'mode': '0o100755', 'sha256': sha(observer), 'size': len(observer)}, 'candidate observer identity')
    return prepared


def completed_baseline(admission):
    prepared = candidate_inputs(admission)
    bindings = {'admission_id': admission['baseline_admission_id'],
                'candidate_sha256': prepared['admission']['candidate_sha256'],
                'candidate_manifest_sha256': admission['candidate_manifest_sha256'],
                'baseline_manifest_sha256': admission['baseline_manifest_sha256'],
                'confirmation_manifest_sha256': admission['confirmation_manifest_sha256']}
    if admission['prerequisite_selector'] == 'original-strict':
        verified = V['verify'](REPO / 'artifacts/a53-authenticated', bindings)
    else:
        selected = P['verify_prerequisite'](REPO / 'artifacts/a53-authenticated',
            admission['prerequisite_selector'], {**bindings, 'phase_manifests': admission['prerequisite_phase_manifests']})
        # Reuse original manifest snapshots for cross-binding and boot identities;
        # never upgrade the supplemental classification to the strict one.
        VC, VF, VD = V['tools']()
        archive = REPO / 'artifacts/a53-authenticated'
        original = V['original'](archive / 'attempts' / bindings['admission_id'], bindings, VC, VF, VD)
        snap = V['confirm_inventory'](archive / 'sessions' / bindings['admission_id'] / 'confirm-recovery',
                                     bindings['confirmation_manifest_sha256'], VF)
        final = VF.snapshot_load(snap, 'result.json')
        verified = {**selected['evidence_result'],
            'candidate_sha256': bindings['candidate_sha256'],
            'candidate_manifest_sha256': bindings['candidate_manifest_sha256'],
            'baseline_admission_sha256': sha(original['prepared']['admission_raw']),
            'deployment_receipt_sha256': sha(original['prepared']['deployment_raw']),
            'baseline_boot_id': original['baseline']['boot_id'],
            'original_known_good_boot_id': original['prepared']['recovery_id'],
            'recovered_boot_id': final['boot_id']}

    require(verified['classification'] == {'original-strict': 'verified-first-authenticated-baseline-and-recovery',
            'reviewed-supplemental': 'supplemental-authenticated-baseline-recovery-verified'}[admission['prerequisite_selector']] and
            verified['dependent_admission'] is False and verified['network_access'] == 'none', 'archive proof scope')
    require(verified['baseline_admission_sha256'] == sha(prepared['admission_raw']) and
            verified['deployment_receipt_sha256'] == sha(prepared['deployment_raw']) == admission['deployment_receipt_sha256'] and
            verified['candidate_manifest_sha256'] == sha(prepared['candidate_raw']) == admission['candidate_manifest_sha256'] and
            prepared['admission']['admission_id'] == bindings['admission_id'] and
            verified['candidate_sha256'] == prepared['candidate']['files']['boot.img'] == bindings['candidate_sha256'] and
            verified['original_known_good_boot_id'] == prepared['recovery_id'], 'candidate/archive cross-binding')
    return {'prepared': prepared, 'first_boot': verified['baseline_boot_id'],
            'recovered_boot': verified['recovered_boot_id'], 'verification': verified}


def check_admission(value):
    require(type(value) is dict and set(value) == FIELDS and type(value['schema']) is int and value['schema'] == 1 and
            value['experiment'] == 'a53-emmc-readonly' and value['action'] == 'single-read-session', 'admission scope/inventory')
    for name in ('admission_id', 'baseline_admission_id'):
        require(isinstance(value[name], str) and C['UUID'].fullmatch(value[name]), 'admission UUID')
    require(value['admission_id'] != value['baseline_admission_id'], 'new observation admission required')
    for name in ('baseline_manifest_sha256', 'confirmation_manifest_sha256', 'candidate_manifest_sha256',
                 'deployment_receipt_sha256', 'custody_handoff_sha256'):
        require(isinstance(value[name], str) and C['SHA'].fullmatch(value[name]), 'admission digest')
    require(value['prerequisite_selector'] in P['SELECTORS'], 'explicit prerequisite selector')
    phase_pins = value['prerequisite_phase_manifests']
    if value['prerequisite_selector'] == 'original-strict':
        require(phase_pins is None, 'strict prerequisite has no supplemental pins')
    else:
        require(type(phase_pins) is dict and set(phase_pins) == {'auth-checks', 'preserve-log', 'request-recovery'} and
                all(type(v) is str and C['SHA'].fullmatch(v) for v in phase_pins.values()), 'supplemental phase pins')
    require(value['source_identity'] == source_identity(), 'launcher source identity')
    require(value['action_budgets'] == BUDGETS and all(type(n) is int for n in value['action_budgets'].values()), 'fixed budget')
    require(isinstance(value['custodian_role'], str) and
            re.fullmatch(r'[A-Za-z][A-Za-z0-9 _-]{0,63}', value['custodian_role']), 'custodian role')
    require(all(value[name] is True for name in ('custody_exclusive', 'physical_selection_confirmed',
                'no_other_device_operations', 'stable_power_confirmed')), 'custody/selection/power unconfirmed')


def prepare(path):
    path = Path(path).absolute()
    C['ignored'](REPO, path)
    raw = regular(path, 16384)
    admission = json.loads(raw, object_pairs_hook=unique)
    check_admission(admission)
    dependency = completed_baseline(admission)
    return {'admission': admission, 'admission_raw': raw, 'dependency': dependency}


def observer_guard(candidate):
    return O['observer_guard'](candidate)


def script_for(context, phase, boot):
    prepared = context['dependency']['prepared']
    baseline = C['remote_script'](prepared) if phase in ('pre', 'post') else b''
    return O['script_for'](prepared, phase, boot, baseline, S['RELEASE'])


def classify_phase(context, phase, out, err, process, boot):
    seconds, limit = PHASES[phase]
    process_ok(out, err, process, seconds, limit)
    prepared = context['dependency']['prepared']
    if phase == 'read':
        value = E['classify'](out.decode('ascii'), boot, S['RELEASE'],
                              prepared['candidate']['files']['boot2-padded.img'],
                              prepared['candidate']['members']['bin/busybox']['sha256'])
        if value['classification'] != 'read-integrity-pass':
            raise ObservationRejected(value)
    else:
        value = C['classify_capture'](prepared, out, err, process)
        if value['classification'] != 'baseline-observation-only-pass':
            raise ObservationRejected(value)
        current = value['boot_id']
        require(current not in (context['dependency']['first_boot'], context['dependency']['recovered_boot']),
                'subsequent mainline boot required')
        require(phase == 'pre' or current == boot, 'boot changed between phases')
    return value


def phase_claim(context, phase, boot, script):
    seconds, limit = PHASES[phase]
    return {'budget': 'consumed', 'phase': phase, 'admission_sha256': sha(context['admission_raw']),
            'command_sha256': sha(script), 'connections': 1, 'seconds': seconds,
            'stdout_limit': limit, 'stderr_limit': 16384, 'boot_id': boot}


def session_claim(context):
    return {'budget': 'consumed', 'admission_sha256': sha(context['admission_raw']),
            'action_budgets': BUDGETS, 'source_identity': context['admission']['source_identity']}


def phase_capture(context, root, phase, boot):
    directory = root / phase
    directory.mkdir(mode=0o700)  # Never resume, overwrite or retry a phase.
    script = script_for(context, phase, boot)
    seconds, limit = PHASES[phase]
    C['write_new'](directory / 'claim.json', json_bytes(phase_claim(context, phase, boot, script)))
    C['write_new'](directory / 'command.sh', script)
    F['sync_directory'](directory)
    F['sync_directory'](root)
    prepared = context['dependency']['prepared']
    require(sha(regular(prepared['keys'] / 'known_hosts', 8192)) == prepared['candidate']['known_hosts_sha256'],
            'known host changed before dispatch')
    process = C['run_once'](C['ssh_command'](prepared['keys']), script, directory, seconds,
                            stdout_limit=limit, stderr_limit=16384)
    C['write_new'](directory / 'process.json', json_bytes(process))
    return classify_phase(context, phase, regular(directory / 'stdout.txt', limit),
                          regular(directory / 'stderr.txt', 16384), process, boot)


def collect(context, execute=False, live_window=None):
    if not execute:
        return {'classification': 'dry-run', 'readiness': 'preparing', 'network_access': 'none',
                'attempt_created': False, 'budgets': BUDGETS,
                'completion': 'separate preservation and recovery admission required'}
    execution_gate()
    require(type(context) is dict and set(context) == {'admission', 'admission_raw', 'dependency'},
            'prepared observation context required')
    require(type(context['admission']) is dict and type(context['admission_raw']) is bytes,
            'prepared admission required')
    require(json.loads(context['admission_raw'], object_pairs_hook=unique) == context['admission'],
            'prepared admission bytes changed')
    check_admission(context['admission'])
    require(source_identity() == context['admission']['source_identity'], 'source changed after preparation')
    # Recheck the complete prior chain immediately before permanently claiming.
    require(completed_baseline(context['admission']) == context['dependency'], 'dependency changed after preparation')
    require(isinstance(live_window, LiveWindow), 'authenticated live timing receipt required')
    live_window.require(context['admission']['candidate_manifest_sha256'], None,
                        context['admission']['admission_id'], sha(context['admission_raw']), 164, 400)
    C['private_root'](ATTEMPT_ROOT.parent)
    ATTEMPT_ROOT.mkdir(mode=0o700)  # Fixed experiment scope: a new UUID is no reset.
    C['write_new'](ATTEMPT_ROOT / 'claim.json', json_bytes(session_claim(context)))
    C['write_new'](ATTEMPT_ROOT / 'admission.json', context['admission_raw'])
    F['sync_directory'](ATTEMPT_ROOT)
    F['sync_directory'](ATTEMPT_ROOT.parent)
    results, boot = {}, None
    try:
        for phase in ('pre', 'read', 'post'):
            # Include one second runner tolerance per phase and for log export.
            live_window.require(context['admission']['candidate_manifest_sha256'], boot,
                context['admission']['admission_id'], sha(context['admission_raw']),
                {'pre': 164, 'read': 118, 'post': 77}[phase])
            results[phase] = phase_capture(context, ATTEMPT_ROOT, phase, boot)
            if phase == 'pre':
                boot = results[phase]['boot_id']
                require(boot == live_window.boot, 'identity/preflight boot changed')
        outcome = {'classification': 'read-serviceability-only-pass', 'boot_id': boot,
                   'phases': results, 'readiness': 'preparing',
                   'remaining': ['independent-log-preservation-and-continuity', 'changed-ID-known-good-recovery']}
    except (OSError, ValueError, KeyError, TypeError) as error:
        negative = getattr(error, 'observation', None)
        if negative is not None:
            results[phase] = negative
        classification = 'fail' if negative and negative['classification'] in ('fail', 'baseline-observation-rejected') else 'inconclusive'
        outcome = {'classification': classification, 'reason': str(error), 'boot_id': boot,
                   'phases': results, 'budget': 'consumed', 'further_observations': 'none',
                   'next_action': 'review partial evidence; separately admit preservation/recovery; never retry'}
    C['write_new'](ATTEMPT_ROOT / 'result.json', json_bytes(outcome))
    sums = ''.join(sha(regular(path, 2097152)) + '  ' + path.relative_to(ATTEMPT_ROOT).as_posix() + '\n'
                   for path in sorted(ATTEMPT_ROOT.rglob('*')) if path.is_file())
    C['write_new'](ATTEMPT_ROOT / 'SHA256SUMS', sums.encode())
    return outcome


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--admission', type=Path, required=True)
    parser.add_argument('--collect', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    try:
        if args.collect: execution_gate()
        result = collect(prepare(args.admission), args.collect)
    except (OSError, ValueError, KeyError, TypeError) as error:
        result = {'classification': 'refused', 'reason': str(error), 'readiness': 'preparing'}
    print(json.dumps(result, sort_keys=True))
    return 0 if result['classification'] in ('dry-run', 'read-serviceability-only-pass') else 2


if __name__ == '__main__':
    raise SystemExit(main())
