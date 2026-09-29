#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind the authenticated A53 session to the firmware-start image."""

import importlib.util
from pathlib import Path


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / '2026-09-28-mt6797-wifi-firmware-probe/passive-session.py'
SPEC = importlib.util.spec_from_file_location('passive_wlan_session', SOURCE)
SESSION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SESSION)
SESSION.HERE = HERE
SESSION.RELEASE = '7.1.3-gemini-a53-wifi-firmware-start-probe'
SESSION.SESSION.RELEASE = SESSION.RELEASE
SOURCE_PINS = SESSION.SOURCE_PINS
load = SESSION.load
boot_uuid = SESSION.boot_uuid
prepare = SESSION.prepare
classify = SESSION.classify
