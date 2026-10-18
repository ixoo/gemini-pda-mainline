#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fresh GTK6 namespaces and reviewed no-scan route; completed hosts unchanged."""
import importlib.util
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent


def bind_ccmp_gtk6(host):
    host.CCMP_CLASSIFIER = HERE / 'classify-ccmp-gtk-budget.py'
    root = host.RUNTIME_ROOT / 'ccmp-stable-monitor/session-ccmp-gtk6'
    capture = host.RUNTIME_ROOT / 'ccmp-stable-monitor/capture-ccmp-gtk6'
    host.ROOT, host.CAPTURE = root, capture
    ph = host.PH
    ph.ROOT = ph.SCAN.ROOT = ph.SCAN.PARENT.ROOT = ph.HOST.ROOT = \
        ph.HOST.DOMAIN.ROOT = ph.HOST.DOMAIN.HOST.ROOT = root
    ph.CAPTURE = ph.SCAN.CAPTURE = ph.SCAN.PARENT.CAPTURE = ph.HOST.CAPTURE = capture
    ph.HOST.HERE = HERE / 'runtime-ccmp-gtk6'
    if ph.WIFI_SSH_RECEIPT is not None:
        ph.WIFI_SSH_RECEIPT = root / 'wifi-ssh-receipt.json'
        if ph.HELPER is not None:
            ph.HELPER.receipt_path = ph.WIFI_SSH_RECEIPT
            ph.HELPER.record['receipt'] = str(ph.WIFI_SSH_RECEIPT)
    no_scan = runpy.run_path(str(HERE / 'ccmp-no-scan.py'))['run_without_scan']
    ph.run_without_scan = lambda candidate: no_scan(ph, candidate)


def load_host():
    spec = importlib.util.spec_from_file_location('ccmp-gtk6_frozen_host_base', HERE / 'passive-host-ccmp.py')
    host = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(host)
    bind_ccmp_gtk6(host)
    return host


if __name__ == '__main__':
    raise SystemExit(load_host().main())
