#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compose one passive CONN-provider DT onto the boot-tested A53 image."""

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
PARENT_RECEIPT = REPO / 'experiments/2026-09-27-mt6797-consys-reset-passive/results/candidate.json'
BUILD_COMMIT = '25eb161f34a61a7b15daf26f10d776e6d88b401e'
PACKAGE_ID = 'af8601b099f7d40b9d05a58bf77388e613aaf098e87891bda971dfd28e07c91f'
PROFILE = 'mt6797-a53-conn-provider-passive'
RELEASE = '7.1.3-gemini-a53-consys-owner-passive'
SPM = '/power-controller@10006000'
MODERN = SPM + '/power-controller'
CONN = MODERN + '/power-domain@c'
PARTITION_BYTES = 16777216


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def regular(path):
    require(path.is_file() and not path.is_symlink(), 'missing or linked input: ' + str(path))
    return path.read_bytes()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def run(*argv):
    return subprocess.run(argv, check=True, capture_output=True).stdout


def prop(path, node, name, kind='x'):
    return run('fdtget', '-t', kind, str(path), node, name).strip()


def nodes(path):
    """Compare all preexisting DT properties irrespective of fdtput ordering."""
    tree = {}
    stack = []
    for raw in run('dtc', '-q', '-I', 'dtb', '-O', 'dts', str(path)).decode('ascii').splitlines():
        line = raw.strip()
        if line.endswith('{'):
            stack.append(line[:-1].strip())
            tree['/' + '/'.join(stack[1:])] = {}
        elif line == '};':
            stack.pop()
        elif stack and line.endswith(';'):
            name, sep, value = line[:-1].partition(' = ')
            tree['/' + '/'.join(stack[1:])][name] = value if sep else None
    return tree


def overlay(parent, built, output):
    output.write_bytes(regular(parent))
    old = nodes(output)
    require(MODERN not in old and CONN not in old, 'parent already has modern provider')
    require(prop(output, SPM, 'compatible', 's') == b'mediatek,mt6797-scpsys' and
            prop(output, SPM, '#power-domain-cells') == b'1',
            'parent SPM topology changed')
    infra = prop(output, SPM, 'infracfg')
    require(infra == prop(output, '/syscon@10001000', 'phandle'),
            'parent infracfg phandle changed')
    require(prop(built, SPM, 'compatible', 's') ==
            b'mediatek,mt6797-scpsys syscon simple-mfd' and
            prop(built, MODERN, 'compatible', 's') ==
            b'mediatek,mt6797-power-controller' and
            prop(built, CONN, 'reg') == b'c' and
            prop(built, MODERN, 'access-controllers') ==
            prop(built, '/syscon@10001000', 'phandle'),
            'built provider topology changed')
    run('fdtput', '-t', 's', str(output), SPM, 'compatible',
        'mediatek,mt6797-scpsys', 'syscon', 'simple-mfd')
    for name, value in (('#address-cells', '1'), ('#size-cells', '0')):
        run('fdtput', '-t', 'x', str(output), SPM, name, value)
    run('fdtput', '-c', str(output), MODERN)
    run('fdtput', '-t', 's', str(output), MODERN, 'compatible',
        'mediatek,mt6797-power-controller')
    for name, value in (('#address-cells', '1'), ('#size-cells', '0'),
                        ('#power-domain-cells', '1'), ('access-controllers', infra.decode('ascii'))):
        run('fdtput', '-t', 'x', str(output), MODERN, name, value)
    run('fdtput', '-c', str(output), CONN)
    run('fdtput', '-t', 'x', str(output), CONN, 'reg', 'c')
    run('fdtput', '-t', 'x', str(output), CONN, '#power-domain-cells', '0')
    changed = nodes(output)
    require(set(changed) == set(old) | {MODERN, CONN}, 'unexpected DT nodes')
    require('phandle' not in changed[MODERN] and 'phandle' not in changed[CONN],
            'unexpected modern-domain consumer reference')
    for node, properties in old.items():
        if node == SPM:
            require({k: v for k, v in changed[node].items()
                     if k not in {'compatible', '#address-cells', '#size-cells'}} ==
                    {k: v for k, v in properties.items() if k != 'compatible'},
                    'SPM existing properties changed')
        else:
            require(changed[node] == properties, 'unrelated DT property changed: ' + node)
    require(prop(output, SPM, 'compatible', 's') ==
            prop(built, SPM, 'compatible', 's') and
            all(prop(output, SPM, name) == prop(built, SPM, name)
                for name in ('#address-cells', '#size-cells')) and
            prop(output, MODERN, 'compatible', 's') ==
            prop(built, MODERN, 'compatible', 's') and
            all(prop(output, MODERN, name) == prop(built, MODERN, name)
                for name in ('#address-cells', '#size-cells', '#power-domain-cells')) and
            prop(output, MODERN, 'access-controllers') == infra and
            prop(output, CONN, 'reg') == prop(built, CONN, 'reg') and
            prop(output, CONN, '#power-domain-cells') == b'0',
            'provider overlay readback changed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('kernel-package', 'parent', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    accepted = json.loads(regular(PARENT_RECEIPT))
    parent = args.parent.resolve(strict=True)
    require(parent.is_dir() and not args.parent.is_symlink() and
            {p.name for p in parent.iterdir()} == set(accepted['files']) | {'candidate.json'} and
            json.loads(regular(parent / 'candidate.json')) == accepted,
            'private parent candidate changed')
    for name, identity in accepted['files'].items():
        data = regular(parent / name)
        require(len(data) == identity['bytes'] and sha(data) == identity['sha256'],
                'parent candidate file changed: ' + name)
    require(accepted['files']['boot2-padded.img']['sha256'] ==
            '9483e4bc1bb1882052a0158a024ddf20bff9018440aaa03b4a9bd3ad3abfc2de',
            'wrong boot-tested parent')
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
            sha(image) == accepted['files']['Image.gz']['sha256'],
            'kernel image differs from boot-tested parent')
    config = regular(package / 'kernel.config')
    require(sha(config) == accepted['files']['kernel.config']['sha256'] and
            b'# CONFIG_MTK_SCPSYS is not set\n' in config and
            b'CONFIG_MTK_SCPSYS_PM_DOMAINS=y\n' in config,
            'power provider config changed')
    built = package / 'dtbs/mediatek/mt6797-gemini-pda.dtb'
    regular(built)
    output = Path(os.path.abspath(args.output))
    require(output.parent.is_dir() and not output.exists() and not output.is_symlink(),
            'output path occupied')
    require(shutil.disk_usage(output.parent).free >= 256 * 1024 * 1024,
            'insufficient free space')
    with tempfile.TemporaryDirectory(prefix='.conn-provider-stage-', dir=output.parent) as tmp:
        stage = Path(tmp)
        board = stage / 'board.dtb'
        overlay(parent / 'board.dtb', built, board)
        for name in ('Image.gz', 'kernel.config', 'initramfs.img'):
            (stage / name).write_bytes(regular(parent / name))
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
        result = {'status': 'offline-passive-conn-provider-composition-validated',
                  'kernel_build_commit': BUILD_COMMIT, 'kernel_release': RELEASE,
                  'kernel_package_sha256': PACKAGE_ID,
                  'parent_boot_sha256': accepted['files']['boot.img']['sha256'],
                  'files': {p.name: {'sha256': sha(regular(p)), 'bytes': p.stat().st_size}
                            for p in sorted(stage.iterdir())},
                  'device_tree_change': 'same SPM syscon modern CONN child; no consumer',
                  'secret_bearing': True, 'device_action': 'none', 'physical_admission': False}
        (stage / 'candidate.json').write_text(json.dumps(result, indent=2) + '\n')
        stage.rename(output)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
