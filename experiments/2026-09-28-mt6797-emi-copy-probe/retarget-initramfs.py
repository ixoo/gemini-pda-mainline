#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Retarget the validated EMI-set RAM root to the EMI-copy release."""

import importlib.util
from pathlib import Path


SOURCE = (Path(__file__).resolve().parents[2] /
          'experiments/2026-09-28-mt6797-wifi-firmware-probe/retarget-initramfs.py')
SPEC = importlib.util.spec_from_file_location('passive_wlan_ram_root', SOURCE)
RETARGET = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RETARGET)
RETARGET.PARENT_SHA256 = 'be97b760b9e086b184b4bb754fe11b8f8c03cc1edc9c84fc6cafad0f75abff98'
RETARGET.OLD = b'7.1.3-gemini-a53-wifi-emi-set-probe'
RETARGET.NEW = b'7.1.3-gemini-a53-wifi-emi-copy-probe'


if __name__ == '__main__':
    RETARGET.main()
