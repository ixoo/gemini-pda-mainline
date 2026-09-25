#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Derive the existing guarded boot2 installer for one pinned CONSYS image."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import shlex
import subprocess
import sys
import uuid

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
BASELINE = REPO / 'experiments/2026-09-05-owner-away-experiment-preparation/baseline/scripts'
EXPERIMENT = 'mt6797-consys-status-snapshot'
RECEIPT_NAME = 'mt6797-consys-status-deployment-1'
MANIFEST_SHA = '0a7b047d01718edb39346a697df4b9c05651277370102eb98f3569684cb7eddb'
PINS = {
    BASELINE / 'installer.py': '405749e387a5b4383b56a3073575f7a26b335a42f9ecafb22f126b5578973467',
    BASELINE / 'deployment_receipt.py': 'a2dc643ddedf5c9c93ede43598208cafd17242fccbb45db6ddaf078f30ae6f23',
}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def boot_uuid(value):
    parsed = uuid.UUID(value)
    require(parsed.int != 0 and str(parsed) == value, 'canonical nonzero boot UUID required')
    return value


def sources():
    for path, expected in PINS.items():
        require(not path.is_symlink() and digest(path.read_bytes()) == expected,
                'installer input changed: ' + path.name)
    return runpy.run_path(str(BASELINE / 'installer.py')), runpy.run_path(
        str(BASELINE / 'deployment_receipt.py'))


def validate(candidate, previous):
    boot_uuid(previous)
    candidate = Path(os.path.abspath(candidate))
    require(not candidate.is_symlink() and candidate.is_dir(), 'candidate directory missing')
    published = HERE / 'results/candidate.json'
    require(digest(published.read_bytes()) == MANIFEST_SHA, 'published candidate changed')
    expected = json.loads(published.read_text())
    require(expected['kernel_release'] == '7.1.3-gemini-consys-status-snapshot' and
            expected['physical_admission'] is False, 'candidate scope changed')
    require(candidate.name == 'candidate-' + expected['files']['boot.img']['sha256'],
            'candidate path does not name its boot image')
    require({p.name for p in candidate.iterdir()} == set(expected['files']) | {'candidate.json'},
            'candidate inventory changed')
    require(digest((candidate / 'candidate.json').read_bytes()) == MANIFEST_SHA,
            'private candidate manifest changed')
    for name, identity in expected['files'].items():
        path = candidate / name
        require(not path.is_symlink() and path.is_file() and
                path.stat().st_size == identity['bytes'] and
                digest(path.read_bytes()) == identity['sha256'],
                'candidate file changed: ' + name)
    raw = (candidate / 'boot.img').read_bytes()
    padded = (candidate / 'boot2-padded.img').read_bytes()
    require(len(padded) == 16777216 and padded == raw + bytes(16777216 - len(raw)),
            'full boot2 padding changed')
    return expected, candidate


def receipt(raw, candidate_sha, manifest_sha, previous):
    boot_uuid(previous)
    _, parser = sources()
    original = 'experiment=' + EXPERIMENT
    lines = raw.splitlines()
    require(lines.count(original) == 1 and
            not any(line.startswith('experiment=') and line != original for line in lines),
            'wrong or duplicate experiment receipt')
    translated = '\n'.join('experiment=a53-authenticated-baseline' if line == original
                           else line for line in lines)
    require(parser['receipt'](translated, candidate_sha, manifest_sha) == previous,
            'deployment belongs to another Gemian boot')


def adapt(source, candidate, previous):
    tool = HERE / 'installer.py'

    def replace(old, new, count=1):
        nonlocal source
        require(source.count(old) == count, 'guarded installer anchor changed')
        source = source.replace(old, new)

    validator = BASELINE / 'validate-candidate.py'
    old = shlex.join(['python3', str(validator), '--foundation', str(candidate),
                      '--userspace', str(candidate)])
    new = shlex.join(['python3', str(tool), 'validate', '--previous-gemian-boot', previous])
    replace(old, new)

    def check(path):
        return ('[[ "$(sha256sum ' + shlex.quote(str(path)) + " | awk '{print $1}')\" == " +
                digest(path.read_bytes()) + " ]] || die 'validation tool changed'\n")

    replace(check(validator), check(tool) + check(HERE / 'results/candidate.json'))
    old = shlex.join(['python3', str(BASELINE / 'deployment_receipt.py'), '--candidate-sha256'])
    new = shlex.join(['python3', str(tool), 'receipt', '--previous-gemian-boot',
                      previous, '--candidate-sha256'])
    replace(old, new)
    replace('a53-authenticated-baseline-deployment-2', RECEIPT_NAME, 3)
    replace("printf 'experiment=a53-authenticated-baseline\\n",
            "printf 'experiment=" + EXPERIMENT + "\\n")
    anchor = "[[ \"$initial_boot_id\" =~ ^[0-9a-f-]{36}$ ]] || die 'malformed initial boot ID'\n"
    replace(anchor, anchor + '[[ "$initial_boot_id" == ' + shlex.quote(previous) +
            " ]] || die 'preceding Gemian boot changed'\n")
    return source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('prepare', 'validate', 'receipt'):
        item = commands.add_parser(name)
        item.add_argument('--previous-gemian-boot', required=True)
        if name == 'receipt':
            item.add_argument('--receipt', type=Path, required=True)
            item.add_argument('--candidate-sha256', required=True)
            item.add_argument('--candidate-manifest-sha256', required=True)
        else:
            item.add_argument('--candidate', type=Path, required=True)
        if name == 'prepare':
            item.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    try:
        if args.command == 'receipt':
            require(not args.receipt.is_symlink() and args.receipt.is_file(),
                    'unsafe receipt path')
            receipt(args.receipt.read_text(), args.candidate_sha256,
                    args.candidate_manifest_sha256, args.previous_gemian_boot)
        else:
            _, candidate = validate(args.candidate, args.previous_gemian_boot)
            if args.command == 'prepare':
                installer, _ = sources()
                source = installer['derive'](installer['pinned_sources'](), REPO,
                                              candidate, candidate, candidate)
                source = adapt(source, candidate, args.previous_gemian_boot)
                output = Path(os.path.abspath(args.output))
                require(not output.exists() and not output.is_symlink(), 'output occupied')
                output.mkdir(mode=0o700)
                path = output / 'install.sh'
                path.write_text(source)
                subprocess.run(['bash', '-n', str(path)], check=True, timeout=15)
                subprocess.run(['shellcheck', str(path)], check=True, timeout=30)
                (output / 'installer.json').write_text(json.dumps({
                    'status': 'offline-installer-preparation-only',
                    'candidate_sha256': candidate.name.removeprefix('candidate-'),
                    'previous_gemian_boot': args.previous_gemian_boot,
                    'installer_sha256': digest(source.encode()),
                    'receipt_name': RECEIPT_NAME, 'device_action': 'none',
                }, indent=2) + '\n')
        print(args.command + '=pass; device_action=none')
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        parser.exit(2, 'CONSYS installer refused: ' + str(error) + '\n')


if __name__ == '__main__':
    main()
