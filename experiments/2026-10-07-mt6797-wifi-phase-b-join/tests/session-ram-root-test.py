#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""passive-session.py admits exactly the candidate-4 RAM root shape.

Loads the Phase B session module with a throwaway private root and drives its
production check_ram_root() with a synthetic 62-member RAM root built by the
inherited newc tools: the parent's pinned members (digests substituted into the
module's own pins for the synthetic data) plus bin/join-connect with the real
pinned size, digest, mode 0100755, root ownership and one link. The parent's
61-member shape, which refused the real candidate 4 offline, is refused; so is
a helper with another size, digest, mode, owner or link count, or 63 members.
No device action.
"""
import hashlib
import importlib.util
import os
import runpy
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parents[1]
REPO = HERE.parents[1]
validator = runpy.run_path(str(REPO / 'experiments/2026-07-25-emmc-development/scripts/validate-emmc-initramfs.py'))
Member = validator['Member']

with tempfile.TemporaryDirectory(prefix='mt6797-session-ram-root-') as directory:
    work = Path(directory)
    (work / 'private/artifacts/credentials').mkdir(parents=True)
    (work / 'runtime').mkdir()
    bound = work / 'bound.sh'
    bound.write_bytes(b'TARGET_SSID=x\n' + (HERE / 'join-once.sh').read_bytes()); bound.chmod(0o600)
    os.environ.update(GEMINI_PRIVATE_REPO=str(work / 'private'), GEMINI_RUNTIME_ROOT=str(work / 'runtime'),
                      GEMINI_JOIN_SCRIPT=str(bound))
    spec = importlib.util.spec_from_file_location('phase_b_session', HERE / 'passive-session.py')
    session = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(session)
    assert session.RAM_ROOT_MEMBERS == 62 and session.HELPER_MEMBER == 'bin/join-connect'
    assert session.HELPER_BYTES == 665552
    assert session.HELPER_SHA256 == 'bc499f28bc052a24713ead3175e5b6405e2e5f787acf276e4e82c1278241d5ca'
    composer = HERE / 'build-candidate.py'
    assert session.HELPER_SHA256 in composer.read_text() and (session.HELPER_SHA256 + '  bin/join-connect') in (HERE / 'join-once.sh').read_text()
    digest = lambda b: hashlib.sha256(b).hexdigest()

    def member(data, mode=0o100644, uid=0, gid=0, nlink=1):
        return Member(mode=mode, uid=uid, gid=gid, nlink=nlink, mtime=0, devmajor=0, devminor=0,
                      rdevmajor=0, rdevminor=0, data=data)

    # Synthetic parent: substitute the module's pins with the synthetic digests.
    rom = {name: b'rom:' + name.encode() for name in session.ROM_PATCHES}
    session.ROM_PATCHES = {name: digest(data) for name, data in rom.items()}
    userspace = {'files': [{'path': 'bin/iw', 'sha256': digest(b'iw'), 'bytes': 2},
                           {'path': 'lib/libc.so.6', 'sha256': digest(b'libc'), 'bytes': 4}]}
    session.SESSION.FIRMWARE_MEMBER = 'lib/firmware/mediatek/mt6797/WIFI_RAM_CODE'
    session.SESSION.FIRMWARE_SHA256 = digest(b'firmware')
    record = b'R' * 514
    members = {'init': member(b'#!/bin/sh\n' + session.RELEASE.encode() + b'\n', 0o100755),
               'bin/iw': member(b'iw', 0o100755), 'lib/libc.so.6': member(b'libc'),
               session.SESSION.FIRMWARE_MEMBER: member(b'firmware'),
               session.RECORD_MEMBER: member(record, 0o100600)}
    for name, data in rom.items():
        members[name] = member(data)
    index = 0
    while len(members) < 61:
        members['etc/pad-%02d' % index] = member(b'pad'); index += 1
    assert len(members) == 61
    helper_data = bytes([0x7f, ord('E'), ord('L'), ord('F')]) + bytes(session.HELPER_BYTES - 4)
    session.HELPER_SHA256 = digest(helper_data)  # synthetic helper bytes with the pinned size
    good = dict(members); good['bin/join-connect'] = member(helper_data, 0o100755)
    # Runtime 13's committed receipt declares the supplicant: the 62-member
    # candidate-4 shape is refused until the pinned member is present.
    assert session.SUPPLICANT_REQUIRED is True
    try:
        session.check_ram_root(good, record, userspace)
    except ValueError:
        pass
    else:
        raise AssertionError('62 members admitted although the receipt declares the supplicant')
    session.SUPPLICANT_REQUIRED = False
    session.check_ram_root(good, record, userspace)  # candidate-4 shape admitted

    def refused(bad):
        try:
            session.check_ram_root(bad, record, userspace)
        except ValueError:
            return True
        return False
    assert refused(members), 'the 61-member parent shape must be refused'
    assert refused(dict(good, **{'etc/extra': member(b'x')})), '63 members with a foreign member refused'
    # Phase C2: the pinned supplicant as the 63rd member is admitted; any variant refused.
    supplicant_data = bytes([0x7f, ord('E'), ord('L'), ord('F')]) + bytes(session.SUPPLICANT_BYTES - 4)
    session.SUPPLICANT_SHA256 = digest(supplicant_data)
    with_supplicant = dict(good); with_supplicant['bin/wpa_supplicant'] = member(supplicant_data, 0o100755)
    session.check_ram_root(with_supplicant, record, userspace)
    session.SUPPLICANT_REQUIRED = True
    session.check_ram_root(with_supplicant, record, userspace)
    assert refused(good), '62 members refused when the receipt declares the supplicant'
    for variant in (member(supplicant_data[:-1], 0o100755), member(supplicant_data, 0o100644),
                    member(supplicant_data, 0o100755, uid=1000), member(supplicant_data, 0o100755, nlink=2)):
        assert refused(dict(good, **{'bin/wpa_supplicant': variant})), 'supplicant variant refused'
    assert refused(dict(with_supplicant, **{'etc/extra': member(b'x')})), '64 members refused'
    for variant in (member(helper_data[:-1], 0o100755), member(helper_data + b'\0', 0o100755),
                    member(b'Z' + helper_data[1:], 0o100755), member(helper_data, 0o100644),
                    member(helper_data, 0o100755, uid=1000), member(helper_data, 0o100755, gid=1000),
                    member(helper_data, 0o100755, nlink=2)):
        assert refused(dict(good, **{'bin/join-connect': variant})), variant.mode
    assert refused({**good, 'init': member(b'#!/bin/sh\n', 0o100755)}), 'release gate kept'
    assert refused({**good, session.RECORD_MEMBER: member(record, 0o100644)}), 'record mode kept'
print('session RAM root: PASS (62 members with the pinned helper admitted only when no supplicant is declared, 63 with the pinned supplicant admitted; parent shape, helper and supplicant variants refused; release/firmware/record guards kept)')
