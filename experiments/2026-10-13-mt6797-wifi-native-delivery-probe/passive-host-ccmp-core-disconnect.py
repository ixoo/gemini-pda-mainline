#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""S1 host namespace on the unchanged, validated GTK8 image and periodic leaf."""
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('s1_gtk8_host', HERE / 'passive-host-ccmp-gtk8.py')
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)


def bind_core_disconnect(host):
    root = host.RUNTIME_ROOT / 'ccmp-stable-monitor/session-ccmp-gtk8-s1'
    capture = host.RUNTIME_ROOT / 'ccmp-stable-monitor/capture-ccmp-gtk8-s1'
    host.ROOT, host.CAPTURE = root, capture
    host.CCMP_CLASSIFIER = HERE / 'classify-ccmp-core-disconnect.py'
    ph = host.PH
    ph.ROOT = ph.SCAN.ROOT = ph.SCAN.PARENT.ROOT = ph.HOST.ROOT = \
        ph.HOST.DOMAIN.ROOT = ph.HOST.DOMAIN.HOST.ROOT = root
    ph.CAPTURE = ph.SCAN.CAPTURE = ph.SCAN.PARENT.CAPTURE = ph.HOST.CAPTURE = capture
    ph.HOST.HERE = HERE / 'runtime-ccmp-gtk8-s1'
    if ph.WIFI_SSH_RECEIPT is not None:
        ph.WIFI_SSH_RECEIPT = root / 'wifi-ssh-receipt.json'
        if ph.HELPER is not None:
            if ph.HELPER.record['started']:
                raise ValueError('cannot rebind a running helper')
            ph.HELPER.receipt_path = ph.WIFI_SSH_RECEIPT
            ph.HELPER.record['receipt'] = str(ph.WIFI_SSH_RECEIPT)
            original = ph.HELPER.spawn

            def spawn(argv, **kwargs):
                if argv[1] != str(HERE / 'laptop-wifi-ssh-retain.py'):
                    raise ValueError('unexpected S1 owned helper')
                return original([argv[0], str(HERE / 'laptop-wifi-ssh-core-disconnect.py'),
                                 *argv[2:]], **kwargs)
            ph.HELPER.spawn = spawn
            original_join = ph.HELPER.join_and_record

            def join_and_record(active):
                original_join(active)
                if ph.HELPER.record['started']:
                    try:
                        receipt = json.loads(ph.WIFI_SSH_RECEIPT.read_text())
                        remote = receipt['s1_remote_stream_quiescence']
                    except (OSError, ValueError, KeyError, TypeError):
                        remote = {'quiesced': False, 'reason': 'no verified remote ownership result'}
                    active['collector'].write_new(root / 's1-remote-stream-quiescence.json',
                                                  ph.HOST.DOMAIN.HOST.encoded(remote))
                    if remote.get('quiesced') is not True:
                        raise RuntimeError('S1 remote stream owner not confirmed quiescent; refusing export, seal and recovery')
            ph.HELPER.join_and_record = join_and_record


def load_host():
    host = BASE.load_host()
    bind_core_disconnect(host)
    return host


if __name__ == '__main__':
    raise SystemExit(load_host().main())
