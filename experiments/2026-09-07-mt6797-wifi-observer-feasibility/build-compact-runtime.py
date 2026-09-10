#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Select a boot-sized controller runtime from the pinned preparation archive."""
import copy
import gzip
import hashlib
import io
from pathlib import Path, PurePosixPath
import posixpath
import sys
import tarfile

PARENT = '7ff2ebf4153d8055f92f3baa1c550a3376b913e680162de60a3557ca2d855294'
EXTENSIONS = {
    '_asyncio', '_bz2', '_contextvars', '_json', '_lzma',
    '_multiprocessing', '_posixshmem', '_queue', '_typing',
    'mmap', 'resource', 'termios',
}
LIBRARIES = {
    'ld-linux-aarch64.so.1', 'libc.so.6', 'libm.so.6',
    'libdl.so.2', 'libpthread.so.0',
    'libbz2.so.1.0', 'libbz2.so.1.0.4',
    'libexpat.so.1', 'libexpat.so.1.8.10',
    'liblzma.so.5', 'liblzma.so.5.4.1', 'libz.so.1', 'libz.so.1.2.13',
}


def compact(source):
    if hashlib.sha256(source).hexdigest() != PARENT:
        raise ValueError('parent runtime identity mismatch')
    with tarfile.open(fileobj=io.BytesIO(source), mode='r:gz') as archive:
        members = {m.name.removeprefix('./'): m for m in archive.getmembers()}
        selected = {'bin/busybox', 'usr/bin/python3.11', 'lib/ld-linux-aarch64.so.1',
                    'etc/python3.11/sitecustomize.py'}
        selected.update('lib/aarch64-linux-gnu/' + name for name in LIBRARIES)
        selected.update('usr/lib/python3.11/lib-dynload/' + name +
                        '.cpython-311-aarch64-linux-gnu.so' for name in EXTENSIONS)
        selected.update(name for name in members if
                        (name.startswith('usr/lib/python3.11/') and name.endswith('.py')) or
                        (name.startswith('opt/wifi-cycle/') and name.endswith('.py')) or
                        (name.startswith('usr/share/doc/') and name.endswith('/copyright')) or
                        name.startswith('usr/share/common-licenses/'))
        for name in list(selected):
            selected.update(str(p) for p in PurePosixPath(name).parents if str(p) != '.')
        if not selected <= members.keys():
            raise ValueError('required runtime members absent')
        result = io.BytesIO()
        with tarfile.open(fileobj=result, mode='w', format=tarfile.GNU_FORMAT) as output:
            for name in sorted(selected):
                member = copy.copy(members[name])
                if not (member.isfile() or member.isdir() or member.issym()):
                    raise ValueError('unexpected runtime member type')
                if member.issym():
                    target = posixpath.normpath(str(PurePosixPath(name).parent / member.linkname))
                    if target.lstrip('/') not in selected:
                        raise ValueError('runtime symlink leaves selection')
                member.name = name
                member.uid = member.gid = member.mtime = 0
                member.uname = member.gname = ''
                output.addfile(member, archive.extractfile(members[name]) if member.isfile() else None)
        compressed = io.BytesIO()
        with gzip.GzipFile(filename='', mode='wb', fileobj=compressed,
                           compresslevel=9, mtime=0) as stream:
            stream.write(result.getvalue())
        return compressed.getvalue()


def main():
    if len(sys.argv) != 3:
        raise SystemExit('usage: build-compact-runtime.py PARENT_TAR NEW_TAR')
    source, destination = map(Path, sys.argv[1:])
    if source.is_symlink():
        raise ValueError('parent must be a regular file')
    payload = compact(source.read_bytes())
    with destination.open('xb') as output:
        output.write(payload)
    print('runtime_bytes=' + str(len(payload)))
    print('runtime_sha256=' + hashlib.sha256(payload).hexdigest())


if __name__ == '__main__':
    main()
