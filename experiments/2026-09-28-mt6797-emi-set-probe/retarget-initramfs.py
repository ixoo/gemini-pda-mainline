#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Retarget the validated HIF RAM root to the EMI set probe build."""

import importlib.util
from pathlib import Path


SOURCE = (Path(__file__).resolve().parents[2] /
          'experiments/2026-09-28-mt6797-wifi-firmware-probe/retarget-initramfs.py')
SPEC = importlib.util.spec_from_file_location('passive_wlan_ram_root', SOURCE)
RETARGET = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RETARGET)
RETARGET.PARENT_SHA256 = '3ff87f9405b8dde5f09a61419845337903251e3dc34efa7b21e60d5b7551d4c4'
RETARGET.OLD = b'7.1.3-gemini-a53-wifi-hif-probe'
RETARGET.NEW = b'7.1.3-gemini-a53-wifi-emi-set-probe'


if __name__ == '__main__':
    RETARGET.main()
