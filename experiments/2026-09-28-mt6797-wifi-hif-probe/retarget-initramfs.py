#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Retarget the validated reset-release RAM root to the HIF probe build."""

import importlib.util
from pathlib import Path


SOURCE = (Path(__file__).resolve().parents[2] /
          'experiments/2026-09-28-mt6797-wifi-firmware-probe/retarget-initramfs.py')
SPEC = importlib.util.spec_from_file_location('passive_wlan_ram_root', SOURCE)
RETARGET = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RETARGET)
RETARGET.PARENT_SHA256 = '5ae0c0fe388795475e3f3a4bf682d1cb09a847f53f089b8ad3e4115ba5264bf6'
RETARGET.OLD = b'7.1.3-gemini-a53-wifi-reset-release'
RETARGET.NEW = b'7.1.3-gemini-a53-wifi-hif-probe'


if __name__ == '__main__':
    RETARGET.main()
