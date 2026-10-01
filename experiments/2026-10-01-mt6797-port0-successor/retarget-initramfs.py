#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Change only the validated private RAM root's kernel-release gate."""

import importlib.util
from pathlib import Path


SOURCE = (Path(__file__).resolve().parent.parent /
          '2026-09-28-mt6797-wifi-firmware-probe/retarget-initramfs.py')
SPEC = importlib.util.spec_from_file_location('wlan_ram_root', SOURCE)
RETARGET = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RETARGET)
RETARGET.PARENT_SHA256 = 'e349faf905fb0b03ffb93cefe9270ad14da029da8eea4ee20fffda9b95b6cd00'
RETARGET.OLD = b'7.1.3-gemini-a53-wifi-port0-header'
RETARGET.NEW = b'7.1.3-gemini-a53-wifi-port0-successor'


if __name__ == '__main__':
    RETARGET.main()
