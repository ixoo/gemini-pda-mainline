#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Retarget the validated private RAM root to the WMT-memory release."""

import importlib.util
from pathlib import Path


SOURCE = (Path(__file__).resolve().parent.parent /
          '2026-09-29-mt6797-region19-private-export/retarget-initramfs.py')
SPEC = importlib.util.spec_from_file_location('region19_export_ram_root', SOURCE)
RETARGET = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RETARGET)
RETARGET.RETARGET.PARENT_SHA256 = 'a5cd9bb770875dda3073e5068207eb7ba07531fd1f35d4c26736f15b3820cb37'
RETARGET.RETARGET.OLD = b'7.1.3-gemini-a53-wifi-region19-export'
RETARGET.RETARGET.NEW = b'7.1.3-gemini-a53-wifi-region19-wmtmem'


if __name__ == '__main__':
    RETARGET.RETARGET.main()
