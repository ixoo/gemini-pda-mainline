#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compose the Phase A common-init, WLAN-start and scan candidate offline."""

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
PARENT_RECEIPT = HERE.parent / '2026-10-03-mt6797-wmt-versions/results/candidate.json'
PARENT_MANIFEST_SHA = 'd6a22f27246ea98632fb11f057249fc6ff254f3e5a0f4a08d09e76b390b93b53'
PARENT_BOOT2_SHA256 = '391f44a8f5c79467f3a2741bcad51c95ea34791248585baae69b0a19f852ac73'
PARENT_RELEASE = b'7.1.3-gemini-a53-wmt-versions'
COMMIT = 'b6fa6a62f767609759cf6f4b35803bcafe1f8ed5'
PACKAGE = '499233263a327fc49c31776ec22e15bb5180d12a9ea192ead4b75d7f2baf205d'
PROFILE = 'mt6797-a53-wifi-phase-a-compile'
RELEASE = '7.1.3-gemini-a53-wifi-phase-a'
BUILT_DTB_SHA256 = '07b097d581cae6208eea8387d534e14bb2c2bc30752b0d4b783f711284284734'
FIRMWARE_DIR = 'lib/firmware/mediatek/mt6797/'
ROM_PATCHES = {
    'ROMv3_patch_1_1_hdr.bin': ('5732c0730380e937b48ad169f2805b65e8d4a178265566c5083cb2cc2d249f1e', 46472),
    'ROMv3_patch_1_0_hdr.bin': ('450c2b0949cf879217ac9aef81b18b860982f0e69340784b448b54365d8cf630', 210904),
}
USERSPACE = HERE.parent / '2026-10-01-mt6797-passive-scan/results/userspace.json'
USERSPACE_SHA256 = '4aedbc779d32fc6729de689cda22d0ace5ba8f2050134ec95c81f699a138498c'
OWNER = '/consys@10001340'
WIFI = OWNER + '/wifi'
PARTITION_BYTES = 16777216


def fdt(*args):
    return subprocess.run(['fdtget' if args[0] == 'get' else 'fdtput'] + list(args[1:]),
                          check=True, capture_output=True, text=True).stdout.strip()


def edit_dt(board):
    """Apply the Phase A CONSYS changes to a copy of the booted parent DT."""
    before = nodes(board)
    require(before[WIFI].get('status') == '"disabled"' and
            'mediatek,one-shot-wmt-identity-capture' in before[OWNER] and
            'vcn33-wifi-supply' in before[OWNER], 'parent CONSYS node changed')
    # Resolve the Wi-Fi rail node and its regulators parent from the booted DT.
    wifi_rail = int(fdt('get', '-t', 'x', str(board), OWNER, 'vcn33-wifi-supply'), 16)
    rails = [path for path, props in before.items()
             if props.get('phandle') == '<0x%02x>' % wifi_rail]
    require(len(rails) == 1, 'VCN33-WIFI regulator node not unique')
    regulators = rails[0].rsplit('/', 1)[0]
    bt_path = regulators + '/ldo-vcn33-bt'
    require(bt_path not in before, 'VCN33-BT node already present')
    handles = [int(props['phandle'][1:-1], 16) for props in before.values() if 'phandle' in props]
    bt_handle = max(handles) + 1
    fdt('put', '-c', str(board), bt_path)
    fdt('put', '-t', 's', str(board), bt_path, 'regulator-name', 'vcn33-bt')
    fdt('put', '-t', 'x', str(board), bt_path, 'phandle', format(bt_handle, 'x'))
    fdt('put', '-d', str(board), OWNER, 'mediatek,one-shot-wmt-identity-capture')
    for flag in ('mediatek,one-shot-wmt-negotiate', 'mediatek,one-shot-wmt-common-init'):
        fdt('put', str(board), OWNER, flag)
    fdt('put', '-t', 'u', str(board), OWNER, 'mediatek,coex-antenna-mode', '1')
    fdt('put', '-t', 'x', str(board), OWNER, 'vcn33-bt-supply', format(bt_handle, 'x'))
    reg = fdt('get', '-t', 'x', str(board), OWNER, 'reg').split()
    names = fdt('get', '-t', 's', str(board), OWNER, 'reg-names').split()
    require(len(reg) == 36 and len(names) == 9 and names[-1] == 'btif-dma-rx',
            'parent CONSYS resources changed')
    fdt('put', '-t', 'x', str(board), OWNER, 'reg', *reg, '0', '180b6000', '0', '100')
    fdt('put', '-t', 's', str(board), OWNER, 'reg-names', *names, 'afe')
    fdt('put', '-d', str(board), WIFI, 'status')
    after = nodes(board)
    changed = {OWNER, WIFI, bt_path}
    require(set(after) == set(before) | {bt_path} and
            all(after[path] == props for path, props in before.items()
                if path not in changed) and
            after[WIFI] == {key: value for key, value in before[WIFI].items()
                            if key != 'status'} and
            'mediatek,one-shot-bt-reset' not in after[OWNER] and
            'mediatek,one-shot-wmt-identity-capture' not in after[OWNER],
            'unrelated DT change')
    return bt_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('kernel-package', 'parent', 'rom-patch-dir', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)

    # Parent: the booted WMT-versions candidate, exactly as published.
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

    # Kernel: the exact validated Phase A package.
    package = args.kernel_package.resolve(strict=True)
    require(package.is_dir() and not args.kernel_package.is_symlink() and
            package.name == 'linux-7.1.3-gemini-' + PACKAGE, 'not the Phase A package')
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
                b'CONFIG_CRYPTO_LIB_SHA256=y\n', b'CONFIG_DEBUG_FS=y\n',
                b'CONFIG_SERIAL_8250_CONSOLE=y\n',
                ('CONFIG_LOCALVERSION="-' + RELEASE.split('-', 1)[1] + '"\n').encode())),
            'kernel image or configuration changed')
    require(sha(regular(package / 'dtbs/mediatek/mt6797-gemini-pda.dtb')) == BUILT_DTB_SHA256,
            'compiled board DT changed')

    # RAM root: parent members, release gate, plus the two retained ROM patches.
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
    template = old[FIRMWARE_DIR + 'WIFI_RAM_CODE_6797']
    rom_dir = args.rom_patch_dir.resolve(strict=True)
    for name, (digest, size) in ROM_PATCHES.items():
        data = regular(rom_dir / name)
        require(len(data) == size and sha(data) == digest, 'ROM patch changed: ' + name)
        require(FIRMWARE_DIR + name not in old, 'parent already carries ' + name)
        new[FIRMWARE_DIR + name] = replace(template, data=data,
                                           mode=0o100644)
    initramfs = encode(new)
    require(parse(initramfs) == new and len(new) == len(old) + 2, 'RAM root encoding changed')

    output = Path(os.path.abspath(args.output))
    require(output.parent.is_dir() and not output.exists() and not output.is_symlink() and
            shutil.disk_usage(output.parent).free >= 256 * 1024 * 1024,
            'output occupied or insufficient space')
    with tempfile.TemporaryDirectory(prefix='.wifi-phase-a-', dir=output.parent) as tmp:
        stage = Path(tmp)
        board = stage / 'board.dtb'
        board.write_bytes(regular(parent / 'board.dtb'))
        edit_dt(board)
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
        result = {'status': 'offline-gated-wifi-phase-a-candidate-validated',
                  'kernel_build_commit': COMMIT, 'kernel_release': RELEASE,
                  'kernel_package_sha256': PACKAGE,
                  'parent_boot2_sha256': PARENT_BOOT2_SHA256,
                  'rom_patches': {name: digest for name, (digest, _) in ROM_PATCHES.items()},
                  'files': {p.name: {'sha256': sha(regular(p)), 'bytes': p.stat().st_size}
                            for p in sorted(stage.iterdir())},
                  'device_tree_change': 'CONSYS negotiate/common-init/antenna/AFE/VCN33-BT, '
                                        'new ldo-vcn33-bt node, WLAN child re-enabled',
                  'ram_root_change': 'release gate and two ROM patches',
                  'secret_bearing': True, 'device_action': 'none',
                  'physical_admission': False}
        (stage / 'candidate.json').write_text(json.dumps(result, indent=2) + '\n')
        stage.rename(output)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
