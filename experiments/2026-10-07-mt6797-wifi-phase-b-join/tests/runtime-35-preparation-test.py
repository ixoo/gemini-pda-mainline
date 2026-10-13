#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Actual runtime35 host namespace preparation; no candidate or device claim."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='runtime35-binding-') as temporary:
    root = Path(temporary)
    (root / 'private/artifacts/credentials').mkdir(parents=True)
    (root / 'runtime').mkdir()
    (root / 'keys').mkdir()
    os.environ.update(GEMINI_PRIVATE_REPO=str(root / 'private'),
                      GEMINI_RUNTIME_ROOT=str(root / 'runtime'),
                      GEMINI_JOIN_SCRIPT=str(HERE / 'join-twice.sh'),
                      GEMINI_WIFI_SSH_KEYS=str(root / 'keys'),
                      GEMINI_WIFI_SSH_BOOT='c3c13385-7138-493e-b7df-6fe5673c6739')
    spec = importlib.util.spec_from_file_location('runtime35_session', HERE / 'laptop-session-35.py')
    session = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(session)
    host = session.GLOBALS['HOST']
    expected_root = root / 'runtime/wifi-phase-b/session-35'
    expected_capture = root / 'runtime/wifi-phase-b/capture-35'
    for module in (host, host.SCAN, host.SCAN.PARENT, host.HOST,
                   host.HOST.DOMAIN, host.HOST.DOMAIN.HOST):
        assert module.ROOT == expected_root
    for module in (host, host.SCAN, host.SCAN.PARENT, host.HOST):
        assert module.CAPTURE == expected_capture
    assert host.HOST.HERE == HERE / 'runtime-35'
    assert host.HELPER.receipt_path == host.WIFI_SSH_RECEIPT == expected_root / 'wifi-ssh-receipt.json'
    assert host.HELPER.record['receipt'] == str(host.WIFI_SSH_RECEIPT)
    assert host.HELPER.cycles == 2
    result = subprocess.run([sys.executable, str(HERE / 'passive-host-35.py')],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode != 0 and 'use laptop-session-35.py' in result.stderr
    assert not expected_root.exists() and not expected_capture.exists()

print('runtime35 actual host binding: PASS (preparation only, no candidate/device/evidence claim)')
