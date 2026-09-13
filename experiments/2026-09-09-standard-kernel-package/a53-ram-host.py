#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""One A53 RAM observation, preserved log and reviewed return; offline by default."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
BASELINE = REPO / 'experiments/2026-09-05-owner-away-experiment-preparation/baseline/scripts'
SESSION = REPO / 'artifacts/a53-service-ram/session-1'
PINS = {
    HERE / 'a53-ram-installer.py': 'ff7c560176c0d1dfd82adba200e8b673b2be2336a1359c99f3a70eb09af440c9',
    HERE / 'a53-ram-return.py': '9813be751c161009aa667714f322b2b3b9fc13396dc4736736c18093f8b77f66',
    BASELINE / 'validate-candidate.py': 'ef76e8b99aeb94dc56651752855efdb493bdfabbd31fbd91a0cba07f1a7f22bb',
    BASELINE.parent.parent / 'emmc/mainline_host.py': '57491d7ac60a380ee85215e391274e5ced2733b33ab6df70e0757db7b67bf082',
}
BUDGETS = {'observation': (45, 131072), 'probe': (15, 131072),
           'log-export': (30, 3 * 1024 * 1024), 'native-reboot': (15, 131072)}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def prepare(candidate):
    for path, expected in PINS.items():
        require(not path.is_symlink() and sha(path.read_bytes()) == expected, 'host input changed: ' + path.name)
    adapter = runpy.run_path(str(HERE / 'a53-ram-installer.py'))
    binding, _, _ = adapter['sources']()
    collector = binding['load_module']('a53_host_reader', BASELINE / 'collect-baseline.py')
    collector.directory(SESSION)
    require({p.name for p in SESSION.iterdir()} == {'deployment-summary.txt'},
            'session already claimed or unexpected initial files')
    deployment = collector.regular(SESSION / 'deployment-summary.txt', 16384)
    previous = binding['boot_uuid'](collector.fields(deployment.decode('ascii').splitlines())['boot_id'])
    context, collector = adapter['validate'](candidate, previous)
    context, collector, steps, finish = binding['prepare'](candidate, previous)
    adapter['receipt'](deployment.decode('ascii'), context['candidate']['files']['boot2-padded.img'],
                       adapter['MANIFEST_SHA'], previous)
    keys = REPO / 'artifacts/credentials/a53-auth'
    validator = runpy.run_path(str(BASELINE / 'validate-candidate.py'))
    authorized, host_key, known = validator['check_credentials'](keys)
    for name, data in (('root/.ssh/authorized_keys', authorized), ('etc/dropbear/host_key', host_key)):
        require(sha(data) == context['candidate']['members'][name]['sha256'], 'candidate authentication differs')
    credentials = {path: sha(collector.regular(path, 16384)) for path in sorted(keys.iterdir())}
    context['candidate']['known_hosts_sha256'] = sha(known)
    context['keys'] = keys
    network = binding['load_module']('a53_host_network', BASELINE.parent.parent / 'emmc/mainline_host.py')
    returning = binding['load_module']('a53_host_return', HERE / 'a53-ram-return.py')
    gemian_key = REPO / 'artifacts/credentials/gemini_ed25519'
    gemian_trust = REPO / 'artifacts/credentials/a53-recovery-known_hosts'
    require(collector.regular(gemian_key, 16384), 'empty Gemian return key')
    require(sha(collector.regular(gemian_trust, 8192)) == returning.TRUST_SHA, 'Gemian return trust changed')
    for path in (gemian_key, gemian_trust):
        credentials[path] = sha(collector.regular(path, 16384))
    return {'candidate_path': candidate, 'context': context, 'collector': collector, 'steps': steps,
            'finish': finish, 'binding': binding, 'network': network, 'returning': returning,
            'credentials': credentials, 'deployment': deployment, 'root': SESSION,
            'command': collector.ssh_command(keys),
            'claim': {'candidate_sha256': context['admission']['candidate_sha256'],
                      'deployment_sha256': sha(deployment), 'previous_gemian_boot': previous,
                      'runner_sha256': sha(Path(__file__).read_bytes()),
                      'source_sha256': {str(p.relative_to(REPO)): value for p, value in PINS.items()},
                      'credential_sha256': {p.name: value for p, value in credentials.items()},
                      'phase_budgets': {name: {'connections': 1, 'seconds': seconds, 'stdout_bytes': limit,
                                              'stderr_bytes': 16384} for name, (seconds, limit) in BUDGETS.items()}}}


def process_ok(raw, stderr, process):
    require(process['stdout_bytes'] == len(raw) and process['stderr_bytes'] == len(stderr),
            'captured byte counts differ')
    require(not stderr and process['exit_status'] == 0 and process['reason'] is None and
            process['stdin_complete'] is True, 'incomplete phase transport')


def probe_ok(raw, stderr, process, boot):
    process_ok(raw, stderr, process)
    require(raw == ('authenticated_boot_id=' + boot + '\n').encode(), 'bound probe identity differs')


def invoke(prepared, label, script, *, network_status=None):
    collector, finish, root = prepared['collector'], prepared['finish'], prepared['root']
    require(label in BUDGETS and len(script) <= 131072, 'phase or script exceeds admitted scope')
    status = network_status if network_status is not None else prepared['network'].require_ready()
    require(status['ready'], 'direct USB route absent')
    for path, expected in prepared['credentials'].items():
        require(sha(collector.regular(path, 16384)) == expected, 'USB credentials changed')
    child = root / label
    child.mkdir(mode=0o700)
    collector.write_new(child / 'command.sh', script)
    # The native request keeps the exact four-file inventory used by the return helper.
    collector.write_new(root / (label + '-host-route.json'), encoded(status))
    finish.sync_directory(child)
    finish.sync_directory(root)
    seconds, limit = BUDGETS[label]
    process = collector.run_once(prepared['command'], script, child, seconds,
                                 stdout_limit=limit, stderr_limit=16384)
    collector.write_new(child / 'process.json', encoded(process))
    finish.sync_directory(child)
    raw = collector.regular(child / 'stdout.txt', limit)
    err = collector.regular(child / 'stderr.txt', 16384)
    require(process['stdout_bytes'] == len(raw) and process['stderr_bytes'] == len(err),
            'captured phase byte counts differ')
    return raw, err, process


def preserved_snapshot(prepared, boot):
    collector, finish, root = prepared['collector'], prepared['finish'], prepared['root']
    manifest = ''.join(sha(collector.regular(p, 4 * 1024 * 1024)) + '  ' +
                       p.relative_to(root).as_posix() + '\n' for p in sorted(root.rglob('*')) if p.is_file()).encode()
    collector.write_new(root / 'PRE_RECOVERY_SHA256SUMS', manifest)
    for path in root.iterdir():
        if path.is_dir():
            finish.sync_directory(path)
    finish.sync_directory(root)
    finish.sync_directory(root.parent)
    require(collector.regular(root / 'PRE_RECOVERY_SHA256SUMS', 16384) == manifest, 'manifest readback differs')
    snapshot = finish.verified_snapshot(root, manifest)
    require(snapshot['deployment-summary.txt'] == prepared['deployment'], 'deployment evidence changed')
    require(snapshot['execution-claim.json'] == encoded({**prepared['claim'], 'budget': 'consumed'}) and
            snapshot['ssh-command.json'] == encoded(prepared['command']), 'saved execution binding changed')
    for label, expected in (('observation', collector.remote_script(prepared['context'])),
                            ('probe', prepared['steps'].probe_script(prepared['context']['candidate'], boot)),
                            ('log-export', prepared['steps'].seal_script(prepared['context']['candidate'], boot))):
        require(snapshot[label + '/command.sh'] == expected, 'saved phase script changed')
    def process(label):
        return json.loads(snapshot[label + '/process.json'], object_pairs_hook=collector.no_duplicates)
    observation = prepared['binding']['classify_observation'](prepared['context'], collector,
        snapshot['observation/stdout.txt'], snapshot['observation/stderr.txt'], process('observation'))
    require(observation['classification'] == 'baseline-observation-only-pass' and observation['boot_id'] == boot,
            'saved observation no longer passes')
    probe_ok(snapshot['probe/stdout.txt'], snapshot['probe/stderr.txt'], process('probe'), boot)
    log_process = process('log-export')
    require(log_process['stdout_bytes'] == len(snapshot['log-export/stdout.txt']) and
            log_process['stderr_bytes'] == len(snapshot['log-export/stderr.txt']), 'saved log byte counts differ')
    export = finish.recheck_export(root, boot, snapshot=snapshot)
    require(export['export']['preservation_complete'] is True,
            'ordinary recovery requires complete preservation of available RAM logs')
    return {'manifest_sha256': sha(manifest), 'log_complete': export['classification'] == 'complete-log-through-seal'}


def execute(prepared):
    collector, finish, root = prepared['collector'], prepared['finish'], prepared['root']
    collector.directory(root)
    require({p.name for p in root.iterdir()} == {'deployment-summary.txt'}, 'session already claimed')
    require(collector.regular(root / 'deployment-summary.txt', 16384) == prepared['deployment'],
            'deployment receipt changed before execution')
    status = prepared['network'].require_ready()  # No claim or SSH if the host is not ready.
    collector.write_new(root / 'execution-claim.json', encoded({**prepared['claim'], 'budget': 'consumed'}))
    collector.write_new(root / 'ssh-command.json', encoded(prepared['command']))
    finish.sync_directory(root)
    finish.sync_directory(root.parent)
    result = {'classification': 'session-inconclusive', 'regression_pass': False, 'phase': 'observation',
              'recovery_requested': False, 'recovery_confirmed': False}
    try:
        raw, err, process = invoke(prepared, 'observation', collector.remote_script(prepared['context']), network_status=status)
        observation = prepared['binding']['classify_observation'](prepared['context'], collector, raw, err, process)
        collector.write_new(root / 'observation-result.json', encoded(observation))
        require(observation['classification'] == 'baseline-observation-only-pass', 'baseline observation did not pass')
        boot = observation['boot_id']
        result['mainline_boot'] = boot
        result['phase'] = 'probe'
        probe_ok(*invoke(prepared, 'probe', prepared['steps'].probe_script(prepared['context']['candidate'], boot)), boot)
        result['phase'] = 'log-export'
        raw, err, process = invoke(prepared, 'log-export', prepared['steps'].seal_script(prepared['context']['candidate'], boot))
        export = prepared['steps'].parse_log_export(raw, err, process)
        require(set(export['files']) <= set(finish.EXPORT_FILES), 'log export file scope')
        for name in finish.EXPORT_FILES:
            collector.write_new(root / name, export['files'].get(name, b''))
        collector.write_new(root / 'log-result.json', encoded(export['result']))
        result['phase'] = 'preservation'
        proof = preserved_snapshot(prepared, boot)
        result['preservation'] = proof
        result['phase'] = 'native-reboot'
        result['recovery_requested'] = None  # Unknown until the request frame is classified.
        raw, _err, process = invoke(prepared, 'native-reboot', prepared['steps'].recovery_script(prepared['context']['candidate'], boot))
        requested = finish.parse_recovery_request(raw, process, boot,
            {'finish_source_sha256': prepared['binding']['SOURCE_PINS']['finish-baseline.py']})
        collector.write_new(root / 'native-request-result.json', encoded(requested))
        finish.sync_directory(root)
        result['recovery_requested'] = True
        result['phase'] = 'gemian-return'
        returning = prepared['returning'].watch(prepared['returning'].prepare(prepared['candidate_path']))
        result['return'] = returning
        result['recovery_confirmed'] = returning['recovery_confirmed']
        if returning['recovery_confirmed']:
            result['returned_gemian_boot'] = returning['boot_id']
            result['regression_pass'] = proof['log_complete']
            result['classification'] = 'ram-service-regression-pass' if proof['log_complete'] else 'returned-with-incomplete-log'
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        result['reason'] = str(error)
    collector.write_new(root / 'session-result.json', encoded(result))
    finish.sync_directory(root)
    finish.sync_directory(root.parent)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--execute', action='store_true', help='consume the one admitted observation/log/recovery session')
    args = parser.parse_args()
    os.umask(0o077)
    try:
        prepared = prepare(Path(os.path.abspath(args.candidate)))
        result = execute(prepared) if args.execute else {'classification': 'offline-preparation-only', 'device_action': 'none'}
        print(json.dumps(result, sort_keys=True))
        return int(args.execute and not result['regression_pass'])
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        parser.exit(2, 'service RAM host refused: ' + str(error) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
