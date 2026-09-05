#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Read-only complete prefix/library gate around the one admitted QEMU run."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess

REVISION = '30f20586cf19293fd985e4aec838c75b3d1c94c6'
EXPERIMENT = 'experiments/2026-09-05-mt6797-infracfg-upstream-preparation'
RECEIPT_MAX_BYTES = 4 * 1024 * 1024


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def sha(path):
    require(stat.S_ISREG(path.lstat().st_mode), 'regular file required: ' + str(path))
    h = hashlib.sha256()
    with path.open('rb') as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def receipt_snapshot(path):
    # A single bounded snapshot supplies both the identity and parsed inventory.
    # No second open/read may choose different bytes after the hash check.
    def regular_open(name, flags):
        return os.open(name, flags | os.O_NOFOLLOW | os.O_NONBLOCK)
    with open(path, 'rb', opener=regular_open) as stream:
        info = os.fstat(stream.fileno())
        require(stat.S_ISREG(info.st_mode), 'regular setup receipt required')
        require(0 < info.st_size <= RECEIPT_MAX_BYTES, 'setup receipt size')
        raw = stream.read(RECEIPT_MAX_BYTES + 1)
    require(len(raw) == info.st_size and len(raw) <= RECEIPT_MAX_BYTES,
            'setup receipt size changed or exceeded limit')
    return raw


def fail_walk(error):
    raise error


def verify(checkout):
    head = subprocess.check_output(['git', '-C', str(checkout), 'rev-parse', 'HEAD'], text=True).strip()
    require(head == REVISION, 'execution checkout identity')
    experiment = checkout / EXPERIMENT
    evidence = json.loads((experiment / 'results/qemu-debian-setup.json').read_text())
    prefix = Path(evidence['destination'])
    require(prefix.resolve() == prefix and prefix.is_dir(), 'real fixed QEMU prefix required')
    require(stat.S_ISREG((prefix / 'setup-receipt.json').lstat().st_mode),
            'regular setup receipt required')
    receipt_bytes = receipt_snapshot(prefix / 'setup-receipt.json')
    receipt_sha = hashlib.sha256(receipt_bytes).hexdigest()
    require(receipt_sha == evidence['remote_receipt_sha256'], 'setup receipt changed')
    receipt = json.loads(receipt_bytes)
    members = receipt['members']
    actual = set()
    for root, directories, files in os.walk(prefix, followlinks=False, onerror=fail_walk):
        for name in directories + files:
            actual.add((Path(root) / name).relative_to(prefix).as_posix())
    require(actual == set(members) | {'setup-receipt.json'}, 'extra or missing prefix inventory member')
    require(len(members) == 2257, 'prefix inventory count')
    spec = importlib.util.spec_from_file_location('verified_qemu_setup', experiment / 'scripts/setup-qemu-debian.py')
    setup = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(setup)
    setup.verify_prefix(prefix, members)
    libraries = evidence['inspection']['resolved_libraries']
    require(len(libraries) == 50, 'resolved library count')
    for label, record in libraries.items():
        path = Path(label.replace('$QEMU_PREFIX', str(prefix), 1))
        require(path.stat().st_size == record['bytes'] and sha(path) == record['sha256'],
                'resolved library changed: ' + label)
    # Re-resolve with the same bounded, eager-binding setup inspection. This
    # enumerates virt/max only; it does not supply a kernel or start a guest.
    observed = setup.inspect_emulator(prefix)
    require(observed['resolved_libraries'] == libraries, 'loader resolution changed')
    require(observed['executable_sha256'] == evidence['inspection']['executable_sha256'], 'emulator changed')
    return {'result': 'PASS', 'execution_revision': REVISION, 'prefix_members': len(members),
            'allowed_extra': 'setup-receipt.json', 'resolved_libraries': len(libraries),
            'setup_receipt_sha256': receipt_sha, 'qemu_sha256': observed['executable_sha256'],
            'qemu_version': observed['version'], 'loader_resolution': 'unchanged', 'guest_run': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkout', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.checkout), indent=2, sort_keys=True))
