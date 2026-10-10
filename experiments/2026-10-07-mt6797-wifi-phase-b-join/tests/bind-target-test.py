#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline binding of the revised join script with synthetic inputs: the bound wrapper
fits the binder's and the runtime preparer's finite caps, carries the C2 prefix shape
and ends with the exact reviewed source. No real target, PSK or device."""
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
SOURCE = (HERE / 'join-once.sh').read_bytes()
binder = (HERE / 'bind-target.py').read_text()
preparer = (HERE / 'prepare-runtime.py').read_text()
BINDER_CAP = int(re.search(r"source\.stat\(\)\.st_size > (\d+)", binder).group(1))
WRAPPER_CAP = int(re.search(r"info\.st_size > (\d+)\):", preparer).group(1))
assert BINDER_CAP == WRAPPER_CAP == 32768, (BINDER_CAP, WRAPPER_CAP)
assert len(SOURCE) <= BINDER_CAP - 1024, 'the reviewed source leaves room for the private prefix'
with tempfile.TemporaryDirectory(prefix='mt6797-bind-') as directory:
    work = Path(directory)
    target = work / 'target.json'
    target.write_text(json.dumps({'ssid': 'fixture', 'bssid': '02:11:22:33:44:55', 'frequency_mhz': 5200, 'channel': 40}))
    target.chmod(0o600)
    psk = work / 'psk'
    psk.write_bytes(b'0' * 64 + b'\n')
    psk.chmod(0o600)
    out = work / 'bound.sh'
    result = subprocess.run([sys.executable, str(HERE / 'bind-target.py'), '--target', str(target), '--psk-file', str(psk),
                             '--output', str(out)], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'private-target-bound=1; psk_bound=1; device_action=none'
    bound = out.read_bytes()
    assert stat.S_IMODE(out.lstat().st_mode) == 0o600
    assert bound.startswith(b'TARGET_SSID=fixture\nTARGET_BSSID=02:11:22:33:44:55\nexport TARGET_SSID TARGET_BSSID\n')
    assert b'\nTARGET_SSID_HEX=' + b'fixture'.hex().encode() + b'\nWPA_PSK_HEX=' + b'0' * 64 + b'\nexport TARGET_SSID_HEX WPA_PSK_HEX\n' in bound
    assert bound.endswith(SOURCE) and len(bound) <= WRAPPER_CAP, len(bound)
    # The runtime preparer's wrapper checks (shape, size, PSK binding) accept this wrapper.
    assert bound.startswith(b'TARGET_SSID=') and b'\nWPA_PSK_HEX=' in bound and b'\nTARGET_SSID_HEX=' in bound
    # Binding never replaces an existing output.
    result = subprocess.run([sys.executable, str(HERE / 'bind-target.py'), '--target', str(target), '--psk-file', str(psk),
                             '--output', str(out)], capture_output=True, text=True, timeout=60)
    assert result.returncode != 0 and out.read_bytes() == bound
print('bind-target: PASS (revised source bound offline within the 32768-byte caps; C2 prefix; exact source tail; no overwrite)')
