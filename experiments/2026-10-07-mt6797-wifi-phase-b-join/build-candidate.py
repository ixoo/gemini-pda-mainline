#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compose the bounded Phase B kernel on the proven Phase A runtime-3 parent."""

import argparse
import gzip
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
from dataclasses import replace


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
BASE = runpy.run_path(str(HERE.parent / '2026-09-28-mt6797-emi-set-probe/build-candidate.py'))
require, regular, sha, nodes = (BASE[name] for name in ('require', 'regular', 'sha', 'nodes'))
BOOT = REPO / 'experiments/2026-07-12-boot-contract-recovery/scripts'
PARENT_RECEIPT = HERE.parent / '2026-10-06-mt6797-wifi-common-init/results/candidate.json'
PARENT_MANIFEST_SHA = '28e6b6df119c30c8c9e91ab9bd7c08cbaaef64504167265d6d74e7bde6aa4f1c'
PARENT_BOOT2_SHA256 = '827a6582b8913d5130704be38a347beceda2a133b8b86a4033e6fa06df892ce9'
PARENT_RELEASE = b'7.1.3-gemini-a53-wifi-phase-a'
COMMIT = '8efe639e750d76f82050c375e2635497605c047c'
PACKAGE = '07caf6b555debfcaa20c642d336f702705fca8f36c71b20a402cef4fd273dd79'
PROFILE = 'mt6797-a53-wifi-phase-b-compile'
RELEASE = '7.1.3-gemini-a53-wifi-phase-b-compile'
BUILT_DTB_SHA256 = '07b097d581cae6208eea8387d534e14bb2c2bc30752b0d4b783f711284284734'
FIRMWARE_DIR = 'lib/firmware/mediatek/mt6797/'
ROM_PATCHES = {
    'ROMv3_patch_1_1_hdr.bin': ('5732c0730380e937b48ad169f2805b65e8d4a178265566c5083cb2cc2d249f1e', 46472),
    'ROMv3_patch_1_0_hdr.bin': ('450c2b0949cf879217ac9aef81b18b860982f0e69340784b448b54365d8cf630', 210904),
}
USERSPACE = HERE.parent / '2026-10-01-mt6797-passive-scan/results/userspace.json'
USERSPACE_SHA256 = '4aedbc779d32fc6729de689cda22d0ace5ba8f2050134ec95c81f699a138498c'
# Reviewed static nl80211 connect helper (helper/join-connect.c, built by
# helper/build-join-connect.sh on Buildbox-1); inserted as bin/join-connect.
HELPER_PATH = 'bin/join-connect'
HELPER_SHA256 = 'bc499f28bc052a24713ead3175e5b6405e2e5f787acf276e4e82c1278241d5ca'
HELPER_BYTES = 665552
OWNER = '/consys@10001340'
WIFI = OWNER + '/wifi'
PARTITION_BYTES = 16777216


def add_helper(members, helper):
    """Return the RAM root members plus the reviewed helper next to the pinned iw.

    The helper takes iw's ownership and mode (0755, root, one link); the parent
    never carried it and every other member stays byte-identical.
    """
    require(len(helper) == HELPER_BYTES and sha(helper) == HELPER_SHA256 and
            HELPER_PATH not in members, 'join-connect helper absent, changed or already present')
    tool = members['bin/iw']
    require(tool.mode == 0o100755 and tool.uid == 0 and tool.gid == 0 and tool.nlink == 1,
            'pinned iw member ownership changed')
    new = dict(members)
    new[HELPER_PATH] = replace(tool, data=helper)
    return new


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('kernel-package', 'parent', 'helper', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)

    # Parent: the booted Phase A runtime-3 candidate, exactly as published.
    published = regular(PARENT_RECEIPT)
    require(sha(published) == PARENT_MANIFEST_SHA, 'parent receipt changed')
    accepted = json.loads(published)
    parent = args.parent.resolve(strict=True)
    require(parent.is_dir() and not args.parent.is_symlink() and
            parent.name == 'candidate-' + accepted['files']['boot.img']['sha256'] and
            {p.name for p in parent.iterdir()} == set(accepted['files']) | {'candidate.json'} and
            json.loads(regular(parent / 'candidate.json')) == accepted and
            accepted['files']['boot2-padded.img']['sha256'] == PARENT_BOOT2_SHA256,
            'parent candidate changed')
    for name, identity in accepted['files'].items():
        data = regular(parent / name)
        require(len(data) == identity['bytes'] and sha(data) == identity['sha256'],
                'parent member changed: ' + name)

    # Kernel: the exact validated Phase B package.
    package = args.kernel_package.resolve(strict=True)
    require(package.is_dir() and not args.kernel_package.is_symlink() and
            package.name == 'linux-7.1.3-gemini-' + PACKAGE, 'not the Phase B package')
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
    require(gzip.decompress(image) == regular(package / 'Image') and
            all(line in config for line in (
                b'CONFIG_MTK_MT6797_CONSYS=y\n', b'CONFIG_MT6797_MAC80211=y\n',
                b'CONFIG_MT6797_PASSIVE_SCAN=y\n', b'CONFIG_MT6797_SCAN_TUNING_SAMPLE=y\n',
                b'CONFIG_MT6797_STATION_JOIN=y\n', b'CONFIG_ARM_PSCI_FW=y\n',
                b'CONFIG_CMDLINE_FORCE=y\n',
                b'CONFIG_CRYPTO_LIB_SHA256=y\n', b'CONFIG_DEBUG_FS=y\n',
                b'CONFIG_SERIAL_8250_CONSOLE=y\n',
                ('CONFIG_LOCALVERSION="-' + RELEASE.split('-', 1)[1] + '"\n').encode())),
            'kernel image or configuration changed')
    require(sha(regular(package / 'dtbs/mediatek/mt6797-gemini-pda.dtb')) == BUILT_DTB_SHA256,
            'compiled board DT changed')

    parent_config = regular(parent / 'kernel.config')
    expected_config = parent_config.replace(
        b'CONFIG_LOCALVERSION="-gemini-a53-wifi-phase-a"',
        b'CONFIG_LOCALVERSION="-gemini-a53-wifi-phase-b-compile"').replace(
        b'CONFIG_MT6797_SCAN_TUNING_SAMPLE=y\n',
        b'CONFIG_MT6797_SCAN_TUNING_SAMPLE=y\nCONFIG_MT6797_STATION_JOIN=y\n')
    require(config == expected_config, 'unrelated kernel configuration change')
    command = [line for line in config.splitlines() if line.startswith(b'CONFIG_CMDLINE=')]
    require(len(command) == 1 and b' clk_ignore_unused ' in command[0] and
            b'regulator_ignore_unused' not in command[0] and
            nodes(parent / 'board.dtb')['/psci']['method'] == '"smc"',
            'parent clock or PSCI contract changed')

    # RAM root: change only the release gate; keep every private input byte.
    parse = runpy.run_path(str(REPO /
        'experiments/2026-07-25-emmc-development/scripts/validate-emmc-initramfs.py'))['parse_newc']
    encode = runpy.run_path(str(REPO /
        'experiments/2026-08-14-mt6797-runtime-provenance-observer/scripts/build-diagnostic-initramfs.py'))['encode_newc']
    parent_ram = regular(parent / 'initramfs.img')
    old = parse(parent_ram)
    require(encode(old) == parent_ram and old['init'].data.count(PARENT_RELEASE) == 1 and
            RELEASE.encode() not in old['init'].data, 'parent RAM root contract changed')
    userspace_raw = regular(USERSPACE)
    require(sha(userspace_raw) == USERSPACE_SHA256, 'userspace receipt changed')
    for item in json.loads(userspace_raw)['files']:
        member = old.get(item['path'])
        require(member is not None and sha(member.data) == item['sha256'] and
                len(member.data) == item['bytes'],
                'pinned iw userspace absent or changed in parent: ' + item['path'])
    new = dict(old)
    new['init'] = replace(old['init'], data=old['init'].data.replace(PARENT_RELEASE,
                                                                     RELEASE.encode()))
    require(len(old) == 61, 'parent RAM root inventory changed')
    require(not args.helper.is_symlink(), 'helper path is a symlink')
    new = add_helper(new, regular(args.helper))
    for name, (digest, size) in ROM_PATCHES.items():
        member = old[FIRMWARE_DIR + name]
        require(len(member.data) == size and sha(member.data) == digest and
                member.mode == 0o100644, 'parent ROM patch changed: ' + name)
    require(old[FIRMWARE_DIR + 'WIFI.storage'].mode == 0o100600,
            'private board record permissions changed')
    initramfs = encode(new)
    require(parse(initramfs) == new and len(new) == len(old) + 1 and
            parse(initramfs)[HELPER_PATH].data == new[HELPER_PATH].data,
            'RAM root encoding changed')

    output = Path(os.path.abspath(args.output))
    require(output.parent.is_dir() and not output.exists() and not output.is_symlink() and
            shutil.disk_usage(output.parent).free >= 256 * 1024 * 1024,
            'output occupied or insufficient space')
    with tempfile.TemporaryDirectory(prefix='.wifi-phase-b-', dir=output.parent) as tmp:
        stage = Path(tmp)
        board = stage / 'board.dtb'
        board.write_bytes(regular(parent / 'board.dtb'))
        require(regular(board) == regular(parent / 'board.dtb'), 'parent DT changed')
        (stage / 'Image.gz').write_bytes(image)
        (stage / 'kernel.config').write_bytes(config)
        (stage / 'initramfs.img').write_bytes(initramfs)
        boot = stage / 'boot.img'
        name = 'gemini-obs-P'
        cmdline = 'bootopt=64S3,32N2,64N2'
        subprocess.run([sys.executable, str(BOOT / 'build-android-boot-v0.py'),
                        '--kernel', str(stage / 'Image.gz'), '--ramdisk',
                        str(stage / 'initramfs.img'), '--dtb', str(board),
                        '--name', name, '--cmdline', cmdline,
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
        result = {'status': 'offline-gated-wifi-phase-b-candidate-validated',
                  'kernel_build_commit': COMMIT, 'kernel_release': RELEASE,
                  'kernel_package_sha256': PACKAGE,
                  'parent_boot2_sha256': PARENT_BOOT2_SHA256,
                  'rom_patches': {name: digest for name, (digest, _) in ROM_PATCHES.items()},
                  'files': {p.name: {'sha256': sha(regular(p)), 'bytes': p.stat().st_size}
                            for p in sorted(stage.iterdir())},
                  'device_tree_change': 'none; exact Phase A runtime-3 parent DT',
                  'ram_root_change': 'release gate and the reviewed bin/join-connect helper',
                  'helper': {'path': HELPER_PATH, 'sha256': HELPER_SHA256, 'bytes': HELPER_BYTES},
                  'secret_bearing': True, 'device_action': 'none',
                  'physical_admission': False}
        (stage / 'candidate.json').write_text(json.dumps(result, indent=2) + '\n')
        stage.rename(output)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
