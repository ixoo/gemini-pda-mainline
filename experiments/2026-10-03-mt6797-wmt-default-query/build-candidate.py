#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compose the isolated WMT query using the proven booted DT and private RAM root."""

import argparse
from dataclasses import replace
import gzip
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
BASE = runpy.run_path(str(HERE.parent / '2026-09-28-mt6797-emi-set-probe/build-candidate.py'))
require, regular, sha, nodes = (BASE[name] for name in ('require', 'regular', 'sha', 'nodes'))
BOOT = REPO / 'experiments/2026-07-12-boot-contract-recovery/scripts'
PARENT_RECEIPT = HERE.parent / '2026-10-02-mt6797-scan-pool-sample/results/candidate.json'
COMMIT = '28500dbb27a6b9add21659732d8ef52f1e59e9ef'
PROFILE = 'mt6797-a53-wmt-default-query-compile'
RELEASE = '7.1.3-gemini-a53-wmt-query'
PARENT_BOOT2_SHA256 = '3d9186a96f4000d318f5615746257bcb83d3bb58e6aca74928f1e69106476d79'
BOOTED_DTB_SHA256 = 'cef9373ea3aa0e1a8a45a13b953ae95e48939b211e41a73052543be784ee3214'
BUILT_DTB_SHA256 = '1bd2fffc78902460261881e2b0a939b1be26d90d448ce472a0a13540c2371b44'
INITRAMFS_SHA256 = '6eeae9ddad5cc54543a3be0e79b3af6d22d3cc238d0495b8cc0366c15eac8225'
FIRMWARE_SHA256 = 'a69383d74d829430487c39eef6b5e281b25f901595c903a632a10aa8631426dd'
FIRMWARE_MEMBER = 'lib/firmware/mediatek/mt6797/WIFI_RAM_CODE_6797'
RECORD_MEMBER = 'lib/firmware/mediatek/mt6797/WIFI.storage'
PARTITION_BYTES = 16777216


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('kernel-package', 'parent', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)

    parent = args.parent.resolve(strict=True)
    accepted = json.loads(regular(PARENT_RECEIPT))
    require(parent.is_dir() and not args.parent.is_symlink() and
            parent.name == 'candidate-' + accepted['files']['boot.img']['sha256'] and
            {p.name for p in parent.iterdir()} == set(accepted['files']) | {'candidate.json'} and
            json.loads(regular(parent / 'candidate.json')) == accepted and
            accepted['files']['boot2-padded.img']['sha256'] == PARENT_BOOT2_SHA256 and
            accepted['files']['board.dtb']['sha256'] == BOOTED_DTB_SHA256,
            'booted parent changed')
    for name, identity in accepted['files'].items():
        data = regular(parent / name)
        require(len(data) == identity['bytes'] and sha(data) == identity['sha256'],
                'parent member changed: ' + name)

    package = args.kernel_package.resolve(strict=True)
    require(package.is_dir() and not args.kernel_package.is_symlink() and
            package.name.startswith('linux-7.1.3-gemini-'), 'package location changed')
    package_id = package.name.removeprefix('linux-7.1.3-gemini-')
    require(package_id ==
            'c6beed6c5ab6f03a7b73b34cc873acfb935bebe3936abfd66e7191ca01fb9c88',
            'not the selected validated package')
    audit = runpy.run_path(str(REPO /
        'experiments/2026-09-05-owner-away-experiment-preparation/baseline/audit_foundation.py'))
    sums = regular(package / 'SHA256SUMS')
    audit['inventory'](package, {'manifest_sha256': package_id,
                                 'inventory_count': len(sums.splitlines())})
    build = json.loads(regular(package / 'provenance/build.json'))
    require(build['repository_commit'] == COMMIT and not build['repository_dirty'] and
            build['build_profile'] == PROFILE and build['kernel_release'] == RELEASE,
            'build provenance changed')
    image = regular(package / 'Image.gz')
    config = regular(package / 'kernel.config')
    require(gzip.decompress(image) == regular(package / 'Image') and
            b'CONFIG_MTK_MT6797_CONSYS=y\n' in config and
            b'CONFIG_MT6797_HIF_CORE=y\n' in config and
            b'CONFIG_SERIAL_8250_CONSOLE=y\n' in config and
            b'CONFIG_DEBUG_FS=y\n' in config and
            b'CONFIG_SERIAL_8250_MT6577=y\n' in config and
            ('CONFIG_LOCALVERSION="-' + RELEASE.split('-', 1)[1] + '"\n').encode() in config,
            'kernel image or configuration changed')
    require(sha(regular(package / 'dtbs/mediatek/mt6797-gemini-pda.dtb')) ==
            BUILT_DTB_SHA256, 'compiled board DT changed from selected predecessor')

    parent_ram = regular(parent / 'initramfs.img')
    require(sha(parent_ram) == INITRAMFS_SHA256, 'private RAM root changed')
    parser_path = REPO / 'experiments/2026-07-25-emmc-development/scripts/validate-emmc-initramfs.py'
    serializer_path = REPO / 'experiments/2026-08-14-mt6797-runtime-provenance-observer/scripts/build-diagnostic-initramfs.py'
    require(sha(regular(parser_path)) ==
            '19c1c63df5f4732d3cae253a5b7edbb90d0ad609ed1ea411a200dc0060adba9c' and
            sha(regular(serializer_path)) ==
            '0abe8a8b02ec3767c21fc018c69cc7e2db5ddb475a00e443247474a582f29f38',
            'RAM archive tools changed')
    parse = runpy.run_path(str(parser_path))['parse_newc']
    encode = runpy.run_path(str(serializer_path))['encode_newc']
    old_members = parse(parent_ram)
    old_release = b'7.1.3-gemini-a53-wifi-scan-pool-sample'
    require(len(old_members) == 59 and encode(old_members) == parent_ram and
            old_members['init'].data.count(old_release) == 1 and
            RELEASE.encode() not in old_members['init'].data and
            sha(old_members[FIRMWARE_MEMBER].data) == FIRMWARE_SHA256 and
            old_members[RECORD_MEMBER].mode == 0o100600 and
            len(old_members[RECORD_MEMBER].data) == 514,
            'parent RAM-root contract changed')
    new_members = dict(old_members)
    new_members['init'] = replace(old_members['init'],
                                  data=old_members['init'].data.replace(old_release, RELEASE.encode()))
    initramfs = encode(new_members)
    require(parse(initramfs) == new_members and
            all(new_members[name] == member for name, member in old_members.items()
                if name != 'init'), 'RAM root changed outside the release gate')

    output = Path(os.path.abspath(args.output))
    require(output.parent.is_dir() and not output.exists() and not output.is_symlink() and
            shutil.disk_usage(output.parent).free >= 256 * 1024 * 1024,
            'output occupied or insufficient space')
    with tempfile.TemporaryDirectory(prefix='.wmt-default-query-', dir=output.parent) as tmp:
        stage = Path(tmp)
        (stage / 'Image.gz').write_bytes(image)
        board = stage / 'board.dtb'
        board.write_bytes(regular(parent / 'board.dtb'))
        before = nodes(board)
        built = nodes(package / 'dtbs/mediatek/mt6797-gemini-pda.dtb')
        owner = '/consys@10001340'
        wifi = owner + '/wifi'
        infra = '/syscon@10001000'
        sysirq = '/interrupt-controller@10200620'
        uart = '/serial@11002000'
        additions = {'clocks', 'clock-names', 'interrupts',
                     'mediatek,one-shot-wmt-default-query'}
        refs = {'memory-region', 'vcn18-supply', 'vcn28-supply',
                'vcn33-wifi-supply', 'resets', 'mediatek,conn-power-domain'}
        changed = additions | {'reg', 'reg-names'}
        require(set(built[owner]) == set(before[owner]) | additions and
                all(before[owner][key] == built[owner][key]
                    for key in before[owner] if key not in changed | refs) and
                before[wifi] == {'compatible': '"mediatek,mt6797-wlan"'} and
                built[wifi] == dict(before[wifi], status='"disabled"') and
                before['/']['interrupt-parent'] == before[sysirq]['phandle'] and
                '"mediatek,mt6797-sysirq"' in before[sysirq]['compatible'] and
                before[uart]['status'] == '"okay"' and
                before[uart]['clock-names'] == '"baud", "bus"' and
                before['/chosen']['stdout-path'] == '"serial0:921600n8"' and
                before['/aliases']['serial0'] == '"/serial@11002000"',
                'compiled owner, inherited IRQ or active console contract changed')
        def cells(node, prop):
            raw = subprocess.run(['fdtget', '-t', 'x', str(board), node, prop],
                                 check=True, capture_output=True, text=True).stdout.split()
            return [int(value, 16) for value in raw]
        clock_phandle, = cells(infra, 'phandle')
        require(cells(uart, 'clocks') == [clock_phandle, 22, clock_phandle, 46],
                'UART bus no longer uses the same AP-DMA clock')
        # New phandles are resolved from the booted DT, never copied from the build.
        values = {
            'reg': ('x', [0, 0x10001340, 0, 4, 0, 0x10001350, 0, 4,
                          0, 0x18070008, 0, 4, 0, 0x18070110, 0, 4,
                          0, 0x180f0000, 0, 0x1100, 0, 0x10001f00, 0, 4,
                          0, 0x1100c000, 0, 0x1000, 0, 0x11000a00, 0, 0x80,
                          0, 0x11000a80, 0, 0x80]),
            'reg-names': ('s', ['remap', 'conn2ap-sleep-mask', 'chip-id', 'mcu-acr',
                                'wifi-hif', 'emi-selector', 'btif', 'btif-dma-tx',
                                'btif-dma-rx']),
            'clocks': ('x', [clock_phandle, 30, clock_phandle, 46]),
            'clock-names': ('s', ['btif', 'ap-dma']),
            'interrupts': ('x', [0, 130, 8]),
        }
        for prop, (kind, values_list) in values.items():
            args_list = [format(v, 'x') if kind == 'x' else v for v in values_list]
            subprocess.run(['fdtput', '-t', kind, str(board), owner, prop] + args_list,
                           check=True, stdout=subprocess.DEVNULL)
        subprocess.run(['fdtput', str(board), owner, 'mediatek,one-shot-wmt-default-query'],
                       check=True, stdout=subprocess.DEVNULL)
        subprocess.run(['fdtput', '-t', 's', str(board), wifi, 'status', 'disabled'],
                       check=True, stdout=subprocess.DEVNULL)
        after = nodes(board)
        expected = dict(before[owner])
        expected.update({key: built[owner][key] for key in changed - {'clocks'}})
        expected['clocks'] = ('<0x%02x 0x1e 0x%02x 0x2e>' %
                              (clock_phandle, clock_phandle))
        require(set(after) == set(before) and after[owner] == expected and
                after[wifi] == dict(before[wifi], status='"disabled"') and
                all(after[name] == props for name, props in before.items()
                    if name not in {owner, wifi}),
                'unrelated boot DT change or query property mismatch')
        (stage / 'kernel.config').write_bytes(config)
        (stage / 'initramfs.img').write_bytes(initramfs)
        boot = stage / 'boot.img'
        name = 'gemini-obs-P'
        cmdline = 'bootopt=64S3,32N2,64N2'
        subprocess.run([sys.executable, str(BOOT / 'build-android-boot-v0.py'),
                        '--kernel', str(stage / 'Image.gz'), '--ramdisk',
                        str(stage / 'initramfs.img'), '--dtb', str(stage / 'board.dtb'),
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
                        '--expected-dtb', str(stage / 'board.dtb'), '--expected-name', name,
                        '--expected-cmdline', cmdline, str(boot)],
                       check=True, stdout=subprocess.DEVNULL)
        result = {'status': 'offline-gated-wmt-default-query-candidate-validated',
                  'kernel_build_commit': COMMIT, 'kernel_release': RELEASE,
                  'kernel_package_sha256': package_id,
                  'parent_boot2_sha256': PARENT_BOOT2_SHA256,
                  'parent_dtb_sha256': BOOTED_DTB_SHA256,
                  'unchanged_dt_nodes': len(before) - 2,
                  'ram_root_changed_members': ['init release gate only'],
                  'firmware_sha256': FIRMWARE_SHA256,
                  'files': {p.name: {'sha256': sha(regular(p)), 'bytes': p.stat().st_size}
                            for p in sorted(stage.iterdir())},
                  'device_tree_change': 'only CONSYS transport resources/query property and WLAN disabled; all other nodes unchanged',
                  'secret_bearing': True, 'device_action': 'none',
                  'physical_admission': False}
        (stage / 'candidate.json').write_text(json.dumps(result, indent=2) + '\n')
        stage.rename(output)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
