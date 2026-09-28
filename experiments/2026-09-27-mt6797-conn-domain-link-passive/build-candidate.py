#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compose a passive CONN-owner link onto the boot-tested A53 candidate."""

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
PREV = REPO / 'experiments/2026-09-27-mt6797-conn-provider-passive'
PARENT_RECEIPT = PREV / 'results/candidate.json'
BOOT = REPO / 'experiments/2026-07-12-boot-contract-recovery/scripts'
BUILD_COMMIT = 'ad6751b2e4e31495c3af6d0d024a0603e48bb841'
PACKAGE_ID = '3fad062b895e86579a4df6e1867aeb32f7d5a5a96bc66be8532354e2b21ff406'
PROFILE = 'mt6797-a53-conn-domain-link-passive'
RELEASE = '7.1.3-gemini-a53-consys-owner-passive'
MODERN = '/power-controller@10006000/power-controller'
OWNER = '/consys@10001340'
PARTITION_BYTES = 16777216


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def regular(path):
    require(path.is_file() and not path.is_symlink(), 'missing or linked input: ' + str(path))
    return path.read_bytes()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def run(*argv):
    return subprocess.run(argv, check=True, capture_output=True).stdout


def nodes(path):
    return runpy.run_path(str(PREV / 'build-candidate.py'))['nodes'](path)


def prop(path, node, name):
    return run('fdtget', '-t', 'x', str(path), node, name).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('kernel-package', 'parent', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    accepted = json.loads(regular(PARENT_RECEIPT))
    parent = args.parent.resolve(strict=True)
    require(parent.is_dir() and not args.parent.is_symlink() and
            {p.name for p in parent.iterdir()} == set(accepted['files']) | {'candidate.json'} and
            json.loads(regular(parent / 'candidate.json')) == accepted,
            'wrong parent candidate')
    for name, ident in accepted['files'].items():
        data = regular(parent / name)
        require(len(data) == ident['bytes'] and sha(data) == ident['sha256'],
                'parent candidate changed: ' + name)
    require(accepted['files']['boot2-padded.img']['sha256'] ==
            '99888ffbed5e3494377dbb7442e08ef20c2a7f6190922311ff8dc84bb05c4750',
            'wrong boot-tested predecessor')
    package = args.kernel_package.resolve(strict=True)
    require(package.is_dir() and not args.kernel_package.is_symlink() and
            package.name == 'linux-7.1.3-gemini-' + PACKAGE_ID,
            'wrong kernel package')
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
    require(gzip.decompress(image) == regular(package / 'Image') and
            sha(image) != accepted['files']['Image.gz']['sha256'],
            'kernel image unchanged or damaged')
    config = regular(package / 'kernel.config')
    require(sha(config) == accepted['files']['kernel.config']['sha256'] and
            b'# CONFIG_MTK_SCPSYS is not set\n' in config and
            b'CONFIG_MTK_SCPSYS_PM_DOMAINS=y\n' in config and
            b'CONFIG_MTK_MT6797_CONSYS=y\n' in config,
            'power/owner config changed')
    built = package / 'dtbs/mediatek/mt6797-gemini-pda.dtb'
    regular(built)
    require(prop(built, OWNER, 'mediatek,conn-power-domain') == b'40 c' and
            prop(built, MODERN, 'phandle') == b'40' and
            prop(built, MODERN + '/power-domain@c', 'reg') == b'c',
            'built domain link changed')
    output = Path(os.path.abspath(args.output))
    require(output.parent.is_dir() and not output.exists() and not output.is_symlink(),
            'output path occupied')
    require(shutil.disk_usage(output.parent).free >= 256 * 1024 * 1024,
            'insufficient free space')
    with tempfile.TemporaryDirectory(prefix='.conn-link-stage-', dir=output.parent) as tmp:
        stage = Path(tmp)
        board = stage / 'board.dtb'
        board.write_bytes(regular(parent / 'board.dtb'))
        old = nodes(board)
        require(MODERN in old and OWNER in old and 'phandle' not in old[MODERN] and
                'mediatek,conn-power-domain' not in old[OWNER] and
                all('0x40' not in props.get('phandle', '') for props in old.values()),
                'parent DT not the unlinked provider')
        run('fdtput', '-t', 'x', str(board), MODERN, 'phandle', '40')
        run('fdtput', '-t', 'x', str(board), OWNER, 'mediatek,conn-power-domain', '40', 'c')
        changed = nodes(board)
        require(set(changed) == set(old) and
                changed[MODERN] == old[MODERN] | {'phandle': '<0x40>'} and
                changed[OWNER] == old[OWNER] |
                {'mediatek,conn-power-domain': '<0x40 0x0c>'} and
                all(changed[k] == v for k, v in old.items() if k not in {MODERN, OWNER}),
                'unrelated DT change')
        require(prop(board, OWNER, 'mediatek,conn-power-domain') == b'40 c' and
                prop(board, MODERN, 'phandle') == b'40', 'DT readback changed')
        (stage / 'Image.gz').write_bytes(image)
        (stage / 'kernel.config').write_bytes(config)
        (stage / 'initramfs.img').write_bytes(regular(parent / 'initramfs.img'))
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
        result = {'status': 'offline-passive-conn-domain-link-composition-validated',
                  'kernel_build_commit': BUILD_COMMIT, 'kernel_release': RELEASE,
                  'kernel_package_sha256': PACKAGE_ID,
                  'parent_boot2_sha256': accepted['files']['boot2-padded.img']['sha256'],
                  'files': {p.name: {'sha256': sha(regular(p)), 'bytes': p.stat().st_size}
                            for p in sorted(stage.iterdir())},
                  'device_tree_change': 'one modern provider phandle and one CONN owner link',
                  'secret_bearing': True, 'device_action': 'none', 'physical_admission': False}
        (stage / 'candidate.json').write_text(json.dumps(result, indent=2) + '\n')
        stage.rename(output)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
