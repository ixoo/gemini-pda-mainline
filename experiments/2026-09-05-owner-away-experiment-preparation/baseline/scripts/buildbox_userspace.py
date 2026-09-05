#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build once, or recover a published userspace package without rebuilding."""
import argparse
import fcntl
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import selectors
import signal
import time
import stat
import subprocess
import tarfile

REPO = Path(__file__).resolve().parents[4]
ORIGIN = 'https://github.com/ixoo/gemini-pda-mainline.git'
BRANCH = 'codex/a53-authenticated-baseline'
SSH = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5', '-o',
       'ServerAliveInterval=10', '-o', 'ServerAliveCountMax=3', '-o', 'ForwardAgent=no', 'buildbox']
REMOTE_BUILD = r'''
set -euo pipefail
umask 077
revision=$1
branch=$2
kind=$3
[[ $kind == userspace || $kind == keyboard-monitor ]]
[[ $revision =~ ^[0-9a-f]{40}$ && $branch == codex/a53-authenticated-baseline ]]
root=/workspace/gemini-a53-userspace
[[ ! -L $root ]]
mkdir -p "$root/checkouts"
exec 8>"$root/.dispatch.lock"
flock -n 8
checkout="$root/checkouts/$revision"
[[ ! -L $checkout ]]
if [[ ! -e $checkout ]]; then
  partial="$root/checkouts/.partial"
  [[ ! -L $partial ]]
  if [[ -e $partial ]]; then rm -rf -- "$partial"; fi
  mkdir "$partial"
  cleanup() { rm -rf -- "$partial"; }
  trap cleanup EXIT
  trap 'exit 130' INT
  trap 'exit 143' HUP TERM
  git -C "$partial" init -q
  git -C "$partial" remote add origin https://github.com/ixoo/gemini-pda-mainline.git
  git -C "$partial" fetch -q origin "refs/heads/$branch:refs/remotes/origin/$branch"
  [[ $(git -C "$partial" rev-parse "origin/$branch") == "$revision" ]]
  git -C "$partial" checkout -q --detach "$revision"
  mv "$partial" "$checkout"
  trap - EXIT HUP INT TERM
fi
if [[ $kind == keyboard-monitor ]]; then
  timeout 1200 bash "$checkout/experiments/2026-09-05-owner-away-experiment-preparation/keyboard/build-monitor.sh" "$revision" "$root"
else
  bash "$checkout/experiments/2026-09-05-owner-away-experiment-preparation/baseline/scripts/build-userspace.sh" "$revision" "$root"
fi
'''
REMOTE_FETCH = r'''
set -euo pipefail
revision=$1
identity=$2
kind=$3
[[ $kind == userspace || $kind == keyboard-monitor ]]
publication=published
[[ $kind == userspace ]] || publication=keyboard-monitor-published
[[ $revision =~ ^[0-9a-f]{40}$ && $identity =~ ^[0-9a-f]{64}$ ]]
root=/workspace/gemini-a53-userspace
exec 8>"$root/.dispatch.lock"
flock -n 8
[[ -f $root/$publication/$revision && ! -L $root/$publication/$revision ]]
[[ $(cat "$root/$publication/$revision") == "$identity" ]]
package="$root/$kind-$identity"
[[ -d $package && ! -L $package ]]
cd "$package"
[[ $(sha256sum SHA256SUMS | cut -d' ' -f1) == "$identity" ]]
sha256sum -c --strict SHA256SUMS >/dev/null
[[ $(grep -c '^repository_commit=' provenance.txt) == 1 ]]
grep -Fxq "repository_commit=$revision" provenance.txt
tar -czf - .
'''


def require(value, message):
    if not value:
        raise ValueError(message)


def git(*args):
    return subprocess.check_output(['git', '-C', str(REPO), *args], text=True).strip()


def managed_dir(path):
    require(not path.is_symlink(), 'managed directory symlink')
    path.mkdir(mode=0o700, exist_ok=True)
    info = path.stat()
    require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.getuid(), 'managed directory owner/type')


def clear_partial(stage):
    """Only this fixed managed name is disposable; never follow linked state."""
    require(stage.name in ('.fetch-userspace', '.fetch-keyboard-monitor'), 'unexpected partial name')
    if not stage.exists() and not stage.is_symlink():
        return
    require(not stage.is_symlink() and stage.is_dir(), 'partial path type')
    for directory, dirs, files in os.walk(stage, followlinks=False):
        for path in [Path(directory), *(Path(directory) / name for name in dirs + files)]:
            info = path.lstat()
            require(info.st_uid == os.getuid() and not stat.S_ISLNK(info.st_mode) and
                    (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)), 'unsafe partial state')
    shutil.rmtree(stage)


def check_package(target, identity, revision):
    sums = target / 'SHA256SUMS'
    require(sums.is_file() and not sums.is_symlink(), 'package manifest type')
    raw = sums.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == identity, 'package manifest identity')
    seen = set()
    for line in raw.decode('ascii').splitlines():
        match = re.fullmatch(r'([0-9a-f]{64})  \./(.+)', line)
        require(match is not None, 'checksum line')
        sha, name = match.groups()
        path = PurePosixPath(name)
        require(not path.is_absolute() and '..' not in path.parts and str(path) == name and
                name not in seen and name != 'SHA256SUMS', 'checksum path/inventory')
        file = target / name
        require(file.is_file() and not file.is_symlink() and file.stat().st_nlink == 1 and
                hashlib.sha256(file.read_bytes()).hexdigest() == sha, 'package file checksum/type')
        seen.add(name)
    actual = set()
    for directory, dirs, names in os.walk(target, followlinks=False):
        for name in dirs:
            require(not (Path(directory) / name).is_symlink(), 'package directory symlink')
        for name in names:
            actual.add((Path(directory) / name).relative_to(target).as_posix())
    require(actual == seen | {'SHA256SUMS'}, 'package exact inventory')
    provenance = (target / 'provenance.txt').read_text().splitlines()
    require([line for line in provenance if line.startswith('repository_commit=')] ==
            ['repository_commit=' + revision], 'package revision')


def extract(archive_path, target, identity, revision):
    target.mkdir(mode=0o700)
    seen = set()
    with tarfile.open(archive_path, mode='r|gz') as archive:
        count, total = 0, 0
        for item in archive:
            count += 1
            total += item.size
            require(count <= 40 and 0 <= item.size <= 33554432 and total <= 33554432, 'package size/inventory')
            path = PurePosixPath(item.name)
            require(not path.is_absolute() and '..' not in path.parts and
                    (item.isfile() or item.isdir()) and str(path) not in seen, 'unsafe archive path/type')
            seen.add(str(path))
            destination = target / path
            if item.isdir():
                destination.mkdir(mode=0o700, parents=True, exist_ok=True)
            else:
                destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                with destination.open('xb') as output:
                    shutil.copyfileobj(archive.extractfile(item), output)
                destination.chmod(0o700 if item.mode & 0o111 else 0o600)
    check_package(target, identity, revision)



def fetch_bounded(command, script, path, *, limit=33554432, timeout=180):
    """Cap transfer bytes while streaming; kill/reap on timeout or interruption."""
    process = None
    selector = selectors.DefaultSelector()
    handlers, interrupted = {}, []
    deadline = time.monotonic() + timeout
    try:
        for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            handlers[number] = signal.signal(number, lambda signum, _frame: interrupted.append(signum))
        with path.open('xb') as output:
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, start_new_session=True)
            require(len(script) <= 4096, 'fetch script bound')
            process.stdin.write(script)
            process.stdin.close()
            os.set_blocking(process.stdout.fileno(), False)
            selector.register(process.stdout, selectors.EVENT_READ)
            count = 0
            while selector.get_map():
                require(not interrupted, 'fetch interrupted')
                require(time.monotonic() < deadline - 1, 'fetch deadline')
                for key, _ in selector.select(0.1):
                    data = os.read(key.fileobj.fileno(), 65536)
                    if not data:
                        selector.unregister(key.fileobj)
                        break
                    require(len(data) <= limit - count, 'compressed transfer byte cap')
                    output.write(data)
                    count += len(data)
            while process.poll() is None:
                require(not interrupted, 'fetch interrupted')
                require(time.monotonic() < deadline - 1, 'fetch deadline')
                try:
                    process.wait(timeout=0.1)
                except subprocess.TimeoutExpired:
                    pass
            require(not interrupted, 'fetch interrupted')
            require(process.returncode == 0, 'remote fetch failed')
    finally:
        if process is not None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=1)
            for stream in (process.stdin, process.stdout):
                if stream and not stream.closed:
                    stream.close()
        selector.close()
        for number, previous in handlers.items():
            signal.signal(number, previous)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch-only', nargs=2, metavar=('REVISION', 'MANIFEST_SHA256'),
                        help='recover an already published exact package; never builds')
    parser.add_argument('--keyboard-monitor', action='store_true', help='build/fetch the disabled keyboard monitor only')
    args = parser.parse_args()
    kind = 'keyboard-monitor' if args.keyboard_monitor else 'userspace'
    os.umask(0o077)
    require(git('remote', 'get-url', 'origin') == ORIGIN, 'unexpected origin')
    if args.fetch_only:
        revision, identity = args.fetch_only
        require(re.fullmatch('[0-9a-f]{40}', revision) and re.fullmatch('[0-9a-f]{64}', identity),
                'recovery identity format')
        require(git('rev-parse', revision + '^{commit}') == revision, 'unknown revision')
    else:
        require(not git('status', '--porcelain'), 'build source checkout must be clean')
        require(git('branch', '--show-current') == BRANCH, 'build branch')
        revision = git('rev-parse', 'HEAD')
        require(git('ls-remote', '--exit-code', 'origin', 'refs/heads/' + BRANCH).split()[0] == revision,
                'build revision must be published')
        identity = None
    output = REPO / 'artifacts/buildbox' / revision
    for directory in (REPO / 'artifacts', REPO / 'artifacts/buildbox', output):
        managed_dir(directory)
    descriptor = os.open(output / '.userspace-transfer.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'r+') as lock:
        require(os.fstat(lock.fileno()).st_nlink == 1 and os.fstat(lock.fileno()).st_uid == os.getuid(),
                'transfer lock identity')
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if identity is None:
            log = output / (kind + '-build.log')
            require(not log.exists() and not log.is_symlink(),
                    'build log already exists; preserve it and use --fetch-only for a published package')
            with log.open('xb') as stream:
                result = subprocess.run(SSH + ['/bin/bash', '-s', '--', revision, BRANCH, kind],
                                        input=REMOTE_BUILD.encode(), stdout=stream,
                                        stderr=subprocess.STDOUT, timeout=1800)
            print(log.read_text(errors='replace'), end='', flush=True)
            require(result.returncode == 0, 'userspace build failed; diagnostics preserved in userspace-build.log')
            matches = re.findall(r'^validated_' + kind.replace('-', '_') + r'_package=/workspace/gemini-a53-userspace/' + kind + r'-([0-9a-f]{64})$',
                                 log.read_text(), re.MULTILINE)
            require(len(matches) == 1, 'published package identity missing; inspect exact remote publication receipt')
            identity = matches[0]
            require(not git('status', '--porcelain') and git('rev-parse', 'HEAD') == revision,
                    'source changed during build')
        stage = output / ('.fetch-' + kind)
        destination = output / (kind + '-' + identity)
        clear_partial(stage)
        if destination.exists() or destination.is_symlink():
            require(not destination.is_symlink() and destination.is_dir(), 'destination type')
            check_package(destination, identity, revision)
        else:
            stage.mkdir(mode=0o700)
            try:
                fetch_bounded(SSH + ['/bin/bash', '-s', '--', revision, identity, kind], REMOTE_FETCH.encode(),
                              stage / 'package.tar.gz')
                extract(stage / 'package.tar.gz', stage / 'package', identity, revision)
                os.rename(stage / 'package', destination)
            finally:
                clear_partial(stage)
        print('fetched_' + kind.replace('-', '_') + '=' + destination.relative_to(REPO).as_posix())


if __name__ == '__main__':
    main()
