#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build the bounded 900-second logger on Linux from a clean pushed checkout.

Derive one constant from the unchanged reviewed capture source. The existing
2 MiB byte cap, record limit, syscall/error handling and seal protocol remain.
Only the validated static helper/provenance package is fetched to the laptop.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
BASELINE = REPO / 'experiments/2026-09-05-owner-away-experiment-preparation/baseline'
PINS = {
    'src/kmsg-capture.c': '528a8babe897e5d683e37067d0750facdc57cce119b103f789a7e412f069b8b5',
    'test-kmsg.py': '65b4abeb7692d7ee37be0adaf05b08a59d0910d2c2beae5de20314ed1ca7fcbf',
    'test-kmsg-io.py': '3d83863677a91dea9a87cd54c0c264a42929c26da41b5a3a9047f4e1bfd6de45',
    'tests/kmsg-io-harness.c': 'b3e19aade7cfe3830f70187e234eec2c426dbd6b9cc20658d6ecb09a046079db',
}
OLD = b'#define DEADLINE_MS UINT64_C(600000)\n'
NEW = b'#define DEADLINE_MS UINT64_C(900000)\n'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def derive(source):
    if sha(source) != PINS['src/kmsg-capture.c'] or source.count(OLD) != 1:
        raise ValueError('reviewed capture source changed')
    return source.replace(OLD, NEW)


def command(argv, **kwargs):
    return subprocess.check_output(argv, text=True, **kwargs).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-parent', required=True, type=Path)
    args = parser.parse_args()
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        raise ValueError('Buildbox Linux x86_64 required; no local or VM fallback')
    if command(['git', '-C', str(REPO), 'remote', 'get-url', 'origin']) != \
            'https://github.com/ixoo/gemini-pda-mainline.git':
        raise ValueError('unexpected origin')
    commit = command(['git', '-C', str(REPO), 'rev-parse', 'HEAD'])
    if command(['git', '-C', str(REPO), 'status', '--porcelain']) or \
            command(['git', '-C', str(REPO), 'rev-parse', 'origin/main']) != commit:
        raise ValueError('clean checkout at pushed origin/main required')
    parent = args.output_parent.resolve(strict=True)
    if not parent.is_relative_to('/workspace/gemini-pda') or \
            parent.is_relative_to(REPO) or shutil.disk_usage(parent).free < 1024**3:
        raise ValueError('managed workspace output and at least 1 GiB free required')
    inputs = {}
    for name, digest in PINS.items():
        path = BASELINE / name
        if path.is_symlink() or not path.is_file() or sha(path.read_bytes()) != digest:
            raise ValueError('source/fixture identity changed: ' + name)
        inputs[name] = path.read_bytes()
    source = derive(inputs['src/kmsg-capture.c'])
    cc, elf = 'aarch64-linux-gnu-gcc', 'aarch64-linux-gnu-readelf'
    flags = ['-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-static']
    with tempfile.TemporaryDirectory(prefix='.kmsg-900-', dir=parent) as tmp:
        stage = Path(tmp)
        (stage / 'src').mkdir()
        (stage / 'tests').mkdir()
        (stage / 'src/kmsg-capture.c').write_bytes(source)
        for name in ['test-kmsg.py', 'tests/kmsg-io-harness.c']:
            (stage / name).write_bytes(inputs[name])
        fixture = inputs['test-kmsg-io.py']
        if fixture.count(b'600000') != 2:
            raise ValueError('I/O fixture deadline expectations changed')
        (stage / 'test-kmsg-io.py').write_bytes(fixture.replace(b'600000', b'900000'))
        # Existing real-source parser and syscall-model tests; no /dev/kmsg access.
        subprocess.run(['python3', str(stage / 'test-kmsg.py')], check=True, timeout=60)
        subprocess.run(['python3', str(stage / 'test-kmsg-io.py')], check=True, timeout=60)
        binaries = []
        for replica in ['one', 'two']:
            target = stage / replica
            subprocess.run([cc, *flags, '-ffile-prefix-map=' + str(stage) + '=.',
                            str(stage / 'src/kmsg-capture.c'), '-o', str(target)],
                           check=True, timeout=60)
            if 'AArch64' not in command([elf, '-h', str(target)]) or \
                    'INTERP' in command([elf, '-l', str(target)]):
                raise ValueError('static AArch64 ELF required')
            binaries.append(target.read_bytes())
        if binaries[0] != binaries[1]:
            raise ValueError('replica binaries differ')
        provenance = {
            'repository_commit': commit, 'repository_dirty': False,
            'build_host_architecture': platform.machine(), 'target_architecture': 'aarch64',
            'toolchain': command([cc, '--version']).splitlines()[0],
            'compiler_flags': flags + ['-ffile-prefix-map=<managed-build>=.'],
            'input_sha256': PINS, 'derived_source_sha256': sha(source),
            'derivation': 'one DEADLINE_MS constant: 600000 to 900000',
            'deadline_ms': 900000, 'byte_limit': 2097152, 'record_bytes_limit': 65536,
            'replicas_identical': True, 'parser_and_io_fixtures_pass': True,
            'helper_sha256': sha(binaries[0]), 'source_license': 'MIT',
            'build_script_sha256': sha(Path(__file__).read_bytes()),
        }
        package = stage / 'package'
        package.mkdir(mode=0o700)
        (package / 'kmsg-capture').write_bytes(binaries[0])
        (package / 'kmsg-capture').chmod(0o700)
        (package / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
        manifest = ''.join(sha(p.read_bytes()) + '  ' + p.name + '\n'
                           for p in sorted(package.iterdir()))
        (package / 'SHA256SUMS').write_text(manifest)
        output = parent / ('kmsg-900-' + sha(manifest.encode()))
        if output.exists():
            raise ValueError('validated package already exists; no overwrite')
        package.rename(output)
    print(json.dumps({'package': output.name, 'source_commit': commit,
                      'inventory_sha256': sha(manifest.encode()),
                      'helper_sha256': sha(binaries[0])}, sort_keys=True))


if __name__ == '__main__':
    main()
