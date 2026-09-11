#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Derive the private installer for an independently validated export package."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import shlex
import subprocess
import uuid

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
BASE = REPO / 'experiments/2026-08-14-mt6797-runtime-provenance-observer/scripts/install-boot2.sh'
DERIVER = REPO / 'experiments/2026-09-04-mt6797-thermal-snapshot/scripts/v4_installer_guard.py'
GUARD = REPO / 'scripts/boot2-device-guard.sh'
PINS = {BASE: 'deaa0e886a881132dd49ee1e3d5b0e6f776400f51fa86a8d0b7c791e979d12a8',
        DERIVER: '9c72675e3043dcf735c8a368800ce9297ca6c343d81283505e7030de82253211',
        GUARD: '0f0fc88ce4650590c6cb86f0ef5ce22b95b2a0f41c9b39b397e24e39cf9f0ebf'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def regular(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError('requires a regular file: ' + path.name)
    return path.read_bytes()


def derive(candidate, filesystem, padded_sha, session_sha, boot_id):
    if any(not re.fullmatch('[0-9a-f]{64}', value) for value in (padded_sha, session_sha)):
        raise ValueError('invalid externally pinned digest')
    if str(uuid.UUID(boot_id)) != boot_id or uuid.UUID(boot_id).int == 0:
        raise ValueError('invalid preceding Gemian boot UUID')
    if candidate.name != 'wifi-export-container-20260910':
        raise ValueError('unexpected validated package name')
    for path, expected in PINS.items():
        if sha(regular(path)) != expected:
            raise ValueError('reviewed installer source changed')
    padded = regular(candidate / 'boot2-padded.img')
    receipt = json.loads(regular(candidate / 'private-result.json'))
    session_raw = regular(filesystem / 'session.json')
    session = json.loads(session_raw)
    if len(padded) != 16777216 or sha(padded) != padded_sha or receipt['padded_sha256'] != padded_sha:
        raise ValueError('padded image identity changed')
    if sha(session_raw) != session_sha or receipt['session_sha256'] != session_sha:
        raise ValueError('session identity changed')
    if session['startup_action'] != 'export':
        raise ValueError('only preservation export is selected')
    if receipt['assembler_sha256'] != sha(regular(HERE / 'build-export-container.py')):
        raise ValueError('container constructor changed')
    if receipt['filesystem_sha256'] != sha(regular(filesystem / 'rootfs.cpio.gz')):
        raise ValueError('filesystem identity changed')
    linked = json.loads(regular(HERE / 'results/full-kernel-link-46.json'))
    if (session['kernel_image_sha256'] != linked['outputs']['Image.gz-dtb'] or
            receipt['kernel_sha256'] != session['kernel_image_sha256'] or
            session['kernel_inputs_sha256'] != linked['inputs_sha256'] or
            session['kernel_config_sha256'] != linked['config_sha256']):
        raise ValueError('kernel provenance changed')
    expected_paths = {'init', *(f'opt/wifi-cycle/{name}' for name in (
        'startup.py', 'capture-device.py', 'capture-export.py', 'check-retained-patches.py',
        'cycle-controller.py', 'respond-once.py'))}
    if set(session['startup_files']) != expected_paths:
        raise ValueError('startup file inventory changed')
    for path, expected in session['startup_files'].items():
        local = HERE / ('startup-init.sh' if path == 'init' else Path(path).name)
        if sha(regular(local)) != expected:
            raise ValueError('startup source changed: ' + local.name)
    subprocess.run(['sha256sum', '--check', '--strict', 'SHA256SUMS'],
                   cwd=candidate, check=True, timeout=20, stdout=subprocess.DEVNULL)
    source = runpy.run_path(str(DERIVER))['derive'](regular(BASE).decode(), regular(GUARD))

    def replace(old, new, count=1):
        nonlocal source
        if source.count(old) != count:
            raise ValueError('installer anchor changed: ' + old[:60])
        source = source.replace(old, new)

    replace('ea603c1b1a64d4f1aa9cac3e53957a3e858a7ce04127f1aef36d4b0e8173cb02', padded_sha)
    replace('ad92d496dfb4fd183c35e6e0f32ce626b2045528657fb2567d8561dd02540f1a',
            sha(regular(candidate / 'SHA256SUMS')))
    replace('gemian-runtime-provenance-observer-rndis-1d303dda10b4', candidate.name)
    replace('2026-08-14-mt6797-runtime-provenance-observer', HERE.name)
    replace('provenance-observer', 'wifi-export', 7)
    replace('wifi-export-deployment-*', 'wifi-export-deployment-1', 2)
    replace('wifi-export-deployment-N', 'wifi-export-deployment-1')
    replace('script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"\n'
            'repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"',
            'repo_root=' + shlex.quote(str(REPO)))
    replace("size=\"$(stat -f '%z' \"$candidate\" 2>/dev/null || stat -c '%s' \"$candidate\")\"",
            "size=\"$(wc -c <\"$candidate\" | tr -d ' ')\"")
    replace('-o StrictHostKeyChecking=yes -i "$identity"',
            '-o StrictHostKeyChecking=yes -o UpdateHostKeys=no -i "$identity"')
    replace('initial_boot_id=${initial_boot_id//$\'\\r\'/}\n',
            'initial_boot_id=${initial_boot_id//$\'\\r\'/}\n'
            '[[ "$initial_boot_id" == ' + boot_id + " ]] || die 'preceding Gemian boot changed'\n")
    return source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('candidate', 'filesystem', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    for name in ('padded-sha256', 'session-sha256', 'boot-id'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    source = derive(args.candidate, args.filesystem, args.padded_sha256,
                    args.session_sha256, args.boot_id)
    output = args.output.absolute()
    if output.is_symlink() or not output.parent.is_dir() or output.parent.is_symlink():
        raise ValueError('unsafe output parent')
    if output.parent.stat().st_mode & 0o077 or output.parent.stat().st_uid != os.getuid():
        raise ValueError('output parent must be caller-owned and private')
    subprocess.run(['git', '-C', str(REPO), 'check-ignore', '-q', str(output)], check=True)
    with output.open('x') as stream:
        stream.write(source)
    subprocess.run(['bash', '-n', str(output)], check=True, timeout=15)
    subprocess.run(['shellcheck', str(output)], check=True, timeout=30)
    print('installer_sha256=' + sha(source.encode()))
    print('device_action=none; review and explicit installer invocation remain required')


if __name__ == '__main__':
    main()
