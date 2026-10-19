#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fresh I50 namespaces and reviewed no-scan route; completed hosts unchanged."""
import importlib.util
import hashlib
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent


def bind_ccmp_i50(host):
    reviewed = (HERE / 'join-ccmp-i50.sh').read_bytes()
    if hashlib.sha256(reviewed).hexdigest() != '48e782530ba35c1a8344c622093c50605c1d252086416e5cce4a227a3cd04bc6' or not host.PH.SCAN.SCAN_SOURCE.read_bytes().endswith(reviewed):
        raise ValueError('I50 requires its exact reviewed periodic leaf')
    host.CCMP_CLASSIFIER = HERE / 'classify-ccmp-i50.py'
    root = host.RUNTIME_ROOT / 'ccmp-stable-monitor/session-ccmp-i50'
    capture = host.RUNTIME_ROOT / 'ccmp-stable-monitor/capture-ccmp-i50'
    host.ROOT, host.CAPTURE = root, capture
    ph = host.PH
    ph.ROOT = ph.SCAN.ROOT = ph.SCAN.PARENT.ROOT = ph.HOST.ROOT = \
        ph.HOST.DOMAIN.ROOT = ph.HOST.DOMAIN.HOST.ROOT = root
    ph.CAPTURE = ph.SCAN.CAPTURE = ph.SCAN.PARENT.CAPTURE = ph.HOST.CAPTURE = capture
    ph.HOST.HERE = HERE / 'runtime-ccmp-i50'
    if ph.WIFI_SSH_RECEIPT is not None:
        ph.WIFI_SSH_RECEIPT = root / 'wifi-ssh-receipt.json'
        if ph.HELPER is not None:
            ph.HELPER.receipt_path = ph.WIFI_SSH_RECEIPT
            ph.HELPER.record['receipt'] = str(ph.WIFI_SSH_RECEIPT)
    no_scan = runpy.run_path(str(HERE / 'ccmp-no-scan.py'))['run_without_scan']
    ph.run_without_scan = lambda candidate: no_scan(ph, candidate)


def load_host():
    spec = importlib.util.spec_from_file_location('ccmp-i50_frozen_host_base', HERE / 'passive-host-ccmp.py')
    host = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(host)
    bind_ccmp_i50(host)
    return host


if __name__ == '__main__':
    raise SystemExit(load_host().main())
