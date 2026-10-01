#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Add the private board record and retarget one hash-pinned RAM root."""

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
PARENT_SHA256 = 'ca3d874c546601418ec7700d7b06480657556a11697fee4a6c704dd93f38c3c7'
FIRMWARE_SHA256 = 'a69383d74d829430487c39eef6b5e281b25f901595c903a632a10aa8631426dd'
OLD = b'7.1.3-gemini-a53-wifi-port0-successor'
NEW = b'7.1.3-gemini-a53-wifi-record-runtime'
FIRMWARE_MEMBER = 'lib/firmware/mediatek/mt6797/WIFI_RAM_CODE_6797'
RECORD_MEMBER = 'lib/firmware/mediatek/mt6797/WIFI.storage'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def regular(path, private=False):
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError('input must be a single regular file')
    if private and stat.S_IMODE(info.st_mode) != 0o600:
        raise ValueError('private record must have mode 0600')
    return path.read_bytes()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parent', required=True, type=Path)
    parser.add_argument('--record', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    if sha(regular(PARSER)) != PARSER_SHA256 or sha(regular(SERIALIZER)) != SERIALIZER_SHA256:
        raise ValueError('RAM archive tools changed')
    parent = regular(args.parent)
    if sha(parent) != PARENT_SHA256:
        raise ValueError('private parent RAM root changed')
    record = regular(args.record, private=True)
    if len(record) != 514 or record[512] != 0xaa:
        raise ValueError('private record shape changed')
    check = 0
    for index, value in enumerate(record[:512]):
        check = (check ^ value if index & 1 else check + value) & 0xff
    if check != record[513]:
        raise ValueError('private record trailer changed')
    parse = runpy.run_path(str(PARSER))['parse_newc']
    encode = runpy.run_path(str(SERIALIZER))['encode_newc']
    inherited = parse(parent)
    if len(inherited) != 52 or sha(inherited[FIRMWARE_MEMBER].data) != FIRMWARE_SHA256 or RECORD_MEMBER in inherited:
        raise ValueError('parent RAM root member inventory changed')
    init = inherited['init'].data
    if init.count(OLD) != 1 or NEW in init:
        raise ValueError('kernel release gate changed')
    members = dict(inherited)
    members['init'] = replace(inherited['init'], data=init.replace(OLD, NEW))
    members[RECORD_MEMBER] = replace(inherited[FIRMWARE_MEMBER],
                                     mode=stat.S_IFREG | 0o600, data=record)
    image = encode(members)
    parsed = parse(image)
    if parsed != members or encode(parsed) != image or len(parsed) != 53 or len(image) >= 16777216:
        raise ValueError('RAM root round trip or size failed')
    if any(parsed[name] != original for name, original in inherited.items() if name != 'init'):
        raise ValueError('unrelated RAM member changed')
    output = args.output.absolute()
    if not output.parent.is_dir() or output.exists() or output.is_symlink():
        raise ValueError('output occupied')
    output.write_bytes(image)
    print(json.dumps({'status': 'private-record-ram-root-prepared-no-device-action',
                      'parent_initramfs_sha256': PARENT_SHA256,
                      'output_initramfs_sha256': sha(image),
                      'output_bytes': len(image), 'member_count': len(parsed),
                      'changed_members': ['init', RECORD_MEMBER],
                      'secret_bearing': True, 'device_action': 'none'}, sort_keys=True))


if __name__ == '__main__':
    main()
