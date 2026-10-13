#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fresh R36 identity for the unchanged finite two-lifetime host."""
import importlib.util
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent


def bind_runtime36(host):
    root = Path(os.environ['GEMINI_RUNTIME_ROOT']).resolve(strict=True) / 'wifi-phase-b/session-36'
    capture = root.parent / 'capture-36'
    host.ROOT = host.SCAN.ROOT = host.SCAN.PARENT.ROOT = host.HOST.ROOT = \
        host.HOST.DOMAIN.ROOT = host.HOST.DOMAIN.HOST.ROOT = root
    host.CAPTURE = host.SCAN.CAPTURE = host.SCAN.PARENT.CAPTURE = host.HOST.CAPTURE = capture
    host.HOST.HERE = HERE / 'runtime-36'
    if host.WIFI_SSH_RECEIPT is not None:
        host.WIFI_SSH_RECEIPT = root / 'wifi-ssh-receipt.json'
        host.HELPER.receipt_path = host.WIFI_SSH_RECEIPT
        host.HELPER.record['receipt'] = str(host.WIFI_SSH_RECEIPT)


def load_host():
    os.environ['GEMINI_PHASE_B_SESSION'] = '33'
    spec = importlib.util.spec_from_file_location('runtime36_phase_b_host', HERE / 'passive-host.py')
    host = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(host)
    bind_runtime36(host)
    return host


if __name__ == '__main__':
    raise SystemExit('runtime36 refused: use laptop-session-36.py for full identity/source binding')
