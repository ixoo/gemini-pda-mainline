#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Retarget the validated private WLAN RAM root to the chip-ID release."""

import importlib.util
from pathlib import Path


SOURCE = (Path(__file__).resolve().parents[2] /
          'experiments/2026-09-28-mt6797-wifi-power-probe/retarget-initramfs.py')
SPEC = importlib.util.spec_from_file_location('power_probe_ram_root', SOURCE)
POWER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(POWER)
POWER.RETARGET.PARENT_SHA256 = '53edd8fb924cd72d63f9edde81463aebd5313bfc556f5e0a35a34f93c9683b0d'
POWER.RETARGET.OLD = b'7.1.3-gemini-a53-wifi-power-probe'
POWER.RETARGET.NEW = b'7.1.3-gemini-a53-wifi-chip-id-probe'


if __name__ == '__main__':
    POWER.RETARGET.main()
