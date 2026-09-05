#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Acquire and inspect one immutable upstream snapshot on Buildbox; never extract."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import posixpath
import shutil
import tarfile
import tempfile
import time
import urllib.request

HERE = Path(__file__).resolve().parent
REVISION = '4d7d9486c04d917265f64c55bd23b2cc4fe7749c'
URL = 'https://codeload.github.com/torvalds/linux/tar.gz/' + REVISION
ARCHIVE_ROOT = 'linux-' + REVISION
CACHE = Path('/workspace/gemini-pda/cache/upstream-snapshots')
MAX_COMPRESSED = 512 * 1024 * 1024
MAX_CONTENT = 8 * 1024 * 1024 * 1024
MAX_MEMBERS = 200000


def safe_member(member, root):
    name = member.name
    parts = name.split('/')
    if (name.startswith('/') or any(p in ('', '.', '..') for p in parts)
            or parts[0] != root or any(ord(c) < 32 for c in name)):
        raise ValueError('unsafe archive member path')
    if not (member.isfile() or member.isdir() or member.issym() or member.islnk()):
        raise ValueError('unsupported archive member type')
    if member.issym() or member.islnk():
        target = member.linkname
        if target.startswith('/') or any(ord(c) < 32 for c in target):
            raise ValueError('unsafe archive link')
        resolved = posixpath.normpath(posixpath.join(posixpath.dirname(name), target)
                                     if member.issym() else target)
        if resolved != root and not resolved.startswith(root + '/'):
            raise ValueError('archive link escapes root')
    return name


def inspect(path, inputs):
    expected = {ARCHIVE_ROOT + '/' + entry['path']: entry for entry in inputs}
    found, seen = {}, set()
    size = 0
    with tarfile.open(path, mode='r|gz') as archive:
        for member in archive:
            name = safe_member(member, ARCHIVE_ROOT)
            if name in seen or len(seen) >= MAX_MEMBERS:
                raise ValueError('duplicate or excessive archive members')
            seen.add(name)
            if member.size < 0:
                raise ValueError('negative archive member size')
            size += member.size
            if size > MAX_CONTENT:
                raise ValueError('archive content exceeds bound')
            if name in expected:
                entry = expected[name]
                if not member.isfile() or member.size != entry['bytes']:
                    raise ValueError('review input type or size mismatch')
                stream = archive.extractfile(member)
                data = stream.read(entry['bytes'] + 1)
                sha = hashlib.sha256(data).hexdigest()
                if sha != entry['sha256']:
                    raise ValueError('review input checksum mismatch')
                found[entry['path']] = sha
    if len(found) != len(expected):
        raise ValueError('review inputs missing from archive')
    return {'member_count': len(seen), 'uncompressed_member_bytes': size,
            'reviewed_inputs': found}


def file_hash(path):
    sha = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            sha.update(chunk)
    return sha.hexdigest()


def main():
    if platform.system() != 'Linux' or not str(HERE).startswith('/workspace/gemini-pda/'):
        raise ValueError('Buildbox checkout required')
    inputs = json.loads((HERE.parent / 'archive-inputs.json').read_text())
    if inputs['upstream_commit'] != REVISION:
        raise ValueError('archive revision mismatch')
    CACHE.mkdir(exist_ok=True)
    if CACHE.is_symlink() or shutil.disk_usage(CACHE).free < 2 * 1024**3:
        raise ValueError('unsafe cache or insufficient free space')
    final = CACHE / ('linux-' + REVISION + '.tar.gz')
    lock = CACHE / '.acquire.lock'
    if lock.is_symlink():
        raise ValueError('unsafe cache lock')
    with lock.open('a') as locking:
        fcntl.flock(locking, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if final.is_symlink() or (final.exists() and not final.is_file()):
            raise ValueError('unsafe retained archive')
        for stale in CACHE.glob('.acquire-*'):
            if stale.is_symlink() or not stale.is_dir():
                raise ValueError('unsafe stale acquisition directory')
            entries = list(stale.iterdir())
            if any(p.name != 'source.tar.gz' or p.is_symlink() or not p.is_file() for p in entries):
                raise ValueError('unexpected stale acquisition contents')
            shutil.rmtree(stale)
        if final.exists():
            published = HERE.parent / 'results/upstream-archive.json'
            if not published.is_file():
                raise ValueError('retained archive requires a published checksum before reuse')
            known = json.loads(published.read_text())
            if (known['upstream_commit'] != REVISION or known['source_url'] != URL
                    or file_hash(final) != known['sha256']):
                raise ValueError('retained archive differs from published identity')
        with tempfile.TemporaryDirectory(prefix='.acquire-', dir=CACHE) as temporary:
            archive = final if final.exists() else Path(temporary) / 'source.tar.gz'
            reused = final.exists()
            if not reused:
                started = time.monotonic()
                received = 0
                with urllib.request.urlopen(URL, timeout=30) as response, archive.open('xb') as output:
                    if response.status != 200 or response.url != URL:
                        raise ValueError('unexpected snapshot response')
                    while chunk := response.read(1024 * 1024):
                        received += len(chunk)
                        if received > MAX_COMPRESSED or time.monotonic() - started > 300:
                            raise ValueError('archive download exceeds bound')
                        output.write(chunk)
                    output.flush()
                    os.fsync(output.fileno())
            if not 0 < archive.stat().st_size <= MAX_COMPRESSED:
                raise ValueError('archive size outside bound')
            result = inspect(archive, inputs['remote'])
            sha = file_hash(archive)
            count = archive.stat().st_size
            if not reused:
                os.replace(archive, final)
            print(json.dumps({**result, 'upstream_commit': REVISION, 'source_url': URL,
                              'sha256': sha, 'bytes': count, 'archive_format': 'tar.gz',
                              'archive_root': ARCHIVE_ROOT, 'cache_reused': reused,
                              'cache_relative_path': str(final.relative_to('/workspace/gemini-pda')),
                              'source_tree_extracted': False, 'kernel_build': 'not run',
                              'attribution': 'immutable upstream HTTPS snapshot; reviewed input hashes agree; full Git tree equivalence not independently established'},
                             indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
