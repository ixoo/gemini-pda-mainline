#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Add the hash-pinned private WLAN image to the accepted A53 RAM root."""

from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import runpy
import stat


REPO = Path(__file__).resolve().parents[3]
PARENT = REPO / ('artifacts/consys-reset/'
                 'candidate-bfdd4ca0b6bcbbaaa26ddaad0794f84c86bd3acd6ef9044209e45db88da14507/'
                 'initramfs.img')
FIRMWARE = REPO / 'artifacts/firmware/gemian-2019-vendor/vendor/firmware/WIFI_RAM_CODE_6797'
OUTPUT = REPO / 'artifacts/firmware/mainline-wlan-initramfs'
MEMBER = 'lib/firmware/mediatek/mt6797/WIFI_RAM_CODE_6797'
PARENT_SHA256 = '62619d682e79ba5df929b055df0de8e48ed68412b358fe8f82d2368f924623b1'
FIRMWARE_SHA256 = 'a69383d74d829430487c39eef6b5e281b25f901595c903a632a10aa8631426dd'
PARSER = REPO / 'experiments/2026-07-25-emmc-development/scripts/validate-emmc-initramfs.py'
SERIALIZER = REPO / ('experiments/2026-08-14-mt6797-runtime-provenance-observer/'
                     'scripts/build-diagnostic-initramfs.py')
PARSER_SHA256 = '19c1c63df5f4732d3cae253a5b7edbb90d0ad609ed1ea411a200dc0060adba9c'
SERIALIZER_SHA256 = '0abe8a8b02ec3767c21fc018c69cc7e2db5ddb475a00e443247474a582f29f38'


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def regular(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or path.is_symlink():
        raise ValueError('input must be a single regular file')
    return path.read_bytes()


def main():
    os.umask(0o077)
    if sha256(regular(PARSER)) != PARSER_SHA256 or sha256(regular(SERIALIZER)) != SERIALIZER_SHA256:
        raise ValueError('archive tools changed')
    parent = regular(PARENT)
    firmware = regular(FIRMWARE)
    if sha256(parent) != PARENT_SHA256 or sha256(firmware) != FIRMWARE_SHA256:
        raise ValueError('parent or firmware identity changed')
    if len(firmware) != 411632:
        raise ValueError('firmware length changed')

    parse = runpy.run_path(str(PARSER))['parse_newc']
    encode = runpy.run_path(str(SERIALIZER))['encode_newc']
    inherited = parse(parent)
    members = dict(inherited)
    for name in ('lib', 'lib/firmware', 'lib/firmware/mediatek',
                 'lib/firmware/mediatek/mt6797'):
        if name in members:
            raise ValueError('firmware directory already exists')
        members[name] = replace(inherited['etc'], mode=stat.S_IFDIR | 0o755, data=b'')
    if MEMBER in members:
        raise ValueError('firmware member already exists')
    members[MEMBER] = replace(inherited['etc/passwd'], mode=stat.S_IFREG | 0o644,
                              data=firmware)
    image = encode(members)
    parsed = parse(image)
    if len(image) >= 16777216 or parsed != members or encode(parsed) != image:
        raise ValueError('archive round trip or size failed')
    for name, value in inherited.items():
        if parsed[name] != value:
            raise ValueError('inherited RAM-root member changed')

    if OUTPUT.exists() or OUTPUT.is_symlink():
        raise ValueError('private output already exists')
    OUTPUT.mkdir(mode=0o700)
    with (OUTPUT / 'initramfs.img').open('xb') as stream:
        stream.write(image)
    receipt = {
        'status': 'private-firmware-initramfs-staged-no-device-action',
        'parent_initramfs_sha256': PARENT_SHA256,
        'firmware_sha256': FIRMWARE_SHA256,
        'firmware_bytes': len(firmware),
        'firmware_member': MEMBER,
        'inherited_members': len(inherited),
        'added_members': len(members) - len(inherited),
        'output_initramfs_sha256': sha256(image),
        'output_bytes': len(image),
        'secret_bearing': True,
        'physical_admission': False,
    }
    with (OUTPUT / 'receipt.json').open('x') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(json.dumps(receipt, sort_keys=True))


if __name__ == '__main__':
    main()
