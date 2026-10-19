#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""S1 guarded skip-if-matching installation: exact GTK8 image, fresh custody."""
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('s1_gtk8_installer', HERE / 'install-ccmp-gtk8.py')
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)
INSTALLER = BASE.INSTALLER
ADAPTER = BASE.ADAPTER
PREDECESSOR_SHA = 'ffbb0d343aa7061e1c592488ee6ee92786cc70abe7a6f9008ca1f4a17cce2dff'
MANIFEST_SHA = BASE.MANIFEST_SHA
ADAPTER.PREDECESSOR_SHA = PREDECESSOR_SHA
INSTALLER.TOOL_NAME = 'install-ccmp-core-disconnect.py'
INSTALLER.RECEIPT_NAME = 'mt6797-wifi-ccmp-stable-monitor-deployment-gtk8-s1'
validate = BASE.validate
sources = BASE.sources
ORIGINAL_SOURCES = BASE.ORIGINAL_SOURCES
receipt = BASE.receipt

if __name__ == '__main__':
    INSTALLER.main()
