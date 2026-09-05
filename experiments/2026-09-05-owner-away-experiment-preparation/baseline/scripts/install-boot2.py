#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Validate an exact A53 installer; --execute explicitly enables deployment."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import signal
import stat
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
from installer import derive, pinned_sources, REPO, HERE, RECEIPT_NAME


def run_installer(command):
    """Forward interruption to the complete local transport process group."""
    process = subprocess.Popen(command, start_new_session=True)
    received = []
    previous = {}

    def forward(number, _frame):
        received.append(number)
        try:
            os.killpg(process.pid, number)
        except ProcessLookupError:
            pass

    for number in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM):
        previous[number] = signal.signal(number, forward)
    try:
        try:
            status = process.wait(timeout=360)
        except subprocess.TimeoutExpired:
            forward(signal.SIGTERM, None)
            try:
                process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)
            raise ValueError('deployment deadline expired; no completed receipt is established') from None
        if received:
            raise ValueError('deployment interrupted; inspect private evidence before any new attempt')
        if status:
            raise subprocess.CalledProcessError(status, command)
    finally:
        for number, handler in previous.items():
            signal.signal(number, handler)


def prepare(args):
    candidate, foundation, userspace = (path.resolve(strict=True) for path in
                                      (args.candidate, args.foundation, args.userspace))
    validator = runpy.run_path(str(HERE / 'validate-candidate.py'))
    validator['validate'](args.candidate, args.foundation, args.userspace)
    source = derive(pinned_sources(), REPO, candidate, foundation, userspace)
    return source, candidate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('candidate', 'foundation', 'userspace'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--execute', action='store_true', help='install, verify and shut down the exact known-good device')
    parser.add_argument('--target', help='required with --execute; only gemini@192.168.1.50 is accepted')
    args = parser.parse_args()
    if args.execute and args.target != 'gemini@192.168.1.50':
        parser.error('--execute requires the exact --target gemini@192.168.1.50')
    if not args.execute and args.target is not None:
        parser.error('--target requires --execute; default operation is local validation only')
    os.umask(0o077)
    try:
        for program in ('bash', 'shellcheck'):
            if shutil.which(program) is None:
                raise ValueError('required local validator missing: ' + program)
        source, candidate = prepare(args)
        managed = REPO / 'artifacts/a53-authenticated/installer-work'
        for parent in (managed, *managed.parents):
            if parent.is_symlink():
                raise ValueError('symlink in installer work path')
        managed.mkdir(parents=True, exist_ok=True, mode=0o700)
        info = managed.stat()
        if stat.S_IMODE(info.st_mode) != 0o700 or info.st_uid != os.getuid():
            raise ValueError('installer work directory is not private')
        # One deterministic managed root; each temporary derivation is removed
        # on success and exception, and never becomes a candidate member.
        with tempfile.TemporaryDirectory(prefix='derive-', dir=managed) as temporary:
            path = Path(temporary) / 'install.sh'
            path.write_text(source)
            path.chmod(0o600)
            subprocess.run(['bash', '-n', str(path)], check=True, timeout=15)
            subprocess.run(['shellcheck', str(path)], check=True, timeout=30)
            if args.execute:
                evidence = REPO / 'artifacts/device-install-evidence' / RECEIPT_NAME
                run_installer(['bash', str(path), '--target', args.target,
                               '--candidate-dir', str(candidate), '--evidence-dir', str(evidence)])
            else:
                print(json.dumps({'installer_derivation': 'pass', 'installer_sha256': hashlib.sha256(source.encode()).hexdigest(),
                                  'mode': 'local-validation-only', 'device_action': 'none', 'physical_admission': False}, sort_keys=True))
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        parser.exit(2, 'A53 installer refused: ' + str(error) + '\n')


if __name__ == '__main__':
    main()
