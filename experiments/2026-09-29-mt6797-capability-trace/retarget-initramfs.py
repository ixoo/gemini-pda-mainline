#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Retarget the validated WMT-start RAM root to the capability probe release."""

import importlib.util
from pathlib import Path


SOURCE = (Path(__file__).resolve().parent.parent /
          '2026-09-28-mt6797-wifi-firmware-probe/retarget-initramfs.py')
SPEC = importlib.util.spec_from_file_location('wlan_ram_root', SOURCE)
RETARGET = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RETARGET)
RETARGET.PARENT_SHA256 = '9802557c5b7201fb9921b6ec0b1a60e45fffbcb97735ae47eb8bb5956784f3c2'
RETARGET.OLD = b'7.1.3-gemini-a53-wifi-wmt-start'
RETARGET.NEW = b'7.1.3-gemini-a53-wifi-capability-trace'


if __name__ == '__main__':
    RETARGET.main()
