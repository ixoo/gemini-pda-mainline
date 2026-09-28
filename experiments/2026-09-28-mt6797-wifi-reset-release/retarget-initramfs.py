#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Retarget the validated powered-EMI RAM root to the reset-release build."""

import importlib.util
from pathlib import Path


SOURCE = (Path(__file__).resolve().parents[2] /
          'experiments/2026-09-28-mt6797-wifi-firmware-probe/retarget-initramfs.py')
SPEC = importlib.util.spec_from_file_location('passive_wlan_ram_root', SOURCE)
RETARGET = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RETARGET)
RETARGET.PARENT_SHA256 = '27cfdf4c91b872fbdf8f6587659d0efa8f9aa379bdc6e5dc87dedb1aa154410b'
RETARGET.OLD = b'7.1.3-gemini-a53-wifi-powered-emi'
RETARGET.NEW = b'7.1.3-gemini-a53-wifi-reset-release'


if __name__ == '__main__':
    RETARGET.main()
