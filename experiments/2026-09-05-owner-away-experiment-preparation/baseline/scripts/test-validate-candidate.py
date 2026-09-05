#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Refuse mutated real private candidates without transport or device access.

One managed private copy is reused and removed on every handled outcome. The
original package, candidate and credential files are never changed.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
V = runpy.run_path(str(HERE / 'validate-candidate.py'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--foundation', type=Path, required=True)
    parser.add_argument('--userspace', type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    candidate, foundation, userspace = [p.resolve(strict=True) for p in
                                       (args.candidate, args.foundation, args.userspace)]
    V['validate'](candidate, foundation, userspace)
    managed = V['REPO'] / 'artifacts/a53-authenticated/validation'
    managed.mkdir(mode=0o700, parents=True, exist_ok=True)
    V['AUDIT']['safe_directory'](managed)
    originals = {name: (candidate / name).read_bytes() for name in V['CANDIDATE_FILES']}
    cases = []
    descriptor = os.open(managed / '.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'r+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # One managed name is safely removable after a hard-interrupted run;
        # rmtree never follows member symlinks, which are intentional fixtures.
        stale = managed / '.candidate-refusals'
        V['require'](not stale.is_symlink(), 'unsafe stale fixture root')
        if stale.exists():
            V['require'](stale.is_dir() and stale.stat().st_uid == os.getuid(), 'stale fixture identity')
            shutil.rmtree(stale)
        stale.mkdir(mode=0o700)
        # TemporaryDirectory owns immediate cleanup, inside the held lock.
        with tempfile.TemporaryDirectory(prefix='run-', dir=stale) as temporary:
            run_cases(Path(temporary) / 'candidate', candidate, foundation, userspace, originals, cases)
        stale.rmdir()
    print(json.dumps({'classification': 'private-candidate-refusals-pass', 'rejected_cases': cases,
                      'case_count': len(cases), 'original_candidate': 'unchanged',
                      'private_fixture': 'removed', 'device_access': 'none'}, sort_keys=True))


def run_cases(target, candidate, foundation, userspace, originals, cases):
    shutil.copytree(candidate, target)

    def restore():
        for path in target.iterdir():
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
            else:
                path.unlink()
        for name, data in originals.items():
            path = target / name
            path.write_bytes(data)
            path.chmod(0o600)
        target.chmod(0o700)

    def reject(label, mutate):
        restore()
        mutate()
        try:
            V['validate'](target, foundation, userspace)
        except (ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError):
            cases.append(label)
        else:
            raise ValueError('mutated candidate accepted: ' + label)

    def change_manifest(update):
        path = target / 'candidate.json'
        value = json.loads(path.read_bytes())
        update(value)
        path.write_text(json.dumps(value, sort_keys=True) + '\n')

    for field, value in [('physical_admission', True), ('secret_bearing', False),
                         ('preparation_state', 'ready'), ('foundation_commit', '0' * 40),
                         ('foundation_manifest_sha256', '0' * 64), ('userspace_manifest_sha256', '0' * 64),
                         ('known_hosts_sha256', '0' * 64), ('repository_commit', '0' * 40)]:
        reject('manifest-' + field, lambda field=field, value=value: change_manifest(lambda m: m.update({field: value})))
    reject('unknown-manifest-field', lambda: change_manifest(lambda m: m.update(extra=True)))
    reject('missing-member-record', lambda: change_manifest(lambda m: m['members'].pop('bin/kmsg-seal')))
    reject('changed-member-digest', lambda: change_manifest(lambda m: m['members']['bin/kmsg-seal'].update(sha256='0' * 64)))
    reject('extra-file', lambda: (target / 'extra').write_text('fixture'))
    reject('missing-file', lambda: (target / 'board.dtb').unlink())
    reject('public-file-mode', lambda: (target / 'boot.img').chmod(0o644))
    reject('public-directory-mode', lambda: target.chmod(0o755))
    reject('linked-file', lambda: ((target / 'board.dtb').unlink(), (target / 'board.dtb').symlink_to(candidate / 'board.dtb')))
    reject('hardlinked-file', lambda: ((target / 'board.dtb').unlink(), os.link(target / 'kernel.config', target / 'board.dtb')))
    for name in ('boot.img', 'boot2-padded.img', 'board.dtb', 'Image.gz', 'kernel.config', 'initramfs.img'):
        reject('corrupt-' + name, lambda name=name: (target / name).write_bytes(originals[name][:-1] + bytes([originals[name][-1] ^ 1])))
    restore()
    V['validate'](target, foundation, userspace)


if __name__ == '__main__':
    main()
