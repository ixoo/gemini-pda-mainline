#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Pinned patch replay and synthetic whole-image planning validation only."""
import ast
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import urllib.request

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[1]


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    spec = json.loads((HERE / 'inputs.json').read_text())
    patch = HERE / '0003-wifi-mediatek-prevalidate-image-plan.patch'
    generated = subprocess.check_output([sys.executable, str(HERE / 'scripts/generate-patch.py')])
    require(generated == patch.read_bytes(), 'patch reproduction differs')
    managed = ROOT / 'artifacts/wifi-whole-image-plan'
    managed.mkdir(parents=True, exist_ok=True)
    require(not managed.is_symlink(), 'managed root symlink')
    lock_path = managed / '.verify.lock'
    require(not lock_path.is_symlink(), 'lock symlink')
    lock = lock_path.open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    marker = 'whole-image-plan-verify-v1\n'
    for stale in managed.glob('verify-*'):
        require(stale.is_dir() and not stale.is_symlink(), 'unsafe scratch')
        require((stale / '.owner').read_text() == marker, 'unowned scratch')
        require(all(not path.is_symlink() for path in stale.rglob('*')), 'scratch symlink')
        shutil.rmtree(stale)
    report = {'patch_sha256': digest(generated), 'patch_reproduction_and_replay': 'PASS',
              'kernel_build': 'NOT RUN', 'backend': 'NOT ACCESSED',
              'hardware': 'NOT ACCESSED', 'host_fixtures': {}}
    with tempfile.TemporaryDirectory(prefix='verify-', dir=managed) as directory:
        scratch = Path(directory)
        (scratch / '.owner').write_text(marker)
        for name, expected in spec['oracle_files'].items():
            data = subprocess.check_output(['git', 'show', spec['oracle_commit'] +
                ':experiments/2026-09-05-mt6797-wifi-contract/scripts/' + name], cwd=ROOT)
            require(digest(data) == expected, 'oracle hash changed')
            (scratch / name).write_bytes(data)
        for name in ('mtke.c', 'mtke.h'):
            data = (HERE.parent / '2026-09-05-mt6797-hif-parser-compile/src' / name).read_bytes()
            require(digest(data) == spec['parser_files'][name], 'parser source changed')
            (scratch / name).write_bytes(data)
        for name, expected in spec['plan_files'].items():
            require(digest((HERE / 'src' / name).read_bytes()) == expected, 'plan source changed')
        env = dict(os.environ, TMPDIR=str(scratch), PYTHONDONTWRITEBYTECODE='1',
                   ASAN_OPTIONS='halt_on_error=1', UBSAN_OPTIONS='halt_on_error=1')
        result = subprocess.run([sys.executable, str(HERE / 'tests/test-plan.py'),
                                 '--scratch', str(scratch)], capture_output=True,
                                text=True, timeout=120, env=env)
        require(result.returncode == 0, result.stdout + result.stderr)
        report['host_fixtures']['differential'] = result.stdout + result.stderr
        flags = ['-std=c11', '-Wall', '-Wextra', '-Werror', '-Wconversion', '-pedantic',
                 '-g', '-O1', '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                 '-fno-omit-frame-pointer']
        executable = scratch / 'memory'
        subprocess.run(['cc', *flags, '-I', str(scratch), '-I', str(HERE / 'src'),
                        str(scratch / 'mtke.c'), str(HERE / 'src/image-plan.c'),
                        str(HERE / 'tests/test-plan-memory.c'), '-lz', '-o', str(executable)], check=True)
        result = subprocess.run([str(executable)], capture_output=True, text=True,
                                timeout=60, env=env)
        require(result.returncode == 0 and not result.stderr, result.stdout + result.stderr)
        report['host_fixtures']['sanitizer'] = 'PASS: 280 exact-allocation count/short-input cases plus late reserved, invalidation and null checks'
        report['sanitizer_flags'] = flags
        report['compiler'] = subprocess.check_output(['cc', '--version']).decode().splitlines()[0]
        report['test_hashes'] = {path.name: digest(path.read_bytes()) for path in (HERE / 'tests').iterdir() if path.is_file()}
        checks = json.loads((HERE / 'checkpatch-inputs.json').read_text())
        for name, expected in checks['files'].items():
            with urllib.request.urlopen('https://raw.githubusercontent.com/torvalds/linux/' + spec['upstream_commit'] + '/scripts/' + name, timeout=20) as response:
                data = response.read(400001)
            require(len(data) <= 400000 and digest(data) == expected, 'checkpatch source mismatch')
            (scratch / name).write_bytes(data)
        result = subprocess.run(['perl', str(scratch / 'checkpatch.pl'), '--strict', '--no-tree', str(patch)], capture_output=True, text=True, timeout=60)
        output = (result.stdout + result.stderr).replace(str(ROOT), '<project>')
        report['checkpatch'] = {'exit': result.returncode, 'exclusions': [], 'output': output}
    for script in [*(HERE / 'scripts').glob('*.py'), *(HERE / 'tests').glob('*.py')]:
        ast.parse(script.read_text())
    (HERE / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    findings = [line for line in output.splitlines() if line.startswith(('ERROR:', 'WARNING:', 'CHECK:'))]
    require(findings == ['WARNING: added, moved or deleted file(s), does MAINTAINERS need updating?',
                         'ERROR: Missing Signed-off-by: line(s)'], 'unexpected source findings; see validation.json')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
    main()
