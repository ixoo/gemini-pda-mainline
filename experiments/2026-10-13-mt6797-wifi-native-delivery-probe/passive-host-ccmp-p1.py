#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fresh P1 namespaces and reviewed no-scan route; completed hosts unchanged."""
import importlib.util
import hashlib
import json
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent


def bind_ccmp_p1(host):
    reviewed = (HERE / 'join-ccmp-p1.sh').read_bytes()
    if hashlib.sha256(reviewed).hexdigest() != 'd7959108e8a51d26c14c23493d199ff9dd35f786e5dd3b0d39c59f131b5722a0' or not host.PH.SCAN.SCAN_SOURCE.read_bytes().endswith(reviewed):
        raise ValueError('P1 requires its exact reviewed periodic leaf')
    host.CCMP_CLASSIFIER = HERE / 'classify-ccmp-connected.py'
    root = host.RUNTIME_ROOT / 'ccmp-stable-monitor/session-ccmp-p1'
    capture = host.RUNTIME_ROOT / 'ccmp-stable-monitor/capture-ccmp-p1'
    host.ROOT, host.CAPTURE = root, capture
    ph = host.PH
    ph.ROOT = ph.SCAN.ROOT = ph.SCAN.PARENT.ROOT = ph.HOST.ROOT = \
        ph.HOST.DOMAIN.ROOT = ph.HOST.DOMAIN.HOST.ROOT = root
    ph.CAPTURE = ph.SCAN.CAPTURE = ph.SCAN.PARENT.CAPTURE = ph.HOST.CAPTURE = capture
    ph.HOST.HERE = HERE / 'runtime-ccmp-p1'
    if ph.WIFI_SSH_RECEIPT is not None:
        ph.WIFI_SSH_RECEIPT = root / 'wifi-ssh-receipt.json'
        if ph.HELPER is not None:
            ph.HELPER.receipt_path = ph.WIFI_SSH_RECEIPT
            ph.HELPER.record['receipt'] = str(ph.WIFI_SSH_RECEIPT)
    if hashlib.sha256((HERE / 'laptop-wifi-ssh-connected.py').read_bytes()).hexdigest() != '31b65043570988dc3f9d06cd3269cd98e9c8015d48f45bc6fa838c7b20d4b3bf':
        raise ValueError('P1 reviewed helper changed')
    if ph.HELPER is not None:
        if ph.HELPER.record['started']:
            raise ValueError('cannot rebind a running P1 helper')
        ph.HELPER.poll, ph.HELPER.join_timeout = 210, 270
        ph.HELPER.record['host_observation_limits'] = {'poll_seconds':210,'join_seconds':270,'grace_seconds':5}
        original_spawn = ph.HELPER.spawn
        def spawn(argv, **kwargs):
            if argv[1] != str(HERE / 'laptop-wifi-ssh-retain.py'):
                raise ValueError('unexpected P1 owned helper')
            return original_spawn([argv[0],str(HERE / 'laptop-wifi-ssh-connected.py'),*argv[2:]],**kwargs)
        ph.HELPER.spawn = spawn
        original_join = ph.HELPER.join_and_record
        def join_and_record(active):
            original_join(active)
            if ph.HELPER.record['started']:
                try:
                    result=json.loads(ph.WIFI_SSH_RECEIPT.read_text())
                    remote=result['p1_remote_stream_quiescence']
                except (OSError,ValueError,KeyError,TypeError):
                    remote={'quiesced':False,'reason':'no verified P1 remote ownership result'}
                active['collector'].write_new(root / 'p1-remote-stream-quiescence.json',ph.HOST.DOMAIN.HOST.encoded(remote))
                if remote.get('quiesced') is not True:
                    raise RuntimeError('P1 remote owner not confirmed quiescent; refusing export, seal and recovery')
        ph.HELPER.join_and_record = join_and_record
    no_scan = runpy.run_path(str(HERE / 'ccmp-no-scan.py'))['run_without_scan']
    ph.run_without_scan = lambda candidate: no_scan(ph, candidate)


def load_host():
    spec = importlib.util.spec_from_file_location('ccmp-p1_frozen_host_base', HERE / 'passive-host-ccmp.py')
    host = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(host)
    bind_ccmp_p1(host)
    return host


if __name__ == '__main__':
    raise SystemExit(load_host().main())
