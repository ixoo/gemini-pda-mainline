#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Retarget the validated WMT RAM root to the deferred-start release."""

import importlib.util
from pathlib import Path


SOURCE = (Path(__file__).resolve().parent.parent /
          '2026-09-29-mt6797-region19-private-export/retarget-initramfs.py')
SPEC = importlib.util.spec_from_file_location('region19_export_ram_root', SOURCE)
RETARGET = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RETARGET)
RETARGET.RETARGET.PARENT_SHA256 = '0b76f1a3289cad8726b13184ef6fc4b90a87932a5c86eed156122242567e63f0'
RETARGET.RETARGET.OLD = b'7.1.3-gemini-a53-wifi-region19-wmtmem'
RETARGET.RETARGET.NEW = b'7.1.3-gemini-a53-wifi-wmt-start'


if __name__ == '__main__':
    RETARGET.RETARGET.main()
