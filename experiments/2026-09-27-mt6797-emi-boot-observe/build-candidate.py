#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Replace only the kernel in the boot-tested VCN28 observer candidate."""

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
PARENT_RECEIPT = (REPO / 'experiments/2026-09-27-mt6351-vcn28-boot-observe'
                  / 'results/candidate.json')
BOOT = REPO / 'experiments/2026-07-12-boot-contract-recovery/scripts'
BUILD_COMMIT = '35465d470dbc7dbc3720a1b3436d8b2ff42d67e6'
PACKAGE_ID = '96f235567f0b259f1026cd88f12cacb5e6bda92321499fe53cc2956b1a25cfe8'
PROFILE = 'mt6797-a53-emi-boot-observe'
RELEASE = '7.1.3-gemini-a53-consys-owner-passive'
PARENT_RECEIPT_SHA = '03b0782e90125f3c7e2b047afc652305878a35367aa7fcb2b04c7330606c17e3'
PARENT_BOOT2_SHA = 'a592c6032e26da3fc6125d954a134a20a30072dbf0f550f585901869e2ce536b'
PARTITION_BYTES = 16777216


def require(condition, message):
    if not condition:
        raise ValueError(message)


def regular(path):
    require(path.is_file() and not path.is_symlink(), 'missing or linked input: ' + str(path))
    return path.read_bytes()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def run(*args):
    return subprocess.run(args, check=True, capture_output=True).stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('kernel-package', 'parent', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)

    require(sha(regular(PARENT_RECEIPT)) == PARENT_RECEIPT_SHA,
            'parent public receipt changed')
    accepted = json.loads(regular(PARENT_RECEIPT))
    parent = args.parent.resolve(strict=True)
    require(parent.is_dir() and not args.parent.is_symlink() and
            {p.name for p in parent.iterdir()} == set(accepted['files']) | {'candidate.json'} and
            json.loads(regular(parent / 'candidate.json')) == accepted,
            'wrong private parent candidate')
    for name, identity in accepted['files'].items():
        data = regular(parent / name)
        require(len(data) == identity['bytes'] and sha(data) == identity['sha256'],
                'changed parent file: ' + name)
    require(accepted['files']['boot2-padded.img']['sha256'] == PARENT_BOOT2_SHA,
            'wrong boot-tested predecessor')

    package = args.kernel_package.resolve(strict=True)
    require(package.is_dir() and not args.kernel_package.is_symlink() and
            package.name == 'linux-7.1.3-gemini-' + PACKAGE_ID,
            'wrong kernel package')
    audit = runpy.run_path(str(REPO / 'experiments/2026-09-05-owner-away-experiment-preparation'
                               / 'baseline/audit_foundation.py'))
    sums = regular(package / 'SHA256SUMS')
    audit['inventory'](package, {'manifest_sha256': PACKAGE_ID,
                                 'inventory_count': len(sums.splitlines())})
    build = json.loads(regular(package / 'provenance/build.json'))
    require(build['repository_commit'] == BUILD_COMMIT and not build['repository_dirty'] and
            build['build_profile'] == PROFILE and build['kernel_release'] == RELEASE,
            'build provenance changed')
    image = regular(package / 'Image.gz')
    kernel = regular(package / 'Image')
    require(gzip.decompress(image) == kernel and
            sha(image) != accepted['files']['Image.gz']['sha256'],
            'new kernel unchanged or damaged')
    require(b'VCN28 boot control=0x%04x on=%u source-mode=%u' in kernel and
            b'EMI boot region=%u range=0x%08x policy=0x%08x' in kernel,
            'VCN28 or EMI observation record missing from built Image')
    config = regular(package / 'kernel.config')
    require(sha(config) == accepted['files']['kernel.config']['sha256'] and
            b'CONFIG_MTK_MT6797_CONSYS=y\n' in config and
            b'CONFIG_REGULATOR_MT6351=y\n' in config and
            b'CONFIG_MTK_SCPSYS_PM_DOMAINS=y\n' in config,
            'kernel config changed')
    symbols = regular(package / 'System.map')
    require(b' mt6797_consys_probe\n' in symbols and
            b' regulator_get_regmap\n' in symbols and
            b' mt6797_consys_read_emi\n' in symbols,
            'CONSYS owner or regulator accessor missing')
    board = regular(parent / 'board.dtb')
    built = package / 'dtbs/mediatek/mt6797-gemini-pda.dtb'
    require(run('fdtget', '-t', 'x', str(built), '/consys@10001340',
                'mediatek,conn-power-domain').strip() == b'40 c',
            'built DT lost CONN link')

    output = Path(os.path.abspath(args.output))
    require(output.parent.is_dir() and not output.exists() and not output.is_symlink(),
            'output path occupied')
    require(shutil.disk_usage(output.parent).free >= 256 * 1024 * 1024,
            'insufficient free space')
    with tempfile.TemporaryDirectory(prefix='.emi-observe-stage-',
                                     dir=output.parent) as tmp:
        stage = Path(tmp)
        for name, data in (('Image.gz', image), ('board.dtb', board),
                           ('kernel.config', config),
                           ('initramfs.img', regular(parent / 'initramfs.img'))):
            (stage / name).write_bytes(data)
        boot = stage / 'boot.img'
        subprocess.run([sys.executable, str(BOOT / 'build-android-boot-v0.py'),
                        '--kernel', str(stage / 'Image.gz'),
                        '--ramdisk', str(stage / 'initramfs.img'),
                        '--dtb', str(stage / 'board.dtb'),
                        '--name', 'gemini-obs-L',
                        '--cmdline', 'bootopt=64S3,32N2,64N2',
                        '--kernel-addr', '0x40200000',
                        '--ramdisk-addr', '0x45000000',
                        '--second-addr', '0x40f00000',
                        '--tags-addr', '0x44000000', '--lk-android8',
                        '--output', str(boot)], check=True,
                       stdout=subprocess.DEVNULL)
        raw = regular(boot)
        require(len(raw) < PARTITION_BYTES, 'boot image too large')
        (stage / 'boot2-padded.img').write_bytes(raw + bytes(PARTITION_BYTES - len(raw)))
        subprocess.run([sys.executable, str(BOOT / 'analyze-lk-boot-image.py'),
                        '--validate-lk', '--expected-image-gz', str(stage / 'Image.gz'),
                        '--expected-ramdisk', str(stage / 'initramfs.img'),
                        '--expected-dtb', str(stage / 'board.dtb'),
                        '--expected-name', 'gemini-obs-L',
                        '--expected-cmdline', 'bootopt=64S3,32N2,64N2',
                        str(boot)], check=True, stdout=subprocess.DEVNULL)
        result = {
            'status': 'offline-emi-boot-observer-composition-validated',
            'kernel_build_commit': BUILD_COMMIT,
            'kernel_release': RELEASE,
            'kernel_package_sha256': PACKAGE_ID,
            'parent_boot2_sha256': PARENT_BOOT2_SHA,
            'files': {p.name: {'sha256': sha(regular(p)), 'bytes': p.stat().st_size}
                      for p in sorted(stage.iterdir())},
            'device_tree_change': 'none; exact boot-tested board DTB reused',
            'secret_bearing': True,
            'device_action': 'none',
            'physical_admission': False,
        }
        (stage / 'candidate.json').write_text(json.dumps(result, indent=2) + '\n')
        stage.rename(output)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
