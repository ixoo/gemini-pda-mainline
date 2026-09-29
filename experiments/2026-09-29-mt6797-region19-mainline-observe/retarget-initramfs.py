#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Retarget the validated firmware-start RAM root to the passive release."""

import importlib.util
from pathlib import Path


SOURCE = (Path(__file__).resolve().parents[2] /
          'experiments/2026-09-28-mt6797-wifi-firmware-probe/retarget-initramfs.py')
SPEC = importlib.util.spec_from_file_location('passive_wlan_ram_root', SOURCE)
RETARGET = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RETARGET)
RETARGET.PARENT_SHA256 = '2f3753f50e6c82fd8b2b48baa61302ecd23e14bcf92dacb7e307a92a4b66473c'
RETARGET.OLD = b'7.1.3-gemini-a53-wifi-firmware-start-probe'
RETARGET.NEW = b'7.1.3-gemini-a53-wifi-region19-observe'


if __name__ == '__main__':
    RETARGET.main()
