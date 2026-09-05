#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Verify pinned review inputs in memory; never fetch a tree or contact hardware."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
LIMIT = 2 * 1024 * 1024


def verify(entry, data):
    if len(data) != entry['bytes']:
        raise ValueError('input size mismatch: ' + entry['path'])
    if hashlib.sha256(data).hexdigest() != entry['sha256']:
        raise ValueError('input digest mismatch: ' + entry['path'])
    return data.decode('utf-8')


def fetch(entry):
    with urllib.request.urlopen(entry['url'], timeout=30) as response:
        if response.status != 200 or response.url != entry['url']:
            raise ValueError('unexpected HTTP response: ' + entry['path'])
        return verify(entry, response.read(LIMIT + 1))


def audit(manifest, network=False):
    records = []
    for entry in manifest['local']:
        path = ROOT / entry['path']
        if path.is_symlink() or not path.is_file():
            raise ValueError('missing or symlinked patch: ' + entry['path'])
        source = verify(entry, path.read_bytes())
        records.append({**entry, 'verified': True,
                        'changed_paths': [line.split()[2][2:] for line in
                                          source.splitlines()
                                          if line.startswith('diff --git ')],
                        'certification': 'not established by existing metadata'})
    remote = []
    if network:
        for entry in manifest['remote']:
            fetch(entry)
            remote.append({**entry, 'verified': True})
    return {'schema_version': 1, 'upstream_commit': manifest['upstream_commit'],
            'related_commit': manifest['related_commit'],
            'local': records, 'remote': remote,
            'remote_inputs_verified': network,
            'scope': 'input integrity and patch footprint only; not semantic, build, hardware or certification approval'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch', action='store_true',
                        help='explicitly verify the pinned public remote inputs')
    args = parser.parse_args()
    manifest = json.loads((HERE.parent / 'sources.json').read_text())
    # Output is emitted only after all requested inputs have passed.
    print(json.dumps(audit(manifest, args.fetch), indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
