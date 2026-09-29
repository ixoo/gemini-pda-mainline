#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Retarget the validated EMI-copy RAM root to the firmware-start release."""

import importlib.util
from pathlib import Path


SOURCE = (Path(__file__).resolve().parents[2] /
          'experiments/2026-09-28-mt6797-wifi-firmware-probe/retarget-initramfs.py')
SPEC = importlib.util.spec_from_file_location('passive_wlan_ram_root', SOURCE)
RETARGET = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RETARGET)
RETARGET.PARENT_SHA256 = '557ed0996f7843b26d1bee00d001333fab435ac5ce87869a601d5bdf3edda7fb'
RETARGET.OLD = b'7.1.3-gemini-a53-wifi-emi-copy-probe'
RETARGET.NEW = b'7.1.3-gemini-a53-wifi-firmware-start-probe'


if __name__ == '__main__':
    RETARGET.main()
