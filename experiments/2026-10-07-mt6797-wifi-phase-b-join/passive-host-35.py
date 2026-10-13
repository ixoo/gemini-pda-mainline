#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fresh runtime35 identity for the reviewed two-lifetime phase-b host.

Preparation only until the real candidate-34/runtime35 receipt and installer
bindings exist. Budgets, verdict, helper quiescence and recovery are unchanged.
"""
import importlib.util
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent


def bind_runtime35(host):
    root = Path(os.environ['GEMINI_RUNTIME_ROOT']).resolve(strict=True) / 'wifi-phase-b/session-35'
    capture = root.parent / 'capture-35'
    host.ROOT = host.SCAN.ROOT = host.SCAN.PARENT.ROOT = host.HOST.ROOT = \
        host.HOST.DOMAIN.ROOT = host.HOST.DOMAIN.HOST.ROOT = root
    host.CAPTURE = host.SCAN.CAPTURE = host.SCAN.PARENT.CAPTURE = host.HOST.CAPTURE = capture
    host.HOST.HERE = HERE / 'runtime-35'
    if host.WIFI_SSH_RECEIPT is not None:
        host.WIFI_SSH_RECEIPT = root / 'wifi-ssh-receipt.json'
        host.HELPER.receipt_path = host.WIFI_SSH_RECEIPT
        host.HELPER.record['receipt'] = str(host.WIFI_SSH_RECEIPT)


def load_host():
    os.environ['GEMINI_PHASE_B_SESSION'] = '33'
    spec = importlib.util.spec_from_file_location('runtime35_phase_b_host', HERE / 'passive-host.py')
    host = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(host)
    bind_runtime35(host)
    return host


if __name__ == '__main__':
    raise SystemExit('runtime35 refused: use laptop-session-35.py for full identity/source binding')
