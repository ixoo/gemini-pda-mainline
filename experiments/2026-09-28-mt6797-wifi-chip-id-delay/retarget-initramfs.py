#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Retarget the validated chip-ID RAM root to the delayed-ID release."""

import importlib.util
from pathlib import Path


SOURCE = (Path(__file__).resolve().parents[2] /
          'experiments/2026-09-28-mt6797-wifi-power-probe/retarget-initramfs.py')
SPEC = importlib.util.spec_from_file_location('power_probe_ram_root', SOURCE)
POWER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(POWER)
POWER.RETARGET.PARENT_SHA256 = '1db518186d666c170625c9c53fee304bb742d32fcb44c3ade72252acce47e579'
POWER.RETARGET.OLD = b'7.1.3-gemini-a53-wifi-chip-id-probe'
POWER.RETARGET.NEW = b'7.1.3-gemini-a53-wifi-chip-id-delay'


if __name__ == '__main__':
    POWER.RETARGET.main()
