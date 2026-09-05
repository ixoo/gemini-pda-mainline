#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Proposed source-selection contract; no build, network or extraction actions."""
import argparse
import datetime
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

REQUIRED = {'version', 'released', 'source_url', 'sha256'}
ARCHIVE = {'archive_format', 'archive_root'}
OPTIONAL = ARCHIVE | {'git_commit'}


def unique_object(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            raise ValueError('duplicate JSON field: ' + name)
        result[name] = value
    return result


def load_manifest(path):
    return json.loads(Path(path).read_text(), object_pairs_hook=unique_object)


def normalize(source, override=False):
    if not isinstance(source, dict):
        raise ValueError('kernel source must be an object')
    mandatory = REQUIRED | (ARCHIVE if override else set())
    if not mandatory <= source.keys() or source.keys() - REQUIRED - OPTIONAL:
        raise ValueError('incomplete or unknown kernel source fields')
    if any(not isinstance(value, str) or not value for value in source.values()):
        raise ValueError('kernel source fields must be nonempty strings')
    if not re.fullmatch(r'[0-9][A-Za-z0-9.+_-]{0,79}', source['version']):
        raise ValueError('unsafe kernel version')
    if not re.fullmatch(r'[0-9a-f]{64}', source['sha256']):
        raise ValueError('source checksum must be SHA-256')
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', source['released']):
        raise ValueError('invalid release date')
    datetime.date.fromisoformat(source['released'])
    url = source['source_url']
    if len(url) > 2048 or any(ord(c) <= 32 or ord(c) >= 127 for c in url):
        raise ValueError('unsafe source URL')
    parsed = urlsplit(url)
    if (parsed.scheme != 'https' or not parsed.hostname or not parsed.path
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.port not in (None, 443)):
        raise ValueError('source URL must be public HTTPS without credentials or query')
    archive_format = source.get('archive_format', 'tar.xz')
    if archive_format not in {'tar.xz', 'tar.gz'}:
        raise ValueError('unsupported source archive format')
    archive_root = source.get('archive_root', 'linux-' + source['version'])
    if not re.fullmatch(r'linux-[A-Za-z0-9][A-Za-z0-9.+_-]{0,119}', archive_root):
        raise ValueError('unsafe archive root')
    if 'git_commit' in source and not re.fullmatch(r'[0-9a-f]{40}', source['git_commit']):
        raise ValueError('invalid upstream Git commit')
    return {**source, 'archive_format': archive_format, 'archive_root': archive_root}


def resolve(manifest, profile=None):
    if (not isinstance(manifest, dict) or type(manifest.get('schema')) is not int
            or manifest.get('schema') != 1):
        raise ValueError('unsupported manifest')
    fallback = normalize(manifest.get('kernel'))
    config = manifest.get('config')
    if not isinstance(config, dict):
        raise ValueError('missing config object')
    if 'profiles' not in config:
        if profile is not None:
            raise ValueError('legacy manifest cannot select a profile')
        return {'profile': None, 'selection': 'global', 'kernel': fallback}
    profiles = config['profiles']
    if not isinstance(profiles, dict) or not profiles:
        raise ValueError('missing profiles')
    selected = profile if profile is not None else config.get('default_profile')
    if not isinstance(selected, str) or selected not in profiles:
        raise ValueError('unknown selected profile')
    entry = profiles[selected]
    if not isinstance(entry, dict):
        raise ValueError('selected profile must be an object')
    # Presence selects the override; null, empty and partial values are refusals.
    if 'kernel' in entry:
        return {'profile': selected, 'selection': 'profile',
                'kernel': normalize(entry['kernel'], override=True)}
    return {'profile': selected, 'selection': 'global', 'kernel': fallback}


def check_provenance(manifest, build):
    """Only source identity; existing package/config/series checks remain required."""
    if not isinstance(build, dict):
        raise ValueError('build provenance must be an object')
    profile = build.get('build_profile')
    if 'profiles' in manifest.get('config', {}) and not profile:
        raise ValueError('profile required in build provenance')
    selected = resolve(manifest, profile)
    expected = selected['kernel']
    if build.get('source_sha256') != expected['sha256']:
        raise ValueError('build source checksum does not match selected profile')
    if selected['selection'] == 'profile' and 'kernel_source' not in build:
        raise ValueError('override build requires complete source provenance')
    if 'kernel_source' in build and build['kernel_source'] != expected:
        raise ValueError('build source tuple disagrees with selected manifest source')
    return selected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--profile')
    parser.add_argument('--build', type=Path)
    args = parser.parse_args()
    manifest = load_manifest(args.manifest)
    if args.build:
        if args.profile:
            raise ValueError('build provenance owns the selected profile')
        result = check_provenance(manifest, load_manifest(args.build))
    else:
        result = resolve(manifest, args.profile)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
