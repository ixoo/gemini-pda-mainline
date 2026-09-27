#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind the focused-reader image to the proven A53 observation scripts."""

import hashlib
import json
import os
from pathlib import Path
import runpy
import uuid

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SERVICE = REPO / 'experiments/2026-09-09-standard-kernel-package'
PARENT = REPO / 'artifacts/a53-service-ram/candidate-97c23e3f34686d8831e56f9903e109f6b9ba89cb121c88996f25411e86d5bec0'
PARENT_SESSION_SHA = '0955b3e035487d90d58d1688d9ea6c2350392e8f592fe0b862eecbb6d98a5629'
RECEIPT_SHA = 'f74d8557e6bedcb4d1b7144f0085f381d310e8d46d98a9192535486f08535073'
PRIVATE_MANIFEST_SHA = '9624fa43d189a95ebdbee86582c388ca72b154a6ae9e32c2c1f82b9a84be589b'
READER_SHA = '7d523b28edd51ed1fa393b8d8c8ade8315e40c4bae2edd8059e7b215d0084f51'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(value, reason):
    if not value:
        raise ValueError(reason)


def boot_uuid(value):
    parsed = uuid.UUID(value)
    require(parsed.int != 0 and str(parsed) == value,
            'canonical nonzero boot UUID required')
    return value


def prepare(candidate, previous):
    source = SERVICE / 'a53-ram-session.py'
    require(sha(source.read_bytes()) == PARENT_SESSION_SHA,
            'accepted A53 session source changed')
    parent = runpy.run_path(str(source))
    context, collector, steps, finish = parent['prepare'](PARENT, previous)
    candidate = Path(os.path.abspath(candidate))
    collector.directory(candidate)
    public_path = HERE / 'results/candidate.json'
    require(sha(collector.regular(public_path, 65536, private=False)) == RECEIPT_SHA,
            'public focused candidate receipt changed')
    public = json.loads(collector.regular(public_path, 65536, private=False),
                        object_pairs_hook=collector.no_duplicates)
    require(public['status'] == 'offline-composition-validated-not-selected-for-boot2' and
            public['kernel_release'] == parent['RELEASE'],
            'focused candidate receipt identity')
    raw_manifest = collector.regular(candidate / 'candidate.json', 65536)
    require(sha(raw_manifest) == PRIVATE_MANIFEST_SHA,
            'private focused candidate manifest changed')
    manifest = json.loads(raw_manifest, object_pairs_hook=collector.no_duplicates)
    files = manifest['files']
    require(candidate.name == 'candidate-' + public['boot_image_sha256'] and
            manifest['repository_commit'] == public['repository_commit'] and
            manifest['reader_sha256'] == public['focused_reader_sha256'] == READER_SHA and
            files['boot.img']['sha256'] == public['boot_image_sha256'] and
            files['boot2-padded.img']['sha256'] == public['boot2_full_sha256'] and
            files['initramfs.img']['sha256'] == public['initramfs_sha256'] and
            manifest['boot2_exact_bytes'] == 16777216 and
            manifest['changed_initramfs_members'] == ['bin/keyboard-observe'] and
            {p.name for p in candidate.iterdir()} == set(files) | {'candidate.json'},
            'focused candidate inventory identity')
    for name, entry in files.items():
        data = collector.regular(candidate / name, 16777216)
        require(len(data) == entry['bytes'] and sha(data) == entry['sha256'],
                'focused candidate file changed: ' + name)
    raw = collector.regular(candidate / 'boot2-padded.img', 16777216)
    boot = collector.regular(candidate / 'boot.img', 16777216)
    require(len(raw) == 16777216 and raw[:len(boot)] == boot and
            not any(raw[len(boot):]), 'focused boot2 padding changed')
    archive = runpy.run_path(str(REPO / 'experiments/2026-09-05-owner-away-experiment-preparation/baseline/scripts/build-candidate.py'))
    parse, _ = archive['parser_tools']()
    members = parse(collector.regular(candidate / 'initramfs.img', 16777216))
    require(len(members) == 47 and sha(members['bin/keyboard-observe'].data) == READER_SHA,
            'focused reader not embedded')
    old_members = context['candidate']['members']
    require(set(members) == set(old_members) and
            all(sha(member.data) == old_members[name]['sha256']
                for name, member in members.items() if name != 'bin/keyboard-observe'),
            'A53 RAM member outside reader changed')
    context['candidate'] = {
        'files': {name: entry['sha256'] for name, entry in files.items()},
        'members': {name: {'sha256': sha(member.data), 'size': len(member.data),
                           'mode': oct(member.mode)} for name, member in members.items()},
    }
    context['admission'] = {'candidate_sha256': files['boot.img']['sha256']}
    return context, collector, steps, finish
