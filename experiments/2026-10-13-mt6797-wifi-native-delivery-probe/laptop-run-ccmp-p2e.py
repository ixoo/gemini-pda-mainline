#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""One P2E identity/capture/session launch; offline preparation is the default."""
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import runpy
import subprocess
import sys

HERE = Path(__file__).resolve().parent
PROOF_SHA = '85333866812c678302b8b6a7394a42fef532bad7533b2ac4c5e18299831b4b09'
RECEIPT_SHA = 'bf73a14d7cfe6f2ddd528025da6c0c2cb01a24e69e9669146ecc39a75ecb4073'
NOTES_SHA = 'b0213c37e6080b8b334f73842ca3162390cdfeecb29d8eb93bd41d2c2bf9b160'
COLLECT_SHA = 'efbca1e464e04005d3b7d503742b426eb9f642140ec289c40bc43563852208cf'


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def digest(path):
    require(path.is_file() and not path.is_symlink(), 'missing/linked source: '+path.name)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    data = (json.dumps(value, indent=2)+'\n').encode()
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def prepare(candidate):
    proof_path = HERE / 'results/p2e-host-validation.json'
    require(digest(proof_path) == PROOF_SHA, 'P2E host proof changed')
    proof = json.loads(proof_path.read_bytes())
    for name, expected in {**proof['source_sha256'], **proof['consumed_p2_source_sha256']}.items():
        require(digest(HERE/name) == expected, 'P2E input changed: '+name)
    receipt_path = HERE / 'results/ccmp-stable-monitor-candidate-p2.json'
    require(digest(receipt_path) == RECEIPT_SHA, 'P2 image receipt changed')
    private = Path(os.environ['GEMINI_PRIVATE_REPO']).resolve(strict=True)
    runtime = Path(os.environ['GEMINI_RUNTIME_ROOT']).resolve(strict=True)
    require(runtime.is_relative_to(private/'artifacts') and not runtime.is_symlink(), 'runtime root')
    root = runtime/'ccmp-stable-monitor'
    deployment = root/'session-ccmp-p2e/deployment-summary.txt'
    require(deployment.is_file() and not deployment.is_symlink(), 'real deployment receipt missing')
    require(not (root/'capture-ccmp-p2e').exists() and
            not (root/'session-ccmp-p2e/execution-claim.json').exists() and
            not (runtime/'launcher-claim.json').exists(), 'P2E launch already consumed')
    fields = dict(line.split('=', 1) for line in deployment.read_text().splitlines())
    spec = importlib.util.spec_from_file_location('p2e_deployment_validator', HERE/'install-ccmp-p2.py')
    installer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(installer)
    protocol, candidate = installer.validate(candidate, fields['boot_id'])
    installer.receipt(deployment.read_text(), protocol['files']['boot2-padded.img']['sha256'],
                      RECEIPT_SHA, fields['boot_id'])
    cohort = Path(os.environ['GEMINI_SESSION_SOURCE_ROOT']).resolve(strict=True)
    collector_path = cohort/'experiments/2026-09-05-owner-away-experiment-preparation/baseline/scripts/collect-baseline.py'
    require(digest(collector_path) == COLLECT_SHA, 'identity collector changed')
    collector = runpy.run_path(str(collector_path))
    keys = private/'artifacts/credentials/a53-auth'
    collector['directory'](keys)
    env = dict(os.environ)
    env.pop('GEMINI_WIFI_SSH_BOOT', None)  # Only the live identity may supply it.
    env['GEMINI_WIFI_SSH_KEYS'] = str(keys)
    for name in ('capture', 'session'):
        command = [sys.executable, str(HERE/('laptop-'+name+'-ccmp-p2e.py')),
                   '--candidate', str(candidate)]
        response = subprocess.run(command, env=env, capture_output=True, timeout=30)
        require(response.returncode == 0, 'offline '+name+' preparation refused')
    return dict(runtime=runtime, protocol=protocol, candidate=candidate, env=env,
                previous_boot=fields['boot_id'], collector=collector, keys=keys)


def identity_script(protocol):
    source = ('set -eu\nBB=/bin/busybox\n$BB uname -r\n$BB uname -m\n'
              '$BB cat /proc/sys/kernel/random/boot_id\n$BB sha256sum /sys/kernel/notes\n'
              '$BB wc -c </sys/kernel/notes\n$BB cat /proc/uptime\n'
              '[ ! -e /run/a53/kmsg-exit ]\n[ ! -e /run/a53/kmsg.status ]\n'
              'p=$($BB cat /run/a53/kmsg-pid)\n[ "$p" -gt 1 ]\n'
              '[ "$($BB readlink /proc/$p/exe)" = /bin/kmsg-capture ]\n'
              'printf "logger_active=yes\\n"\n')
    return (source+''.join('$BB sha256sum /'+name+'\n'
                         for name in protocol['live_root_sha256'])).encode()


def identity(state):
    attempt = state['runtime']/'identity'
    attempt.mkdir(mode=0o700)  # The collector requires this before opening output.
    collector = state['collector']
    script = identity_script(state['protocol'])
    (attempt/'command.sh').write_bytes(script)
    process = collector['run_once'](collector['ssh_command'](state['keys']), script,
                                    attempt, 10, stdout_limit=4096, stderr_limit=4096)
    write(attempt/'process.json', process)
    require(process['exit_status'] == 0 and process['reason'] is None and
            process['stdin_complete'], 'live identity acquisition refused')
    lines = (attempt/'stdout.txt').read_bytes().decode('ascii').splitlines()
    require(len(lines) == 7+len(state['protocol']['live_root_sha256']), 'identity framing')
    require(lines[0] == state['protocol']['kernel_release'] and lines[1] == 'aarch64', 'live kernel identity')
    require(re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', lines[2]) and
            lines[2] != state['previous_boot'], 'fresh boot identity')
    require(lines[3].split()[0] == NOTES_SHA and int(lines[4]) == 84, 'kernel notes identity')
    uptime = float(lines[5].split()[0])
    # Match the leaf's existing whole-second <=50 guard, including 50.99.
    require(math.isfinite(uptime) and 0 <= uptime and int(uptime) <= 50 and
            lines[6] == 'logger_active=yes', 'cold logger admission')
    require([line.split()[0] for line in lines[7:]] ==
            list(state['protocol']['live_root_sha256'].values()), 'P2 live root identity')
    result = dict(boot_id=lines[2], uptime_s=uptime, logger_active=True,
                  root_hashes_verified=True, notes_bytes=84, notes_sha256=NOTES_SHA)
    write(state['runtime']/'live-identity.json', result)
    return result


def phase(name, state):
    with (state['runtime']/(name+'-execute-host.log')).open('xb') as output:
        return subprocess.run([sys.executable, str(HERE/('laptop-'+name+'-ccmp-p2e.py')),
                               '--candidate', str(state['candidate']), '--execute'],
                              env=state['env'], stdout=output, stderr=subprocess.STDOUT).returncode


def execute(state):
    result = dict(phase='identity', bootstrap_attempted=False, session_attempted=False)
    write(state['runtime']/'launcher-claim.json', dict(
        one_attempt=True, host_proof_sha256=PROOF_SHA,
        launcher_source_sha256=digest(Path(__file__))))
    try:
        live = identity(state)
        state['env']['GEMINI_WIFI_SSH_BOOT'] = live['boot_id']
        result.update(phase='capture', bootstrap_attempted=True, boot_id=live['boot_id'])
        result['capture_exit'] = phase('capture', state)
        preflight = state['runtime']/'ccmp-stable-monitor/capture-ccmp-p2e/preflight.json'
        if preflight.is_file():
            observed = json.loads(preflight.read_bytes())
            require(observed['boot_id'] == live['boot_id'] and
                    observed['release'] == state['protocol']['kernel_release'], 'capture boot changed')
        else:
            require(result['capture_exit'] != 0, 'successful capture missing identity')
        # Capture can fail after WMT/START. The existing session's no-ready
        # path owns preservation and reviewed recovery; never repeat capture.
        result.update(phase='session', session_attempted=True)
        result['session_exit'] = phase('session', state)
        result['phase'] = 'complete'
        return result['session_exit'] or result['capture_exit']
    except (OSError, ValueError, KeyError, UnicodeError) as error:
        result['refusal'] = str(error)
        print('P2E launcher stopped: '+str(error), file=sys.stderr)
        return 2
    finally:
        write(state['runtime']/'launcher-result.json', result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    state = prepare(args.candidate)
    if args.execute:
        return execute(state)
    print('offline-launcher-preparation=pass; device_action=none')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
