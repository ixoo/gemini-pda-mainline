#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compose P1 strict initial-group delivery on verified private C32.

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

COMMIT = '71c4b4a818b5eef6330e0ca844407574941a017c'
PACKAGE = '1e92619aac81cdc66479cc8d6a17ef168237436a7e2dacdf1feca0d0383055d1'
IMAGE_SHA256 = '9beb0899b46a5f9621a5c885c35645f3ea91ab68e06e4fd7bdc6ff4bca0d9172'
CONFIG_SHA256 = 'd4ef9421c59cdf08d2217b8e28ebc697a273e108b7e54f41a941934b728e11a8'
PATCHSET_SHA256 = '4134ce4f0e6b1e13d42a945d425e31752db411a99e88098a0f03194de6de3ba5'
PROFILE = 'mt6797-a53-wifi-ccmp-connected-lifetime'
RELEASE = '7.1.3-gemini-a53-wifi-ccmp-stable-monitor'
SOURCE_COMMIT = 'e7be093e6f4200b03aaff56787dc8d74ca1f3468'
PATCH_SHA256 = '58e5d1475d3024b9a0de783d6e1e8be167dd475c7621bb0190951e795a3ba02e'
SERIES_SHA256 = '3978ed09f029e1be191c6ef1223b133c5e5987f62a8ecfe3d96b9cbabcf8c070'
PERIODIC_LEAF_SHA256 = '3188a0ddf8ead1c58affebff941a2659d21b26f343bb6fb732a037fe1828dd6e'
PARTITION_BYTES = 16777216
BOOT_NAME = 'gemini-obs-P'
BOOT_CMDLINE = 'bootopt=64S3,32N2,64N2'


def expected_ccmp_config(parent_config):
    """Use the frozen C10 oracle, adding only the selected connected-profile symbols."""
    require(b'CONFIG_MT6797_CCMP_CONNECTED_LIFETIME' not in parent_config and
            b'CONFIG_MT6797_CCMP_TX_PID_REUSE' not in parent_config and
            b'CONFIG_MT6797_CCMP_50S_IDLE' not in parent_config and
            b'CONFIG_MT6797_CCMP_CHANNEL_RELEASE' not in parent_config and
            b'CONFIG_MT6797_CCMP_INITIAL_GTK' not in parent_config and
            b'CONFIG_MT6797_CCMP_60S_WINDOW' not in parent_config,
            'parent initial-GTK/window anchors changed')
    oracle = runpy.run_path(str(HERE / 'build-ccmp-candidate-10.py'))
    previous = oracle['expected_ccmp_config'](parent_config)
    anchor = b'CONFIG_MT6797_NATIVE_DELIVERY_DIAG=y\n'
    require(previous.count(anchor) == 1, 'parent native symbol changed')
    return previous.replace(anchor, anchor +
                            b'# CONFIG_MT6797_CCMP_50S_IDLE is not set\n'
                            b'CONFIG_MT6797_CCMP_TX_PID_REUSE=y\n'
                            b'CONFIG_MT6797_CCMP_CONNECTED_LIFETIME=y\n'
                            b'CONFIG_MT6797_CCMP_CHANNEL_RELEASE=y\n'
                            b'CONFIG_MT6797_CCMP_INITIAL_GTK=y\n'
                            b'CONFIG_MT6797_CCMP_60S_WINDOW=y\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('kernel-package', 'parent', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)

    require(sha(regular(HERE / 'join-ccmp-p1.sh')) == PERIODIC_LEAF_SHA256,
            'reviewed periodic leaf changed')

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
    series = regular(REPO / 'patches/series-a53-wifi-ccmp-connected-lifetime')
    require(sha(series) == SERIES_SHA256 and len(series.splitlines()) == 715 and
            sha(regular(REPO / 'patches/proposals/'
                        '0222-wifi-mt6797-size-connected-observation-counters-separately.patch')) ==
            PATCH_SHA256 and
            sha(regular(REPO / 'patches/proposals/0217-wifi-mt6797-test-connected-data-after-bounded-join-privilege-release.patch')) ==
            '40f76affeeeabebe796f655196adf0d6ceefb483d2b9ad9651345f633c1b8cc0' and
            sha(regular(REPO / 'patches/proposals/0218-wifi-mt6797-select-a-50-second-idle-tail-comparison.patch')) ==
            'b71a6f603af5cc174283e1fc2e557dc0b8c1b8f4384b9bd1f0ac7fc120ec8ef9' and
            sha(regular(REPO / 'patches/proposals/0219-wifi-mt6797-separate-connected-data-from-join-and-teardown.patch')) ==
            '47b72248c188d19bd7e5efe557cc0202dad6dd7a9271df78519d94dda8cf98e2' and
            sha(regular(REPO / 'patches/proposals/0220-wifi-mt6797-recycle-only-completed-ordinary-TX-slots.patch')) ==
            '46810fecbf127bcc1b871ef4070896d34557636a92aab82beb59b1b11a222f51' and
            sha(regular(REPO / 'patches/proposals/0221-wifi-mt6797-report-owned-connected-monitor-loss-to-mac80211.patch')) ==
            '1521615c1781591218ad18ef918b8b60738fb455d21749d6ed74a1796ead0f4d' and
            sha(regular(REPO / 'patches/proposals/0216-wifi-mt6797-retain-PM-relative-completion-and-beacon-observations.patch')) ==
            '5e55ac882f0836cbc7a90737d3d4e417abf9aeb5bf918d5125680a287632e73c' and
            sha(regular(REPO / 'patches/proposals/0213-wifi-mt6797-retire-only-reserved-deauth-timeout-for-bounded-cleanup.patch')) ==
            '021d108d0171ed9c47fa1c62c3da7a61106766e7f89b3232705feff221892a64' and
            sha(regular(REPO / 'patches/proposals/0214-wifi-mt6797-quarantine-one-cleanup-page-without-a-healthy-terminal.patch')) ==
            'd1372d470bfc9d31d4a62c9a493610296a9268d85a02291f3af6a95d17cf7134' and
            sha(regular(REPO / 'patches/proposals/0215-wifi-mt6797-credit-PM-abort-before-reserved-deauthentication.patch')) ==
            'c92e39899c0fb8dda3e9f6cbb8c210c1a1626a9d924c457c41e7317ab3969ea7' and
            sha(regular(REPO / 'patches/proposals/0212-wifi-mt6797-own-connection-monitoring-in-PM-required-experiment.patch')) ==
            '0e1944385fcb50da6a4a4e61e983761af8f47de10f2c99a0aac8db8655c9044c' and
            sha(regular(REPO / 'patches/proposals/0210-wifi-mt6797-count-owned-timeout-observations-without-changing-refusal.patch')) ==
            '77dd0d663b34094dda705bd627827012ca0bcaefd32b2059605232be36b1a3bd' and
            sha(regular(REPO / 'patches/proposals/0211-wifi-mt6797-indicate-PM-connection-from-owned-beacon-before-keys.patch')) ==
            '07417c57f17e1733b4c1fb2f6850288c2fffddf7f696cbc931e9245518b39e4c' and
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
                                            'NATIVE_DELIVERY_DIAG/CCMP_TX_PID_REUSE/CCMP_CONNECTED_LIFETIME/CCMP_CHANNEL_RELEASE/CCMP_INITIAL_GTK/CCMP_60S_WINDOW/CCMP_STABLE_EPOCH/CCMP_MASK_CONTROL=y; nothing else'),
                  'device_tree_change': 'none; exact candidate 32 board DT',
                  'ram_root_change': 'release gate only; the exact candidate 32 64-member private RAM root',
                  'native_delivery_diag': False, 'ccmp_stable_epoch': True,
                  'mask_control': True, 'group_pn_observe': False,
                  'connected_lifetime': True, 'key_reuse': False, 'rekey': False,
                  'ordinary_pid_range': [1, 126], 'reserved_deauth_pid': 127,
                  'pid_completion_wire_generation_proven': False,
                  'unowned_completion_policy': 'count-discard-without-ownership-change',
                  'station_beacon_filter': True, 'owned_loss_standard_reporting': True,
                  'teardown_fence_at_first_data_end_ms': 5000,
                  'lifetime_packet_max': 65536, 'connected_data_poll_quota': False,
                  'host_stream_required_ms': 120000, 'host_stream_scheduled_ms': 121000,
                  'host_receive_gap_max_ms': 3000, 'host_control_pm_window_ms': [120000, 135000],
                  'host_helper_sha256': '2c28acdf350943a6fc6159a5799d1f039830309d78f68d7cf9683a4ce867173d',
                  'initial_gtk': True, 'observation_window_ms': None,
                  'connected_channel_release': True, 'join_grant_request_ms': 9000,
                  'connected_release_tail_ms': 2500, 'data_window_inside_grant': False,
                  'post_release_traffic_required': True,
                  'grant_horizon_decoupled': True, 'early_grant_minimum_ms': 9000,
                  'checked_ccmp_max': 8192, 'total_rx_max': 32768,
                  'rx_bytes_max': 16777216, 'pid_reuse': True,
                  'low_traffic_only': True, 'gtk_arp_handoff_counter': True,
                  'bss_timeout_observe': True,
                  'owned_beacon_recency': True,
                  'conditional_bss_timeout': False,
                  'timeout_policy': 'owned-live-loss-to-standard-disconnect-otherwise-refuse',
                  'pm_connected_before_keys': True, 'pm_abort_before_removals': True,
                  'connection_monitor': True, 'reconnect': False,
                  'deauth_timeout_retirement': True, 'deauth_timeout_bound_ms': 750,
                  'deauth_debt_limit_pages': 1, 'abort_waits_full_ledger': True,
                  'late_retired_pid_only': True,
                  'cleanup_waits_full_ledger': False, 'cleanup_uses_latched_debt_floor': True,
                  'bounded_page_debt_terminal': True, 'healthy_stage_requires_whole_ledger': True,
                  'pm_abort_before_deauth': True, 'pm_relative_timing': True,
                  'owned_beacons_at_data_end': True,
                  'periodic_ping_offsets_s': [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110],
                  'periodic_before_ssh_ack': True, 'periodic_clock_resolution_ns': 10000000,
                  'periodic_leaf_sha256': PERIODIC_LEAF_SHA256,
                  'beacon_clock_scope': 'existing owned-beacon queue admission; includes pre-data',
                  'last_rx_clock_scope': 'strict PTK/GTK queue admission only',
                  'bootstrap': 'normal-dhcp-only', 'gtk_rx': True, 'key_reuse': False,
                  'secret_bearing': True, 'device_action': 'none', 'physical_admission': False}
        (stage / 'candidate.json').write_text(json.dumps(result, indent=2) + '\n')
        stage.rename(output)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
