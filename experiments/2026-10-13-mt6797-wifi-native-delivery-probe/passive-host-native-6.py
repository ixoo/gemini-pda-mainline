#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""ND6 one-lifetime host binding; frozen ND5 budgets and verdict unchanged."""
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent


def bind_nd6(host):
    """Rebind actual host namespaces, including the lower capture identity."""
    root = host.RUNTIME_ROOT / 'native-delivery/session-nd6'
    capture = host.RUNTIME_ROOT / 'native-delivery/capture-nd6'
    host.ROOT, host.CAPTURE = root, capture
    ph = host.PH
    ph.ROOT = ph.SCAN.ROOT = ph.SCAN.PARENT.ROOT = ph.HOST.ROOT = \
        ph.HOST.DOMAIN.ROOT = ph.HOST.DOMAIN.HOST.ROOT = root
    ph.CAPTURE = ph.SCAN.CAPTURE = ph.SCAN.PARENT.CAPTURE = ph.HOST.CAPTURE = capture
    ph.HOST.HERE = HERE / 'runtime-nd6'
    if ph.WIFI_SSH_RECEIPT is not None:
        ph.WIFI_SSH_RECEIPT = root / 'wifi-ssh-receipt.json'
        if ph.HELPER is not None:
            ph.HELPER.receipt_path = ph.WIFI_SSH_RECEIPT
            ph.HELPER.record['receipt'] = str(ph.WIFI_SSH_RECEIPT)


def load_host():
    spec = importlib.util.spec_from_file_location('native_nd6_host_base',
                                                 HERE / 'passive-host-native-5.py')
    host = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(host)
    result = host.load_host()
    bind_nd6(result)
    return result

if __name__ == '__main__':
    raise SystemExit(load_host().main())
