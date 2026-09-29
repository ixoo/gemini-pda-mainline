#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compose the passive region-19 private-export boot2 image."""

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
BASE = runpy.run_path(str(HERE.parent /
    '2026-09-28-mt6797-emi-set-probe/build-candidate.py'))
require, regular, sha, nodes = (BASE[name] for name in ('require', 'regular', 'sha', 'nodes'))
BOOT = REPO / 'experiments/2026-07-12-boot-contract-recovery/scripts'
PARENT_RECEIPT = HERE.parent / '2026-09-29-mt6797-region19-mainline-observe/results/candidate.json'
COMMIT = 'b489c1cd9fa91c63a6119ee2c009ca951373489b'
PROFILE = 'mt6797-a53-wifi-region19-export'
RELEASE = '7.1.3-gemini-a53-wifi-region19-export'
PARENT_SHA256 = 'b35f5ea717f9b4909f4743a92255baedb16a307723c4c4590f90f1e03052b2c5'
INITRAMFS_SHA256 = 'a5cd9bb770875dda3073e5068207eb7ba07531fd1f35d4c26736f15b3820cb37'
FIRMWARE_SHA256 = 'a69383d74d829430487c39eef6b5e281b25f901595c903a632a10aa8631426dd'
OWNER = '/consys@10001340'
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
            {p.name for p in parent.iterdir()} == set(accepted['files']) | {'candidate.json'} and
            json.loads(regular(parent / 'candidate.json')) == accepted and
            accepted['files']['boot2-padded.img']['sha256'] == PARENT_SHA256,
            'wrong passive parent')
    for name, identity in accepted['files'].items():
        data = regular(parent / name)
        require(len(data) == identity['bytes'] and sha(data) == identity['sha256'],
                'parent changed: ' + name)

    package = args.kernel_package.resolve(strict=True)
    require(package.is_dir() and not args.kernel_package.is_symlink() and
            package.name.startswith('linux-7.1.3-gemini-'), 'wrong package location')
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
            b'CONFIG_MTK_SCPSYS_PM_DOMAINS=y\n' in config and
            b'# CONFIG_MTK_SCPSYS is not set\n' in config and
            b'CONFIG_LOCALVERSION="-gemini-a53-wifi-region19-export"\n' in config,
            'kernel image or required configuration changed')
    board = regular(parent / 'board.dtb')
    built = nodes(package / 'dtbs/mediatek/mt6797-gemini-pda.dtb')
    previous = nodes(parent / 'board.dtb')
    phandles = {'memory-region', 'vcn18-supply', 'vcn28-supply',
                'vcn33-wifi-supply', 'resets'}
    require(previous[OWNER].keys() == built[OWNER].keys() and
            all(previous[OWNER][key] == built[OWNER][key]
                for key in previous[OWNER] if key not in phandles) and
            all(key in previous[OWNER] and key in built[OWNER]
                for key in phandles) and
            previous[OWNER]['reg'] == '<0x00 0x10001340 0x00 0x04>' and
            previous[OWNER]['reg-names'] == '"remap"' and
            'mediatek,one-shot-region19-observe' in previous[OWNER] and
            {key for key in previous[OWNER] if key.startswith('mediatek,one-shot-')} ==
            {'mediatek,one-shot-region19-observe'},
            'passive DT contract changed')
    initramfs = regular(args.initramfs.resolve(strict=True))
    require(sha(initramfs) == INITRAMFS_SHA256, 'private RAM root changed')
    parse = runpy.run_path(str(REPO /
        'experiments/2026-07-25-emmc-development/scripts/validate-emmc-initramfs.py'))['parse_newc']
    members = parse(initramfs)
    require(len(members) == 52 and
            sha(members['lib/firmware/mediatek/mt6797/WIFI_RAM_CODE_6797'].data) ==
            FIRMWARE_SHA256 and members['init'].data.count(RELEASE.encode()) == 1,
            'RAM-root release or firmware changed')

    output = Path(os.path.abspath(args.output))
    require(output.parent.is_dir() and not output.exists() and not output.is_symlink() and
            shutil.disk_usage(output.parent).free >= 256 * 1024 * 1024,
            'output occupied or insufficient space')
    with tempfile.TemporaryDirectory(prefix='.wifi-region19-export-stage-', dir=output.parent) as tmp:
        stage = Path(tmp)
        (stage / 'Image.gz').write_bytes(image)
        (stage / 'board.dtb').write_bytes(board)
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
        result = {'status': 'offline-gated-passive-region19-export-candidate-validated',
                  'kernel_build_commit': COMMIT, 'kernel_release': RELEASE,
                  'kernel_package_sha256': package_id,
                  'parent_boot2_sha256': PARENT_SHA256,
                  'firmware_sha256': FIRMWARE_SHA256,
                  'files': {p.name: {'sha256': sha(regular(p)), 'bytes': p.stat().st_size}
                            for p in sorted(stage.iterdir())},
                  'device_tree_change': 'none', 'secret_bearing': True,
                  'device_action': 'none', 'physical_admission': False}
        (stage / 'candidate.json').write_text(json.dumps(result, indent=2) + '\n')
        stage.rename(output)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
