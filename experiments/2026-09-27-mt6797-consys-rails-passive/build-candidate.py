#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compose the private passive VCN-handle image from the proven CONSYS boot."""

import argparse
import difflib
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
OWNER = REPO / 'experiments/2026-09-27-mt6797-consys-owner'
BOOT = REPO / 'experiments/2026-07-12-boot-contract-recovery/scripts'
BUILD_COMMIT = '77098ff7ee82670fab9db21cfc0eb7209def5c73'
PACKAGE_ID = '8b92ed6b4e7e133a2f2dc45ff483b24ef6e275f780127ac510df013c8b243b77'
PARENT_MANIFEST_SHA = '0823ac4e088840267edffe9dbd8ce293ad1f6f8bdfb0ebd13c533f77fe8efed3'
RELEASE = '7.1.3-gemini-a53-consys-owner-passive'
PARTITION_BYTES = 16777216
SUPPLIES = (('vcn18', 'ldo-vcn18', '2f'),
            ('vcn28', 'ldo-vcn28', '30'),
            ('vcn33-wifi', 'ldo-vcn33-wifi', '31'))


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def regular(path):
    require(path.is_file() and not path.is_symlink(), 'unsafe file: ' + str(path))
    return path.read_bytes()


def command(*args):
    return subprocess.check_output(args, stderr=subprocess.DEVNULL)


def fdtget(board, node, prop, kind='x'):
    return command('fdtget', '-t', kind, str(board), node, prop).strip()


def overlay_board(parent, built, board):
    board.write_bytes(regular(parent))
    root = '/pwrap@1000d000/pmic/regulators'
    owner = '/consys@10001340'
    original = command('dtc', '-I', 'dtb', '-O', 'dts', str(board)).splitlines(keepends=True)
    require(fdtget(board, root, 'compatible', 's') == b'mediatek,mt6351-regulator' and
            fdtget(board, owner, 'compatible', 's') == b'mediatek,mt6797-consys',
            'parent DT identity changed')
    phandles = {line.split(b'<0x')[1].split(b'>')[0].decode()
                for line in original if b'phandle = <0x' in line}
    require(not phandles.intersection({entry[2] for entry in SUPPLIES}),
            'new phandle collides with parent')
    for name, child, phandle in SUPPLIES:
        path = root + '/' + child
        require(child not in command('fdtget', '-l', str(board), root).decode().split(),
                'parent already contains ' + child)
        subprocess.run(['fdtput', '-c', str(board), path], check=True)
        subprocess.run(['fdtput', '-t', 's', str(board), path, 'regulator-name', name], check=True)
        subprocess.run(['fdtput', '-t', 'x', str(board), path, 'phandle', phandle], check=True)
        subprocess.run(['fdtput', '-t', 'x', str(board), owner, name + '-supply', phandle],
                       check=True)
        require(fdtget(board, path, 'regulator-name', 's') == name.encode() and
                fdtget(board, path, 'phandle') == phandle.encode() and
                fdtget(board, owner, name + '-supply') == phandle.encode(),
                'overlay supply linkage failed: ' + name)
        built_phandle = fdtget(built, owner, name + '-supply')
        require(fdtget(built, root + '/' + child, 'phandle') == built_phandle and
                fdtget(built, root + '/' + child, 'regulator-name', 's') == name.encode(),
                'built DT supply linkage changed: ' + name)
    changed = command('dtc', '-I', 'dtb', '-O', 'dts', str(board)).splitlines(keepends=True)
    edits = list(difflib.SequenceMatcher(a=original, b=changed, autojunk=False).get_opcodes())
    require(all(tag in ('equal', 'insert') for tag, *_ in edits),
            'overlay changed existing DT content')
    additions = b''.join(b''.join(changed[start:end]) for tag, _, _, start, end in edits
                         if tag == 'insert')
    for name, child, phandle in SUPPLIES:
        require(additions.count((name + '-supply = <0x' + phandle + '>;').encode()) == 1 and
                additions.count((child + ' {').encode()) == 1 and
                additions.count(('regulator-name = "' + name + '";').encode()) == 1 and
                additions.count(('phandle = <0x' + phandle + '>;').encode()) == 1,
                'overlay addition inventory changed: ' + name)
    require(additions.count(b'-supply = ') == 3 and
            additions.count(b'regulator-name = ') == 3 and
            additions.count(b'phandle = ') == 3,
            'unexpected overlay additions')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('kernel-package', 'parent', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    previous = OWNER / 'results/passive-candidate.json'
    require(digest(regular(previous)) == PARENT_MANIFEST_SHA,
            'published parent candidate changed')
    accepted = json.loads(regular(previous))
    parent = args.parent.resolve(strict=True)
    require(parent.is_dir() and not args.parent.is_symlink() and
            {path.name for path in parent.iterdir()} == set(accepted['files']) | {'candidate.json'} and
            json.loads(regular(parent / 'candidate.json')) == accepted,
            'private parent candidate changed')
    for name, identity in accepted['files'].items():
        data = regular(parent / name)
        require(len(data) == identity['bytes'] and digest(data) == identity['sha256'],
                'parent file changed: ' + name)
    require(accepted['kernel_release'] == RELEASE and accepted['physical_admission'] is False,
            'parent scope changed')

    package = args.kernel_package.resolve(strict=True)
    require(package.is_dir() and not args.kernel_package.is_symlink() and
            package.name == 'linux-7.1.3-gemini-' + PACKAGE_ID,
            'wrong kernel package')
    audit = runpy.run_path(str(REPO / 'experiments/2026-09-05-owner-away-experiment-preparation/baseline/audit_foundation.py'))
    sums = regular(package / 'SHA256SUMS')
    audit['inventory'](package, {'manifest_sha256': PACKAGE_ID,
                                 'inventory_count': len(sums.splitlines())})
    build = json.loads(regular(package / 'provenance/build.json'))
    require(build['repository_commit'] == BUILD_COMMIT and build['repository_dirty'] is False and
            build['kernel_release'] == RELEASE and
            build['build_profile'] == 'mt6797-a53-consys-rails-passive',
            'kernel build identity changed')
    image = regular(package / 'Image.gz')
    require(gzip.decompress(image) == regular(package / 'Image'), 'kernel compression mismatch')
    config = regular(package / 'kernel.config')
    require(b'CONFIG_MTK_MT6797_CONSYS=y\n' in config and
            b'CONFIG_REGULATOR=y\n' in config and
            b'# CONFIG_MTK_SCPSYS is not set\n' in config,
            'owner config mismatch')
    require(b' mt6797_consys_probe\n' in regular(package / 'System.map'),
            'owner probe missing')
    built = package / 'dtbs/mediatek/mt6797-gemini-pda.dtb'
    regular(built)

    output = Path(os.path.abspath(args.output))
    require(output.parent.is_dir() and not output.exists() and not output.is_symlink(),
            'output path occupied')
    require(shutil.disk_usage(output.parent).free >= 256 * 1024 * 1024,
            'insufficient free space')
    with tempfile.TemporaryDirectory(prefix='.consys-rails-stage-', dir=output.parent) as tmp:
        stage = Path(tmp)
        board = stage / 'board.dtb'
        overlay_board(parent / 'board.dtb', built, board)
        for name, data in (('Image.gz', image), ('kernel.config', config),
                           ('initramfs.img', regular(parent / 'initramfs.img'))):
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
            'status': 'offline-passive-consys-rails-composition-validated',
            'kernel_build_commit': BUILD_COMMIT, 'kernel_release': RELEASE,
            'kernel_package_sha256': PACKAGE_ID,
            'parent_boot_sha256': accepted['files']['boot.img']['sha256'],
            'files': {path.name: {'sha256': digest(regular(path)), 'bytes': path.stat().st_size}
                      for path in sorted(stage.iterdir())},
            'device_tree_change': 'three MT6351 VCN children and owner phandles only',
            'secret_bearing': True, 'device_action': 'none', 'physical_admission': False,
        }
        (stage / 'candidate.json').write_text(json.dumps(result, indent=2) + '\n')
        stage.rename(output)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
