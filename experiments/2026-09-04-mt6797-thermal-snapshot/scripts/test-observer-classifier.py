#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fail-closed fixtures for the ten-case observer KUnit classifier."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

script = Path(__file__).with_name('classify-observer-kunit.py')
spec = importlib.util.spec_from_file_location('classifier', script)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
revision = '1' * 40
build = dict(repository_commit=revision, repository_dirty=False,
             build_profile=module.PROFILE, target_architecture='arm64',
             kernel_release='fixture-observer', config_sha256='2' * 64)
raw = '\n'.join([
    'Linux version fixture-observer fixture', 'KTAP version 1',
    'KTAP version 1', f'# Subtest: {module.SUITE}',
    *[f'ok {i} {name}' for i, name in enumerate(module.EXPECTED_CASES, 1)],
    f'# {module.SUITE}: pass:10 fail:0 skip:0 total:10',
    '# Totals: pass:10 fail:0 skip:0 total:10',
    f'ok 1 {module.SUITE}',
    'Kernel panic - not syncing: VFS: Unable to mount root fs fixture',
]) + '\n'
mutations = [
    ('missing case', raw.replace(f'ok 1 {module.EXPECTED_CASES[0]}\n', ''), {}),
    ('duplicate case', raw + f'ok 1 {module.EXPECTED_CASES[0]}\n', {}),
    ('skip', raw.replace('skip:0', 'skip:1'), {}),
    ('failure', raw.replace('ok 2 ', 'not ok 2 '), {}),
    ('old totals', raw.replace('pass:10', 'pass:7').replace('total:10', 'total:7'), {}),
    ('wrong release', raw.replace('Linux version fixture-observer', 'Linux version wrong'), {}),
    ('missing boundary', raw.split('Kernel panic')[0], {}),
    ('dirty build', raw, {'repository_dirty': True}),
    ('wrong revision', raw, {'repository_commit': '3' * 40}),
    ('wrong profile', raw, {'build_profile': 'wrong'}),
    ('wrong architecture', raw, {'target_architecture': 'x86_64'}),
]
with tempfile.TemporaryDirectory(prefix='gemini-observer-classifier-', dir='/tmp') as work:
    root = Path(work)
    (root / 'provenance').mkdir()
    (root / 'Image').write_bytes(b'fixture-only')
    command = [sys.executable, str(script), '--package', str(root),
               '--raw-log', str(root / 'raw.log'), '--qemu-exit', '124',
               '--repository-commit', revision]
    for name, log, overrides in [('positive', raw, {}), *mutations]:
        (root / 'provenance/build.json').write_text(json.dumps(build | overrides))
        (root / 'raw.log').write_text(log)
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        assert (result.returncode == 0) == (name == 'positive'), name
print(f'positive_cases=1 mutations_rejected={len(mutations)}')
