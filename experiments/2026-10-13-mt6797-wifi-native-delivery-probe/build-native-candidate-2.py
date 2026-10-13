#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compose the native-crypto-delivery candidate from the d104 package on the C32 parent.

The native-delivery diagnostic (proposal 0181, default-off but force-armed by the
profile) is the verified candidate 32 (phase-b station join) with the native
# (ND2 rebuild from commit 2e9cae6e, which adds the 0xFC command-validator case that
# ND1/d104 lacked; ND1 is retained immutable as the host-defect negative)
kernel and exactly three configuration changes -- the forced
mac.native_delivery_diag=1 boot parameter and the distinct USB-gadget identity,
the LOCALVERSION, and CONFIG_MT6797_NATIVE_DELIVERY_DIAG=y. Candidate 32's board
DT and whole 64-member private RAM root are reused byte-identical except the one
release-gate string the init checks (phase-b -> native-delivery). Offline and
gated; it produces the real native candidate receipt and padded image and takes
no device action. Root executes it with the private parent/package. Candidate 32
/ runtime 33 stay pinned; this is a separate one-lifetime diagnostic candidate.
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

COMMIT = '2e9cae6ea4fb3b79221ed8c18829c03326018265'
PACKAGE = '2d2c66154d686b94c384f835e154c2370c4891f5af84752b8f69875134c1c201'
PROFILE = 'mt6797-a53-wifi-native-delivery-diag'
RELEASE = '7.1.3-gemini-a53-wifi-native-delivery-diag'
NEW_IMAGE_SHA256 = 'e376bbd4fdf234501284db7ae95bed2e0a295300de337d9825e899862c3bc31a'
PARTITION_BYTES = 16777216
BOOT_NAME = 'gemini-obs-P'
BOOT_CMDLINE = 'bootopt=64S3,32N2,64N2'


def expected_native_config(parent_config):
    """Candidate 32's phase-b config with exactly the three native-delivery changes
    (verified byte-exact against the d104 package): the armed/identity command
    line, the LOCALVERSION, and the default-off-at-config diagnostic symbol.
    Anything else differing from the parent is an unrelated change and is refused.
    """
    require(parent_config.count(
        b'g_ether.iProduct=Gemini-L-Observability g_ether.iSerialNumber='
        b'GEMINI_OBSERVABILITY_20260717_L clk_ignore_unused fbcon=rotate:3 '
        b'consoleblank=0 fbcon=font:TER16x32"') == 1 and
        parent_config.count(b'CONFIG_LOCALVERSION="-gemini-a53-wifi-phase-b-compile"') == 1 and
        parent_config.count(b'CONFIG_MT6797_STATION_JOIN=y\n') == 1 and
        b'CONFIG_MT6797_NATIVE_DELIVERY_DIAG' not in parent_config,
        'parent native-config anchors changed')
    return parent_config.replace(
        b'g_ether.iProduct=Gemini-L-Observability g_ether.iSerialNumber='
        b'GEMINI_OBSERVABILITY_20260717_L clk_ignore_unused fbcon=rotate:3 '
        b'consoleblank=0 fbcon=font:TER16x32"',
        b'g_ether.iProduct=Gemini-Native-Delivery-Diag g_ether.iSerialNumber='
        b'GEMINI_NATIVE_DELIVERY_20261012 clk_ignore_unused fbcon=rotate:3 '
        b'consoleblank=0 fbcon=font:TER16x32 mac.native_delivery_diag=1"').replace(
        b'CONFIG_LOCALVERSION="-gemini-a53-wifi-phase-b-compile"',
        b'CONFIG_LOCALVERSION="-gemini-a53-wifi-native-delivery-diag"').replace(
        b'CONFIG_MT6797_STATION_JOIN=y\n',
        b'CONFIG_MT6797_STATION_JOIN=y\nCONFIG_MT6797_NATIVE_DELIVERY_DIAG=y\n')


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
            package.name == 'linux-7.1.3-gemini-' + PACKAGE, 'not the native-delivery package')
    audit = runpy.run_path(str(REPO /
        'experiments/2026-09-05-owner-away-experiment-preparation/baseline/audit_foundation.py'))
    audit['inventory'](package, {'manifest_sha256': PACKAGE,
                                 'inventory_count': len(regular(package / 'SHA256SUMS').splitlines())})
    build = json.loads(regular(package / 'provenance/build.json'))
    require(build['repository_commit'] == COMMIT and not build['repository_dirty'] and
            build['build_profile'] == PROFILE and build['kernel_release'] == RELEASE,
            'build provenance changed')
    image = regular(package / 'Image.gz')
    config = regular(package / 'kernel.config')
    require(sha(image) == NEW_IMAGE_SHA256 and gzip.decompress(image) == regular(package / 'Image'),
            'kernel image changed')
    parent_config = regular(parent / 'kernel.config')
    require(config == expected_native_config(parent_config),
            'kernel configuration is not the parent plus the three native changes')
    command = [line for line in config.splitlines() if line.startswith(b'CONFIG_CMDLINE=')]
    require(len(command) == 1 and b' clk_ignore_unused ' in command[0] and
            b' mac.native_delivery_diag=1"' in command[0] and
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
        result = {'status': 'offline-gated-native-delivery-candidate-validated',
                  'kernel_build_commit': COMMIT, 'kernel_release': RELEASE,
                  'kernel_package_sha256': PACKAGE,
                  'parent_candidate': 'candidate-32',
                  'parent_boot2_sha256': PARENT_BOOT2_SHA256,
                  'files': {p.name: {'sha256': sha(regular(p)), 'bytes': p.stat().st_size}
                            for p in sorted(stage.iterdir())},
                  'kernel_config_change': ('the armed mac.native_delivery_diag=1 command line and '
                                           'USB identity, LOCALVERSION, and '
                                           'CONFIG_MT6797_NATIVE_DELIVERY_DIAG=y; nothing else'),
                  'device_tree_change': 'none; exact candidate 32 board DT',
                  'ram_root_change': 'release gate only; the exact candidate 32 64-member private RAM root',
                  'native_delivery_diag': True,
                  'secret_bearing': True, 'device_action': 'none', 'physical_admission': False}
        (stage / 'candidate.json').write_text(json.dumps(result, indent=2) + '\n')
        stage.rename(output)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
