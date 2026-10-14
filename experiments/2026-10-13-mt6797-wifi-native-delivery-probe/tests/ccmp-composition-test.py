#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Focused config oracle for the CCMP compositor; no private RAM or device."""
import hashlib
import json
from pathlib import Path
import runpy
import sys

HERE = Path(__file__).resolve().parent.parent
M = runpy.run_path(str(HERE / 'build-ccmp-candidate.py'))
N = runpy.run_path(str(HERE / 'build-native-candidate-2.py'))
old = Path(sys.argv[1]).read_bytes()  # actual immutable ND6 kernel.config
new = Path(sys.argv[2]).read_bytes()  # actual validated new kernel.config
parent = old.replace(
    b'g_ether.iProduct=Gemini-Native-Delivery-Diag g_ether.iSerialNumber='
    b'GEMINI_NATIVE_DELIVERY_20261012 clk_ignore_unused fbcon=rotate:3 '
    b'consoleblank=0 fbcon=font:TER16x32 mac.native_delivery_diag=1"',
    b'g_ether.iProduct=Gemini-L-Observability g_ether.iSerialNumber='
    b'GEMINI_OBSERVABILITY_20260717_L clk_ignore_unused fbcon=rotate:3 '
    b'consoleblank=0 fbcon=font:TER16x32"').replace(
    b'CONFIG_LOCALVERSION="-gemini-a53-wifi-native-delivery-diag"',
    b'CONFIG_LOCALVERSION="-gemini-a53-wifi-phase-b-compile"').replace(
    b'CONFIG_MT6797_NATIVE_DELIVERY_DIAG=y\n', b'')
receipt = json.loads((HERE.parent / '2026-10-07-mt6797-wifi-phase-b-join/'
                     'results/candidate-32.json').read_text())
assert hashlib.sha256(parent).hexdigest() == receipt['files']['kernel.config']['sha256']
assert N['expected_native_config'](parent) == old
assert M['expected_ccmp_config'](parent) == new
assert hashlib.sha256(new).hexdigest() == M['CONFIG_SHA256']
for mutation in [
    parent.replace(b'CONFIG_MT6797_STATION_JOIN=y', b'# CONFIG_MT6797_STATION_JOIN is not set'),
    parent.replace(b'-gemini-a53-wifi-phase-b-compile', b'-wrong-release'),
    parent.replace(b'GEMINI_OBSERVABILITY_20260717_L', b'wrong-identity'),
    parent + b'CONFIG_MT6797_CCMP_STABLE_EPOCH=y\n',
    parent + b'CONFIG_MT6797_NATIVE_DELIVERY_DIAG=y\n',
]:
    try:
        M['expected_ccmp_config'](mutation)
    except (SystemExit, ValueError):
        pass
    else:
        raise AssertionError('changed parent admitted')
for change in [b'mac.ccmp_stable_epoch=1', b'clk_ignore_unused',
               b'CONFIG_MT6797_CCMP_STABLE_EPOCH=y', b'mac.native_delivery_diag=0']:
    assert M['expected_ccmp_config'](parent) != new.replace(change, b'changed')
print('CCMP compositor config: PASS C32 digest, exact actual package,5 parent refusals/4 child differences')
