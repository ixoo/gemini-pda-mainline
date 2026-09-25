#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind the established authenticated RAM collector to the CONSYS image."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import runpy
import sys
import uuid

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
BASELINE = REPO / 'experiments/2026-09-05-owner-away-experiment-preparation/baseline/scripts'
SERVICE = REPO / 'experiments/2026-09-09-standard-kernel-package'
RELEASE = '7.1.3-gemini-consys-handoff-snapshot'
SOURCE_PINS = {
    'collect-baseline.py': 'efbca1e464e04005d3b7d503742b426eb9f642140ec289c40bc43563852208cf',
    'session_steps.py': '762616bb386647e0a25addd36ad9dba2f6384ebde4858f89a806a32678fc60fc',
    'finish-baseline.py': 'f4fc22f6de7456e9c5e3336fd76114151492414d4c09356cda77b2a9d35a6708',
}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def boot_uuid(value):
    parsed = uuid.UUID(value)
    require(parsed.int != 0 and str(parsed) == value, 'canonical nonzero boot UUID required')
    return value


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prepare(candidate_dir, previous):
    boot_uuid(previous)
    for name, expected in SOURCE_PINS.items():
        require(digest((BASELINE / name).read_bytes()) == expected,
                'session source changed: ' + name)
    collector = load('consys_collector', BASELINE / 'collect-baseline.py')
    collector.source_tools()
    legacy = load('consys_observation', collector.HISTORICAL / 'classify_observation.py')
    legacy.RELEASE = RELEASE
    collector.source_tools = lambda: vars(legacy)
    steps = load('consys_steps', BASELINE / 'session_steps.py')
    steps.RELEASE = RELEASE
    finish = load('consys_finish', BASELINE / 'finish-baseline.py')
    candidate_dir = Path(os.path.abspath(candidate_dir))
    collector.directory(candidate_dir)
    receipt = json.loads((HERE / 'results/candidate.json').read_text())
    require(receipt['kernel_release'] == RELEASE and receipt['physical_admission'] is False,
            'candidate receipt changed')
    expected = receipt['files']
    require({p.name for p in candidate_dir.iterdir()} == set(expected) | {'candidate.json'},
            'candidate inventory changed')
    for name, identity in expected.items():
        data = collector.regular(candidate_dir / name, 16777216)
        require(len(data) == identity['bytes'] and digest(data) == identity['sha256'],
                'candidate file changed: ' + name)
    require(json.loads(collector.regular(candidate_dir / 'candidate.json', 65536)) == receipt,
            'private candidate manifest changed')
    builder = runpy.run_path(str(SERVICE / 'build-a53-ram-candidate.py'))
    for path, expected_sha in builder['TOOLS'].items():
        require(digest(path.read_bytes()) == expected_sha, 'RAM parser dependency changed')
    parser = runpy.run_path(str(builder['BASELINE'] / 'scripts/build-candidate.py'))
    members = parser['parser_tools']()[0](collector.regular(candidate_dir / 'initramfs.img', 16777216))
    require(len(members) == 47 and RELEASE.encode() in members['init'].data,
            'RAM release gate changed')
    candidate = {'files': {name: value['sha256'] for name, value in expected.items()},
                 'members': {name: {'sha256': digest(member.data), 'size': len(member.data),
                                    'mode': oct(member.mode)} for name, member in members.items()}}
    context = {'candidate': candidate, 'recovery_id': previous,
               'admission': {'candidate_sha256': expected['boot.img']['sha256']}}
    return context, collector, steps, finish


def classify(context, collector, stdout, stderr, process):
    result = collector.classify_capture(context, stdout, stderr, process)
    if result['classification'] == 'baseline-observation-only-pass':
        boot_uuid(result['boot_id'])
    return result
