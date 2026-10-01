#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Retarget the validated capability-port0 RAM root to the port-0 header release."""

import importlib.util
from pathlib import Path


SOURCE = (Path(__file__).resolve().parent.parent /
          '2026-09-28-mt6797-wifi-firmware-probe/retarget-initramfs.py')
SPEC = importlib.util.spec_from_file_location('wlan_ram_root', SOURCE)
RETARGET = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RETARGET)
RETARGET.PARENT_SHA256 = 'e77410c8135ac62f95c15b7bd5c69367821dfd1e06dcc20ac1effbe26cab5e33'
RETARGET.OLD = b'7.1.3-gemini-a53-wifi-capability-port0'
RETARGET.NEW = b'7.1.3-gemini-a53-wifi-port0-header'


if __name__ == '__main__':
    RETARGET.main()
