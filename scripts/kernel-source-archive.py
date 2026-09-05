#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Verify and safely unpack one pinned Linux archive into an empty staging root."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import stat
import tarfile
import tempfile


def components(name):
    if (not name or name.startswith('/') or '\\' in name
            or any(ord(c) < 32 or ord(c) == 127 for c in name)):
        raise ValueError('unsafe archive path')
    parts = name.rstrip('/').split('/')
    if any(part in ('', '.', '..') for part in parts):
        raise ValueError('unsafe archive component')
    return tuple(parts)


def link_target(member, root):
    target = member.linkname
    if not target or target.startswith('/') or '\\' in target:
        raise ValueError('unsafe archive link')
    parts = list(components(member.name)[:-1]) if member.issym() else []
    for part in target.split('/'):
        if any(ord(c) < 32 or ord(c) == 127 for c in part):
            raise ValueError('unsafe link character')
        if part in ('', '.'):
            continue
        if part == '..':
            if len(parts) <= 1:
                raise ValueError('escaping archive link')
            parts.pop()
        else:
            parts.append(part)
    if not parts or parts[0] != root:
        raise ValueError('link outside archive root')
    return tuple(parts)


def inspect(archive, root):
    members = {}
    total = 0
    for member in archive:
        name = components(member.name)
        if name[0] != root:
            raise ValueError('unexpected archive root')
        if name in members:
            raise ValueError('duplicate archive member')
        if not (member.isdir() or member.isfile() or member.issym() or member.islnk()):
            raise ValueError('unsupported archive member type')
        if len(name) == 1 and not member.isdir():
            raise ValueError('archive root is not a directory')
        if member.size < 0 or (not member.isfile() and member.size != 0):
            raise ValueError('invalid archive member size')
        total += member.size
        if len(members) >= 200000 or total > 8 * 1024**3:
            raise ValueError('archive size budget exceeded')
        members[name] = member
    if not members:
        raise ValueError('empty source archive')
    for name, member in members.items():
        for end in range(1, len(name)):
            parent = members.get(name[:end])
            if parent is not None and not parent.isdir():
                raise ValueError('archive member below non-directory')
        if member.issym() or member.islnk():
            target = link_target(member, root)
            # Disallow targets through other links: lexical containment alone
            # does not establish containment after symlink expansion and '..'.
            for end in range(1, len(target) + 1):
                ancestor = members.get(target[:end])
                if ancestor is not None and (ancestor.issym() or ancestor.islnk()):
                    raise ValueError('archive link chain refused')
            if member.islnk() and (target not in members or not members[target].isfile()):
                raise ValueError('hard link requires an archived regular file')
    return members


def unpack(path, destination, digest, archive_format, root):
    destination = Path(destination)
    if destination.is_symlink() or not destination.is_dir() or any(destination.iterdir()):
        raise ValueError('extraction destination must be an empty real directory')
    if components(root) != (root,) or not root.startswith('linux-'):
        raise ValueError('invalid declared archive root')
    mode = {'tar.gz': 'r:gz', 'tar.xz': 'r:xz'}.get(archive_format)
    if mode is None:
        raise ValueError('unsupported declared compression')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as source:
        if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
            raise ValueError('archive is not a regular file')
        sha = hashlib.sha256()
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            sha.update(chunk)
        if sha.hexdigest() != digest:
            raise ValueError('source archive checksum mismatch')
        source.seek(0)
        with tarfile.open(fileobj=source, mode=mode) as archive:
            members = inspect(archive, root)
            # Nothing is installed until the complete archive passed inspection.
            with tempfile.TemporaryDirectory(prefix='.unpack-', dir=destination) as temporary:
                staging = Path(temporary)
                (staging / root).mkdir()
                for name, member in members.items():
                    target = staging.joinpath(*name)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if member.isdir():
                        target.mkdir(exist_ok=True)
                    elif member.isfile():
                        with archive.extractfile(member) as reader, target.open('xb') as writer:
                            shutil.copyfileobj(reader, writer, 1024 * 1024)
                        if target.stat().st_size != member.size:
                            raise ValueError('truncated archive member')
                        target.chmod(member.mode & 0o777)
                for name, member in members.items():
                    target = staging.joinpath(*name)
                    if member.issym():
                        target.symlink_to(member.linkname)
                    elif member.islnk():
                        os.link(staging.joinpath(*link_target(member, root)), target)
                os.replace(staging / root, destination / root)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--format', choices=('tar.gz', 'tar.xz'), required=True)
    parser.add_argument('--root', required=True)
    args = parser.parse_args()
    unpack(args.archive, args.destination, args.sha256, args.format, args.root)


if __name__ == '__main__':
    main()
