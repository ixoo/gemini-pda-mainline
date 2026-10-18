#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compose GTK4 strict initial-group delivery on verified private C32.

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

COMMIT = 'aabc1cc3bdbe16b4049f93038f33a13e97a9f851'
PACKAGE = '4fc69aa055b443b5200d9011cc6687cce6ef27ee4822aa8e590bd42e81c5be02'
IMAGE_SHA256 = 'fab29715e417a5788012f9ccb5757a3ff31f1ac4a2df97a4aded6d76f2ada4e4'
CONFIG_SHA256 = 'ff1f087376b3a1a2afb38e5325e799926f58db67b46efac1e1ebb6214fea9bd1'
PATCHSET_SHA256 = 'eaed7daf0ff3cc9dba0cf172a06470e214061511e85f64a769e7472aab769085'
PROFILE = 'mt6797-a53-wifi-ccmp-initial-gtk'
RELEASE = '7.1.3-gemini-a53-wifi-ccmp-stable-monitor'
SOURCE_COMMIT = '2f9eb1a21120a8cb9d8e99f5f2eb5cd2c88f59cd'
PATCH_SHA256 = '08ff0b17fc4ed2ae19a6c15c9a19d2caf89a4efede81193702305b673e1242f6'
SERIES_SHA256 = 'ab281a96c054e98e3106610a4b279951e1400a22aa1381144d2b3372cf9799ba'
PARTITION_BYTES = 16777216
BOOT_NAME = 'gemini-obs-P'
BOOT_CMDLINE = 'bootopt=64S3,32N2,64N2'


def expected_ccmp_config(parent_config):
    """Use the frozen C10 oracle, adding only the two selected symbols."""
    require(b'CONFIG_MT6797_CCMP_INITIAL_GTK' not in parent_config and
            b'CONFIG_MT6797_CCMP_60S_WINDOW' not in parent_config,
            'parent initial-GTK/window anchors changed')
    oracle = runpy.run_path(str(HERE / 'build-ccmp-candidate-10.py'))
    previous = oracle['expected_ccmp_config'](parent_config)
    anchor = b'CONFIG_MT6797_NATIVE_DELIVERY_DIAG=y\n'
    require(previous.count(anchor) == 1, 'parent native symbol changed')
    return previous.replace(anchor, anchor +
                            b'CONFIG_MT6797_CCMP_INITIAL_GTK=y\n'
                            b'CONFIG_MT6797_CCMP_60S_WINDOW=y\n')


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
    series = regular(REPO / 'patches/series-a53-wifi-ccmp-initial-gtk')
    require(sha(series) == SERIES_SHA256 and len(series.splitlines()) == 701 and
            sha(regular(REPO / 'patches/proposals/'
                        '0208-wifi-mt6797-observe-refused-BSS-timeout-and-checked-RX-age.patch')) ==
            PATCH_SHA256 and
            sha(regular(REPO / 'patches/proposals/0206-wifi-mt6797-bound-low-traffic-CCMP-observation-capacity.patch')) ==
            'e6645a1bbbba03bc9e32d236418b91987effd91b6bb7f5f436dd938e70dd5185' and
            sha(regular(REPO / 'patches/proposals/0205-wifi-mt6797-retain-the-validated-channel-grant-horizon.patch')) ==
            '623acad53f4ce4f273ee050dfd55ad256ffad780a8a36a2728274497855f1690', 'approved source selection changed')
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
        result = {'status': 'offline-gated-ccmp-initial-gtk-candidate-validated',
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
                                            'NATIVE_DELIVERY_DIAG/CCMP_INITIAL_GTK/CCMP_60S_WINDOW/CCMP_STABLE_EPOCH/CCMP_MASK_CONTROL=y; nothing else'),
                  'device_tree_change': 'none; exact candidate 32 board DT',
                  'ram_root_change': 'release gate only; the exact candidate 32 64-member private RAM root',
                  'native_delivery_diag': False, 'ccmp_stable_epoch': True,
                  'mask_control': True, 'group_pn_observe': False,
                  'initial_gtk': True, 'observation_window_ms': 60000,
                  'grant_horizon_decoupled': True, 'early_grant_minimum_ms': 62500,
                  'checked_ccmp_max': 1024, 'total_rx_max': 4096,
                  'rx_bytes_max': 2097152, 'pid_reuse': False,
                  'low_traffic_only': True, 'gtk_arp_handoff_counter': True,
                  'bss_timeout_observe': True,
                  'last_rx_clock_scope': 'strict PTK/GTK queue admission only',
                  'bootstrap': 'normal-dhcp-only', 'gtk_rx': True, 'key_reuse': False,
                  'secret_bearing': True, 'device_action': 'none', 'physical_admission': False}
        (stage / 'candidate.json').write_text(json.dumps(result, indent=2) + '\n')
        stage.rename(output)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
