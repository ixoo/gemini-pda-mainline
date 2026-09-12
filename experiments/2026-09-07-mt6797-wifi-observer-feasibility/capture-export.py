#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bounded snapshot transfer over an already established binary stream.

This module neither configures USB nor reads device memory. Its receiver may
acknowledge durable preservation; that acknowledgement authorizes no clearing.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import select
import stat
import struct
import time
import tty
import uuid

SIZE = 65536
HEADER = struct.Struct('<4s16s32s32sI')
MAGIC = b'WFP1'
REQUEST = struct.Struct('<4s16s32s')
PRESERVED = struct.Struct('<4s16s32s32s')


class SerialStream:
    """Unbuffered I/O on an already open nonblocking terminal, one deadline."""
    def __init__(self, fd, seconds=60):
        self.fd = fd
        self.deadline = time.monotonic() + seconds

    def transfer(self, value, writing):
        while True:
            remaining = self.deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('snapshot transport deadline expired')
            readable, writable, _ = select.select(
                [] if writing else [self.fd], [self.fd] if writing else [], [], remaining)
            if not (readable or writable):
                raise TimeoutError('snapshot transport deadline expired')
            try:
                return os.write(self.fd, value) if writing else os.read(self.fd, value)
            except BlockingIOError:
                continue

    def read(self, size):
        return self.transfer(size, False)

    def write(self, data):
        return self.transfer(data, True)

    def flush(self):
        # No userspace buffer; this is not a USB drain/receipt acknowledgement.
        pass


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


def request_snapshot(stream, previous_boot_id, session_sha256):
    previous, session = identities(previous_boot_id, session_sha256)
    write_all(stream, REQUEST.pack(b'WFR1', previous, session))
    stream.flush()


def await_request(stream, boot_id, session_sha256):
    boot, session = identities(boot_id, session_sha256)
    magic, previous, selected = REQUEST.unpack(read_exact(stream, REQUEST.size))
    if magic != b'WFR1' or not any(previous) or previous == boot or selected != session:
        raise ValueError('snapshot request identity mismatch')


def await_preserved(stream, snapshot, boot_id, session_sha256):
    boot, session = identities(boot_id, session_sha256)
    if not isinstance(snapshot, bytes) or len(snapshot) != SIZE:
        raise ValueError('expected the complete immutable snapshot')
    expected = (b'WFA1', boot, session, hashlib.sha256(snapshot).digest())
    if PRESERVED.unpack(read_exact(stream, PRESERVED.size)) != expected:
        raise ValueError('snapshot preservation acknowledgement mismatch')


def open_private_parent(output):
    if not output.name or output.name in ('.', '..'):
        raise ValueError('expected a new output directory name')
    fd = os.open(output.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        info = os.fstat(fd)
        if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077:
            raise ValueError('output parent must be owned and private')
        if not os.access('.', os.W_OK | os.X_OK, dir_fd=fd, effective_ids=True):
            raise ValueError('output parent is not writable and searchable')
    except BaseException:
        os.close(fd)
        raise
    return fd


def check_destination(output):
    """Reject an unusable existing destination before requesting the one shot."""
    output = Path(output)
    parent = open_private_parent(output)
    try:
        try:
            os.stat(output.name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            return
        raise FileExistsError('snapshot output already exists')
    finally:
        os.close(parent)


def receive_snapshot(stream, output, previous_boot_id, session_sha256, *, acknowledge=False):
    """Save one frame; return only after file readback and directory sync.

    The output directory must not exist. A failed save is retained privately
    for inspection; any files left behind do not certify a completed save.
    The caller supplies a deadline/disconnect policy for its chosen stream.
    """
    previous, session = identities(previous_boot_id, session_sha256)
    magic, actual_boot, actual_session, digest, size = HEADER.unpack(
        read_exact(stream, HEADER.size))
    if ((magic, actual_session, size) != (MAGIC, session, SIZE) or
            not any(actual_boot) or actual_boot == previous):
        raise ValueError('snapshot identity or framing mismatch')
    boot_id = str(uuid.UUID(bytes=actual_boot))
    snapshot = read_exact(stream, SIZE)
    if hashlib.sha256(snapshot).digest() != digest:
        raise ValueError('snapshot digest mismatch')

    output = Path(output)
    # A private, caller-owned parent is required; do not follow an output link
    # or replace a prior export. Never remove evidence after a failed save.
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    parent = open_private_parent(output)
    try:
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
    # This comes after raw readback, both files' fsync and both directory syncs.
    # No acknowledgement is sent after any failed save or sync.
    if acknowledge:
        write_all(stream, PRESERVED.pack(b'WFA1', actual_boot, actual_session, digest))
        stream.flush()
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
    parser.add_argument('--previous-boot-id', required=True)
    parser.add_argument('--session-sha256', required=True)
    parser.add_argument('--serial', required=True, help='explicit host USB serial terminal')
    parser.add_argument('--acknowledge', action='store_true',
                        help='send one bound preservation acknowledgement after durable save')
    parser.add_argument('output', help='new directory below a private parent')
    args = parser.parse_args()
    identities(args.previous_boot_id, args.session_sha256)
    check_destination(args.output)
    fd = os.open(args.serial, os.O_RDWR | os.O_NONBLOCK | os.O_NOCTTY |
                 os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        if not stat.S_ISCHR(os.fstat(fd).st_mode) or not os.isatty(fd):
            raise ValueError('expected a serial terminal')
        tty.setraw(fd, when=tty.TCSANOW)
        stream = SerialStream(fd)
        request_snapshot(stream, args.previous_boot_id, args.session_sha256)
        receive_snapshot(stream, args.output, args.previous_boot_id, args.session_sha256,
                         acknowledge=args.acknowledge)
    finally:
        os.close(fd)
    print('snapshot preserved; acknowledgement sent' if args.acknowledge else
          'snapshot preserved; no clearing command sent')


if __name__ == '__main__':
    main()
