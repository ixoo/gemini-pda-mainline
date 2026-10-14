#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compose CCMP4 failure-only staged type hint on the same verified private C32.

Reuses the frozen ND2 compositor's parent/inventory/config/DT/RAM/container gates.
Only the release gate changes in C32's64-member RAM. Pins below come from the REAL
validated package, never a placeholder receipt. No device action.
"""

import argparse
import gzip
import json
import os
import runpy
import shutil
import subprocess
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PHASE_B = REPO / 'experiments/2026-10-07-mt6797-wifi-phase-b-join'
BASE = runpy.run_path(str(PHASE_B.parent / '2026-09-28-mt6797-emi-set-probe/build-candidate.py'))
require, regular, sha, nodes = (BASE[name] for name in ('require', 'regular', 'sha', 'nodes'))
BOOT = REPO / 'experiments/2026-07-12-boot-contract-recovery/scripts'

PARENT_RECEIPT = PHASE_B / 'results/candidate-32.json'
PARENT_RECEIPT_SHA = 'e487260cda36a706433d5eb5790032413df2db997ef3d4abb4f0f09b54424320'
PARENT_BOOT2_SHA256 = '5260715b453d4ad9e635845132f7d08530e0386ce6bce98f53a818b3ab87b815'
PARENT_RELEASE = b'7.1.3-gemini-a53-wifi-phase-b-compile'

COMMIT = '92be8e69a39aa899701026294776c9ea79c9806a'
PACKAGE = '949d7d049ebb90c4b8fb01584a183129dc7f79ab954da0d64f904bc3b6c01cf1'
IMAGE_SHA256 = 'ae1d4f15bc1505952e70443071ce1b8d7af41f817820a7505e9f41a277b3eb09'
CONFIG_SHA256 = '483e0165368ce521f7f6e082e5acbc612c26badab7cacdc1e1cd60166f15c350'
PATCHSET_SHA256 = '3d7dbc3821b2430441475efdc45627b24eb1a6c68dbd92a3d27f723b3b1a3fc2'
PROFILE = 'mt6797-a53-wifi-ccmp-refused-type'
RELEASE = '7.1.3-gemini-a53-wifi-ccmp-stable-monitor'
SOURCE_COMMIT = 'b5969e62f02486f70fec2f202e21ec3e724286d9'
PATCH_SHA256 = '96443818f38fb74e5f09362d7216c9b42f09a349beb23cd06cb3e442fe968701'
SERIES_SHA256 = '1516a2dcefdf29e6f60bc7b55971320eed74fcfa2bba646fc581a5fe2c0576c6'
PARTITION_BYTES = 16777216
BOOT_NAME = 'gemini-obs-P'
BOOT_CMDLINE = 'bootopt=64S3,32N2,64N2'


def expected_ccmp_config(parent_config):
    """C32 config plus mode/identity/release and the two diagnostic symbols only."""
    require(parent_config.count(
        b'g_ether.iProduct=Gemini-L-Observability g_ether.iSerialNumber='
        b'GEMINI_OBSERVABILITY_20260717_L clk_ignore_unused fbcon=rotate:3 '
        b'consoleblank=0 fbcon=font:TER16x32"') == 1 and
        parent_config.count(b'CONFIG_LOCALVERSION="-gemini-a53-wifi-phase-b-compile"') == 1 and
        parent_config.count(b'CONFIG_MT6797_STATION_JOIN=y\n') == 1 and
        b'CONFIG_MT6797_NATIVE_DELIVERY_DIAG' not in parent_config and
        b'CONFIG_MT6797_CCMP_STABLE_EPOCH' not in parent_config,
        'parent native-config anchors changed')
    return parent_config.replace(
        b'g_ether.iProduct=Gemini-L-Observability g_ether.iSerialNumber='
        b'GEMINI_OBSERVABILITY_20260717_L clk_ignore_unused fbcon=rotate:3 '
        b'consoleblank=0 fbcon=font:TER16x32"',
        b'g_ether.iProduct=Gemini-CCMP-Stable-Monitor g_ether.iSerialNumber='
        b'GEMINI_CCMP_STABLE_MONITOR_20261014 clk_ignore_unused fbcon=rotate:3 '
        b'consoleblank=0 fbcon=font:TER16x32 mac.native_delivery_diag=0 '
        b'mac.ccmp_stable_epoch=1"').replace(
        b'CONFIG_LOCALVERSION="-gemini-a53-wifi-phase-b-compile"',
        b'CONFIG_LOCALVERSION="-gemini-a53-wifi-ccmp-stable-monitor"').replace(
        b'CONFIG_MT6797_STATION_JOIN=y\n',
        b'CONFIG_MT6797_STATION_JOIN=y\nCONFIG_MT6797_NATIVE_DELIVERY_DIAG=y\n'
        b'CONFIG_MT6797_CCMP_STABLE_EPOCH=y\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('kernel-package', 'parent', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)

    published = regular(PARENT_RECEIPT)
    require(sha(published) == PARENT_RECEIPT_SHA, 'candidate 32 receipt changed')
    accepted = json.loads(published)
    require(accepted['kernel_release'] == PARENT_RELEASE.decode() and
            accepted['files']['boot2-padded.img']['sha256'] == PARENT_BOOT2_SHA256,
            'candidate 32 receipt is not the expected parent')
    parent = args.parent.resolve(strict=True)
    require(parent.is_dir() and not args.parent.is_symlink() and
            {p.name for p in parent.iterdir()} == set(accepted['files']) | {'candidate.json'} and
            json.loads(regular(parent / 'candidate.json')) == accepted,
            'parent candidate changed')
    for name, identity in accepted['files'].items():
        data = regular(parent / name)
        require(len(data) == identity['bytes'] and sha(data) == identity['sha256'],
                'parent member changed: ' + name)

    package = args.kernel_package.resolve(strict=True)
    require(package.is_dir() and not args.kernel_package.is_symlink() and
            package.name == 'linux-7.1.3-gemini-' + PACKAGE, 'not the pinned CCMP package')
    audit = runpy.run_path(str(REPO /
        'experiments/2026-09-05-owner-away-experiment-preparation/baseline/audit_foundation.py'))
    audit['inventory'](package, {'manifest_sha256': PACKAGE,
                                 'inventory_count': len(regular(package / 'SHA256SUMS').splitlines())})
    build = json.loads(regular(package / 'provenance/build.json'))
    require(build['repository_commit'] == COMMIT and not build['repository_dirty'] and
            build['build_profile'] == PROFILE and build['kernel_release'] == RELEASE and
            build['modules_built'] is False and build['base_config'] == 'defconfig' and
            build['build_architecture'] == 'x86_64' and build['target_architecture'] == 'arm64' and
            build['toolchain_mode'] == 'cross' and build['patchset_sha256'] == PATCHSET_SHA256 and
            build['config_sha256'] == CONFIG_SHA256,
            'build provenance changed')
    series = regular(REPO / 'patches/series-a53-wifi-ccmp-refused-type')
    require(sha(series) == SERIES_SHA256 and len(series.splitlines()) == 689 and
            sha(regular(REPO / 'patches/proposals/'
                        '0194-wifi-mt6797-retain-failure-only-staged-type-word.patch')) ==
            PATCH_SHA256, 'approved source selection changed')
    image = regular(package / 'Image.gz')
    config = regular(package / 'kernel.config')
    require(sha(image) == IMAGE_SHA256 and sha(config) == CONFIG_SHA256 and
            gzip.decompress(image) == regular(package / 'Image'),
            'kernel image changed')
    parent_config = regular(parent / 'kernel.config')
    require(config == expected_ccmp_config(parent_config),
            'kernel configuration is not C32 plus the reviewed mode changes')
    command = [line for line in config.splitlines() if line.startswith(b'CONFIG_CMDLINE=')]
    require(len(command) == 1 and b' clk_ignore_unused ' in command[0] and
            b' mac.native_delivery_diag=0 mac.ccmp_stable_epoch=1"' in command[0] and
            b'regulator_ignore_unused' not in command[0] and
            nodes(parent / 'board.dtb')['/psci']['method'] == '"smc"',
            'parent clock or PSCI contract changed')

    # RAM root: reuse candidate 32's 64 members byte-identical; change only the one
    # release-gate string the init checks (phase-b -> native-delivery).
    parse = runpy.run_path(str(REPO /
        'experiments/2026-07-25-emmc-development/scripts/validate-emmc-initramfs.py'))['parse_newc']
    encode = runpy.run_path(str(REPO /
        'experiments/2026-08-14-mt6797-runtime-provenance-observer/scripts/build-diagnostic-initramfs.py'))['encode_newc']
    parent_ram = regular(parent / 'initramfs.img')
    old = parse(parent_ram)
    require(encode(old) == parent_ram and old['init'].data.count(PARENT_RELEASE) == 1 and
            RELEASE.encode() not in old['init'].data, 'parent RAM root contract changed')
    new = dict(old)
    new['init'] = replace(old['init'], data=old['init'].data.replace(PARENT_RELEASE, RELEASE.encode()))
    require(len(new) == len(old), 'RAM root inventory changed')
    initramfs = encode(new)
    require(parse(initramfs) == new, 'RAM root re-encoding changed')
    board = regular(parent / 'board.dtb')

    output = Path(os.path.abspath(args.output))
    require(output.parent.is_dir() and not output.exists() and not output.is_symlink() and
            shutil.disk_usage(output.parent).free >= 256 * 1024 * 1024,
            'output occupied or insufficient space')
    with tempfile.TemporaryDirectory(prefix='.wifi-native-', dir=output.parent) as tmp:
        stage = Path(tmp)
        (stage / 'Image.gz').write_bytes(image)
        (stage / 'kernel.config').write_bytes(config)
        (stage / 'initramfs.img').write_bytes(initramfs)
        (stage / 'board.dtb').write_bytes(board)
        boot = stage / 'boot.img'
        subprocess.run([sys.executable, str(BOOT / 'build-android-boot-v0.py'),
                        '--kernel', str(stage / 'Image.gz'), '--ramdisk',
                        str(stage / 'initramfs.img'), '--dtb', str(stage / 'board.dtb'),
                        '--name', BOOT_NAME, '--cmdline', BOOT_CMDLINE,
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
                        '--expected-dtb', str(stage / 'board.dtb'), '--expected-name', BOOT_NAME,
                        '--expected-cmdline', BOOT_CMDLINE, str(boot)],
                       check=True, stdout=subprocess.DEVNULL)
        result = {'status': 'offline-gated-ccmp-stable-monitor-candidate-validated',
                  'kernel_build_commit': COMMIT, 'kernel_release': RELEASE,
                  'kernel_package_sha256': PACKAGE,
                  'integration_source_commit': SOURCE_COMMIT,
                  'integration_patch_sha256': PATCH_SHA256,
                  'kernel_profile': PROFILE,
                  'parent_candidate': 'candidate-32',
                  'parent_boot2_sha256': PARENT_BOOT2_SHA256,
                  'files': {p.name: {'sha256': sha(regular(p)), 'bytes': p.stat().st_size}
                            for p in sorted(stage.iterdir())},
                  'kernel_config_change': ('old native arm0, CCMP stable arm1 command line and '
                                            'USB identity, LOCALVERSION, and '
                                            'NATIVE_DELIVERY_DIAG/CCMP_STABLE_EPOCH=y; nothing else'),
                  'device_tree_change': 'none; exact candidate 32 board DT',
                  'ram_root_change': 'release gate only; the exact candidate 32 64-member private RAM root',
                  'native_delivery_diag': False, 'ccmp_stable_epoch': True,
                  'bootstrap': 'normal-dhcp-only', 'gtk_rx': False, 'key_reuse': False,
                  'secret_bearing': True, 'device_action': 'none', 'physical_admission': False}
        (stage / 'candidate.json').write_text(json.dumps(result, indent=2) + '\n')
        stage.rename(output)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
