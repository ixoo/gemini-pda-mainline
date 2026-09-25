#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run one bounded authenticated CONSYS snapshot session after verified boot2 deployment."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys
from types import SimpleNamespace

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SERVICE = REPO / 'experiments/2026-09-09-standard-kernel-package'
BASELINE = REPO / 'experiments/2026-09-05-owner-away-experiment-preparation/baseline/scripts'
ROOT = REPO / 'artifacts/consys-status/session-1'
HOST_SHA = 'edba94181863d4e49ca9d7c5d3a6e5b8e638d8e6f140144f7d9238c0468e1bf0'
RETURN_SHA = '0f6f20c324dc7bb4911c34a8e793b09a0af819ed46474ee996b723930bf5d081'


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def prepare(candidate):
    require(sha((SERVICE / 'a53-ram-host.py').read_bytes()) == HOST_SHA and
            sha((SERVICE / 'a53-ram-return.py').read_bytes()) == RETURN_SHA,
            'established host or return workflow changed')
    session = runpy.run_path(str(HERE / 'session.py'))
    installer = runpy.run_path(str(HERE / 'installer.py'))
    host = runpy.run_path(str(SERVICE / 'a53-ram-host.py'))
    returning = runpy.run_path(str(SERVICE / 'a53-ram-return.py'))
    collector = session['load']('consys_host_reader', BASELINE / 'collect-baseline.py')
    collector.directory(ROOT)
    require({p.name for p in ROOT.iterdir()} == {'deployment-summary.txt'},
            'session already claimed or unexpected initial files')
    deployment = collector.regular(ROOT / 'deployment-summary.txt', 16384)
    previous = session['boot_uuid'](collector.fields(deployment.decode('ascii').splitlines())['boot_id'])
    receipt, candidate = installer['validate'](candidate, previous)
    context, collector, steps, finish = session['prepare'](candidate, previous)
    installer['receipt'](deployment.decode('ascii'), receipt['files']['boot2-padded.img']['sha256'],
                         installer['MANIFEST_SHA'], previous)

    keys = REPO / 'artifacts/credentials/a53-auth'
    validator = runpy.run_path(str(BASELINE / 'validate-candidate.py'))
    authorized, host_key, known = validator['check_credentials'](keys)
    for name, data in (('root/.ssh/authorized_keys', authorized), ('etc/dropbear/host_key', host_key)):
        require(sha(data) == context['candidate']['members'][name]['sha256'],
                'candidate authentication differs')
    credentials = {path: sha(collector.regular(path, 16384)) for path in sorted(keys.iterdir())}
    context['candidate']['known_hosts_sha256'] = sha(known)
    context['keys'] = keys
    network = session['load']('consys_host_network',
                              REPO / 'experiments/2026-09-05-owner-away-experiment-preparation/emmc/mainline_host.py')
    gemian_key = REPO / 'artifacts/credentials/gemini_ed25519'
    gemian_trust = REPO / 'artifacts/credentials/a53-recovery-known_hosts'
    require(collector.regular(gemian_key, 16384), 'empty Gemian return key')
    require(sha(collector.regular(gemian_trust, 8192)) == returning['TRUST_SHA'],
            'Gemian return trust changed')
    for path in (gemian_key, gemian_trust):
        credentials[path] = sha(collector.regular(path, 16384))

    def return_prepare(_candidate):
        request = ROOT / 'native-reboot'
        collector.directory(request)
        require({p.name for p in request.iterdir()} ==
                {'command.sh', 'stdout.txt', 'stderr.txt', 'process.json'},
                'native request inventory differs')
        captured = {name: collector.regular(request / name, limit) for name, limit in
                    (('command.sh', 131072), ('stdout.txt', 131072),
                     ('stderr.txt', 16384), ('process.json', 16384))}
        boots = [line[8:].decode('ascii') for line in captured['stdout.txt'].splitlines()
                 if line.startswith(b'boot_id=')]
        require(len(boots) == 1, 'native request boot missing or repeated')
        mainline = session['boot_uuid'](boots[0])
        require(mainline != previous and
                captured['command.sh'] == steps.recovery_script(context['candidate'], mainline),
                'native request identity changed')
        process = json.loads(captured['process.json'], object_pairs_hook=collector.no_duplicates)
        finish.parse_recovery_request(captured['stdout.txt'], process, mainline,
                                      {'finish_source_sha256': session['SOURCE_PINS']['finish-baseline.py']})
        return {'collector': collector, 'finish': finish,
                'command': finish.known_good_command({'prepared': {'keys': keys}}),
                'key': gemian_key, 'key_sha256': sha(collector.regular(gemian_key, 16384)),
                'trust': gemian_trust, 'previous': previous, 'mainline': mainline,
                'output': ROOT / 'gemian-return',
                'binding': {'candidate_sha256': context['admission']['candidate_sha256'],
                            'deployment_sha256': sha(deployment),
                            'request_sha256': {name: sha(data) for name, data in captured.items()},
                            'previous_gemian_boot': previous, 'mainline_boot': mainline,
                            'source_sha256': sha(Path(__file__).read_bytes()),
                            'host_trust_sha256': returning['TRUST_SHA']}}

    source_pins = {name: sha((BASELINE / name).read_bytes())
                   for name in session['SOURCE_PINS']}
    require(source_pins == session['SOURCE_PINS'], 'collector source changed')
    return {'candidate_path': candidate, 'context': context, 'collector': collector,
            'steps': steps, 'finish': finish,
            'binding': {'classify_observation': session['classify'],
                        'SOURCE_PINS': session['SOURCE_PINS']},
            'network': network, 'returning': SimpleNamespace(
                prepare=return_prepare, watch=returning['watch']),
            'credentials': credentials, 'deployment': deployment, 'root': ROOT,
            'command': collector.ssh_command(keys),
            'claim': {'candidate_sha256': context['admission']['candidate_sha256'],
                      'deployment_sha256': sha(deployment), 'previous_gemian_boot': previous,
                      'runner_sha256': sha(Path(__file__).read_bytes()),
                      'phase_budgets': {name: {'connections': 1, 'seconds': seconds,
                                              'stdout_bytes': limit, 'stderr_bytes': 16384}
                                        for name, (seconds, limit) in host['BUDGETS'].items()}},
            'execute': host['execute']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', required=True, type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    try:
        prepared = prepare(args.candidate)
        if not args.execute:
            print('offline-preparation=pass; device_action=none')
            return 0
        result = prepared['execute'](prepared)
        log = ROOT / 'kmsg.log'
        if result.get('preservation', {}).get('log_complete') and log.is_file():
            lines = [line for line in log.read_bytes().splitlines()
                     if b'mt6797-consys-status: state=' in line]
            if len(lines) == 1:
                record = lines[0].decode('ascii', errors='replace')
                for state in ('off', 'on', 'mixed', 'moved', 'unavailable'):
                    if 'mt6797-consys-status: state=' + state in record:
                        result['consys_state'] = state
                        break
        (ROOT / 'consys-result.json').write_bytes(encoded(result))
        prepared['finish'].sync_directory(ROOT)
        print(json.dumps(result, sort_keys=True))
        return 0 if result.get('consys_state') else 1
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, 'CONSYS host refused: ' + str(error) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
