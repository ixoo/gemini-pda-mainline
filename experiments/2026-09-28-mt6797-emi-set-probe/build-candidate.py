#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compose the EMI set probe on the observed HIF boot image."""

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
PARENT_RECEIPT = REPO / 'experiments/2026-09-28-mt6797-wifi-hif-probe/results/candidate.json'
BUILD_COMMIT = '5b99ce59d0b39132a9aa434143f201d506d9e026'
PROFILE = 'mt6797-a53-wifi-emi-set-probe'
RELEASE = '7.1.3-gemini-a53-wifi-emi-set-probe'
PARENT_BOOT2_SHA256 = '8e6d80e9c22b658ee8e79c7e4813d0ad80365d26907f2c374a69a2193c1c9049'
INITRAMFS_SHA256 = 'be97b760b9e086b184b4bb754fe11b8f8c03cc1edc9c84fc6cafad0f75abff98'
FIRMWARE_SHA256 = 'a69383d74d829430487c39eef6b5e281b25f901595c903a632a10aa8631426dd'
OWNER = '/consys@10001340'
WIFI = OWNER + '/wifi'
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
    script = REPO / 'experiments/2026-09-27-mt6797-conn-provider-passive/build-candidate.py'
    return runpy.run_path(str(script))['nodes'](path)


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
            'wrong observed HIF parent')
    for name, identity in accepted['files'].items():
        data = regular(parent / name)
        require(len(data) == identity['bytes'] and sha(data) == identity['sha256'],
                'parent changed: ' + name)

    package = args.kernel_package.resolve(strict=True)
    require(package.is_dir() and not args.kernel_package.is_symlink() and
            package.name.startswith('linux-7.1.3-gemini-'), 'wrong package location')
    package_id = package.name.removeprefix('linux-7.1.3-gemini-')
    require(len(package_id) == 64 and all(c in '0123456789abcdef' for c in package_id),
            'malformed package identity')
    audit = runpy.run_path(str(REPO /
        'experiments/2026-09-05-owner-away-experiment-preparation/baseline/audit_foundation.py'))
    sums = regular(package / 'SHA256SUMS')
    audit['inventory'](package, {'manifest_sha256': package_id,
                                 'inventory_count': len(sums.splitlines())})
    build = json.loads(regular(package / 'provenance/build.json'))
    require(build['repository_commit'] == BUILD_COMMIT and not build['repository_dirty'] and
            build['build_profile'] == PROFILE and build['kernel_release'] == RELEASE,
            'build provenance changed')
    image = regular(package / 'Image.gz')
    config = regular(package / 'kernel.config')
    require(gzip.decompress(image) == regular(package / 'Image') and
            b'CONFIG_MTK_MT6797_CONSYS=y\n' in config and
            b'CONFIG_FW_LOADER=y\n' in config and
            b'CONFIG_MTK_SCPSYS_PM_DOMAINS=y\n' in config and
            b'# CONFIG_MTK_SCPSYS is not set\n' in config and
            b'CONFIG_LOCALVERSION="-gemini-a53-wifi-emi-set-probe"\n' in config,
            'kernel image or required configuration changed')
    built = nodes(package / 'dtbs/mediatek/mt6797-gemini-pda.dtb')
    target = {name: built[OWNER][name] for name in
              ('reg', 'reg-names', 'mediatek,one-shot-power-probe',
               'mediatek,one-shot-chip-id-probe',
               'mediatek,one-shot-reset-release-probe',
               'mediatek,one-shot-hif-probe',
               'mediatek,one-shot-emi-set-probe')}
    require(target['mediatek,one-shot-power-probe'] is None and
            target['mediatek,one-shot-chip-id-probe'] is None and
            target['mediatek,one-shot-reset-release-probe'] is None and
            target['mediatek,one-shot-hif-probe'] is None and
            target['mediatek,one-shot-emi-set-probe'] is None and
            built[WIFI] == {'compatible': '"mediatek,mt6797-wlan"'},
            'compiled active CONSYS node changed')

    initramfs = regular(args.initramfs.resolve(strict=True))
    require(sha(initramfs) == INITRAMFS_SHA256, 'private RAM root changed')
    parse = runpy.run_path(str(REPO /
        'experiments/2026-07-25-emmc-development/scripts/validate-emmc-initramfs.py'))['parse_newc']
    members = parse(initramfs)
    require(len(members) == 52 and
            sha(members['lib/firmware/mediatek/mt6797/WIFI_RAM_CODE_6797'].data) ==
            FIRMWARE_SHA256 and RELEASE.encode() in members['init'].data and
            b'7.1.3-gemini-a53-wifi-hif-probe' not in members['init'].data,
            'RAM-root release or firmware changed')

    output = Path(os.path.abspath(args.output))
    require(output.parent.is_dir() and not output.exists() and not output.is_symlink() and
            shutil.disk_usage(output.parent).free >= 256 * 1024 * 1024,
            'output occupied or insufficient space')
    with tempfile.TemporaryDirectory(prefix='.wifi-emi-set-probe-stage-', dir=output.parent) as tmp:
        stage = Path(tmp)
        board = stage / 'board.dtb'
        board.write_bytes(regular(parent / 'board.dtb'))
        before = nodes(board)
        require(OWNER in before and WIFI in before and
                'mediatek,one-shot-emi-set-probe' not in before[OWNER] and
                all(before[OWNER][key] == target[key] for key in
                    ('mediatek,one-shot-power-probe',
                     'mediatek,one-shot-chip-id-probe',
                     'mediatek,one-shot-reset-release-probe',
                     'mediatek,one-shot-hif-probe')) and
                before[WIFI] == built[WIFI],
                'observed HIF DT contract changed')
        run('fdtput', '-t', 'x', str(board), OWNER, 'reg',
            '0', '10001340', '0', '4', '0', '10001350', '0', '4',
            '0', '18070008', '0', '4', '0', '18070110', '0', '4',
            '0', '180f0000', '0', '1100',
            '0', '10001f00', '0', '4')
        run('fdtput', '-t', 's', str(board), OWNER, 'reg-names',
            'remap', 'conn2ap-sleep-mask', 'chip-id', 'mcu-acr',
            'wifi-hif', 'emi-selector')
        run('fdtput', str(board), OWNER, 'mediatek,one-shot-emi-set-probe')
        after = nodes(board)
        expected_owner = dict(before[OWNER])
        expected_owner.update(target)
        require(set(after) == set(before) and after[OWNER] == expected_owner and
                all(after[name] == props for name, props in before.items()
                    if name != OWNER),
                'unrelated boot DT change or compiled CONSYS fields mismatch')
        (stage / 'Image.gz').write_bytes(image)
        (stage / 'kernel.config').write_bytes(config)
        (stage / 'initramfs.img').write_bytes(initramfs)
        boot = stage / 'boot.img'
        name = 'gemini-obs-P'
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
        result = {'status': 'offline-gated-wifi-emi-set-probe-candidate-validated',
                  'kernel_build_commit': BUILD_COMMIT, 'kernel_release': RELEASE,
                  'kernel_package_sha256': package_id,
                  'parent_boot2_sha256': PARENT_BOOT2_SHA256,
                  'firmware_sha256': FIRMWARE_SHA256,
                  'files': {p.name: {'sha256': sha(regular(p)), 'bytes': p.stat().st_size}
                            for p in sorted(stage.iterdir())},
                  'device_tree_change': 'CONSYS EMI selector resource and one-shot flag only',
                  'secret_bearing': True, 'device_action': 'none',
                  'physical_admission': False}
        (stage / 'candidate.json').write_text(json.dumps(result, indent=2) + '\n')
        stage.rename(output)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
