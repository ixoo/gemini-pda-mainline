#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Retarget the validated capability-admit RAM root to the port-0 release."""

import importlib.util
from pathlib import Path


SOURCE = (Path(__file__).resolve().parent.parent /
          '2026-09-28-mt6797-wifi-firmware-probe/retarget-initramfs.py')
SPEC = importlib.util.spec_from_file_location('wlan_ram_root', SOURCE)
RETARGET = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RETARGET)
RETARGET.PARENT_SHA256 = 'a701a2d42568744bac1b42eb479920b961c09fdbd52b996972737cd561b93cfc'
RETARGET.OLD = b'7.1.3-gemini-a53-wifi-capability-admit'
RETARGET.NEW = b'7.1.3-gemini-a53-wifi-capability-port0'


if __name__ == '__main__':
    RETARGET.main()
