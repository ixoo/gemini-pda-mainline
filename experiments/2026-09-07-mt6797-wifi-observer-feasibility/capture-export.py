#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bounded snapshot transfer over an already established binary stream.

This module neither configures USB nor reads device memory. Its receiver
preserves evidence only; it sends no acknowledgement or preparation command.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import struct
import sys
import uuid

SIZE = 65536
HEADER = struct.Struct('<4s16s32s32sI')
MAGIC = b'WFP1'


def identities(boot_id, session_sha256):
    boot = uuid.UUID(boot_id)
    if str(boot) != boot_id or not boot.int:
        raise ValueError('invalid boot identity')
    if (len(session_sha256) != 64 or
            any(c not in '0123456789abcdef' for c in session_sha256)):
        raise ValueError('invalid session digest')
    session = bytes.fromhex(session_sha256)
    if not any(session):
        raise ValueError('empty session digest')
    return boot.bytes, session


def write_all(stream, data):
    while data:
        count = stream.write(data)
        if count is None or count <= 0 or count > len(data):
            raise OSError('incomplete snapshot write')
        data = data[count:]


def read_exact(stream, size):
    result = bytearray()
    while len(result) < size:
        chunk = stream.read(size - len(result))
        if not chunk or len(chunk) > size - len(result):
            raise ValueError('incomplete snapshot transfer')
        result.extend(chunk)
    return bytes(result)


def send_snapshot(stream, snapshot, boot_id, session_sha256):
    boot, session = identities(boot_id, session_sha256)
    if not isinstance(snapshot, bytes) or len(snapshot) != SIZE:
        raise ValueError('expected one immutable complete raw snapshot')
    digest = hashlib.sha256(snapshot).digest()
    write_all(stream, HEADER.pack(MAGIC, boot, session, digest, SIZE))
    write_all(stream, snapshot)
    stream.flush()


def receive_snapshot(stream, output, boot_id, session_sha256):
    """Save one frame; return only after file readback and directory sync.

    The output directory must not exist. A failed save is retained privately
    for inspection; any files left behind do not certify a completed save.
    The caller supplies a deadline/disconnect policy for its chosen stream.
    """
    boot, session = identities(boot_id, session_sha256)
    magic, actual_boot, actual_session, digest, size = HEADER.unpack(
        read_exact(stream, HEADER.size))
    if (magic, actual_boot, actual_session, size) != (MAGIC, boot, session, SIZE):
        raise ValueError('snapshot identity or framing mismatch')
    snapshot = read_exact(stream, SIZE)
    if hashlib.sha256(snapshot).digest() != digest:
        raise ValueError('snapshot digest mismatch')

    output = Path(output)
    # A private, caller-owned parent is required; do not follow an output link
    # or replace a prior export. Never remove evidence after a failed save.
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    parent = os.open(output.parent, flags)
    try:
        info = os.fstat(parent)
        if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077:
            raise ValueError('output parent must be owned and private')
        os.mkdir(output.name, mode=0o700, dir_fd=parent)
        directory = os.open(output.name, flags, dir_fd=parent)
        try:
            receipt = save_snapshot(directory, snapshot, digest, boot_id, session_sha256)
            os.fsync(directory)
        finally:
            os.close(directory)
        # Persist directory creation before reporting success.
        os.fsync(parent)
    finally:
        os.close(parent)
    return receipt


def save_snapshot(directory, snapshot, digest, boot_id, session_sha256):
    name = 'snapshot.raw'
    fd = os.open(name, os.O_RDWR | os.O_CREAT | os.O_EXCL |
                 os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=directory)
    with os.fdopen(fd, 'w+b', buffering=0) as saved:
        write_all(saved, snapshot)
        os.fsync(saved.fileno())
        saved.seek(0)
        if read_exact(saved, SIZE) != snapshot or saved.read(1):
            raise OSError('saved snapshot readback mismatch')
    receipt = {
        'schema': 1, 'boot_id': boot_id,
        'session_sha256': session_sha256,
        'snapshot_sha256': digest.hex(), 'snapshot_bytes': SIZE,
        'scope': 'stream bytes preserved; no physical ownership attestation',
        'clearing_authorized': False,
    }
    data = (json.dumps(receipt, sort_keys=True, indent=2) + '\n').encode()
    fd = os.open('receipt.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=directory)
    with os.fdopen(fd, 'wb', buffering=0) as saved:
        write_all(saved, data)
        os.fsync(saved.fileno())
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--boot-id', required=True)
    parser.add_argument('--session-sha256', required=True)
    parser.add_argument('output', help='new directory below a private parent')
    args = parser.parse_args()
    receive_snapshot(sys.stdin.buffer, args.output, args.boot_id, args.session_sha256)
    print('snapshot preserved; no clearing command sent')


if __name__ == '__main__':
    main()
