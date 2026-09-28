#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Retarget the hash-pinned private WLAN RAM root to this kernel release."""

import argparse
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import runpy
import stat

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PARSER = REPO / 'experiments/2026-07-25-emmc-development/scripts/validate-emmc-initramfs.py'
SERIALIZER = REPO / 'experiments/2026-08-14-mt6797-runtime-provenance-observer/scripts/build-diagnostic-initramfs.py'
PARSER_SHA256 = '19c1c63df5f4732d3cae253a5b7edbb90d0ad609ed1ea411a200dc0060adba9c'
SERIALIZER_SHA256 = '0abe8a8b02ec3767c21fc018c69cc7e2db5ddb475a00e443247474a582f29f38'
PARENT_SHA256 = 'd023fd7048189deed63c72346a9b0014cc3efbe3204458f787e6c2588ff31a73'
FIRMWARE_SHA256 = 'a69383d74d829430487c39eef6b5e281b25f901595c903a632a10aa8631426dd'
OLD = b'7.1.3-gemini-a53-consys-owner-passive'
NEW = b'7.1.3-gemini-a53-wifi-firmware-probe'
MEMBER = 'lib/firmware/mediatek/mt6797/WIFI_RAM_CODE_6797'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def regular(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or path.is_symlink():
        raise ValueError('input must be a single regular file')
    return path.read_bytes()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parent', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    if sha(regular(PARSER)) != PARSER_SHA256 or sha(regular(SERIALIZER)) != SERIALIZER_SHA256:
        raise ValueError('RAM archive tools changed')
    parent = regular(args.parent)
    if sha(parent) != PARENT_SHA256:
        raise ValueError('private parent changed')
    parse = runpy.run_path(str(PARSER))['parse_newc']
    encode = runpy.run_path(str(SERIALIZER))['encode_newc']
    inherited = parse(parent)
    if len(inherited) != 52 or sha(inherited[MEMBER].data) != FIRMWARE_SHA256:
        raise ValueError('firmware archive changed')
    init = inherited['init'].data
    if init.count(OLD) != 1 or NEW in init:
        raise ValueError('init release gate changed')
    members = dict(inherited)
    members['init'] = replace(inherited['init'], data=init.replace(OLD, NEW))
    image = encode(members)
    parsed = parse(image)
    if parsed != members or encode(parsed) != image or len(image) >= 16777216:
        raise ValueError('RAM archive round trip or size failed')
    if any(parsed[name] != original for name, original in inherited.items() if name != 'init'):
        raise ValueError('unrelated RAM member changed')
    if parsed['init'].data.count(NEW) != 1 or OLD in parsed['init'].data:
        raise ValueError('release gate readback changed')
    output = args.output.absolute()
    if not output.parent.is_dir() or output.exists() or output.is_symlink():
        raise ValueError('output occupied')
    output.write_bytes(image)
    receipt = {'status': 'private-wlan-initramfs-retargeted-no-device-action',
               'parent_initramfs_sha256': PARENT_SHA256,
               'firmware_sha256': FIRMWARE_SHA256,
               'changed_member': 'init',
               'old_release': OLD.decode(), 'new_release': NEW.decode(),
               'member_count': len(parsed),
               'output_initramfs_sha256': sha(image), 'output_bytes': len(image),
               'secret_bearing': True, 'device_action': 'none'}
    print(json.dumps(receipt, sort_keys=True))


if __name__ == '__main__':
    main()
