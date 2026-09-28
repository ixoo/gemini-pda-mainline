#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind the authenticated A53 collector to the private WLAN RAM root."""

import importlib.util
import json
import os
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / '2026-09-27-mt6797-consys-rails-passive/passive-session.py'
SPEC = importlib.util.spec_from_file_location('consys_rails_session', SOURCE)
SESSION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SESSION)
RELEASE = '7.1.3-gemini-a53-wifi-firmware-probe'
FIRMWARE_SHA256 = 'a69383d74d829430487c39eef6b5e281b25f901595c903a632a10aa8631426dd'
FIRMWARE_MEMBER = 'lib/firmware/mediatek/mt6797/WIFI_RAM_CODE_6797'
SOURCE_PINS = SESSION.SOURCE_PINS
load = SESSION.load
boot_uuid = SESSION.boot_uuid
classify = SESSION.classify
SESSION.RELEASE = RELEASE


def prepare(candidate_dir, previous):
    boot_uuid(previous)
    for name, expected in SOURCE_PINS.items():
        SESSION.require(SESSION.digest((SESSION.BASELINE / name).read_bytes()) == expected,
                        'session source changed: ' + name)
    collector = load('wlan_collector', SESSION.BASELINE / 'collect-baseline.py')
    collector.source_tools()
    legacy = load('wlan_observation', collector.HISTORICAL / 'classify_observation.py')
    legacy.RELEASE = RELEASE
    collector.source_tools = lambda: vars(legacy)
    steps = load('wlan_steps', SESSION.BASELINE / 'session_steps.py')
    steps.RELEASE = RELEASE
    finish = load('wlan_finish', SESSION.BASELINE / 'finish-baseline.py')
    candidate_dir = Path(os.path.abspath(candidate_dir))
    collector.directory(candidate_dir)
    receipt = json.loads((HERE / 'results/candidate.json').read_text())
    SESSION.require(receipt['kernel_release'] == RELEASE and
                    receipt['physical_admission'] is False,
                    'candidate receipt changed')
    expected = receipt['files']
    SESSION.require({p.name for p in candidate_dir.iterdir()} ==
                    set(expected) | {'candidate.json'}, 'candidate inventory changed')
    for name, identity in expected.items():
        data = collector.regular(candidate_dir / name, 16777216)
        SESSION.require(len(data) == identity['bytes'] and
                        SESSION.digest(data) == identity['sha256'],
                        'candidate file changed: ' + name)
    SESSION.require(json.loads(collector.regular(candidate_dir / 'candidate.json', 65536)) ==
                    receipt, 'private candidate manifest changed')
    builder = runpy.run_path(str(SESSION.SERVICE / 'build-a53-ram-candidate.py'))
    for path, expected_sha in builder['TOOLS'].items():
        SESSION.require(SESSION.digest(path.read_bytes()) == expected_sha,
                        'RAM parser dependency changed')
    parser = runpy.run_path(str(builder['BASELINE'] / 'scripts/build-candidate.py'))
    members = parser['parser_tools']()[0](collector.regular(candidate_dir / 'initramfs.img',
                                                            16777216))
    SESSION.require(len(members) == 52 and RELEASE.encode() in members['init'].data and
                    SESSION.digest(members[FIRMWARE_MEMBER].data) == FIRMWARE_SHA256,
                    'private RAM-root release or firmware changed')
    candidate = {'files': {name: value['sha256'] for name, value in expected.items()},
                 'members': {name: {'sha256': SESSION.digest(member.data),
                                    'size': len(member.data), 'mode': oct(member.mode)}
                             for name, member in members.items()}}
    context = {'candidate': candidate, 'recovery_id': previous,
               'admission': {'candidate_sha256': expected['boot.img']['sha256']}}
    return context, collector, steps, finish
