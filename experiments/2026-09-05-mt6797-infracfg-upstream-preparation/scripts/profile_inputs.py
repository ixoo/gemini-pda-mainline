#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fingerprint effective source/config/ordered-patch inputs across integration."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath

from kernel_source_contract import load_manifest, resolve


def digest(data):
    return hashlib.sha256(data).hexdigest()


def serialized(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def file_identity(root, name):
    if not isinstance(name, str) or not name or any(c.isspace() for c in name):
        raise ValueError('invalid input path')
    path = PurePosixPath(name)
    if path.is_absolute() or any(p in ('.', '..', '') for p in name.split('/')):
        raise ValueError('unsafe input path')
    target = root / name
    if target.is_symlink() or not target.is_file() or not target.resolve().is_relative_to(root.resolve()):
        raise ValueError('missing or unsafe profile input')
    return {'path': name, 'sha256': digest(target.read_bytes())}


def fingerprint(root, manifest, profile):
    selected = manifest['config']['profiles'][profile]
    series = selected.get('patch_series')
    if series is None:
        series = manifest.get('patch_series')
    file_identity(root, series)
    directory = PurePosixPath(series).parent
    names = (root / series).read_text().splitlines()
    patches = [file_identity(root, str(directory) + '/' + name) for name in names
               if name and not name.startswith('#')]
    if not patches or len({p['path'] for p in patches}) != len(patches):
        raise ValueError('empty or duplicated profile patch selection')
    inputs = {'architecture': manifest['architecture'], 'source': resolve(manifest, profile)['kernel'], 'base': selected['base'],
              'fragments': [file_identity(root, name) for name in selected['fragments']],
              'patches': patches}
    return {'effective_inputs_sha256': digest(serialized(inputs)),
            'patch_count': len(patches), 'fragment_count': len(inputs['fragments'])}


def snapshot(root):
    manifest = load_manifest(root / 'kernel/manifest.json')
    return {'schema_version': 1, 'default_profile': manifest['config']['default_profile'],
            'profiles': {p: fingerprint(root, manifest, p)
                         for p in sorted(manifest['config']['profiles'])}}


def compare(before, after):
    if before['default_profile'] != after['default_profile']:
        raise ValueError('existing default profile changed')
    for profile, identity in before['profiles'].items():
        if after['profiles'].get(profile) != identity:
            raise ValueError('existing effective inputs changed: ' + profile)
    return {'existing_profiles_preserved': len(before['profiles']),
            'added_profiles': sorted(set(after['profiles']) - set(before['profiles']))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repository', type=Path)
    parser.add_argument('--compare', type=Path)
    args = parser.parse_args()
    current = snapshot(args.repository)
    print(json.dumps(compare(load_manifest(args.compare), current) if args.compare else current,
                     indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
