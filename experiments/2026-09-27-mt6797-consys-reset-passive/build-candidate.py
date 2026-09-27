#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compose a passive reset-handle image from the boot-tested CONSYS rails image."""

import argparse
import difflib
import gzip
import json
import os
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import sys
import tempfile


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
RAILS = REPO / 'experiments/2026-09-27-mt6797-consys-rails-passive'
BOOT = REPO / 'experiments/2026-07-12-boot-contract-recovery/scripts'
HELPERS = runpy.run_path(str(RAILS / 'build-candidate.py'))
require = HELPERS['require']
digest = HELPERS['digest']
regular = HELPERS['regular']
command = HELPERS['command']
fdtget = HELPERS['fdtget']
BUILD_COMMIT = '766ada26f0ef52d46e5ce2daa8ea7132f7827a36'
PACKAGE_ID = '9de5901f25a0ec584e70d36297dccb89399a571632af079b81737a604ec09724'
PARENT_MANIFEST_SHA = '655d4f26b90fea910ca4b9c46dd94e14b897ced96f40caa1d9caef650d9dee1e'
RELEASE = '7.1.3-gemini-a53-consys-owner-passive'
PARTITION_BYTES = 16777216
OWNER = '/consys@10001340'
WATCHDOG = '/watchdog@10007000'
RESET_PHANDLE = '32'


def absent(board, node, prop):
    result = subprocess.run(['fdtget', str(board), node, prop], capture_output=True)
    require(result.returncode != 0, 'parent already has ' + prop)


def overlay_board(parent, built, board):
    board.write_bytes(regular(parent))
    require(fdtget(board, OWNER, 'compatible', 's') == b'mediatek,mt6797-consys' and
            fdtget(board, WATCHDOG, 'compatible', 's') ==
            b'mediatek,mt6797-wdt mediatek,mt6589-wdt' and
            fdtget(board, WATCHDOG, 'reg') == b'0 10007000 0 100',
            'parent owner or TOPRGU identity changed')
    original = command('dtc', '-q', '-I', 'dtb', '-O', 'dts', str(board)).splitlines(keepends=True)
    phandles = {int(value, 16) for value in
                re.findall(rb'phandle = <0x([0-9a-f]+)>;', b''.join(original))}
    require(phandles and max(phandles) == 0x31 and 0x32 not in phandles,
            'parent phandle allocation changed')
    for node, prop in ((WATCHDOG, '#reset-cells'), (WATCHDOG, 'phandle'),
                       (OWNER, 'resets'), (OWNER, 'reset-names')):
        absent(board, node, prop)
    require(fdtget(built, OWNER, 'reset-names', 's') == b'con-mcu' and
            fdtget(built, OWNER, 'resets').split()[1] == b'c' and
            fdtget(built, WATCHDOG, '#reset-cells') == b'1' and
            fdtget(built, WATCHDOG, 'phandle') ==
            fdtget(built, OWNER, 'resets').split()[0],
            'built reset linkage changed')
    subprocess.run(['fdtput', '-t', 'x', str(board), WATCHDOG,
                    '#reset-cells', '1'], check=True)
    subprocess.run(['fdtput', '-t', 'x', str(board), WATCHDOG,
                    'phandle', RESET_PHANDLE], check=True)
    subprocess.run(['fdtput', '-t', 'x', str(board), OWNER,
                    'resets', RESET_PHANDLE, 'c'], check=True)
    subprocess.run(['fdtput', '-t', 's', str(board), OWNER,
                    'reset-names', 'con-mcu'], check=True)
    require(fdtget(board, WATCHDOG, '#reset-cells') == b'1' and
            fdtget(board, WATCHDOG, 'phandle') == RESET_PHANDLE.encode() and
            fdtget(board, OWNER, 'resets') == b'32 c' and
            fdtget(board, OWNER, 'reset-names', 's') == b'con-mcu',
            'reset overlay readback failed')
    changed = command('dtc', '-q', '-I', 'dtb', '-O', 'dts', str(board)).splitlines(keepends=True)
    edits = list(difflib.SequenceMatcher(a=original, b=changed,
                                         autojunk=False).get_opcodes())
    require(all(tag in ('equal', 'insert') for tag, *_ in edits),
            'overlay changed existing DT content')
    additions = b''.join(b''.join(changed[start:end]) for tag, _, _, start, end in edits
                         if tag == 'insert')
    require(len(additions.splitlines()) == 4 and
            all(additions.count(line) == 1 for line in (
                b'#reset-cells = <0x01>;', b'phandle = <0x32>;',
                b'resets = <0x32 0x0c>;', b'reset-names = "con-mcu";')),
            'unexpected DT additions')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('kernel-package', 'parent', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    published = RAILS / 'results/candidate.json'
    require(digest(regular(published)) == PARENT_MANIFEST_SHA,
            'published parent candidate changed')
    accepted = json.loads(regular(published))
    parent = args.parent.resolve(strict=True)
    require(parent.is_dir() and not args.parent.is_symlink() and
            {path.name for path in parent.iterdir()} == set(accepted['files']) | {'candidate.json'} and
            json.loads(regular(parent / 'candidate.json')) == accepted,
            'private parent candidate changed')
    for name, identity in accepted['files'].items():
        data = regular(parent / name)
        require(len(data) == identity['bytes'] and digest(data) == identity['sha256'],
                'parent file changed: ' + name)
    require(accepted['files']['boot2-padded.img']['sha256'] ==
            'da9a7cc465d6c7b3bf9d638dd6c2c364329f8617a2d5894cf4434f85b255dbfe',
            'wrong boot-tested parent')

    package = args.kernel_package.resolve(strict=True)
    require(package.is_dir() and not args.kernel_package.is_symlink() and
            package.name == 'linux-7.1.3-gemini-' + PACKAGE_ID,
            'wrong kernel package')
    audit = runpy.run_path(str(REPO / 'experiments/2026-09-05-owner-away-experiment-preparation/baseline/audit_foundation.py'))
    sums = regular(package / 'SHA256SUMS')
    audit['inventory'](package, {'manifest_sha256': PACKAGE_ID,
                                 'inventory_count': len(sums.splitlines())})
    build = json.loads(regular(package / 'provenance/build.json'))
    require(build['repository_commit'] == BUILD_COMMIT and not build['repository_dirty'] and
            build['kernel_release'] == RELEASE and
            build['build_profile'] == 'mt6797-a53-consys-reset-passive',
            'kernel build identity changed')
    image = regular(package / 'Image.gz')
    require(gzip.decompress(image) == regular(package / 'Image'),
            'kernel compression mismatch')
    config = regular(package / 'kernel.config')
    require(digest(config) == accepted['files']['kernel.config']['sha256'] and
            b'CONFIG_RESET_CONTROLLER=y\n' in config and
            b'CONFIG_MEDIATEK_WATCHDOG=y\n' in config and
            b'CONFIG_MTK_MT6797_CONSYS=y\n' in config,
            'owner/reset config mismatch')
    require(b' mt6797_consys_probe\n' in regular(package / 'System.map') and
            b' mtk_wdt_probe\n' in regular(package / 'System.map'),
            'owner or reset-provider probe missing')
    built = package / 'dtbs/mediatek/mt6797-gemini-pda.dtb'
    regular(built)

    output = Path(os.path.abspath(args.output))
    require(output.parent.is_dir() and not output.exists() and not output.is_symlink(),
            'output path occupied')
    require(shutil.disk_usage(output.parent).free >= 256 * 1024 * 1024,
            'insufficient free space')
    with tempfile.TemporaryDirectory(prefix='.consys-reset-stage-', dir=output.parent) as tmp:
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
            'status': 'offline-passive-consys-reset-composition-validated',
            'kernel_build_commit': BUILD_COMMIT, 'kernel_release': RELEASE,
            'kernel_package_sha256': PACKAGE_ID,
            'parent_boot_sha256': accepted['files']['boot.img']['sha256'],
            'files': {path.name: {'sha256': digest(regular(path)), 'bytes': path.stat().st_size}
                      for path in sorted(stage.iterdir())},
            'device_tree_change': 'watchdog #reset-cells and phandle, owner resets and reset-names only',
            'secret_bearing': True, 'device_action': 'none', 'physical_admission': False,
        }
        (stage / 'candidate.json').write_text(json.dumps(result, indent=2) + '\n')
        stage.rename(output)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
