#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Actual ND6 namespace/installer derivation and offline preparation; no device."""
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
SHA = 'a8e76bedb11e5b2c0023731611c11934bb431ef0764cb42df8d76975af8a26ee'
PREDECESSOR = '6fec5cf5227f58deef91c0c1b0213956ab6c88f61292961d2817a6e6ec273ae0'


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), PROBE / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Gate bodies are the frozen ND5 bindings, with only new identities/parent
# wrapper references. In particular, no budget or readiness/recovery change.
for tool in ('prepare-native-delivery', 'install-native', 'laptop-capture-native',
             'passive-host-native', 'laptop-session-native'):
    old = (PROBE / (tool + '-5.py')).read_text()
    new = (PROBE / (tool + '-6.py')).read_text()
    if tool != 'prepare-native-delivery':
        new = new.replace(tool + '-5.py', tool + '-4.py')
    new = new.replace('frozen ND5', 'frozen ND4').replace('ND5 predecessor', 'ND4 predecessor')
    new = new.replace('ND6', 'ND5').replace('nd6', 'nd5').replace('-6.py', '-5.py')
    new = new.replace('candidate-6', 'candidate-5').replace('deployment-6', 'deployment-5')
    new = new.replace(SHA, '25893fa2bf4b67364e0821e635c0105c212f110d37156748d8e5a9338a612ef8')
    new = new.replace(PREDECESSOR, '7ce16dc852c1d89881c3ed4e676713fde1f8af755f297cc3e9671cddf6819a0c')
    assert new == old, tool + ': unexpected gate change'

with tempfile.TemporaryDirectory(prefix='nd6-wiring-', dir='/tmp/opencode') as temporary:
    root = Path(temporary)
    private, runtime, keys = (root / name for name in ('private', 'runtime', 'keys'))
    (private / 'artifacts/credentials').mkdir(parents=True)
    runtime.mkdir()
    keys.mkdir()
    script = root / 'join.sh'
    script.write_bytes(b'TARGET_SSID=fixture\nWPA_PSK_HEX=' + b'0' * 64 +
                       b'\nTARGET_SSID_HEX=66697874757265\n' +
                       (PROBE / 'join-native.sh').read_bytes())
    script.chmod(0o600)
    os.environ.update(GEMINI_PRIVATE_REPO=str(private), GEMINI_RUNTIME_ROOT=str(runtime),
                      GEMINI_JOIN_SCRIPT=str(script), GEMINI_WIFI_SSH_KEYS=str(keys),
                      GEMINI_WIFI_SSH_BOOT='c3c13385-7138-493e-b7df-6fe5673c6739')
    receipt = (PROBE / 'results/native-delivery-candidate-6.json').read_bytes()
    assert hashlib.sha256(receipt).hexdigest() == SHA
    assert (PROBE / 'runtime-nd6/results/candidate.json').read_bytes() == receipt
    prepare = subprocess.run([sys.executable, str(PROBE / 'prepare-native-delivery-6.py')],
                             check=True, capture_output=True, text=True, timeout=30)
    result = json.loads(prepare.stdout)
    assert result['candidate_manifest_sha256'] == SHA
    assert result['created'] == ['session-nd6']
    assert (runtime / 'native-delivery/session-nd6').is_dir()
    assert not list((runtime / 'native-delivery/session-nd6').iterdir())
    assert (runtime / 'native-delivery/session-nd6').stat().st_mode & 0o777 == 0o700
    assert not (runtime / 'native-delivery/capture-nd6').exists()
    assert not (runtime / 'native-delivery/session-nd6/deployment-summary.txt').exists()
    again = subprocess.run([sys.executable, str(PROBE / 'prepare-native-delivery-6.py')],
                           capture_output=True, text=True, timeout=30)
    assert again.returncode != 0 and 'already exists' in again.stderr

    # Actual entry refuses changed/missing receipt BEFORE creating evidence.
    isolated = root / 'isolated'
    (isolated / 'results').mkdir(parents=True)
    for name in ('prepare-native-delivery-6.py', 'prepare-native-delivery-2.py',
                 'join-native.sh'):
        shutil.copyfile(PROBE / name, isolated / name)
    changed_receipt = isolated / 'results/native-delivery-candidate-6.json'
    changed_receipt.write_bytes(receipt + b'\n')
    bad_runtime = root / 'bad-runtime'
    bad_runtime.mkdir()
    command = [sys.executable, str(isolated / 'prepare-native-delivery-6.py')]
    rejected = subprocess.run(command,
                              env={**os.environ, 'GEMINI_RUNTIME_ROOT': str(bad_runtime)},
                              capture_output=True, text=True, timeout=30)
    assert rejected.returncode != 0 and 'ND6 receipt changed' in rejected.stderr
    assert not list(bad_runtime.iterdir())
    changed_receipt.unlink()
    missing = subprocess.run(command,
                             env={**os.environ, 'GEMINI_RUNTIME_ROOT': str(bad_runtime)},
                             capture_output=True, text=True, timeout=30)
    assert missing.returncode != 0 and 'native-delivery-candidate-6.json' in missing.stderr
    assert not list(bad_runtime.iterdir())

    installer = load('install-native-6.py')
    engine = installer.INSTALLER
    assert engine.TOOL_NAME == 'install-native-6.py'
    assert engine.CANDIDATE_RECEIPT == 'results/native-delivery-candidate-6.json'
    assert engine.MANIFEST_SHA == installer.ADAPTER.MANIFEST_SHA == SHA
    assert engine.RECEIPT_NAME == 'mt6797-wifi-native-delivery-deployment-6'
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
    assert str(PROBE / 'install-native-6.py') in derived
    assert engine.digest((PROBE / 'install-native-6.py').read_bytes()) in derived
    assert 'mt6797-wifi-native-delivery-deployment-6' in derived
    assert str(PROBE / 'install-native-5.py') not in derived
    bad = subprocess.run([sys.executable, str(PROBE / 'install-native-6.py'), 'validate',
                          '--previous-gemian-boot', os.environ['GEMINI_WIFI_SSH_BOOT'],
                          '--candidate', str(root / 'absent')], capture_output=True,
                         text=True, timeout=30)
    assert bad.returncode == 2 and 'CONSYS installer refused' in bad.stderr

    capture = load('laptop-capture-native-6.py').CAP
    assert capture.MANIFEST_SHA == capture.WMT.CAPTURE.MANIFEST_SHA == SHA
    assert capture.WMT.CAPTURE.CAPTURE == runtime / 'native-delivery/capture-nd6'
    assert capture.WMT.CAPTURE.DEPLOYMENT == runtime / 'native-delivery/session-nd6/deployment-summary.txt'
    assert capture.WMT.CAPTURE.RECEIPT == PROBE / 'results/native-delivery-candidate-6.json'

    standalone = load('passive-host-native-6.py').load_host()
    assert standalone.ROOT == runtime / 'native-delivery/session-nd6'
    assert standalone.PH.HOST.HERE == PROBE / 'runtime-nd6'
    assert standalone.PH.CAPTURE == runtime / 'native-delivery/capture-nd6'

    session = load('laptop-session-native-6.py')
    host = session.GLOBALS['NH']
    ph = host.PH
    expected_root = runtime / 'native-delivery/session-nd6'
    expected_capture = runtime / 'native-delivery/capture-nd6'
    for module in (host, ph, ph.SCAN, ph.SCAN.PARENT, ph.HOST,
                   ph.HOST.DOMAIN, ph.HOST.DOMAIN.HOST):
        assert module.ROOT == expected_root
    for module in (host, ph, ph.SCAN, ph.SCAN.PARENT, ph.HOST):
        assert module.CAPTURE == expected_capture
    assert ph.HOST.HERE == PROBE / 'runtime-nd6'
    assert ph.HELPER.receipt_path == ph.WIFI_SSH_RECEIPT == expected_root / 'wifi-ssh-receipt.json'
    assert ph.HELPER.record['receipt'] == str(ph.WIFI_SSH_RECEIPT)
    actual = runpy.run_path(str(PHASE_B / 'passive-session.py'))
    globals_ = actual['prepare'].__globals__
    assert globals_ is actual['check_ram_root'].__globals__
    assert globals_['_CANDIDATE'] == 'native-delivery-candidate-6'
    assert globals_['_RECEIPT'] == json.loads(receipt)
    assert globals_['SUPPLICANT_REQUIRED'] and globals_['CLI_REQUIRED']
    routed = runpy.run_path(str(PHASE_B / 'install-passive.py'))
    assert routed['MANIFEST_SHA'] == SHA and routed['INSTALLER'].TOOL_NAME == 'install-native-6.py'

print('ND6 actual binding/preparation/refusal tests: PASS (no device or deployment receipt)')
