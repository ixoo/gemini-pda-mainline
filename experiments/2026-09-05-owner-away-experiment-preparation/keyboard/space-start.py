#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare bounded RAM delivery and a separate on-device readiness wait."""
import base64
import json
from pathlib import Path
import runpy
import shlex

HERE = Path(__file__).resolve().parent
M = runpy.run_path(str(HERE/'capture.py'))
C, S, require, sha = (M[k] for k in ('C', 'S', 'require', 'sha'))


def prepare(context, package, identity, revision):
    package = Path(package)
    require(C['SHA'].fullmatch(identity) and len(revision) == 40
            and all(c in '0123456789abcdef' for c in revision), 'package identity')
    runpy.run_path(str(HERE/'../baseline/scripts/buildbox_userspace.py'))['check_package'](
        package, identity, revision)
    manifest = json.loads(C['regular'](package/'manifest.json', 262144))
    require(manifest['production_entry'] == 'space-ready-v1' and manifest['replicas_identical']
            and manifest['inputs']['space-ready.c'] == sha((HERE/'space-ready.c').read_bytes()),
            'readiness source identity')
    require(C['regular'](package/'fixture-tests.txt', 16384).splitlines() ==
        [f'{case}=pass'.encode() for case in ('press-release', 'held-space-does-not-start',
         'wrong-key', 'release-without-press', 'lost-events', 'timeout', 'signal-restores-console',
         'escape-preserves-pending-space', 'state-query-read-only', 'state-query-failure',
         'console-drain-preserves-and-restores')],
        'readiness fixtures')
    names = ('space-ready', 'licenses/musl-COPYRIGHT', 'licenses/repository-LICENSE',
             'licenses/GCC-copyright')
    files = {name:C['regular'](package/name, 131072, private=name != 'space-ready') for name in names}
    require(all(files.values()) and sum(map(len, files.values())) <= 196608, 'delivery bound')
    a = context['admission']; runtime = a['runtime']
    require(C['UUID'].fullmatch(runtime['retry_id']), 'retry identity')
    destination = '/a53-keyboard-ready-' + runtime['retry_id'] + '-' + identity[:12]
    candidate = context['dependency']['prepared']['candidate']
    guard = S['identity_script'](candidate, a['boot_id']) + S['ram_guard_script']()
    guard += M['console_guard'](candidate) + M['reader_guard']()
    for path, target in runtime['resource_paths'].items():
        guard += f'[ "$($BB readlink -f {shlex.quote(path)})" = {shlex.quote(target)} ]\n'
    guard += f'[ "$($BB readlink -f /sys/class/input/{runtime["event"]}/device)" = {shlex.quote(runtime["input_path"])} ]\n'
    for name, value in runtime['capabilities'].items():
        guard += f'[ "$($BB cat /sys/class/input/{runtime["event"]}/device/capabilities/{name})" = {shlex.quote(value.rstrip())} ]\n'
    guard += "[ \"$($BB awk '$2 == \"/\" {n++; if (($3 == \"rootfs\" || $3 == \"ramfs\" || $3 == \"tmpfs\") && $4 !~ /(^|,)(ro|noexec)(,|$)/) ok++} END {print n+0 \":\" ok+0}' /proc/mounts)\" = 1:1 ]\n"
    guard += f"[ \"$($BB awk '$2 == \"{destination}\" || index($2, \"{destination}/\") == 1 {{n++}} END {{print n+0}}' /proc/mounts)\" = 0 ]\n"
    delivery = guard + '$BB df -Pk /run | $BB awk \'NR == 2 {if ($4 < 1024) exit 1}\'\numask 077\nset -C\n'
    delivery += f'[ ! -e {destination} ] && [ ! -L {destination} ]\n$BB mkdir -m 700 {destination}\n$BB mkdir -m 700 {destination}/licenses\n'
    for index, (name, raw) in enumerate(files.items()):
        delivery += f"$BB base64 -d >{destination}/{name} <<'READY_{index}'\n{base64.b64encode(raw).decode()}\nREADY_{index}\n"
        delivery += f'h=$($BB sha256sum {destination}/{name}); [ "${{h%% *}}" = {sha(raw)} ]\n'
    delivery += f'$BB chmod 700 {destination}/space-ready\n$BB printf "space-delivery=verified\\n"\n'
    wait = guard + f'[ -d {destination} ] && [ ! -L {destination} ]\n[ "$($BB stat -c %u:%a {destination})" = 0:700 ]\n'
    wait += f'[ -f {destination}/space-ready ] && [ ! -L {destination}/space-ready ]\n[ "$($BB stat -c %u:%a:%h {destination}/space-ready)" = 0:700:1 ]\n'
    wait += f'h=$($BB sha256sum {destination}/space-ready); [ "${{h%% *}}" = {sha(files["space-ready"])} ]\n'
    wait += f'exec {destination}/space-ready {runtime["event"]} {runtime["minor"]}\n'
    require(len(delivery.encode()) <= 262144, 'encoded delivery bound')
    return {'delivery':delivery.encode(), 'wait':wait.encode(),
            'binary_sha256':sha(files['space-ready']), 'package_identity':identity}
