#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Use the reviewed passive CONSYS session with this reset-handle candidate."""

import importlib.util
from pathlib import Path


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / '2026-09-27-mt6797-consys-rails-passive/passive-session.py'
SPEC = importlib.util.spec_from_file_location('consys_rails_session', SOURCE)
SESSION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SESSION)
SESSION.HERE = HERE
SOURCE_PINS = SESSION.SOURCE_PINS
load = SESSION.load
boot_uuid = SESSION.boot_uuid
prepare = SESSION.prepare
classify = SESSION.classify
