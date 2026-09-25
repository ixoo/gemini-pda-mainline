#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Preserve one recovered PMSG record from a changed, known-good Gemian boot."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import uuid


REPO = Path(__file__).resolve().parents[2]
KEY = REPO / 'artifacts/credentials/gemini_ed25519'
PMSG = '/sys/fs/pstore/pmsg-ramoops-0'
SIZE = 65524
PROBE = '''set -eu
printf 'boot='; cat /proc/sys/kernel/random/boot_id
printf 'arch='; uname -m
printf 'release='; uname -r
printf 'model='; tr -d '\\000' </proc/device-tree/model; printf '\\n'
printf 'mount='; grep ' /sys/fs/pstore ' /proc/self/mountinfo
printf 'pmsg='; find /sys/fs/pstore -maxdepth 1 -name 'pmsg-*' -printf '%f,'; printf '\\n'
printf 'size='; if test -f /sys/fs/pstore/pmsg-ramoops-0; then wc -c </sys/fs/pstore/pmsg-ramoops-0; else printf 'missing\\n'; fi
printf 'boot_after='; cat /proc/sys/kernel/random/boot_id
'''


def ssh(command, *, preserve_partial=False):
    arguments = [
        'ssh', '-i', str(KEY), '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes',
        '-o', 'IdentityAgent=none', '-o', 'StrictHostKeyChecking=yes',
        '-o', 'UpdateHostKeys=no', '-o', 'ConnectTimeout=4',
        'gemini@192.168.1.50', command,
    ]
    try:
        result = subprocess.run(arguments, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=12)
    except subprocess.TimeoutExpired as error:
        if preserve_partial:
            return error.stdout or b'', 'timeout'
        raise
    if preserve_partial:
        return result.stdout, result.returncode
    if result.returncode:
        raise RuntimeError(f'Gemian read failed (status {result.returncode})')
    return result.stdout


def probe(previous):
    lines = ssh(PROBE).decode('ascii').splitlines()
    fields = {}
    for line in lines:
        key, separator, value = line.partition('=')
        if not separator or key in fields:
            raise ValueError('ambiguous Gemian probe')
        fields[key] = value.strip()
    if set(fields) != {'boot', 'arch', 'release', 'model', 'mount', 'pmsg', 'size', 'boot_after'}:
        raise ValueError('incomplete Gemian probe')
    boot = fields['boot']
    if (str(uuid.UUID(boot)) != boot or boot == previous or
            fields['boot_after'] != boot or fields['arch'] != 'aarch64' or
            fields['release'] != '3.18.41+' or fields['model'] != 'MT6797X' or
            fields['pmsg'] != 'pmsg-ramoops-0,' or fields['size'] != str(SIZE)):
        raise ValueError('Gemian identity or recovered PMSG mismatch')
    mount = fields['mount'].split()
    if (len(mount) < 10 or mount[4] != '/sys/fs/pstore' or
            mount[mount.index('-') + 1:][:2] != ['pstore', 'pstore']):
        raise ValueError('Gemian pstore mount mismatch')
    return boot


def save(path, data):
    with path.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--previous-boot-id', required=True)
    parser.add_argument('output', type=Path, help='new directory below ignored artifacts/')
    args = parser.parse_args()
    previous = str(uuid.UUID(args.previous_boot_id))
    if previous != args.previous_boot_id or uuid.UUID(previous).int == 0:
        raise ValueError('invalid preceding boot identity')
    private = REPO / 'artifacts'
    output = args.output.resolve()
    if private not in output.parents or output.exists():
        raise ValueError('output must be a new private artifacts directory')
    if not KEY.is_file() or KEY.stat().st_mode & 0o077:
        raise ValueError('private SSH key missing or permissions too broad')
    first = probe(previous)
    os.umask(0o077)
    output.mkdir(mode=0o700)
    raw, read_status = ssh('cat ' + PMSG, preserve_partial=True)
    save(output / 'pmsg-ramoops-0.bin', raw)
    try:
        second = probe(previous)
    except (ValueError, RuntimeError, UnicodeError, subprocess.TimeoutExpired):
        second = None
    receipt = {
        'previous_gemian_boot_id': previous,
        'recovered_gemian_boot_id': first,
        'same_boot_after_read': second == first,
        'pmsg_size': len(raw),
        'pmsg_sha256': hashlib.sha256(raw).hexdigest(),
        'read_status': read_status,
        'utc_seconds': time.time(),
    }
    save(output / 'receipt.json', (json.dumps(receipt, sort_keys=True, indent=2) + '\n').encode())
    directory = os.open(output, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    if read_status != 0 or len(raw) != SIZE or second != first:
        raise ValueError('preserved PMSG requires review: read, size or boot mismatch')
    print(f'Preserved {SIZE} PMSG bytes from changed Gemian boot {first}.')


if __name__ == '__main__':
    main()
