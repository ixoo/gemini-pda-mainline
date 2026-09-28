#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compose the passive WLAN probe onto the boot-tested CONSYS DT."""

import argparse
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
BOOT = REPO / 'experiments/2026-07-12-boot-contract-recovery/scripts'
PARENT_RECEIPT = REPO / 'experiments/2026-09-27-mt6797-conn-domain-link-passive/results/candidate.json'
BUILD_COMMIT = '5b4e8726c6549b46a7e4046dc79c93e191785945'
PACKAGE_ID = '4e6240a8346042a7c850c53143990e2bb22f278ee5f8a0f793d0ab30136dc73b'
PROFILE = 'mt6797-a53-wifi-firmware-probe'
RELEASE = '7.1.3-gemini-a53-wifi-firmware-probe'
FIRMWARE_INITRAMFS_SHA256 = 'b4fc6ec679d9a8beb0678244354ae078c628e8c3ea6f68649234dfc237db2367'
FIRMWARE_SHA256 = 'a69383d74d829430487c39eef6b5e281b25f901595c903a632a10aa8631426dd'
WIFI_NODE = '/consys@10001340/wifi'
PARENT_BOOT2_SHA256 = '07dfcc16b6c66442f47c5540eb24a9c1e057c6827d20787b74f39fe945569230'
PARTITION_BYTES = 16777216


def require(condition, message):
    if not condition:
        raise ValueError(message)


def regular(path):
    require(path.is_file() and not path.is_symlink(), 'missing or linked input: ' + str(path))
    return path.read_bytes()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def run(*argv):
    return subprocess.run(argv, check=True, capture_output=True).stdout


def nodes(path):
    return runpy.run_path(str(REPO /
        'experiments/2026-09-27-mt6797-conn-provider-passive/build-candidate.py'))['nodes'](path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('kernel-package', 'parent', 'initramfs', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)

    parent = args.parent.resolve(strict=True)
    accepted = json.loads(regular(PARENT_RECEIPT))
    require(parent.is_dir() and not args.parent.is_symlink() and
            {p.name for p in parent.iterdir()} == set(accepted['files']) | {'candidate.json'} and
            json.loads(regular(parent / 'candidate.json')) == accepted and
            accepted['files']['boot2-padded.img']['sha256'] == PARENT_BOOT2_SHA256,
            'wrong boot-tested CONSYS parent')
    for name, identity in accepted['files'].items():
        data = regular(parent / name)
        require(len(data) == identity['bytes'] and sha(data) == identity['sha256'],
                'parent changed: ' + name)

    package = args.kernel_package.resolve(strict=True)
    require(package.is_dir() and not args.kernel_package.is_symlink() and
            package.name == 'linux-7.1.3-gemini-' + PACKAGE_ID, 'wrong kernel package')
    audit = runpy.run_path(str(REPO /
        'experiments/2026-09-05-owner-away-experiment-preparation/baseline/audit_foundation.py'))
    sums = regular(package / 'SHA256SUMS')
    audit['inventory'](package, {'manifest_sha256': PACKAGE_ID,
                                 'inventory_count': len(sums.splitlines())})
    build = json.loads(regular(package / 'provenance/build.json'))
    require(build['repository_commit'] == BUILD_COMMIT and not build['repository_dirty'] and
            build['build_profile'] == PROFILE and build['kernel_release'] == RELEASE,
            'build provenance changed')
    image = regular(package / 'Image.gz')
    config = regular(package / 'kernel.config')
    require(gzip.decompress(image) == regular(package / 'Image') and
            b'CONFIG_MTK_MT6797_CONSYS=y\n' in config and
            b'CONFIG_MT6797_HIF_CORE=y\n' in config and
            b'CONFIG_FW_LOADER=y\n' in config and
            b'# CONFIG_MTK_SCPSYS is not set\n' in config and
            b'CONFIG_MTK_SCPSYS_PM_DOMAINS=y\n' in config,
            'kernel image or required configuration changed')
    require(nodes(package / 'dtbs/mediatek/mt6797-gemini-pda.dtb')[WIFI_NODE] ==
            {'compatible': '"mediatek,mt6797-wlan"'},
            'compiled WLAN child changed')

    initramfs = regular(args.initramfs.resolve(strict=True))
    require(sha(initramfs) == FIRMWARE_INITRAMFS_SHA256,
            'private firmware initramfs changed')
    parse = runpy.run_path(str(REPO /
        'experiments/2026-07-25-emmc-development/scripts/validate-emmc-initramfs.py'))['parse_newc']
    members = parse(initramfs)
    require(len(members) == 52 and
            sha(members['lib/firmware/mediatek/mt6797/WIFI_RAM_CODE_6797'].data) ==
            FIRMWARE_SHA256 and
            b'7.1.3-gemini-a53-wifi-firmware-probe' in members['init'].data and
            b'7.1.3-gemini-a53-consys-owner-passive' not in members['init'].data,
            'staged firmware or RAM-root release gate changed')

    output = Path(os.path.abspath(args.output))
    require(output.parent.is_dir() and not output.exists() and not output.is_symlink() and
            shutil.disk_usage(output.parent).free >= 256 * 1024 * 1024,
            'output occupied or insufficient space')
    with tempfile.TemporaryDirectory(prefix='.wifi-firmware-stage-', dir=output.parent) as tmp:
        stage = Path(tmp)
        board = stage / 'board.dtb'
        board.write_bytes(regular(parent / 'board.dtb'))
        before = nodes(board)
        require(WIFI_NODE not in before and
                before['/consys@10001340']['mediatek,conn-power-domain'] == '<0x40 0x0c>',
                'parent DT lacks tested checked-OFF owner link')
        run('fdtput', '-c', str(board), WIFI_NODE)
        run('fdtput', '-t', 's', str(board), WIFI_NODE, 'compatible', 'mediatek,mt6797-wlan')
        after = nodes(board)
        require(set(after) == set(before) | {WIFI_NODE} and
                after[WIFI_NODE] == {'compatible': '"mediatek,mt6797-wlan"'} and
                all(after[name] == props for name, props in before.items()),
                'unrelated boot DT change')
        (stage / 'Image.gz').write_bytes(image)
        (stage / 'kernel.config').write_bytes(config)
        (stage / 'initramfs.img').write_bytes(initramfs)
        boot = stage / 'boot.img'
        name = 'gemini-obs-W'
        cmdline = 'bootopt=64S3,32N2,64N2'
        subprocess.run([sys.executable, str(BOOT / 'build-android-boot-v0.py'),
                        '--kernel', str(stage / 'Image.gz'), '--ramdisk', str(stage / 'initramfs.img'),
                        '--dtb', str(board), '--name', name, '--cmdline', cmdline,
                        '--kernel-addr', '0x40200000', '--ramdisk-addr', '0x45000000',
                        '--second-addr', '0x40f00000', '--tags-addr', '0x44000000',
                        '--lk-android8', '--output', str(boot)],
                       check=True, stdout=subprocess.DEVNULL)
        raw = regular(boot)
        require(len(raw) < PARTITION_BYTES, 'boot2 image too large')
        (stage / 'boot2-padded.img').write_bytes(raw + bytes(PARTITION_BYTES - len(raw)))
        subprocess.run([sys.executable, str(BOOT / 'analyze-lk-boot-image.py'),
                        '--validate-lk', '--expected-image-gz', str(stage / 'Image.gz'),
                        '--expected-ramdisk', str(stage / 'initramfs.img'),
                        '--expected-dtb', str(board), '--expected-name', name,
                        '--expected-cmdline', cmdline, str(boot)],
                       check=True, stdout=subprocess.DEVNULL)
        result = {'status': 'offline-passive-wlan-firmware-candidate-validated',
                  'kernel_build_commit': BUILD_COMMIT, 'kernel_release': RELEASE,
                  'kernel_package_sha256': PACKAGE_ID,
                  'parent_boot2_sha256': PARENT_BOOT2_SHA256,
                  'firmware_sha256': FIRMWARE_SHA256,
                  'files': {p.name: {'sha256': sha(regular(p)), 'bytes': p.stat().st_size}
                            for p in sorted(stage.iterdir())},
                  'device_tree_change': 'one passive CONSYS wifi child',
                  'secret_bearing': True, 'device_action': 'none',
                  'physical_admission': False}
        (stage / 'candidate.json').write_text(json.dumps(result, indent=2) + '\n')
        stage.rename(output)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
