#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Confirm Gemian after the service RAM session; default is offline validation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import time
import uuid

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SESSION = REPO / 'artifacts/a53-service-ram/session-1'
ADAPTER = HERE / 'a53-ram-installer.py'
ADAPTER_SHA = 'ff7c560176c0d1dfd82adba200e8b673b2be2336a1359c99f3a70eb09af440c9'
TRUST_SHA = 'd43262bd1f9c76d02eb633900f5e5502e2342d6c1b41586a2d7e524a2293768f'
ATTEMPTS, SLOT_SECONDS, WINDOW_SECONDS = 12, 15, 180
PROBE = b'''set -eu
printf '__A53_GEMIAN_RETURN_BEGIN__\\nboot_before=%s\\n' "$(cat /proc/sys/kernel/random/boot_id)"
printf 'kernel=%s\\narchitecture=%s\\n' "$(uname -r)" "$(uname -m)"
printf 'model=%s\\n' "$(tr -d '\\000' </proc/device-tree/model)"
awk -F= '$1 == "ID" {gsub(/^"|"$/, "", $2); print "os_id=" $2}
          $1 == "VERSION_ID" {gsub(/^"|"$/, "", $2); print "os_version=" $2}' /etc/os-release
printf 'pid1=%s\\n' "$(cat /proc/1/comm)"
system_state=$(systemctl is-system-running)
printf 'system_state=%s\\n' "$system_state"
printf 'boot_after=%s\\n__A53_GEMIAN_RETURN_END__\\n' "$(cat /proc/sys/kernel/random/boot_id)"
'''
EXPECTED = {'kernel': '3.18.41+', 'architecture': 'aarch64', 'model': 'MT6797X',
            'os_id': 'debian', 'os_version': '9', 'pid1': 'systemd', 'system_state': 'running'}
CONNECT_FAILURES = {
    ('ssh: connect to host 192.168.1.50 port 22: ' + reason + '\n').encode()
    for reason in ('Connection refused', 'Connection timed out', 'Operation timed out',
                   'No route to host', 'Network is unreachable')
}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def boot_uuid(value):
    parsed = uuid.UUID(value)
    require(parsed.int != 0 and str(parsed) == value, 'canonical nonzero boot UUID required')
    return value


def classify(raw, stderr, process, previous, mainline):
    require(process['stdout_bytes'] == len(raw) and process['stderr_bytes'] == len(stderr),
            'capture byte counts differ')
    if (not raw and process['exit_status'] == 255 and process['reason'] in (None, 'stdin-closed')
            and stderr in CONNECT_FAILURES):
        return {'classification': 'connection-unavailable', 'recovery_confirmed': False}
    require(not stderr and process['exit_status'] == 0 and process['reason'] is None and
            process['stdin_complete'], 'return transport incomplete or refused')
    require(raw.endswith(b'\n') and b'\r' not in raw, 'return line framing')
    lines = raw.decode('ascii').splitlines()
    require(len(lines) == 11 and lines[0] == '__A53_GEMIAN_RETURN_BEGIN__' and
            lines[-1] == '__A53_GEMIAN_RETURN_END__', 'return framing')
    values = {}
    for line in lines[1:-1]:
        key, sep, value = line.partition('=')
        require(sep and key not in values and value == value.strip(), 'duplicate or malformed return field')
        values[key] = value
    require(values.keys() == EXPECTED.keys() | {'boot_before', 'boot_after'} and
            all(values[key] == expected for key, expected in EXPECTED.items()), 'known-good Gemian identity differs')
    boot = boot_uuid(values['boot_before'])
    require(boot == values['boot_after'] and boot not in (previous, mainline), 'changed boot not established')
    return {'classification': 'changed-ID-Gemian', 'boot_id': boot, 'recovery_confirmed': True}


def prepare(candidate):
    require(not ADAPTER.is_symlink() and sha(ADAPTER.read_bytes()) == ADAPTER_SHA, 'installer adapter changed')
    adapter = runpy.run_path(str(ADAPTER))
    binding, _, _ = adapter['sources']()
    # Read-only confirmation is tied to this session's actual deployment and
    # exact native-request transcript. It never establishes full baseline success.
    collector = binding['load_module']('a53_return_reader', binding['BASELINE'] / 'collect-baseline.py')
    collector.directory(SESSION)
    deployment = collector.regular(SESSION / 'deployment-summary.txt', 16384)
    fields = collector.fields(deployment.decode('ascii').splitlines())
    previous = boot_uuid(fields['boot_id'])
    adapter['validate'](candidate, previous)
    context, collector, steps, finish = binding['prepare'](candidate, previous)
    adapter['receipt'](deployment.decode('ascii'), context['candidate']['files']['boot2-padded.img'],
                       adapter['MANIFEST_SHA'], previous)
    request = SESSION / 'native-reboot'
    collector.directory(request)
    require({p.name for p in request.iterdir()} == {'command.sh', 'stdout.txt', 'stderr.txt', 'process.json'},
            'native request inventory differs')
    captured = {name: collector.regular(request / name, limit) for name, limit in
                (('command.sh', 131072), ('stdout.txt', 131072), ('stderr.txt', 16384), ('process.json', 16384))}
    boots = [line[8:].decode('ascii') for line in captured['stdout.txt'].splitlines() if line.startswith(b'boot_id=')]
    require(len(boots) == 1, 'native request boot missing or repeated')
    mainline = boot_uuid(boots[0])
    require(mainline != previous, 'mainline and Gemian boot IDs match')
    require(captured['command.sh'] == steps.recovery_script(context['candidate'], mainline), 'native request script differs')
    process = json.loads(captured['process.json'], object_pairs_hook=collector.no_duplicates)
    require(process['stdout_bytes'] == len(captured['stdout.txt']) and
            process['stderr_bytes'] == len(captured['stderr.txt']), 'native request byte counts differ')
    finish.parse_recovery_request(captured['stdout.txt'], process, mainline,
                                  {'finish_source_sha256': binding['SOURCE_PINS']['finish-baseline.py']})
    credentials = REPO / 'artifacts/credentials'
    key = credentials / 'gemini_ed25519'
    trust = credentials / 'a53-recovery-known_hosts'
    key_sha = sha(collector.regular(key, 16384))
    require(sha(collector.regular(trust, 8192)) == TRUST_SHA, 'Gemian host trust changed')
    command = finish.known_good_command({'prepared': {'keys': credentials / 'a53-auth'}})
    return {'collector': collector, 'finish': finish, 'command': command,
            'key': key, 'key_sha256': key_sha, 'trust': trust,
            'previous': previous, 'mainline': mainline, 'output': SESSION / 'gemian-return',
            'binding': {'candidate_sha256': context['admission']['candidate_sha256'],
                        'deployment_sha256': sha(deployment), 'request_sha256': {k: sha(v) for k, v in captured.items()},
                        'previous_gemian_boot': previous, 'mainline_boot': mainline,
                        'source_sha256': sha(Path(__file__).read_bytes()), 'host_trust_sha256': TRUST_SHA}}


def watch(prepared):
    collector, finish = prepared['collector'], prepared['finish']
    output = prepared['output']
    collector.directory(output.parent)
    output.mkdir(mode=0o700)  # Fixed namespace: interruption or failure consumes this window.
    collector.write_new(output / 'claim.json', encoded({**prepared['binding'], 'budget': 'consumed',
                        'attempt_limit': ATTEMPTS, 'window_seconds': WINDOW_SECONDS, 'slot_seconds': SLOT_SECONDS}))
    collector.write_new(output / 'command.json', encoded(prepared['command']))
    finish.sync_directory(output)
    finish.sync_directory(output.parent)
    result = {'classification': 'return-unconfirmed', 'recovery_confirmed': False, 'attempts': 0}
    start = time.monotonic()
    try:
        for index in range(ATTEMPTS):
            delay = start + index * SLOT_SECONDS - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            remaining = start + WINDOW_SECONDS - time.monotonic()
            if remaining <= 0:
                break
            # Recheck local credentials before each connection; never silently
            # continue with replaced trust or a changed authentication key.
            require(sha(collector.regular(prepared['key'], 16384)) == prepared['key_sha256'] and
                    sha(collector.regular(prepared['trust'], 8192)) == TRUST_SHA, 'Gemian credentials changed')
            child = output / ('attempt-%02d' % (index + 1))
            child.mkdir(mode=0o700)
            collector.write_new(child / 'command.sh', PROBE)
            result['attempts'] += 1
            process = collector.run_once(prepared['command'], PROBE, child, min(SLOT_SECONDS, remaining),
                                         stdout_limit=4096, stderr_limit=16384)
            collector.write_new(child / 'process.json', encoded(process))
            raw, err = collector.regular(child / 'stdout.txt', 4096), collector.regular(child / 'stderr.txt', 16384)
            observation = classify(raw, err, process, prepared['previous'], prepared['mainline'])
            collector.write_new(child / 'result.json', encoded(observation))
            finish.sync_directory(child)
            require(time.monotonic() <= start + WINDOW_SECONDS, 'return window expired')
            if observation['recovery_confirmed']:
                result.update(observation)
                break
            # Only the exact pre-authentication connection failures above reach
            # another scheduled slot. Partial/authenticated/unknown failures stop.
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        result['reason'] = str(error)
    result['elapsed_seconds'] = round(time.monotonic() - start, 3)
    result['baseline_success'] = 'not-classified-by-return-collector'
    collector.write_new(output / 'result.json', encoded(result))
    manifest = ''.join(sha(collector.regular(p, 131072)) + '  ' + p.relative_to(output).as_posix() + '\n'
                       for p in sorted(output.rglob('*')) if p.is_file())
    collector.write_new(output / 'SHA256SUMS', manifest.encode())
    # Verify saved bytes and persist names, including partial attempts, before
    # reporting a result. This function never requests another restart.
    for line in manifest.splitlines():
        expected, name = line.split('  ', 1)
        require(sha(collector.regular(output / name, 131072)) == expected, 'return evidence readback differs')
    for path in output.iterdir():
        if path.is_dir():
            finish.sync_directory(path)
    finish.sync_directory(output)
    finish.sync_directory(output.parent)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--execute', action='store_true', help='consume the one bounded read-only return window')
    args = parser.parse_args()
    os.umask(0o077)
    try:
        prepared = prepare(Path(os.path.abspath(args.candidate)))
        result = watch(prepared) if args.execute else {'classification': 'offline-preparation-only', 'device_action': 'none'}
        print(json.dumps(result, sort_keys=True))
        return int(args.execute and not result['recovery_confirmed'])
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        parser.exit(2, 'service RAM return refused: ' + str(error) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
