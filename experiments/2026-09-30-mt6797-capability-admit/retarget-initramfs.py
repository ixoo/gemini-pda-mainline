#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Retarget the validated capability-trace RAM root to the admission release."""

import importlib.util
from pathlib import Path


SOURCE = (Path(__file__).resolve().parent.parent /
          '2026-09-28-mt6797-wifi-firmware-probe/retarget-initramfs.py')
SPEC = importlib.util.spec_from_file_location('wlan_ram_root', SOURCE)
RETARGET = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RETARGET)
RETARGET.PARENT_SHA256 = '29cfa7a5d99cb2ffa7336f718832c56f69cdf61d6cf2cb80acf383a4151f0673'
RETARGET.OLD = b'7.1.3-gemini-a53-wifi-capability-trace'
RETARGET.NEW = b'7.1.3-gemini-a53-wifi-capability-admit'


if __name__ == '__main__':
    RETARGET.main()
