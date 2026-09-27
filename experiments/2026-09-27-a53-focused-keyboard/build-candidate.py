#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Replace only the A53 RAM image's unsupported keyboard reader."""

import argparse
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import stat
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SERVICE = REPO / 'experiments/2026-09-09-standard-kernel-package'
BASELINE = REPO / 'experiments/2026-09-05-owner-away-experiment-preparation/baseline'
BOOT = REPO / 'experiments/2026-07-12-boot-contract-recovery/scripts'
PARENT_RECEIPT = SERVICE / 'results/a53-service-ram-candidate.json'
PARENT_RECEIPT_SHA = '0c6df48ed7312d978d9ef6b650063af5a78db259d7e9831fb2c80eef9e65e46f'
PARENT_BOOT_SHA = '97c23e3f34686d8831e56f9903e109f6b9ba89cb121c88996f25411e86d5bec0'
PARENT_MANIFEST_SHA = 'e9126ef952c3174e047b7da6237366e6b2374df9d02de6dcea9f193b501d8255'
OLD_READER_SHA = '51ef03def5461b2c13367906b3184a2dae14ca2f7ba7e835740be6a7268fa223'
READER_PACKAGE_SHA = '477db0d31c2d2a5d9830022e7dc63288a4e8cd48717aa3cee9b25d4043cc1927'
NEW_READER_SHA = '7d523b28edd51ed1fa393b8d8c8ade8315e40c4bae2edd8059e7b215d0084f51'
PARTITION_BYTES = 16777216


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(value, reason):
    if not value:
        raise ValueError(reason)


def regular(path, limit=PARTITION_BYTES):
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and
            info.st_uid == os.getuid() and info.st_size <= limit,
            'unsafe or oversized input: ' + path.name)
    return path.read_bytes()


def reader_package(path):
    sums = regular(path / 'SHA256SUMS', 16384)
    require(sha(sums) == READER_PACKAGE_SHA, 'focused reader package identity')
    names = set()
    for line in sums.decode('ascii').splitlines():
        expected, sep, relative = line.partition('  ./')
        require(sep and len(expected) == 64 and relative and
                not Path(relative).is_absolute() and '..' not in Path(relative).parts and
                relative not in names, 'focused package manifest entry')
        names.add(relative)
        require(sha(regular(path / relative)) == expected,
                'focused package member changed: ' + relative)
    found = {p.relative_to(path).as_posix() for p in path.rglob('*') if p.is_file()}
    require(found == names | {'SHA256SUMS'} and
            all(not p.is_symlink() for p in path.rglob('*')),
            'focused package inventory changed')
    reader = regular(path / 'keyboard-observe')
    require(sha(reader) == NEW_READER_SHA, 'focused reader bytes changed')
    validate = runpy.run_path(str(BASELINE / 'scripts/validate-candidate.py'))
    validate['check_elf'](reader)
    return reader


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parent', required=True, type=Path)
    parser.add_argument('--reader-package', required=True, type=Path)
    parser.add_argument('--output-root', required=True, type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    require(not subprocess.check_output(['git', '-C', str(REPO), 'status', '--porcelain']),
            'source checkout must be clean')
    parent = args.parent.resolve(strict=True)
    require(parent.name == 'candidate-' + PARENT_BOOT_SHA,
            'wrong A53 parent candidate')
    require(sha(regular(PARENT_RECEIPT, 65536)) == PARENT_RECEIPT_SHA,
            'A53 receipt changed')
    expected = json.loads(regular(PARENT_RECEIPT, 65536))['files']
    require({p.name for p in parent.iterdir()} == set(expected) | {'candidate.json'},
            'A53 parent inventory changed')
    require(sha(regular(parent / 'candidate.json', 65536)) == PARENT_MANIFEST_SHA,
            'A53 parent manifest changed')
    for name, entry in expected.items():
        data = regular(parent / name)
        require(len(data) == entry['bytes'] and sha(data) == entry['sha256'],
                'A53 parent file changed: ' + name)
    reader = reader_package(args.reader_package.resolve(strict=True))
    builder = runpy.run_path(str(SERVICE / 'build-a53-ram-candidate.py'))
    for path, digest in builder['TOOLS'].items():
        require(sha(regular(path)) == digest, 'LK composition tool changed')
    archive = runpy.run_path(str(BASELINE / 'scripts/build-candidate.py'))
    parse, encode = archive['parser_tools']()
    members = parse(regular(parent / 'initramfs.img'))
    require(len(members) == 47 and sha(members['bin/keyboard-observe'].data) == OLD_READER_SHA,
            'A53 embedded keyboard reader differs')
    original = members['bin/keyboard-observe']
    require(stat.S_ISREG(original.mode) and stat.S_IMODE(original.mode) == 0o755,
            'A53 reader mode differs')
    updated = dict(members)
    updated['bin/keyboard-observe'] = replace(original, data=reader)
    require({name for name in members if members[name] != updated[name]} ==
            {'bin/keyboard-observe'}, 'unexpected initramfs member delta')
    ramdisk = encode(updated)
    require(parse(ramdisk) == updated, 'focused initramfs round trip')

    root = args.output_root.absolute()
    require(root == REPO / 'artifacts/a53-focused-keyboard' and
            not (REPO / 'artifacts').is_symlink() and not root.is_symlink(),
            'output must use private A53 focused artifact root')
    root.mkdir(mode=0o700, exist_ok=True)
    require(stat.S_IMODE(root.stat().st_mode) == 0o700 and
            shutil.disk_usage(root).free >= 256 * 1024 * 1024,
            'private output root or free space')
    stage = root / '.candidate-stage'
    stage.mkdir(mode=0o700)
    try:
        write = archive['write_file']
        for name in ('Image.gz', 'board.dtb', 'kernel.config'):
            write(stage / name, regular(parent / name))
        write(stage / 'initramfs.img', ramdisk)
        command = [sys.executable, str(BOOT / 'build-android-boot-v0.py'),
                   '--kernel', str(stage / 'Image.gz'), '--ramdisk', str(stage / 'initramfs.img'),
                   '--dtb', str(stage / 'board.dtb'), '--name', 'gemini-obs-L',
                   '--cmdline', 'bootopt=64S3,32N2,64N2', '--kernel-addr', '0x40200000',
                   '--ramdisk-addr', '0x45000000', '--second-addr', '0x40f00000',
                   '--tags-addr', '0x44000000', '--lk-android8', '--output', str(stage / 'boot.img')]
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL)
        boot = regular(stage / 'boot.img')
        require(len(boot) < PARTITION_BYTES, 'boot2 image too large')
        write(stage / 'boot2-padded.img', boot + bytes(PARTITION_BYTES - len(boot)))
        subprocess.run([sys.executable, str(BOOT / 'analyze-lk-boot-image.py'),
                        '--validate-lk', '--expected-image-gz', str(stage / 'Image.gz'),
                        '--expected-ramdisk', str(stage / 'initramfs.img'),
                        '--expected-dtb', str(stage / 'board.dtb'),
                        '--expected-name', 'gemini-obs-L',
                        '--expected-cmdline', 'bootopt=64S3,32N2,64N2',
                        str(stage / 'boot.img')], check=True, stdout=subprocess.DEVNULL)
        result = {
            'status': 'offline-focused-reader-candidate-validated',
            'repository_commit': subprocess.check_output(
                ['git', '-C', str(REPO), 'rev-parse', 'HEAD'], text=True).strip(),
            'parent_boot_sha256': PARENT_BOOT_SHA,
            'parent_receipt_sha256': PARENT_RECEIPT_SHA,
            'reader_package_sha256': READER_PACKAGE_SHA,
            'reader_sha256': NEW_READER_SHA,
            'kernel_release': '7.1.3-gemini-a53-service-facilities',
            'files': {p.name: {'sha256': sha(regular(p)), 'bytes': p.stat().st_size}
                      for p in sorted(stage.iterdir())},
            'changed_initramfs_members': ['bin/keyboard-observe'],
            'initramfs_members': len(updated),
            'boot2_exact_bytes': PARTITION_BYTES,
            'device_action': 'none',
            'physical_admission': False,
            'secret_bearing': True,
        }
        write(stage / 'candidate.json', (json.dumps(result, indent=2) + '\n').encode())
        output = root / ('candidate-' + sha(boot))
        require(not output.exists() and not output.is_symlink(),
                'candidate already exists')
        stage.rename(output)
        print(json.dumps({'candidate': str(output), 'boot_sha256': sha(boot),
                          'boot2_sha256': result['files']['boot2-padded.img']['sha256']},
                         sort_keys=True))
    finally:
        if stage.exists():
            shutil.rmtree(stage)


if __name__ == '__main__':
    main()
