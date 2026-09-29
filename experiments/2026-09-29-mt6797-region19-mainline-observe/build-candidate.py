#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compose the passive region-19 probe from the firmware-start candidate."""

import argparse
import gzip
import importlib.util
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
SOURCE = HERE.parent / '2026-09-28-mt6797-emi-set-probe/build-candidate.py'
SPEC = importlib.util.spec_from_file_location('emi_set_candidate', SOURCE)
OLD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(OLD)
BOOT = REPO / 'experiments/2026-07-12-boot-contract-recovery/scripts'
PARENT_RECEIPT = HERE.parent / '2026-09-28-mt6797-firmware-start-probe/results/candidate.json'
BUILD_COMMIT = '13f2e94ea8b33b52e46ce98c6ea6bfef242d6eef'
PROFILE = 'mt6797-a53-wifi-region19-observe'
RELEASE = '7.1.3-gemini-a53-wifi-region19-observe'
PARENT_BOOT2_SHA256 = '3590bddf2e4ddbc21923bab0ccf18b36c90e365935dca0bafcbdd09aaf6140a6'
INITRAMFS_SHA256 = 'fb4eb60e1d0d86c6340db0041a7326650e1c7870e7548c3f5ee9ca684131aa75'
FIRMWARE_SHA256 = 'a69383d74d829430487c39eef6b5e281b25f901595c903a632a10aa8631426dd'
OWNER = '/consys@10001340'
WIFI = OWNER + '/wifi'
PARTITION_BYTES = 16777216
require, regular, sha, run, nodes = OLD.require, OLD.regular, OLD.sha, OLD.run, OLD.nodes


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
            'wrong firmware-start parent')
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
            b'CONFIG_MT6797_HIF_CORE=y\n' in config and
            b'CONFIG_FW_LOADER=y\n' in config and
            b'CONFIG_MTK_SCPSYS_PM_DOMAINS=y\n' in config and
            b'# CONFIG_MTK_SCPSYS is not set\n' in config and
            b'CONFIG_LOCALVERSION="-gemini-a53-wifi-region19-observe"\n' in config,
            'kernel image or required configuration changed')
    built = nodes(package / 'dtbs/mediatek/mt6797-gemini-pda.dtb')
    require(OWNER in built and WIFI in built and
            built[WIFI] == {'compatible': '"mediatek,mt6797-wlan"'} and
            'mediatek,one-shot-region19-observe' in built[OWNER] and
            built[OWNER]['mediatek,one-shot-region19-observe'] is None and
            not any(key.startswith('mediatek,one-shot-') and
                    key != 'mediatek,one-shot-region19-observe'
                    for key in built[OWNER]),
            'compiled passive region-19 DT contract changed')

    initramfs = regular(args.initramfs.resolve(strict=True))
    require(sha(initramfs) == INITRAMFS_SHA256, 'private RAM root changed')
    parse = runpy.run_path(str(REPO /
        'experiments/2026-07-25-emmc-development/scripts/validate-emmc-initramfs.py'))['parse_newc']
    members = parse(initramfs)
    require(len(members) == 52 and
            sha(members['lib/firmware/mediatek/mt6797/WIFI_RAM_CODE_6797'].data) ==
            FIRMWARE_SHA256 and RELEASE.encode() in members['init'].data and
            b'7.1.3-gemini-a53-wifi-firmware-start-probe' not in members['init'].data,
            'RAM-root release or firmware changed')

    output = Path(os.path.abspath(args.output))
    require(output.parent.is_dir() and not output.exists() and not output.is_symlink() and
            shutil.disk_usage(output.parent).free >= 256 * 1024 * 1024,
            'output occupied or insufficient space')
    with tempfile.TemporaryDirectory(prefix='.wifi-region19-observe-stage-', dir=output.parent) as tmp:
        stage = Path(tmp)
        board = stage / 'board.dtb'
        board.write_bytes(regular(parent / 'board.dtb'))
        before = nodes(board)
        require(OWNER in before and WIFI in before and
                'mediatek,one-shot-firmware-start-probe' in before[OWNER] and
                'mediatek,one-shot-region19-observe' not in before[OWNER] and
                before[WIFI] == built[WIFI] and
                {key for key in before[OWNER] if key.startswith('mediatek,one-shot-')} ==
                {'mediatek,one-shot-power-probe', 'mediatek,one-shot-chip-id-probe',
                 'mediatek,one-shot-reset-release-probe', 'mediatek,one-shot-hif-probe',
                 'mediatek,one-shot-emi-set-probe', 'mediatek,one-shot-emi-copy-probe',
                 'mediatek,one-shot-firmware-start-probe'} and
                all(before[OWNER][key] == built[OWNER][key] for key in
                    ('compatible', 'reg', 'reg-names')),
                'firmware-start parent DT contract changed')
        for flag in sorted(key for key in before[OWNER]
                           if key.startswith('mediatek,one-shot-')):
            run('fdtput', '-d', str(board), OWNER, flag)
        run('fdtput', str(board), OWNER, 'mediatek,one-shot-region19-observe')
        after = nodes(board)
        expected_owner = dict(before[OWNER])
        for flag in tuple(expected_owner):
            if flag.startswith('mediatek,one-shot-'):
                del expected_owner[flag]
        expected_owner['mediatek,one-shot-region19-observe'] = None
        require(set(after) == set(before) and after[OWNER] == expected_owner and
                all(after[name] == props for name, props in before.items()
                    if name != OWNER),
                'unrelated boot DT change')
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
        result = {'status': 'offline-gated-passive-region19-observe-candidate-validated',
                  'kernel_build_commit': BUILD_COMMIT, 'kernel_release': RELEASE,
                  'kernel_package_sha256': package_id,
                  'parent_boot2_sha256': PARENT_BOOT2_SHA256,
                  'firmware_sha256': FIRMWARE_SHA256,
                  'files': {p.name: {'sha256': sha(regular(p)), 'bytes': p.stat().st_size}
                            for p in sorted(stage.iterdir())},
                  'device_tree_change': 'remove seven active probes; add passive region19 observer',
                  'secret_bearing': True, 'device_action': 'none',
                  'physical_admission': False}
        (stage / 'candidate.json').write_text(json.dumps(result, indent=2) + '\n')
        stage.rename(output)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
