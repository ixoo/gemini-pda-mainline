#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""The composer's exact kernel-configuration delta from the Phase A parent:
release name, station join after the scan-tuning sample, and packet sockets
enabled with the PACKET_DIAG prompt left off; anything else is refused. When
the reproduced compile-18 and compile-19 configurations are available locally
(GEMINI_CONFIG_OLD / GEMINI_CONFIG_NEW), the real pair is checked too.
Offline; no device action."""
import importlib.util
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('phase_b_composer_delta', HERE / 'build-candidate.py')
composer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(composer)
expected = composer.expected_kernel_config

PARENT = (b'#\n# Automatically generated file; DO NOT EDIT.\n#\n'
          b'CONFIG_LOCALVERSION="-gemini-a53-wifi-phase-a"\n'
          b'CONFIG_NET=y\n# CONFIG_PACKET is not set\nCONFIG_UNIX=y\n'
          b'CONFIG_MT6797_SCAN_TUNING_SAMPLE=y\nCONFIG_ARM_PSCI_FW=y\n')
NEW = (b'#\n# Automatically generated file; DO NOT EDIT.\n#\n'
       b'CONFIG_LOCALVERSION="-gemini-a53-wifi-phase-b-compile"\n'
       b'CONFIG_NET=y\nCONFIG_PACKET=y\n# CONFIG_PACKET_DIAG is not set\nCONFIG_UNIX=y\n'
       b'CONFIG_MT6797_SCAN_TUNING_SAMPLE=y\nCONFIG_MT6797_STATION_JOIN=y\nCONFIG_ARM_PSCI_FW=y\n')
assert expected(PARENT) == NEW
# The compile-18 shape (packet sockets still unset) no longer matches, and an
# unrelated extra line never matches.
old = NEW.replace(b'CONFIG_PACKET=y\n# CONFIG_PACKET_DIAG is not set\n', b'# CONFIG_PACKET is not set\n')
assert expected(PARENT) != old and expected(PARENT) != NEW + b'CONFIG_PACKET_DIAG=y\n'
assert expected(PARENT) != NEW.replace(b'CONFIG_UNIX=y\n', b'CONFIG_UNIX=y\nCONFIG_IPV6=y\n')
for bad in (PARENT.replace(b'# CONFIG_PACKET is not set\n', b'CONFIG_PACKET=y\n'),
            PARENT.replace(b'# CONFIG_PACKET is not set\n', b''),
            PARENT + b'# CONFIG_PACKET is not set\n',
            PARENT.replace(b'CONFIG_UNIX=y\n', b'CONFIG_UNIX=y\n# CONFIG_PACKET_DIAG is not set\n')):
    try:
        expected(bad)
    except ValueError:
        pass
    else:
        raise AssertionError('parent packet-socket lines must be exactly one unset line')

old_path, new_path = os.environ.get('GEMINI_CONFIG_OLD'), os.environ.get('GEMINI_CONFIG_NEW')
checked = ''
if old_path and new_path:
    # The compile-18 configuration reproduced offline is the parent's with the
    # two earlier replacements already applied; reverse them to the parent.
    old_config = Path(old_path).read_bytes()
    parent = old_config.replace(
        b'CONFIG_LOCALVERSION="-gemini-a53-wifi-phase-b-compile"',
        b'CONFIG_LOCALVERSION="-gemini-a53-wifi-phase-a"').replace(
        b'CONFIG_MT6797_SCAN_TUNING_SAMPLE=y\nCONFIG_MT6797_STATION_JOIN=y\n',
        b'CONFIG_MT6797_SCAN_TUNING_SAMPLE=y\n')
    assert expected(parent) == Path(new_path).read_bytes(), 'real compile-19 configuration differs from the exact delta'
    assert expected(parent) != old_config
    checked = '; real compile-18 -> compile-19 pair checked'
print('composer config delta: PASS (release, station join, packet sockets exact; unrelated changes refused' + checked + ')')
