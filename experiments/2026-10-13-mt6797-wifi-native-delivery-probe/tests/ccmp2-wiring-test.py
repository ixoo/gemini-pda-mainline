#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reuse actual namespace/installer/refusal fixture for REAL fresh CCMP2 receipt."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import runpy
import shlex
import shutil
import subprocess
import sys
import tempfile

PROBE = Path(__file__).resolve().parents[1]
PHASE_B = PROBE.parent / '2026-10-07-mt6797-wifi-phase-b-join'
SHA = 'ba8078a0be1673a81a8159b5166769aeb226785eb0ee29ba682c3db3e50dc93d'
PREDECESSOR = '41881cb1345a9b1e3d39930c646a63d21499d5d7222039b8abfa7a9bf3b0be8e'


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), PROBE / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


with tempfile.TemporaryDirectory(prefix='ccmp-wiring-', dir='/tmp/opencode') as temporary:
    root = Path(temporary)
    private, runtime, keys = (root / name for name in ('private', 'runtime', 'keys'))
    (private / 'artifacts/credentials').mkdir(parents=True)
    runtime.mkdir()
    keys.mkdir()
    script = root / 'join.sh'
    script.write_bytes(b'TARGET_SSID=fixture\nWPA_PSK_HEX=' + b'0' * 64 +
                       b'\nTARGET_SSID_HEX=66697874757265\n' +
                       (PROBE / 'join-ccmp.sh').read_bytes())
    script.chmod(0o600)
    os.environ.update(GEMINI_PRIVATE_REPO=str(private), GEMINI_RUNTIME_ROOT=str(runtime),
                      GEMINI_JOIN_SCRIPT=str(script), GEMINI_WIFI_SSH_KEYS=str(keys),
                      GEMINI_WIFI_SSH_BOOT='c3c13385-7138-493e-b7df-6fe5673c6739')
    receipt = (PROBE / 'results/ccmp-stable-monitor-candidate-2.json').read_bytes()
    assert hashlib.sha256(receipt).hexdigest() == SHA
    assert (PROBE / 'runtime-ccmp2/results/candidate.json').read_bytes() == receipt
    prepare = subprocess.run([sys.executable, str(PROBE / 'prepare-ccmp2.py')],
                             check=True, capture_output=True, text=True, timeout=30)
    result = json.loads(prepare.stdout)
    assert result['candidate_manifest_sha256'] == SHA
    assert result['created'] == ['session-ccmp2']
    assert (runtime / 'ccmp-stable-monitor/session-ccmp2').is_dir()
    assert not list((runtime / 'ccmp-stable-monitor/session-ccmp2').iterdir())
    assert (runtime / 'ccmp-stable-monitor/session-ccmp2').stat().st_mode & 0o777 == 0o700
    assert not (runtime / 'ccmp-stable-monitor/capture-ccmp2').exists()
    assert not (runtime / 'ccmp-stable-monitor/session-ccmp2/deployment-summary.txt').exists()
    again = subprocess.run([sys.executable, str(PROBE / 'prepare-ccmp2.py')],
                           capture_output=True, text=True, timeout=30)
    assert again.returncode != 0 and 'already exists' in again.stderr

    # Actual entry refuses changed/missing receipt BEFORE creating evidence.
    isolated = root / 'isolated'
    (isolated / 'results').mkdir(parents=True)
    for name in ('prepare-ccmp2.py', 'prepare-ccmp.py', 'join-ccmp.sh'):
        shutil.copyfile(PROBE / name, isolated / name)
    changed_receipt = isolated / 'results/ccmp-stable-monitor-candidate-2.json'
    changed_receipt.write_bytes(receipt + b'\n')
    bad_runtime = root / 'bad-runtime'
    bad_runtime.mkdir()
    original_script = script.read_bytes()
    for body, mode, reason in [
        (original_script, 0o644, 'mode-0600'),
        (b'TARGET_SSID=fixture\nWPA_PSK_HEX=' + b'0' * 64 +
         b'\nTARGET_SSID_HEX=66697874757265\n' + (PROBE / 'join-native.sh').read_bytes(),
         0o600, 'join-ccmp.sh'),
    ]:
        script.write_bytes(body); script.chmod(mode)
        bad = subprocess.run([sys.executable, str(PROBE / 'prepare-ccmp2.py')],
                             env={**os.environ, 'GEMINI_RUNTIME_ROOT': str(bad_runtime)},
                             capture_output=True, text=True, timeout=30)
        assert bad.returncode != 0 and reason in bad.stderr
        assert not list(bad_runtime.iterdir())
    script.write_bytes(original_script); script.chmod(0o600)
    command = [sys.executable, str(isolated / 'prepare-ccmp2.py')]
    rejected = subprocess.run(command,
                              env={**os.environ, 'GEMINI_RUNTIME_ROOT': str(bad_runtime)},
                              capture_output=True, text=True, timeout=30)
    assert rejected.returncode != 0 and 'CCMP receipt changed' in rejected.stderr
    assert not list(bad_runtime.iterdir())
    changed_receipt.unlink()
    missing = subprocess.run(command,
                             env={**os.environ, 'GEMINI_RUNTIME_ROOT': str(bad_runtime)},
                             capture_output=True, text=True, timeout=30)
    assert missing.returncode != 0 and 'candidate' in missing.stderr
    assert not list(bad_runtime.iterdir())

    installer = load('install-ccmp2.py')
    engine = installer.INSTALLER
    assert engine.TOOL_NAME == 'install-ccmp2.py'
    assert engine.CANDIDATE_RECEIPT == 'results/ccmp-stable-monitor-candidate-2.json'
    assert engine.MANIFEST_SHA == installer.ADAPTER.MANIFEST_SHA == SHA
    assert engine.RECEIPT_NAME == 'mt6797-wifi-ccmp-stable-monitor-deployment-2'
    assert installer.ADAPTER.PREDECESSOR_SHA == installer.PREDECESSOR_SHA == PREDECESSOR
    assert engine.validate is installer.validate
    candidate = root / 'candidate-fixture'
    validator = engine.BASELINE / 'validate-candidate.py'
    receipt_tool = engine.BASELINE / 'deployment_receipt.py'
    check = ('[[ "$(sha256sum ' + shlex.quote(str(validator)) + " | awk '{print $1}')\" == " +
             engine.digest(validator.read_bytes()) + " ]] || die 'validation tool changed'\n")
    synthetic = (shlex.join(['python3', str(validator), '--foundation', str(candidate),
                            '--userspace', str(candidate)]) + '\n' + check +
                 'a53-authenticated-baseline-deployment-2 ' * 3 + '\n' +
                 "printf 'experiment=a53-authenticated-baseline\\n" + '\n' +
                 shlex.join(['python3', str(receipt_tool), '--candidate-sha256']) + '\n' +
                 "[[ \"$initial_boot_id\" =~ ^[0-9a-f-]{36}$ ]] || die 'malformed initial boot ID'\n")
    derived = installer.ADAPTER.ORIGINAL_ADAPT(synthetic, candidate,
                                              os.environ['GEMINI_WIFI_SSH_BOOT'])
    assert str(PROBE / 'install-ccmp2.py') in derived
    assert engine.digest((PROBE / 'install-ccmp2.py').read_bytes()) in derived
    assert 'mt6797-wifi-ccmp-stable-monitor-deployment-2' in derived
    assert str(PROBE / 'install-native.py') not in derived
    bad = subprocess.run([sys.executable, str(PROBE / 'install-ccmp2.py'), 'validate',
                          '--previous-gemian-boot', os.environ['GEMINI_WIFI_SSH_BOOT'],
                          '--candidate', str(root / 'absent')], capture_output=True,
                         text=True, timeout=30)
    assert bad.returncode == 2 and 'CONSYS installer refused' in bad.stderr

    capture = load('laptop-capture-ccmp2.py').CAP
    assert capture.MANIFEST_SHA == capture.WMT.CAPTURE.MANIFEST_SHA == SHA
    assert capture.WMT.CAPTURE.CAPTURE == runtime / 'ccmp-stable-monitor/capture-ccmp2'
    assert capture.WMT.CAPTURE.DEPLOYMENT == runtime / 'ccmp-stable-monitor/session-ccmp2/deployment-summary.txt'
    assert capture.WMT.CAPTURE.RECEIPT == PROBE / 'results/ccmp-stable-monitor-candidate-2.json'

    standalone = load('passive-host-ccmp2.py').load_host()
    assert standalone.ROOT == runtime / 'ccmp-stable-monitor/session-ccmp2'
    assert standalone.PH.HOST.HERE == PROBE / 'runtime-ccmp2'
    assert standalone.PH.CAPTURE == runtime / 'ccmp-stable-monitor/capture-ccmp2'

    session = load('laptop-session-ccmp2.py')
    host = session.GLOBALS['NH']
    ph = host.PH
    expected_root = runtime / 'ccmp-stable-monitor/session-ccmp2'
    expected_capture = runtime / 'ccmp-stable-monitor/capture-ccmp2'
    for module in (host, ph, ph.SCAN, ph.SCAN.PARENT, ph.HOST,
                   ph.HOST.DOMAIN, ph.HOST.DOMAIN.HOST):
        assert module.ROOT == expected_root
    for module in (host, ph, ph.SCAN, ph.SCAN.PARENT, ph.HOST):
        assert module.CAPTURE == expected_capture
    assert ph.HOST.HERE == PROBE / 'runtime-ccmp2'
    assert ph.HELPER.receipt_path == ph.WIFI_SSH_RECEIPT == expected_root / 'wifi-ssh-receipt.json'
    assert ph.HELPER.record['receipt'] == str(ph.WIFI_SSH_RECEIPT)
    calls = []
    def fake_spawn(argv, **kwargs):
        calls.append((argv, kwargs))
        return __import__('types').SimpleNamespace(pid=34567)
    helper = host.NativeWifiHelper(keys, os.environ['GEMINI_WIFI_SSH_BOOT'],
                                   ph.WIFI_SSH_RECEIPT, cycles=1, spawn=fake_spawn)
    helper.start(); helper.start()
    assert len(calls) == 1 and calls[0][0][1] == str(PROBE / 'laptop-wifi-ssh-ccmp.py')
    assert calls[0][0][calls[0][0].index('--cycles') + 1] == '1'
    assert calls[0][1]['start_new_session'] and helper.pgid == 34567
    assert host.NativeWifiHelper.join_and_record is ph.WifiHelper.join_and_record
    actual = runpy.run_path(str(PHASE_B / 'passive-session.py'))
    globals_ = actual['prepare'].__globals__
    assert globals_ is actual['check_ram_root'].__globals__
    assert globals_['_CANDIDATE'] == 'ccmp-stable-monitor-candidate-2'
    assert globals_['_RECEIPT'] == json.loads(receipt)
    assert globals_['SUPPLICANT_REQUIRED'] and globals_['CLI_REQUIRED']
    routed = runpy.run_path(str(PHASE_B / 'install-passive.py'))
    assert routed['MANIFEST_SHA'] == SHA and routed['INSTALLER'].TOOL_NAME == 'install-ccmp2.py'

print('CCMP2 actual binding/preparation/refusal tests: PASS (no device or deployment receipt)')
