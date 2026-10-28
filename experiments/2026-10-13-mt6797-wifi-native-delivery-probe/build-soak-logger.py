#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build the bounded soak logger (4500 s, 16 MiB) on Linux from a clean pushed checkout.

Derive two constants from the unchanged reviewed capture source: DEADLINE_MS
600000 to 4500000 and LOG_LIMIT 2 MiB to 16 MiB, for one Wi-Fi lifetime of
45 minutes' light traffic and 15 minutes' idle (HIF section 69). The record
limit, syscall/error handling and seal protocol remain. The actual parser and
I/O fixtures run with their limit expectations moved to the new constants.
Derived from build-ten-minute-logger.py; only the validated static
helper/provenance package is fetched to the laptop.
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
DEADLINE_MS, LOG_LIMIT = 4500000, 16 * 1024 * 1024
EDITS = [(b'#define DEADLINE_MS UINT64_C(600000)\n', b'#define DEADLINE_MS UINT64_C(4500000)\n'),
         (b'#define LOG_LIMIT (2U * 1024U * 1024U)\n', b'#define LOG_LIMIT (16U * 1024U * 1024U)\n')]
# The byte-cap fixtures fill the cap with maximum records, 64 KiB each: 32
# exactly fill 2 MiB and a 33rd overflows it; at 16 MiB, 256 and 257.
PARSER_EDITS = [(b'range(33)', b'range(257)'), (b'entries[:32]', b'entries[:256]'),
                (b'b"accepted 0 31 32 2097152\\n"', b'b"accepted 0 255 256 16777216\\n"')]
IO_EDITS = [(b'600000', b'4500000', 2), (b'"2097152"', b'"16777216"', 1),
            (b'large_records(32)', b'large_records(256)'),
            (b'data, 32, passed=True, reads=33)', b'data, 256, passed=True, reads=257)'),
            (b'data, 32, reads=33)', b'data, 256, reads=257)')]
HARNESS_EDITS = [(b'unsigned int count = scenario("cap") ? 33 : 32;',
                  b'unsigned int count = scenario("cap") ? 257 : 256;')]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def edit(data, edits, what):
    for edit_ in edits:
        old, new, count = (edit_ + (1,))[:3]
        if data.count(old) != count:
            raise ValueError(what + ' changed')
        data = data.replace(old, new)
    return data


def derive(source):
    if sha(source) != PINS['src/kmsg-capture.c']:
        raise ValueError('reviewed capture source changed')
    return edit(source, EDITS, 'reviewed capture source')


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
    with tempfile.TemporaryDirectory(prefix='.kmsg-soak-', dir=parent) as tmp:
        stage = Path(tmp)
        (stage / 'src').mkdir()
        (stage / 'tests').mkdir()
        (stage / 'src/kmsg-capture.c').write_bytes(source)
        (stage / 'tests/kmsg-io-harness.c').write_bytes(edit(inputs['tests/kmsg-io-harness.c'], HARNESS_EDITS,
                                                             'I/O harness cap scenario'))
        (stage / 'test-kmsg.py').write_bytes(edit(inputs['test-kmsg.py'], PARSER_EDITS,
                                                  'parser fixture limit expectations'))
        (stage / 'test-kmsg-io.py').write_bytes(edit(inputs['test-kmsg-io.py'], IO_EDITS,
                                                     'I/O fixture limit expectations'))
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
            'derivation': 'DEADLINE_MS 600000 to 4500000 and LOG_LIMIT 2 MiB to 16 MiB',
            'deadline_ms': DEADLINE_MS, 'byte_limit': LOG_LIMIT, 'record_bytes_limit': 65536,
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
        output = parent / ('kmsg-soak-' + sha(manifest.encode()))
        if output.exists():
            raise ValueError('validated package already exists; no overwrite')
        package.rename(output)
    print(json.dumps({'package': output.name, 'source_commit': commit,
                      'inventory_sha256': sha(manifest.encode()),
                      'helper_sha256': sha(binaries[0])}, sort_keys=True))


if __name__ == '__main__':
    main()
