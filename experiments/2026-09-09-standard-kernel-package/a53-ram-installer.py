#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare the service RAM installer offline; never execute device access."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import shlex
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
BASELINE = REPO / 'experiments/2026-09-05-owner-away-experiment-preparation/baseline/scripts'
RECEIPT_NAME = 'a53-service-ram-deployment-1'
EXPERIMENT = 'a53-service-ram-regression'
PINS = {
    BASELINE / 'installer.py': '405749e387a5b4383b56a3073575f7a26b335a42f9ecafb22f126b5578973467',
    BASELINE / 'deployment_receipt.py': 'a2dc643ddedf5c9c93ede43598208cafd17242fccbb45db6ddaf078f30ae6f23',
    HERE / 'a53-ram-session.py': '0955b3e035487d90d58d1688d9ea6c2350392e8f592fe0b862eecbb6d98a5629',
    HERE / 'results/a53-service-ram-candidate.json': '0c6df48ed7312d978d9ef6b650063af5a78db259d7e9831fb2c80eef9e65e46f',
}
MANIFEST_SHA = 'e9126ef952c3174e047b7da6237366e6b2374df9d02de6dcea9f193b501d8255'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sources():
    for path, expected in PINS.items():
        if path.is_symlink() or digest(path.read_bytes()) != expected:
            raise ValueError('installer adapter input changed: ' + path.name)
    return (runpy.run_path(str(HERE / 'a53-ram-session.py')),
            runpy.run_path(str(BASELINE / 'installer.py')),
            runpy.run_path(str(BASELINE / 'deployment_receipt.py')))


def validate(candidate, previous):
    session, _, _ = sources()
    context, collector, _, _ = session['prepare'](candidate, previous)
    if candidate.name != 'candidate-' + context['admission']['candidate_sha256']:
        raise ValueError('candidate directory does not name the exact raw boot image')
    if digest(collector.regular(candidate / 'candidate.json', 65536)) != MANIFEST_SHA:
        raise ValueError('candidate manifest changed')
    return context, collector


def receipt(raw, candidate_sha, manifest_sha, previous):
    session, _, parser = sources()
    session['boot_uuid'](previous)
    original = 'experiment=' + EXPERIMENT
    lines = raw.splitlines()
    if lines.count(original) != 1 or any(line.startswith('experiment=') and line != original for line in lines):
        raise ValueError('wrong or duplicate service RAM experiment receipt')
    translated = '\n'.join('experiment=a53-authenticated-baseline' if line == original else line for line in lines)
    boot = parser['receipt'](translated, candidate_sha, manifest_sha)
    if boot != previous:
        raise ValueError('deployment belongs to a different preceding Gemian boot')
    return boot


def adapt(source, repo, candidate, previous):
    """Exact text delta, called only after candidate validation by prepare()."""
    tool = repo / Path(__file__).relative_to(REPO)
    baseline = repo / BASELINE.relative_to(REPO)

    def replace(old, new, count=1):
        nonlocal source
        if source.count(old) != count:
            raise ValueError('service RAM installer anchor changed: ' + old[:70])
        source = source.replace(old, new)

    validator = baseline / 'validate-candidate.py'
    old = shlex.join(['python3', str(validator), '--foundation', str(candidate), '--userspace', str(candidate)])
    new = shlex.join(['python3', str(tool), 'validate', '--previous-gemian-boot', previous])
    replace(old, new)
    # The generated shell verifies the new validator before any transport.
    def check(path):
        return ('[[ "$(sha256sum ' + shlex.quote(str(path)) + " | awk '{print $1}')\" == " +
                digest(path.read_bytes()) + " ]] || die 'validation tool changed'\n")
    replace(check(validator), check(tool) + check(tool.parent / 'results/a53-service-ram-candidate.json'))
    old = shlex.join(['python3', str(baseline / 'deployment_receipt.py'), '--candidate-sha256'])
    new = shlex.join(['python3', str(tool), 'receipt', '--previous-gemian-boot', previous, '--candidate-sha256'])
    replace(old, new)
    replace('a53-authenticated-baseline-deployment-2', RECEIPT_NAME, 3)
    replace("printf 'experiment=a53-authenticated-baseline\\n", "printf 'experiment=" + EXPERIMENT + "\\n")
    anchor = "[[ \"$initial_boot_id\" =~ ^[0-9a-f-]{36}$ ]] || die 'malformed initial boot ID'\n"
    replace(anchor, anchor + '[[ "$initial_boot_id" == ' + shlex.quote(previous) + " ]] || die 'preceding Gemian boot changed'\n")
    return source


def prepare(candidate, previous):
    context, collector = validate(candidate, previous)
    _, installer, _ = sources()
    source = installer['derive'](installer['pinned_sources'](), REPO, candidate, candidate, candidate)
    return adapt(source, REPO, candidate, previous), context, collector


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('prepare', 'validate', 'receipt'):
        command = commands.add_parser(name)
        command.add_argument('--previous-gemian-boot', required=True)
        if name == 'receipt':
            command.add_argument('--receipt', type=Path, required=True)
            command.add_argument('--candidate-sha256', required=True)
            command.add_argument('--candidate-manifest-sha256', required=True)
        else:
            command.add_argument('--candidate', type=Path, required=True)
        if name == 'prepare':
            command.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    try:
        if args.command == 'receipt':
            if args.receipt.is_symlink() or not args.receipt.is_file():
                raise ValueError('unsafe receipt file')
            receipt(args.receipt.read_text(), args.candidate_sha256,
                    args.candidate_manifest_sha256, args.previous_gemian_boot)
        else:
            candidate = Path(os.path.abspath(args.candidate))
            if args.command == 'validate':
                validate(candidate, args.previous_gemian_boot)
            else:
                source, context, collector = prepare(candidate, args.previous_gemian_boot)
                output = Path(os.path.abspath(args.output))
                for path in (output, *output.parents):
                    if path.is_symlink():
                        raise ValueError('symlink output path')
                output.mkdir(mode=0o700)
                collector.write_new(output / 'install.sh', source.encode())
                subprocess.run(['bash', '-n', str(output / 'install.sh')], check=True, timeout=15)
                subprocess.run(['shellcheck', str(output / 'install.sh')], check=True, timeout=30)
                record = {'status': 'offline-installer-preparation-only', 'device_action': 'none',
                          'physical_admission': False, 'candidate_sha256': context['admission']['candidate_sha256'],
                          'previous_gemian_boot': args.previous_gemian_boot,
                          'installer_sha256': digest(source.encode()), 'receipt_name': RECEIPT_NAME,
                          'identity_warning': 'The supplied boot UUID is a binding, not an observation. No execution or selection budget is granted.'}
                collector.write_new(output / 'installer.json', (json.dumps(record, indent=2) + '\n').encode())
        print(args.command + '=pass; device_action=none')
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        parser.exit(2, 'service RAM installer refused: ' + str(error) + '\n')


if __name__ == '__main__':
    main()
