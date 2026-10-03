#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind the authenticated A53 session to the passive-scan RAM root."""

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
RELEASE = '7.1.3-gemini-a53-wifi-scan-pool-sample'
RECORD_MEMBER = 'lib/firmware/mediatek/mt6797/WIFI.storage'
SOURCE_PINS = SESSION.SOURCE_PINS
load = SESSION.load
boot_uuid = SESSION.boot_uuid
classify = SESSION.classify
SESSION.HERE = HERE
SESSION.RELEASE = RELEASE
SESSION.SESSION.RELEASE = RELEASE


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
    receipt = json.loads((HERE / 'results/candidate.json').read_text())
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
    base.require(len(members) == 59 and
                 all(base.digest(members[item['path']].data) == item['sha256'] and
                     len(members[item['path']].data) == item['bytes']
                     for item in userspace['files']) and RELEASE.encode() in members['init'].data and
                 base.digest(members[SESSION.FIRMWARE_MEMBER].data) ==
                 SESSION.FIRMWARE_SHA256 and RECORD_MEMBER in members and
                 members[RECORD_MEMBER].mode == 0o100600 and
                 members[RECORD_MEMBER].data == record,
                 'private RAM-root release, firmware or record changed')
    candidate = {'files': {name: value['sha256'] for name, value in expected.items()},
                 'members': {name: {'sha256': base.digest(member.data),
                                    'size': len(member.data), 'mode': oct(member.mode)}
                             for name, member in members.items()}}
    context = {'candidate': candidate, 'recovery_id': previous,
               'admission': {'candidate_sha256': expected['boot.img']['sha256']}}
    return context, collector, steps, finish
