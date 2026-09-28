#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Retarget the validated private WLAN RAM root to the power-probe release."""

import importlib.util
from pathlib import Path


SOURCE = (Path(__file__).resolve().parents[2] /
          'experiments/2026-09-28-mt6797-wifi-firmware-probe/retarget-initramfs.py')
SPEC = importlib.util.spec_from_file_location('passive_wlan_ram_root', SOURCE)
RETARGET = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RETARGET)
RETARGET.PARENT_SHA256 = 'b4fc6ec679d9a8beb0678244354ae078c628e8c3ea6f68649234dfc237db2367'
RETARGET.OLD = b'7.1.3-gemini-a53-wifi-firmware-probe'
RETARGET.NEW = b'7.1.3-gemini-a53-wifi-power-probe'


if __name__ == '__main__':
    RETARGET.main()
