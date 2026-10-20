#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fresh P2 namespaces and reviewed no-scan route; completed hosts unchanged."""
import importlib.util
import hashlib
import json
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent


def bind_ccmp_p2(host):
    reviewed = (HERE / 'join-ccmp-p2.sh').read_bytes()
    if hashlib.sha256(reviewed).hexdigest() != '8415967974a673d44d4255a2476347b539f76a62e38acb1394183aa1cd21a1fe' or not host.PH.SCAN.SCAN_SOURCE.read_bytes().endswith(reviewed):
        raise ValueError('P2 requires its exact reviewed periodic leaf')
    host.CCMP_CLASSIFIER = HERE / 'classify-ccmp-connected-p2.py'
    root = host.RUNTIME_ROOT / 'ccmp-stable-monitor/session-ccmp-p2'
    capture = host.RUNTIME_ROOT / 'ccmp-stable-monitor/capture-ccmp-p2'
    host.ROOT, host.CAPTURE = root, capture
    ph = host.PH
    ph.ROOT = ph.SCAN.ROOT = ph.SCAN.PARENT.ROOT = ph.HOST.ROOT = \
        ph.HOST.DOMAIN.ROOT = ph.HOST.DOMAIN.HOST.ROOT = root
    ph.CAPTURE = ph.SCAN.CAPTURE = ph.SCAN.PARENT.CAPTURE = ph.HOST.CAPTURE = capture
    ph.HOST.HERE = HERE / 'runtime-ccmp-p2'
    if ph.WIFI_SSH_RECEIPT is not None:
        ph.WIFI_SSH_RECEIPT = root / 'wifi-ssh-receipt.json'
        if ph.HELPER is not None:
            ph.HELPER.receipt_path = ph.WIFI_SSH_RECEIPT
            ph.HELPER.record['receipt'] = str(ph.WIFI_SSH_RECEIPT)
    if hashlib.sha256((HERE / 'laptop-wifi-ssh-connected-p2.py').read_bytes()).hexdigest() != '5d25538b7a13f8809fe6a2e87fee4f3772a5d3a658625135b7a194299ea828ef':
        raise ValueError('P2 reviewed helper changed')
    if ph.HELPER is not None:
        if ph.HELPER.record['started']:
            raise ValueError('cannot rebind a running P2 helper')
        ph.HELPER.poll, ph.HELPER.join_timeout = 710, 770
        ph.HELPER.record['host_observation_limits'] = {'poll_seconds':710,'join_seconds':770,'grace_seconds':5}
        original_spawn = ph.HELPER.spawn
        def spawn(argv, **kwargs):
            if argv[1] != str(HERE / 'laptop-wifi-ssh-retain.py'):
                raise ValueError('unexpected P2 owned helper')
            return original_spawn([argv[0],str(HERE / 'laptop-wifi-ssh-connected-p2.py'),*argv[2:]],**kwargs)
        ph.HELPER.spawn = spawn
        original_join = ph.HELPER.join_and_record
        def join_and_record(active):
            original_join(active)
            if ph.HELPER.record['started']:
                try:
                    result=json.loads(ph.WIFI_SSH_RECEIPT.read_text())
                    remote=result['p2_remote_stream_quiescence']
                except (OSError,ValueError,KeyError,TypeError):
                    remote={'quiesced':False,'reason':'no verified P2 remote ownership result'}
                active['collector'].write_new(root / 'p2-remote-stream-quiescence.json',ph.HOST.DOMAIN.HOST.encoded(remote))
                if remote.get('quiesced') is not True:
                    raise RuntimeError('P2 remote owner not confirmed quiescent; refusing export, seal and recovery')
        ph.HELPER.join_and_record = join_and_record
    if hashlib.sha256((HERE / 'ten-minute-envelope.py').read_bytes()).hexdigest() != \
            'dbafdb83b95edf261a99fe118cabe1cbdf799d9e4a949cdcd1f809691d27da62':
        raise ValueError('P2 log envelope changed')

    def check_prepared(prepared):
        if getattr(prepared['steps'].classify_log, 'p2_logger_deadline_ms', None) != 900000 or \
                getattr(prepared['finish'].S['classify_log'], 'p2_logger_deadline_ms', None) != 900000:
            raise ValueError('P2 requires the scoped 900-second decoder at both seal checks')
        state = prepared['execute'].__globals__
        state['BUDGETS']['passive-scan'] = (810, 262144)
        if 'passive-scan' in prepared['claim']['phase_budgets']:
            prepared['claim']['phase_budgets']['passive-scan']['seconds'] = 810
        prepared['claim']['p2_logger_contract'] = {
            'deadline_ms':900000,'byte_limit':2097152,
            'origin_source_sha256':'762616bb386647e0a25addd36ad9dba2f6384ebde4858f89a806a32678fc60fc',
            'adapter_sha256':'dbafdb83b95edf261a99fe118cabe1cbdf799d9e4a949cdcd1f809691d27da62'}
        return prepared

    original_scan_prepare = ph.SCAN.prepare
    original_ready_prepare = ph.prepare_with_c2
    original_wiphy_prepare = ph.WIPHY_PREPARE
    def wiphy_prepare(candidate):
        return check_prepared(original_wiphy_prepare(candidate))
    ph.WIPHY_PREPARE = wiphy_prepare
    def scan_prepare(candidate):
        return check_prepared(original_scan_prepare(candidate))
    def ready_prepare(candidate):
        return check_prepared(original_ready_prepare(candidate))
    ph.SCAN.prepare = scan_prepare
    ph.prepare_with_c2 = ready_prepare

    no_scan = runpy.run_path(str(HERE / 'ccmp-no-scan.py'))['run_without_scan']
    ph.run_without_scan = lambda candidate: no_scan(ph, candidate)


def load_host():
    spec = importlib.util.spec_from_file_location('ccmp-p2_frozen_host_base', HERE / 'passive-host-ccmp.py')
    host = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(host)
    bind_ccmp_p2(host)
    return host


if __name__ == '__main__':
    raise SystemExit(load_host().main())
