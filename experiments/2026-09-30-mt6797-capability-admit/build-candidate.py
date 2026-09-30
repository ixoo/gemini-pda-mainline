#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compose the bounded WLAN capability-admit diagnostic boot2 image."""

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
PARENT_RECEIPT = HERE.parent / '2026-09-29-mt6797-region19-wmt-memory/results/candidate.json'
COMMIT = '9c7ef140eea1fc1fd0d2138c3828e95824e11ad8'
PROFILE = 'mt6797-a53-wifi-capability-admit'
RELEASE = '7.1.3-gemini-a53-wifi-capability-admit'
PARENT_SHA256 = '0083834cea0e62d004dc92bf087c8167dfcf6dbbe6cf764a3e8d04d487261b8f'
INITRAMFS_SHA256 = 'a701a2d42568744bac1b42eb479920b961c09fdbd52b996972737cd561b93cfc'
FIRMWARE_SHA256 = 'a69383d74d829430487c39eef6b5e281b25f901595c903a632a10aa8631426dd'
OWNER = '/consys@10001340'
PARTITION_BYTES = 16777216
BOOTED_DTB_SHA256 = 'cef9373ea3aa0e1a8a45a13b953ae95e48939b211e41a73052543be784ee3214'


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
            'wrong WMT-memory parent')
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
            b'CONFIG_LOCALVERSION="-gemini-a53-wifi-capability-admit"\n' in config,
            'kernel image or required configuration changed')
    built = nodes(package / 'dtbs/mediatek/mt6797-gemini-pda.dtb')
    previous = nodes(parent / 'board.dtb')
    phandles = {'memory-region', 'vcn18-supply', 'vcn28-supply',
                'vcn33-wifi-supply', 'resets'}
    added = {'mediatek,one-shot-power-probe',
             'mediatek,one-shot-chip-id-probe',
             'mediatek,one-shot-reset-release-probe',
             'mediatek,one-shot-hif-probe',
             'mediatek,one-shot-emi-set-probe',
             'mediatek,one-shot-emi-copy-probe',
             'mediatek,one-shot-firmware-start-probe',
             'mediatek,deferred-wmt-firmware-start'}
    require(set(built[OWNER]) == set(previous[OWNER]) | added and
            all(previous[OWNER][key] == built[OWNER][key]
                for key in previous[OWNER] if key not in phandles | {'reg', 'reg-names'}) and
            all(key in previous[OWNER] and key in built[OWNER]
                for key in phandles) and
            all(built[OWNER][key] is None for key in added) and
            previous[OWNER]['reg'] == '<0x00 0x10001340 0x00 0x04>' and
            previous[OWNER]['reg-names'] == '"remap"' and
            built[OWNER]['reg'] ==
            '<0x00 0x10001340 0x00 0x04 0x00 0x10001350 0x00 0x04 '
            '0x00 0x18070008 0x00 0x04 0x00 0x18070110 0x00 0x04 '
            '0x00 0x180f0000 0x00 0x1100 0x00 0x10001f00 0x00 0x04>' and
            built[OWNER]['reg-names'] ==
            '"remap", "conn2ap-sleep-mask", "chip-id", "mcu-acr", '
            '"wifi-hif", "emi-selector"' and
            'mediatek,one-shot-region19-observe' in previous[OWNER] and
            {key for key in previous[OWNER] if key.startswith('mediatek,one-shot-')} ==
            {'mediatek,one-shot-region19-observe'},
            'deferred-start DT contract changed')
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
    with tempfile.TemporaryDirectory(prefix='.wifi-capability-admit-stage-', dir=output.parent) as tmp:
        stage = Path(tmp)
        (stage / 'Image.gz').write_bytes(image)
        board = stage / 'board.dtb'
        board.write_bytes(regular(parent / 'board.dtb'))
        before = nodes(board)
        require(before == previous and OWNER in before and
                set(built[OWNER]) == set(before[OWNER]) | added and
                built[OWNER]['compatible'] == before[OWNER]['compatible'],
                'booted parent DT or compiled CONSYS contract changed')
        subprocess.run(['fdtput', '-t', 'x', str(board), OWNER, 'reg',
                        '0', '10001340', '0', '4', '0', '10001350', '0', '4',
                        '0', '18070008', '0', '4', '0', '18070110', '0', '4',
                        '0', '180f0000', '0', '1100', '0', '10001f00', '0', '4'],
                       check=True, stdout=subprocess.DEVNULL)
        subprocess.run(['fdtput', '-t', 's', str(board), OWNER, 'reg-names',
                        'remap', 'conn2ap-sleep-mask', 'chip-id', 'mcu-acr',
                        'wifi-hif', 'emi-selector'],
                       check=True, stdout=subprocess.DEVNULL)
        for name in sorted(added):
            subprocess.run(['fdtput', str(board), OWNER, name],
                           check=True, stdout=subprocess.DEVNULL)
        after = nodes(board)
        expected_owner = dict(before[OWNER])
        expected_owner.update({key: built[OWNER][key] for key in
                               added | {'reg', 'reg-names'}})
        require(set(after) == set(before) and after[OWNER] == expected_owner and
                all(after[name] == props for name, props in before.items()
                    if name != OWNER),
                'unrelated boot DT change or compiled CONSYS fields mismatch')
        require(sha(regular(board)) == BOOTED_DTB_SHA256,
                'booted WMT-start board DT identity changed')
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
        result = {'status': 'offline-gated-capability-admit-candidate-validated',
                  'kernel_build_commit': COMMIT, 'kernel_release': RELEASE,
                  'kernel_package_sha256': package_id,
                  'parent_boot2_sha256': PARENT_SHA256,
                  'firmware_sha256': FIRMWARE_SHA256,
                  'files': {p.name: {'sha256': sha(regular(p)), 'bytes': p.stat().st_size}
                            for p in sorted(stage.iterdir())},
                  'device_tree_change': 'only CONSYS resources and deferred flags on booted parent DT',
                  'secret_bearing': True,
                  'device_action': 'none', 'physical_admission': False}
        (stage / 'candidate.json').write_text(json.dumps(result, indent=2) + '\n')
        stage.rename(output)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
