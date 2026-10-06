#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind a private owner AP input to the reviewed join script without printing it."""

import argparse
import json
import os
from pathlib import Path
import re
import shlex
import stat


def bind(target, source):
    info = target.lstat()
    if (not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600 or
            info.st_nlink != 1 or info.st_size > 4096):
        raise ValueError('private target must be one small mode-0600 regular file')
    value = json.loads(target.read_bytes())
    ssid, bssid = value['ssid'], value['bssid']
    if (not isinstance(ssid, str) or not 1 <= len(ssid.encode()) <= 32 or
            any(ord(c) < 32 or ord(c) == 127 for c in ssid) or
            not isinstance(bssid, str) or
            not re.fullmatch(r'[0-9a-f]{2}(?::[0-9a-f]{2}){5}', bssid) or
            int(bssid[:2], 16) & 1 or bssid == '00:00:00:00:00:00' or
            value['frequency_mhz'] != 5200 or value['channel'] != 40):
        raise ValueError('private target is outside the fixed legacy channel-40 scope')
    if source.is_symlink() or not source.is_file() or source.stat().st_size > 16384:
        raise ValueError('join script source changed')
    prefix = ('TARGET_SSID=' + shlex.quote(ssid) + '\nTARGET_BSSID=' +
              shlex.quote(bssid) + '\nexport TARGET_SSID TARGET_BSSID\n').encode()
    return prefix + source.read_bytes()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    data = bind(args.target, Path(__file__).with_name('join-once.sh'))
    # New ignored private output only; never replace an existing test input.
    with args.output.open('xb') as stream:
        stream.write(data)
    args.output.chmod(0o600)
    print('private-target-bound=1; device_action=none')


if __name__ == '__main__':
    main()
