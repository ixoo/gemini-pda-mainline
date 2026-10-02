#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reuse the pinned private RAM-root transform with the broadcast-scan release gate."""

import hashlib
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / '2026-10-01-mt6797-passive-scan/retarget-initramfs.py'
SOURCE_SHA256 = '0ced8187e5778815b1f81120055efd7774957bc676423a595a6ab44bea64266b'


def main():
    if SOURCE.is_symlink() or hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError('parent RAM-root transform changed')
    transform = runpy.run_path(str(SOURCE))['main']
    transform.__globals__['NEW'] = b'7.1.3-gemini-a53-wifi-passive-scan-dwell'
    transform()


if __name__ == '__main__':
    main()
