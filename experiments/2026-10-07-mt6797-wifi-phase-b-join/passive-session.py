#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind the authenticated A53 session to the Phase B RAM root."""

import importlib.util
import json
import os
from pathlib import Path
import runpy
import stat


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / '2026-09-28-mt6797-wifi-firmware-probe/passive-session.py'
SPEC = importlib.util.spec_from_file_location('passive_wlan_session', SOURCE)
SESSION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SESSION)
RELEASE = '7.1.3-gemini-a53-wifi-phase-b-compile'
ROM_PATCHES = {
    'lib/firmware/mediatek/mt6797/ROMv3_patch_1_1_hdr.bin':
        '5732c0730380e937b48ad169f2805b65e8d4a178265566c5083cb2cc2d249f1e',
    'lib/firmware/mediatek/mt6797/ROMv3_patch_1_0_hdr.bin':
        '450c2b0949cf879217ac9aef81b18b860982f0e69340784b448b54365d8cf630',
}
RECORD_MEMBER = 'lib/firmware/mediatek/mt6797/WIFI.storage'
SOURCE_PINS = SESSION.SOURCE_PINS
load = SESSION.load
boot_uuid = SESSION.boot_uuid
classify = SESSION.classify
SESSION.HERE = HERE
SESSION.RELEASE = RELEASE
SESSION.SESSION.RELEASE = RELEASE


# Candidate 4 adds exactly one member to the parent RAM root: the reviewed
# static nl80211 connect helper, with iw's ownership and mode.
HELPER_MEMBER = 'bin/join-connect'
HELPER_SHA256 = 'b3851a4b1890e7abd9128174b2dfc2ea71f3f1a9119085751b6b087d8f54cbd6'
HELPER_BYTES = 665552
RAM_ROOT_MEMBERS = 62


def check_ram_root(members, record, userspace):
    """Require the candidate-4 RAM root: the parent's 61 members plus the helper.

    Release gate, ROM patches, pinned iw userspace, firmware and the private
    board record are checked as before; the helper's name, size, digest, mode,
    root ownership and single link are checked explicitly.
    """
    base = SESSION.SESSION
    base.require(len(members) == RAM_ROOT_MEMBERS and
                 all(name in members and base.digest(members[name].data) == digest and
                     members[name].mode == 0o100644 for name, digest in ROM_PATCHES.items()) and
                 all(base.digest(members[item['path']].data) == item['sha256'] and
                     len(members[item['path']].data) == item['bytes']
                     for item in userspace['files']) and RELEASE.encode() in members['init'].data and
                 base.digest(members[SESSION.FIRMWARE_MEMBER].data) ==
                 SESSION.FIRMWARE_SHA256 and RECORD_MEMBER in members and
                 members[RECORD_MEMBER].mode == 0o100600 and
                 members[RECORD_MEMBER].data == record,
                 'private RAM-root release, firmware or record changed')
    helper = members.get(HELPER_MEMBER)
    base.require(helper is not None and len(helper.data) == HELPER_BYTES and
                 base.digest(helper.data) == HELPER_SHA256 and helper.mode == 0o100755 and
                 helper.uid == 0 and helper.gid == 0 and helper.nlink == 1,
                 'reviewed join-connect helper absent or changed in the RAM root')


def prepare(candidate_dir, previous):
    base = SESSION.SESSION
    boot_uuid(previous)
    for name, expected in SOURCE_PINS.items():
        base.require(base.digest((base.BASELINE / name).read_bytes()) == expected,
                     'session source changed: ' + name)
    collector = load('wlan_collector', base.BASELINE / 'collect-baseline.py')
    collector.source_tools()
    legacy = load('wlan_observation', collector.HISTORICAL / 'classify_observation.py')
    legacy.RELEASE = RELEASE
    collector.source_tools = lambda: vars(legacy)
    steps = load('wlan_steps', base.BASELINE / 'session_steps.py')
    steps.RELEASE = RELEASE
    finish = load('wlan_finish', base.BASELINE / 'finish-baseline.py')
    candidate_dir = Path(os.path.abspath(candidate_dir))
    collector.directory(candidate_dir)
    receipt = json.loads((HERE / 'results/candidate-5.json').read_text())
    base.require(receipt['kernel_release'] == RELEASE and
                 receipt['physical_admission'] is False, 'candidate receipt changed')
    expected = receipt['files']
    base.require({p.name for p in candidate_dir.iterdir()} ==
                 set(expected) | {'candidate.json'}, 'candidate inventory changed')
    for name, identity in expected.items():
        data = collector.regular(candidate_dir / name, 16777216)
        base.require(len(data) == identity['bytes'] and
                     base.digest(data) == identity['sha256'],
                     'candidate file changed: ' + name)
    base.require(json.loads(collector.regular(candidate_dir / 'candidate.json', 65536)) ==
                 receipt, 'private candidate manifest changed')
    builder = runpy.run_path(str(base.SERVICE / 'build-a53-ram-candidate.py'))
    for path, expected_sha in builder['TOOLS'].items():
        base.require(base.digest(path.read_bytes()) == expected_sha,
                     'RAM parser dependency changed')
    parser = runpy.run_path(str(builder['BASELINE'] / 'scripts/build-candidate.py'))
    members = parser['parser_tools']()[0](collector.regular(candidate_dir / 'initramfs.img',
                                                            16777216))
    record_path = (Path(os.environ['GEMINI_PRIVATE_REPO']).resolve(strict=True) /
                   'artifacts/calibration-live-20261001/record-1/WIFI.storage')
    info = record_path.lstat()
    base.require(not record_path.is_symlink() and stat.S_ISREG(info.st_mode) and
                 stat.S_IMODE(info.st_mode) == 0o600 and info.st_nlink == 1,
                 'private record source changed')
    record = collector.regular(record_path, 514)
    userspace = json.loads((HERE.parent / '2026-10-01-mt6797-passive-scan/results/userspace.json').read_bytes())
    check_ram_root(members, record, userspace)
    candidate = {'files': {name: value['sha256'] for name, value in expected.items()},
                 'members': {name: {'sha256': base.digest(member.data),
                                    'size': len(member.data), 'mode': oct(member.mode)}
                             for name, member in members.items()}}
    context = {'candidate': candidate, 'recovery_id': previous,
               'admission': {'candidate_sha256': expected['boot.img']['sha256']}}
    return context, collector, steps, finish
