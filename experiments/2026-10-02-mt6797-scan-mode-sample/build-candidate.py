#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compose one receive mode diagnostic boot image from the proven booted DT."""

import argparse
import gzip
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
BASE = runpy.run_path(str(HERE.parent / '2026-10-01-mt6797-port0-header/build-candidate.py'))
require, regular, sha = (BASE[name] for name in ('require', 'regular', 'sha'))
BOOT = REPO / 'experiments/2026-07-12-boot-contract-recovery/scripts'
PARENT_RECEIPT = HERE.parent / '2026-10-02-mt6797-scan-rx-sample/results/candidate.json'
COMMIT = '669cfbc9e801ab42ed9af06a3e55bbfad3e38f14'
PROFILE = 'mt6797-a53-wifi-scan-mode-sample'
RELEASE = '7.1.3-gemini-a53-wifi-scan-mode-sample'
PARENT_BOOT2_SHA256 = '4a9499f1861dbc899edb7ebcdf54cf08e8c52a727794870469f13f686397385a'
BOOTED_DTB_SHA256 = 'cef9373ea3aa0e1a8a45a13b953ae95e48939b211e41a73052543be784ee3214'
BUILT_DTB_SHA256 = '5abe5d14ddb424c5939e7ac6f6303210774f85e6be1413f2730f31804df046ca'
INITRAMFS_SHA256 = '45ad776af75d8a7785eee23376436f98a7a8fd081f13f0b3ad0df15dc1475281'
FIRMWARE_SHA256 = 'a69383d74d829430487c39eef6b5e281b25f901595c903a632a10aa8631426dd'
FIRMWARE_MEMBER = 'lib/firmware/mediatek/mt6797/WIFI_RAM_CODE_6797'
RECORD_MEMBER = 'lib/firmware/mediatek/mt6797/WIFI.storage'
PARTITION_BYTES = 16777216


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('kernel-package', 'parent', 'initramfs', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)

    parent = args.parent.resolve(strict=True)
    accepted = json.loads(regular(PARENT_RECEIPT))
    require(parent.is_dir() and not args.parent.is_symlink() and
            parent.name == 'candidate-' + accepted['files']['boot.img']['sha256'] and
            {p.name for p in parent.iterdir()} == set(accepted['files']) | {'candidate.json'} and
            json.loads(regular(parent / 'candidate.json')) == accepted and
            accepted['files']['boot2-padded.img']['sha256'] == PARENT_BOOT2_SHA256 and
            accepted['files']['board.dtb']['sha256'] == BOOTED_DTB_SHA256,
            'booted parent changed')
    for name, identity in accepted['files'].items():
        data = regular(parent / name)
        require(len(data) == identity['bytes'] and sha(data) == identity['sha256'],
                'parent member changed: ' + name)

    package = args.kernel_package.resolve(strict=True)
    require(package.is_dir() and not args.kernel_package.is_symlink() and
            package.name.startswith('linux-7.1.3-gemini-'), 'package location changed')
    package_id = package.name.removeprefix('linux-7.1.3-gemini-')
    audit = runpy.run_path(str(REPO /
        'experiments/2026-09-05-owner-away-experiment-preparation/baseline/audit_foundation.py'))
    sums = regular(package / 'SHA256SUMS')
    audit['inventory'](package, {'manifest_sha256': package_id,
                                 'inventory_count': len(sums.splitlines())})
    build = json.loads(regular(package / 'provenance/build.json'))
    require(build['repository_commit'] == COMMIT and not build['repository_dirty'] and
            build['build_profile'] == PROFILE and build['kernel_release'] == RELEASE,
            'build provenance changed')
    image = regular(package / 'Image.gz')
    config = regular(package / 'kernel.config')
    require(gzip.decompress(image) == regular(package / 'Image') and
            b'CONFIG_MTK_MT6797_CONSYS=y\n' in config and
            b'CONFIG_MT6797_HIF_CORE=y\n' in config and
            b'CONFIG_MT6797_MAC80211=y\n' in config and
            b'CONFIG_MT6797_HIF_TX_STATUS_PROBE=y\n' in config and
            b'CONFIG_MT6797_HIF_TC4_RECONCILE=y\n' in config and
            b'CONFIG_MT6797_PASSIVE_SCAN=y\n' in config and
            b'CONFIG_MT6797_SCAN_MODE_SAMPLE=y\n' in config and
            b'CONFIG_MAC80211=y\n' in config and
            b'CONFIG_CFG80211=y\n' in config and
            ('CONFIG_LOCALVERSION="-' + RELEASE.split('-', 1)[1] + '"\n').encode() in config,
            'kernel image or configuration changed')
    require(sha(regular(package / 'dtbs/mediatek/mt6797-gemini-pda.dtb')) ==
            BUILT_DTB_SHA256, 'compiled board DT changed from selected predecessor')

    initramfs = regular(args.initramfs.resolve(strict=True))
    require(sha(initramfs) == INITRAMFS_SHA256, 'private RAM root changed')
    parse = runpy.run_path(str(REPO /
        'experiments/2026-07-25-emmc-development/scripts/validate-emmc-initramfs.py'))['parse_newc']
    old_members = parse(regular(parent / 'initramfs.img'))
    new_members = parse(initramfs)
    old_release = b'7.1.3-gemini-a53-wifi-scan-rx-sample'
    userspace_raw = regular(HERE.parent / '2026-10-01-mt6797-passive-scan/results/userspace.json')
    require(sha(userspace_raw) == '4aedbc779d32fc6729de689cda22d0ace5ba8f2050134ec95c81f699a138498c',
            'userspace receipt changed')
    userspace = json.loads(userspace_raw)['files']
    require(len(old_members) == 59 and len(new_members) == 59 and
            set(new_members) == set(old_members) and
            new_members[RECORD_MEMBER] == old_members[RECORD_MEMBER] and
            new_members[RECORD_MEMBER].mode == 0o100600 and
            len(new_members[RECORD_MEMBER].data) == 514 and
            sha(new_members[FIRMWARE_MEMBER].data) == FIRMWARE_SHA256 and
            old_members['init'].data.count(old_release) == 1 and
            new_members['init'].data == old_members['init'].data.replace(
                old_release, RELEASE.encode()) and
            all(new_members[name] == member for name, member in old_members.items()
                if name != 'init') and
            all(sha(new_members[item['path']].data) == item['sha256'] and
                len(new_members[item['path']].data) == item['bytes'] and
                new_members[item['path']].mode ==
                (0o100755 if item['path'] in {'bin/iw', 'lib/ld-linux-aarch64.so.1'}
                 else 0o100644) for item in userspace),
            'RAM root changed outside release gate or pinned userspace')

    output = Path(os.path.abspath(args.output))
    require(output.parent.is_dir() and not output.exists() and not output.is_symlink() and
            shutil.disk_usage(output.parent).free >= 256 * 1024 * 1024,
            'output occupied or insufficient space')
    with tempfile.TemporaryDirectory(prefix='.wifi-passive-scan-', dir=output.parent) as tmp:
        stage = Path(tmp)
        (stage / 'Image.gz').write_bytes(image)
        (stage / 'board.dtb').write_bytes(regular(parent / 'board.dtb'))
        (stage / 'kernel.config').write_bytes(config)
        (stage / 'initramfs.img').write_bytes(initramfs)
        boot = stage / 'boot.img'
        name = 'gemini-obs-P'
        cmdline = 'bootopt=64S3,32N2,64N2'
        subprocess.run([sys.executable, str(BOOT / 'build-android-boot-v0.py'),
                        '--kernel', str(stage / 'Image.gz'), '--ramdisk',
                        str(stage / 'initramfs.img'), '--dtb', str(stage / 'board.dtb'),
                        '--name', name, '--cmdline', cmdline,
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
                        '--expected-dtb', str(stage / 'board.dtb'), '--expected-name', name,
                        '--expected-cmdline', cmdline, str(boot)],
                       check=True, stdout=subprocess.DEVNULL)
        result = {'status': 'offline-gated-scan-mode-sample-candidate-validated',
                  'kernel_build_commit': COMMIT, 'kernel_release': RELEASE,
                  'kernel_package_sha256': package_id,
                  'parent_boot2_sha256': PARENT_BOOT2_SHA256,
                  'booted_dtb_sha256': BOOTED_DTB_SHA256,
                  'firmware_sha256': FIRMWARE_SHA256,
                  'files': {p.name: {'sha256': sha(regular(p)), 'bytes': p.stat().st_size}
                            for p in sorted(stage.iterdir())},
                  'device_tree_change': 'none from proven booted board DT',
                  'secret_bearing': True, 'device_action': 'none',
                  'physical_admission': False}
        (stage / 'candidate.json').write_text(json.dumps(result, indent=2) + '\n')
        stage.rename(output)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
