#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compose one private CONSYS handoff boot2 image from the tested A53 RAM image."""

import argparse
from dataclasses import replace
import gzip
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SERVICE = REPO / 'experiments/2026-09-09-standard-kernel-package'
BOOT = REPO / 'experiments/2026-07-12-boot-contract-recovery/scripts'
OLD_RELEASE = b'7.1.3-gemini-a53-service-facilities'
NEW_RELEASE = b'7.1.3-gemini-consys-handoff-snapshot'
BUILD_COMMIT = '2adf4c8df863870e3110590b6b8a35b14babd17e'
PACKAGE_ID = '3f5e1c51069bcd74f5e89529f55ed55e486eff6f1b4d8e7a39d75d33aa273697'
PARTITION_BYTES = 16777216


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def command(*args):
    return subprocess.check_output(args, stderr=subprocess.DEVNULL)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('kernel-package', 'parent', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    prior = runpy.run_path(str(SERVICE / 'build-a53-ram-candidate.py'))
    for path, expected in prior['TOOLS'].items():
        require(digest(path.read_bytes()) == expected, 'composition dependency changed')
    audit = runpy.run_path(str(prior['BASELINE'] / 'audit_foundation.py'))
    regular, safe_directory = audit['regular'], audit['safe_directory']
    tools = runpy.run_path(str(prior['BASELINE'] / 'scripts/build-candidate.py'))
    parse, encode = tools['parser_tools']()

    parent = safe_directory(args.parent)
    accepted = json.loads(regular(SERVICE / 'results/a53-service-ram-candidate.json'))
    require(accepted['kernel_release'] == OLD_RELEASE.decode(), 'wrong parent release')
    require({p.name for p in parent.iterdir()} == set(accepted['files']) | {'candidate.json'},
            'parent inventory changed')
    require(json.loads(regular(parent / 'candidate.json'))['files'] == accepted['files'],
            'parent receipt changed')
    for name, identity in accepted['files'].items():
        data = regular(parent / name)
        require(len(data) == identity['bytes'] and digest(data) == identity['sha256'],
                'parent member changed: ' + name)

    package = safe_directory(args.kernel_package)
    require(package.name == 'linux-7.1.3-gemini-' + PACKAGE_ID, 'wrong kernel package')
    sums = regular(package / 'SHA256SUMS')
    audit['inventory'](package, {'manifest_sha256': PACKAGE_ID,
                                 'inventory_count': len(sums.splitlines())})
    build = json.loads(regular(package / 'provenance/build.json'))
    require(build['repository_commit'] == BUILD_COMMIT and
            build['repository_dirty'] is False and
            build['kernel_release'] == NEW_RELEASE.decode() and
            build['build_profile'] == 'mt6797-a53-consys-handoff-snapshot',
            'kernel build identity changed')
    image = regular(package / 'Image.gz')
    require(gzip.decompress(image) == regular(package / 'Image'), 'compressed kernel mismatch')
    config = regular(package / 'kernel.config')
    require(b'CONFIG_MTK_MT6797_CONSYS_STATUS_SNAPSHOT=y\n' in config and
            b'CONFIG_MTK_MT6797_CONSYS_HANDOFF_SNAPSHOT=y\n' in config and
            b'# CONFIG_MTK_SCPSYS is not set\n' in config, 'observer config mismatch')
    symbols = regular(package / 'System.map')
    for name in (b'mt6797_consys_status_init',
                 b'mt6797_consys_handoff_init', b'__arm64_sys_pidfd_open',
                 b'__arm64_sys_pidfd_send_signal'):
        require(b' ' + name + b'\n' in symbols, 'required symbol missing')

    members = parse(regular(parent / 'initramfs.img'))
    require(len(members) == 47 and members['init'].data.count(OLD_RELEASE) == 1,
            'parent release gate changed')
    updated = dict(members)
    updated['init'] = replace(members['init'], data=members['init'].data.replace(
        OLD_RELEASE, NEW_RELEASE))
    require([name for name in members if updated[name] != members[name]] == ['init'],
            'unexpected RAM member change')
    ramdisk = encode(updated)
    require(parse(ramdisk) == updated, 'RAM archive round trip failed')

    output = Path(os.path.abspath(args.output))
    safe_directory(output.parent)
    require(not output.exists() and not output.is_symlink(), 'output occupied')
    require(shutil.disk_usage(output.parent).free >= 256 * 1024 * 1024,
            'insufficient free space')
    with tempfile.TemporaryDirectory(prefix='.consys-handoff-stage-', dir=output.parent) as tmp:
        stage = Path(tmp)
        board = stage / 'board.dtb'
        board.write_bytes(regular(parent / 'board.dtb'))
        original_dts = command('dtc', '-I', 'dtb', '-O', 'dts', str(board))
        old_compat = b'compatible = "mediatek,mt6797-scpsys";'
        new_compat = b'compatible = "mediatek,mt6797-scpsys", "syscon";'
        require(original_dts.count(old_compat) == 1, 'parent SPM compatible changed')
        subprocess.run(['fdtput', '-t', 's', str(board), '/power-controller@10006000',
                        'compatible', 'mediatek,mt6797-scpsys', 'syscon'], check=True)
        require(command('dtc', '-I', 'dtb', '-O', 'dts', str(board)) ==
                original_dts.replace(old_compat, new_compat),
                'device tree differs beyond one compatible property')
        require(command('fdtget', '-t', 's', str(board),
                        '/power-controller@10006000', 'compatible').strip() ==
                b'mediatek,mt6797-scpsys syscon', 'SPM syscon missing')
        for name, data in {'Image.gz': image, 'kernel.config': config,
                           'initramfs.img': ramdisk}.items():
            (stage / name).write_bytes(data)
        boot = stage / 'boot.img'
        subprocess.run([sys.executable, str(BOOT / 'build-android-boot-v0.py'),
                        '--kernel', str(stage / 'Image.gz'), '--ramdisk', str(stage / 'initramfs.img'),
                        '--dtb', str(board), '--name', 'gemini-obs-L',
                        '--cmdline', 'bootopt=64S3,32N2,64N2', '--kernel-addr', '0x40200000',
                        '--ramdisk-addr', '0x45000000', '--second-addr', '0x40f00000',
                        '--tags-addr', '0x44000000', '--lk-android8', '--output', str(boot)],
                       check=True, stdout=subprocess.DEVNULL)
        raw = regular(boot)
        require(len(raw) < PARTITION_BYTES, 'boot2 image too large')
        (stage / 'boot2-padded.img').write_bytes(raw + bytes(PARTITION_BYTES - len(raw)))
        subprocess.run([sys.executable, str(BOOT / 'analyze-lk-boot-image.py'),
                        '--validate-lk', '--expected-image-gz', str(stage / 'Image.gz'),
                        '--expected-ramdisk', str(stage / 'initramfs.img'),
                        '--expected-dtb', str(board), '--expected-name', 'gemini-obs-L',
                        '--expected-cmdline', 'bootopt=64S3,32N2,64N2', str(boot)],
                       check=True, stdout=subprocess.DEVNULL)
        result = {
            'status': 'offline-consys-handoff-composition-validated',
            'kernel_build_commit': BUILD_COMMIT, 'kernel_release': NEW_RELEASE.decode(),
            'kernel_package_sha256': PACKAGE_ID,
            'parent_boot_sha256': accepted['files']['boot.img']['sha256'],
            'files': {p.name: {'sha256': digest(regular(p)), 'bytes': p.stat().st_size}
                      for p in sorted(stage.iterdir())},
            'changed_ram_members': ['init'], 'unchanged_ram_members': 46,
            'device_tree_change': 'SPM compatible adds syscon only',
            'secret_bearing': True, 'device_action': 'none', 'physical_admission': False,
        }
        (stage / 'candidate.json').write_text(json.dumps(result, indent=2) + '\n')
        stage.rename(output)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
