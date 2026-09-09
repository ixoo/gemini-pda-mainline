#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run one explicitly bound phase of the attended focused keyboard observation."""
import argparse
import json
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
F = runpy.run_path(str(HERE/'focused-session.py'))
M, C, S = F['M'], F['C'], F['S']
LIMITS = {'space-delivery': (30, 1024), 'space-wait': (315, 1024), 'logger': (620, 1024),
          'delivery-a': (30, 4096), 'delivery-b': (30, 4096), 'capture': (60, 131072),
          'export': (30, 278528), 'seal': (30, 3145728)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True, type=Path)
    parser.add_argument('--phase', required=True, choices=LIMITS)
    args = parser.parse_args()
    q, phase = args.session, args.phase
    binding = json.loads((HERE/'focused-execution-binding.json').read_bytes())
    raw = C['regular'](q/'plan.json', 262144)
    plan = json.loads(raw)
    M['require'](binding == {'schema': 'keyboard-focused-execution-v1', 'state': 'enabled',
        'id': plan['id'], 'boot_id': plan['boot_id'], 'plan_sha256': M['sha'](raw),
        'runner_sha256': M['sha'](Path(__file__).read_bytes())}, 'focused execution binding')
    M['require'](plan['fresh_owner_available'] is True and plan['sources'] == M['source_identity']()
        and plan['planner_sha256'] == M['sha']((HERE/'focused-session.py').read_bytes()), 'focused source or owner drift')
    # Private session lies directly under its original preserved session directory.
    reference = C['regular'](q.parent/'space2-admission.json', 65536)
    M['require'](M['sha'](reference) == plan['reference_sha256'], 'reference drift')
    ref = json.loads(reference)
    prepared = M['L']['completed_baseline'](ref['dependency'])['prepared']
    M['require'](ref['boot_id'] == plan['boot_id'], 'boot drift')
    def passed(name):
        result = json.loads(C['regular'](q/name/'result.json', 65536))
        M['require'](result['passed'] is True and result['id'] == plan['id'], 'prior phase did not pass')
    prior = {'space-wait':'space-delivery', 'logger':'space-wait', 'delivery-b':'delivery-a', 'capture':'delivery-b'}
    # The owner can explicitly start a diagnostic of console translation.
    # Requiring correct console bytes to admit that observation is circular.
    # This choice is covered by the exact plan binding and fresh-owner check;
    # it changes no device, logger, reader, capture or preservation guard.
    if phase == 'logger' and plan.get('readiness') == 'owner-confirmed-diagnostic':
        prior.pop('logger')
    if phase in prior:
        passed(prior[phase])
    if phase in ('delivery-a', 'delivery-b', 'capture'):
        M['require']((q/'logger/stdout.txt').is_file() and
            b'__KEYBOARD_LOGGER_STARTED__\n' in (q/'logger/stdout.txt').read_bytes()
            and not (q/'logger/process.json').exists(), 'logger not active')
    if phase == 'export':
        C['regular'](q/'capture/process.json', 65536)
    if phase == 'seal':
        passed('export')
        status = C['regular'](q/'files/monitor.status', 4096)
        M['require'](S['fields'](status).get('reaped') == '1', 'capture child not reaped')
    command = C['regular'](q/(phase+'.sh'), 262144)
    limits = LIMITS[phase]
    M['require'](plan['phases'][phase+'.sh'] == {'seconds': limits[0], 'stdout_limit': limits[1],
        'command_sha256': M['sha'](command), 'command_bytes': len(command)}, 'phase command drift')
    runpy.run_path(str(HERE/'../emmc/mainline_host.py'))['require_ready']()
    target = q/phase
    target.mkdir(mode=0o700)  # Once-only host claim, retained on every outcome.
    C['write_new'](target/'claim.json', M['encode']({'id':plan['id'], 'phase':phase, 'connections':1, 'retries':0}))
    ssh = C['ssh_command'](prepared['keys'])
    if phase in ('logger', 'space-wait'):
        ssh = [v.replace('ServerAliveInterval=0', 'ServerAliveInterval=15') for v in ssh]
        ssh[1:1] = ['-o', 'ServerAliveCountMax=3']
    process = C['run_once'](ssh, command, target, limits[0], stdout_limit=limits[1], stderr_limit=16384)
    C['write_new'](target/'process.json', M['encode'](process))
    stdout, stderr = (target/'stdout.txt').read_bytes(), (target/'stderr.txt').read_bytes()
    M['L']['process_ok'](stdout, stderr, process, *limits)
    if phase in ('space-delivery', 'delivery-a', 'delivery-b'):
        expected = {'space-delivery': b'space-delivery=verified\n', 'delivery-a': b'__FOCUSED_DELIVERY_A_PASS__\n',
                    'delivery-b': b'__FOCUSED_DELIVERY_B_PASS__\n'}[phase]
        M['require'](stdout == expected, 'delivery result')
    elif phase == 'space-wait':
        lines = stdout.splitlines()
        M['require'](1 <= len(lines) <= 15 and stdout == b'space-ready=waiting\n'*(len(lines)-1)
            + b'space-ready=passed released=1 restored=1\n', 'Space readiness result')
    elif phase == 'capture':
        M['require'](stdout.endswith(b'__FOCUSED_POSTFLIGHT_PASS__\n'), 'focused capture postflight')
    elif phase == 'export':
        files = M['parse_export'](stdout)
        saved = q/'files'; saved.mkdir(mode=0o700)
        for name, value in files.items():
            if value is not None:
                C['write_new'](saved/name, value)
        M['require'](all(value is not None for value in files.values()), 'incomplete capture export')
    elif phase == 'seal':
        parsed = S['parse_log_export'](stdout, stderr, process)
        for name, value in parsed['files'].items():
            C['write_new'](target/name, value)
        C['write_new'](target/'seal-result.json', M['encode'](parsed['result']))
        M['require'](parsed['result']['preservation_complete'] and parsed['result']['logger_terminal'], 'incomplete log seal')
    elif phase == 'logger':
        M['require'](stdout.endswith(b'__KEYBOARD_LOGGER_EXIT__=0\n'), 'logger exit')
    result = {'id': plan['id'], 'phase': phase, 'passed': True, 'process':process}
    C['write_new'](target/'result.json', M['encode'](result))
    print(json.dumps(result))


if __name__ == '__main__':
    main()
