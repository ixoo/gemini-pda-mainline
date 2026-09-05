#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Provision private Ed25519 administration material without emitting key bytes."""
import argparse
import base64
import fcntl
import os
from pathlib import Path
import shutil
import struct
import subprocess


def ssh_string(data):
    return struct.pack('>I', len(data)) + data


def take(data):
    if len(data) < 4:
        raise ValueError('truncated SSH field')
    size = struct.unpack('>I', data[:4])[0]
    if size > len(data) - 4:
        raise ValueError('truncated SSH field')
    return data[4:4 + size], data[4 + size:]


def convert_ed25519(raw):
    """Container conversion only; ssh-keygen generates all cryptographic material.

    Dropbear 2026.94 src/ed25519.c uses string(type), string(seed || pub).
    An independent dropbearconvert comparison is required by test-auth.py.
    """
    lines = raw.splitlines()
    # Fragments describe the container delimiter, not stored credential bytes.
    if lines[0] != b'-----' + b'BEGIN OPENSSH PRIVATE KEY' + b'-----' or lines[-1] != b'-----' + b'END OPENSSH PRIVATE KEY' + b'-----':
        raise ValueError('unexpected private-key format')
    blob = base64.b64decode(b''.join(lines[1:-1]), validate=True)
    if not blob.startswith(b'openssh-key-v1\0'):
        raise ValueError('unexpected OpenSSH magic')
    cipher, rest = take(blob[15:])
    kdf, rest = take(rest)
    options, rest = take(rest)
    if (cipher, kdf, options, rest[:4]) != (b'none', b'none', b'', b'\0\0\0\1'):
        raise ValueError('only one unencrypted generated key is accepted')
    outer, rest = take(rest[4:])
    private, rest = take(rest)
    if rest or len(private) < 8 or private[:4] != private[4:8]:
        raise ValueError('private-key framing mismatch')
    kind, private = take(private[8:])
    public, private = take(private)
    secret, private = take(private)
    comment, padding = take(private)
    if kind != b'ssh-ed25519' or len(public) != 32 or len(secret) != 64 or secret[32:] != public:
        raise ValueError('Ed25519 key shape mismatch')
    if outer != ssh_string(kind) + ssh_string(public) or not padding or padding != bytes(range(1, len(padding) + 1)):
        raise ValueError('key integrity framing mismatch')
    return ssh_string(kind) + ssh_string(secret)


def generate(directory):
    directory.mkdir(mode=0o700)
    for name in ('admin', 'host'):
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', '', '-f', str(directory / name)],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=15)
    host = directory / 'host'
    (directory / 'dropbear_host_key').write_bytes(convert_ed25519(host.read_bytes()))
    public = (directory / 'admin.pub').read_text().split()
    (directory / 'authorized_keys').write_text('no-port-forwarding,no-agent-forwarding,no-X11-forwarding ' + ' '.join(public[:2]) + '\n')
    host_public = (directory / 'host.pub').read_text().split()
    (directory / 'known_hosts').write_text('10.15.19.82 ' + ' '.join(host_public[:2]) + '\n')
    for path in directory.iterdir():
        path.chmod(0o600)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', type=Path, required=True)
    args = parser.parse_args()
    repository = args.repository.resolve(strict=True)
    destination = repository / 'artifacts/credentials/a53-auth'
    # Refuse symlink components before creating any state.
    for path in (repository / 'artifacts', repository / 'artifacts/credentials', destination):
        if path.is_symlink():
            raise ValueError('symlink credential path')
    subprocess.run(['git', '-C', str(repository), 'check-ignore', '-q', str(destination)], check=True)
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    destination.parent.chmod(0o700)
    descriptor = os.open(destination.parent / '.a53-provision.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'a') as lock:
        os.fchmod(lock.fileno(), 0o600)
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if destination.exists():
            raise ValueError('credentials already exist; never overwrite')
        stage = destination.parent / '.a53-provision-stage'
        if stage.is_symlink():
            raise ValueError('unsafe stale stage')
        if stage.exists():
            shutil.rmtree(stage)
        try:
            generate(stage)
            stage.rename(destination)
        finally:
            if stage.exists():
                shutil.rmtree(stage)
    print('provisioned=artifacts/credentials/a53-auth; key_bytes_emitted=no; deployment=none')


if __name__ == '__main__':
    main()
