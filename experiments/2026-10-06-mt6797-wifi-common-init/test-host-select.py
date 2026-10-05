#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Phase A host: release overrides and scan selection, offline."""

import importlib.util
import os
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
with tempfile.TemporaryDirectory() as private:
    os.environ['GEMINI_PRIVATE_REPO'] = private
    spec = importlib.util.spec_from_file_location('phase_a_host', HERE / 'passive-host.py')
    host = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(host)

release = '7.1.3-gemini-a53-wifi-phase-a'
assert host.HOST.DOMAIN.RELEASE == release and host.SCAN.RELEASE == release
assert release.encode() in host.SCAN.PARENT.WIPHY_PROBE
assert b'scan-tuning-sample' not in host.SCAN.PARENT.WIPHY_PROBE
assert host.SCAN.SCAN_SOURCE == HERE / 'phase-a-scan.sh'
assert (b'[ "$kernel" = ' + release.encode() + b' ]') in host.SCAN.SCAN_SOURCE.read_bytes()
for level in (host.SCAN.PARENT, host.HOST, host.HOST.DOMAIN, host.HOST.DOMAIN.HOST):
    assert level.HERE == HERE, level
for level in (host.SCAN, host.SCAN.PARENT, host.HOST, host.HOST.DOMAIN, host.HOST.DOMAIN.HOST):
    assert level.ROOT.parent.name == 'wifi-phase-a', level
for level in (host.SCAN, host.SCAN.PARENT, host.HOST):
    assert level.CAPTURE.name == 'capture-1' and level.CAPTURE.parent.name == 'wifi-phase-a'
# Ready: the scan-injecting prepare. Not ready: the wiphy-probe prepare only.
assert host.select_prepare(True) is host.SCAN.prepare
assert host.select_prepare(False) is host.SCAN.PREPARE
assert host.SCAN.PREPARE.__name__ == 'prepare_with_wiphy'
print('phase-a host: release and path overrides at every level; scan only when ready')
