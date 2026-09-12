#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Pair the exact service kernel with the accepted private A53 RAM environment."""
import argparse
from dataclasses import replace
import fcntl
import gzip
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
BASELINE = REPO / 'experiments/2026-09-05-owner-away-experiment-preparation/baseline'
BOOT = REPO / 'experiments/2026-07-12-boot-contract-recovery/scripts'
OLD_RELEASE = b'7.1.3-gemini-mt6797-pwrap-reset'
NEW_RELEASE = b'7.1.3-gemini-a53-service-facilities'
PARTITION_BYTES = 16777216
TOOLS = {
    BASELINE / 'audit_foundation.py': 'd2046d5f41eb447df12f24a44901709b2619bb965bb5ec3801584fb680e61391',
    BASELINE / 'scripts/build-candidate.py': '365e6ba85693abb4a273efc4160abaeea78e425867903c9a5a706738694dc104',
    BOOT / 'build-android-boot-v0.py': '569ca6f2b365f119c8c3668cb3d63724b29e76447e47638d707983ee8eafadf4',
    BOOT / 'analyze-lk-boot-image.py': 'aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95',
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def update_init(members):
    require(len(members) == 47, 'accepted RAM member inventory changed')
    original = members['init']
    require(digest(original.data) == '59db0643a8cce87f34c0be30d91d83e341776ece0a0c682108e03b9b02fd693e',
            'accepted init changed')
    require(original.data.count(OLD_RELEASE) == 1, 'release gate is not unique')
    updated = dict(members)
    updated['init'] = replace(original, data=original.data.replace(OLD_RELEASE, NEW_RELEASE))
    require([name for name in members if updated[name] != members[name]] == ['init'],
            'unexpected userspace change')
    return updated


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('kernel-package', 'parent', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    require(not subprocess.check_output(['git', '-C', str(REPO), 'status', '--porcelain']),
            'candidate source checkout must be clean')
    for path, expected in TOOLS.items():
        require(digest(path.read_bytes()) == expected, 'composition tool changed')
    audit = runpy.run_path(str(BASELINE / 'audit_foundation.py'))
    regular, safe_directory = audit['regular'], audit['safe_directory']
    tools = runpy.run_path(str(BASELINE / 'scripts/build-candidate.py'))
    parse, encode = tools['parser_tools']()
    parent = safe_directory(args.parent)
    parent_receipt = REPO / 'experiments/2026-09-08-keyboard-console-ownership/validation.json'
    accepted = json.loads(regular(parent_receipt))['candidate']
    for name, expected in accepted['files'].items():
        require(digest(regular(parent / name)) == expected, 'accepted parent input changed: ' + name)
    receipt_path = HERE / 'results/a53-service-facilities.json'
    kernel = json.loads(regular(receipt_path))
    package = safe_directory(args.kernel_package)
    require(package.name == kernel['package_name'], 'wrong kernel package')
    sums = regular(package / 'SHA256SUMS')
    audit['inventory'](package, {'manifest_sha256': kernel['artifacts']['SHA256SUMS']['sha256'],
                                 'inventory_count': len(sums.splitlines())})
    for name, expected in kernel['artifacts'].items():
        data = regular(package / name)
        require(len(data) == expected['bytes'] and digest(data) == expected['sha256'],
                'kernel input differs from build receipt: ' + name)
    build = json.loads(regular(package / 'provenance/build.json'))
    require(build['repository_commit'] == kernel['repository_commit'] and
            build['repository_dirty'] is False and build['kernel_release'] == NEW_RELEASE.decode(),
            'kernel build identity changed')
    require(gzip.decompress(regular(package / 'Image.gz')) == regular(package / 'Image'),
            'compressed kernel mismatch')
    symbols = regular(package / 'System.map')
    for name in ('__arm64_sys_pidfd_open', '__arm64_sys_pidfd_send_signal'):
        require((' T ' + name + '\n').encode() in symbols, 'required logger seal syscall absent')
    original = parse(regular(parent / 'initramfs.img'))
    members = update_init(original)
    ramdisk = encode(members)
    require(parse(ramdisk) == members and encode(parse(ramdisk)) == ramdisk,
            'archive data, metadata or serialization mismatch')
    output = Path(os.path.abspath(args.output))
    safe_directory(output.parent)
    require(not output.exists() and not output.is_symlink(), 'output already exists')
    require(shutil.disk_usage(output.parent).free >= 256 * 1024 * 1024, 'insufficient staging space')
    lock_fd = os.open(output.parent / '.a53-service-ram.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(lock_fd, 'r+') as lock:
        info = os.fstat(lock.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and info.st_nlink == 1,
                'unsafe candidate lock')
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        stage = output.parent / '.a53-service-ram-stage'
        require(not stage.is_symlink(), 'unsafe stale stage')
        if stage.exists():
            shutil.rmtree(stage)
        stage.mkdir(mode=0o700)
        try:
            for name, data in {'Image.gz': regular(package / 'Image.gz'),
                               'kernel.config': regular(package / 'kernel.config'),
                               'board.dtb': regular(parent / 'board.dtb'),
                               'initramfs.img': ramdisk}.items():
                tools['write_file'](stage / name, data)
            command = [sys.executable, str(BOOT / 'build-android-boot-v0.py'),
                       '--kernel', str(stage / 'Image.gz'), '--ramdisk', str(stage / 'initramfs.img'),
                       '--dtb', str(stage / 'board.dtb'), '--name', 'gemini-obs-L',
                       '--cmdline', 'bootopt=64S3,32N2,64N2', '--kernel-addr', '0x40200000',
                       '--ramdisk-addr', '0x45000000', '--second-addr', '0x40f00000',
                       '--tags-addr', '0x44000000', '--lk-android8']
            subprocess.run(command + ['--output', str(stage / 'boot.img')], check=True,
                           stdout=subprocess.DEVNULL)
            raw = regular(stage / 'boot.img')
            require(len(raw) < PARTITION_BYTES, 'boot2 size exceeded')
            tools['write_file'](stage / 'boot2-padded.img', raw + bytes(PARTITION_BYTES - len(raw)))
            subprocess.run([sys.executable, str(BOOT / 'analyze-lk-boot-image.py'), '--validate-lk',
                            '--expected-image-gz', str(stage / 'Image.gz'),
                            '--expected-ramdisk', str(stage / 'initramfs.img'),
                            '--expected-dtb', str(stage / 'board.dtb'), '--expected-name', 'gemini-obs-L',
                            '--expected-cmdline', 'bootopt=64S3,32N2,64N2', str(stage / 'boot.img')],
                           check=True, stdout=subprocess.DEVNULL)
            result = {
                'status': 'offline-a53-service-ram-composition-validated',
                'recipe_commit': subprocess.check_output(['git', '-C', str(REPO), 'rev-parse', 'HEAD'], text=True).strip(),
                'recipe_sha256': digest(Path(__file__).read_bytes()),
                'kernel_build_commit': kernel['repository_commit'],
                'kernel_release': NEW_RELEASE.decode(),
                'kernel_package_sha256': digest(sums),
                'parent_receipt_sha256': digest(regular(parent_receipt)),
                'kernel_receipt_sha256': digest(regular(receipt_path)),
                'parent_boot_sha256': accepted['files']['boot.img'],
                'files': {p.name: {'sha256': digest(regular(p)), 'bytes': p.stat().st_size}
                          for p in sorted(stage.iterdir())},
                'initramfs_members': len(members), 'changed_members': ['init'],
                'init_sha256': digest(members['init'].data),
                'unchanged_device_tree': True, 'unchanged_member_count': len(members) - 1,
                'secret_bearing': True, 'device_action': 'none', 'physical_admission': False,
            }
            tools['write_file'](stage / 'candidate.json', (json.dumps(result, indent=2) + '\n').encode())
            stage.rename(output)
            print(json.dumps(result, indent=2))
        finally:
            if stage.exists():
                shutil.rmtree(stage)


if __name__ == '__main__':
    main()
