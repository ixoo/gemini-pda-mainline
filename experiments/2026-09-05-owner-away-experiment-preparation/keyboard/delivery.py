#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exact disabled-monitor delivery preparation. No callable transport is enabled."""
import base64
import hashlib
import json
from pathlib import Path
import re
import runpy

HERE = Path(__file__).resolve().parent
PACKAGE = '7eb7313217d0efe306b33a8bd7f90a4e782c7d0931ce71362b2de0ce8a33767f'
REVISION = '75636670d933b9231f36fddf2ce876801568f64e'
BINARY = 'f4dd3a4c3e1a8d3a1e4bbdb9de2713972ba7efc44643b8b7703e520091a1fccb'
SIZE = 66672
DESTINATION = '/a53-keyboard-delivery'
MEMBERS = ('keyboard-monitor-disabled', 'licenses/musl-COPYRIGHT',
           'licenses/repository-LICENSE', 'licenses/GCC-copyright')
PINS = dict(zip(MEMBERS, (BINARY,
    'b870108ec5e7790e9f9919064f1b9421d62d5f9b0e6c230c6adf7ea2da62e97b',
    'c5de7c87e2505230d7062b4418b6dccd20ce938b4e6f0ffa32157230e3c74d4f',
    'da8191658b3452ce9caf31638ba61dab31a38c619fa39df119812e050f592fd3')))


def require(value, reason):
    if not value:
        raise ValueError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def prepare(package):
    """Verify the exact accepted package; do not copy or execute its binary."""
    package = Path(package).absolute()
    require(all(not p.is_symlink() for p in (package, *package.parents)), 'package symlink')
    verifier = runpy.run_path(str(HERE / '../baseline/scripts/buildbox_userspace.py'))
    verifier['check_package'](package, PACKAGE, REVISION)
    result = {name: (package / name).read_bytes() for name in MEMBERS}
    require(len(result[MEMBERS[0]]) == SIZE and sha(result[MEMBERS[0]]) == BINARY,
            'accepted monitor binary identity')
    require(all(0 < len(raw) <= 131072 for raw in result.values()), 'inherited file limit')
    require(sum(len(raw) for raw in result.values()) <= 262144, 'delivery byte budget')
    return result


def script(files, candidate, boot_id):
    """Generate one fixed exclusive RAM-rootfs delivery; no capture or exec."""
    require(set(files) == set(MEMBERS), 'delivery member inventory')
    require(len(files[MEMBERS[0]]) == SIZE and sha(files[MEMBERS[0]]) == BINARY, 'binary identity')
    require(all(type(raw) is bytes and 0 < len(raw) <= 131072 for raw in files.values()), 'file size')
    require(all(sha(files[name]) == PINS[name] for name in MEMBERS), 'delivery file identity')
    require(type(boot_id) is str and re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', boot_id), 'boot identity')
    session = runpy.run_path(str(HERE / '../baseline/scripts/session_steps.py'))
    lines = [session['identity_script'](candidate, boot_id), session['ram_guard_script'](),
             'umask 077',
             # /run remains noexec; this accepts only the existing executable RAM root.
             "[ \"$($BB awk '$2 == \"/\" {n++; if (($3 == \"rootfs\" || $3 == \"ramfs\" || $3 == \"tmpfs\") && $4 !~ /(^|,)(ro|noexec)(,|$)/) ok++} END {print n+0 \":\" ok+0}' /proc/mounts)\" = 1:1 ]",
             "[ \"$($BB awk '$2 == \"/a53-keyboard-delivery\" || index($2, \"/a53-keyboard-delivery/\") == 1 {n++} END {print n+0}' /proc/mounts)\" = 0 ]",
             '[ ! -e /a53-keyboard-delivery ] && [ ! -L /a53-keyboard-delivery ]',
             '$BB mkdir -m 700 /a53-keyboard-delivery',
             # This directory is the consumed claim. Preserve partial files on failure.
             '$BB mkdir -m 700 /a53-keyboard-delivery/licenses']
    for index, name in enumerate(MEMBERS):
        raw = files[name]
        delimiter = 'A53_DELIVERY_' + str(index)
        lines += [f"$BB base64 -d >{DESTINATION}/{name} <<'{delimiter}'",
                  base64.b64encode(raw).decode(), delimiter,
                  f'[ "$($BB stat -c %s {DESTINATION}/{name})" = {len(raw)} ]',
                  f'h=$($BB sha256sum {DESTINATION}/{name})',
                  f'[ "${{h%% *}}" = {sha(raw)} ]']
    lines += ['$BB chmod 700 /a53-keyboard-delivery/keyboard-monitor-disabled',
              f"$BB printf 'delivery=verified-disabled-monitor\\nboot_id={boot_id}\\nbytes={SIZE}\\nsha256={BINARY}\\n'"]
    raw = ('\n'.join(lines) + '\n').encode()
    require(len(raw) <= 262144, 'encoded command budget')
    return raw


def execute(*args, **kwargs):
    raise ValueError('keyboard delivery disabled pending exact shell and admission review')


if __name__ == '__main__':
    print(json.dumps({'classification': 'refused', 'delivery_execution': 'disabled',
                      'production_monitor': 'disabled', 'package': PACKAGE}, sort_keys=True))
    raise SystemExit(2)
