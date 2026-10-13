#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Actual ND4 namespace/installer derivation and offline preparation; no device."""
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
SHA = 'b7ca24a196fb416b25ce6e078770087b96d3ea240dd9928230d1e3156d7dd079'


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), PROBE / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


with tempfile.TemporaryDirectory(prefix='nd4-wiring-', dir='/tmp/opencode') as temporary:
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
    receipt = (PROBE / 'results/native-delivery-candidate-4.json').read_bytes()
    assert hashlib.sha256(receipt).hexdigest() == SHA
    assert (PROBE / 'runtime-nd4/results/candidate.json').read_bytes() == receipt
    prepare = subprocess.run([sys.executable, str(PROBE / 'prepare-native-delivery-4.py')],
                             check=True, capture_output=True, text=True, timeout=30)
    result = json.loads(prepare.stdout)
    assert result['candidate_manifest_sha256'] == SHA
    assert result['created'] == ['session-nd4']
    assert (runtime / 'native-delivery/session-nd4').is_dir()
    assert not list((runtime / 'native-delivery/session-nd4').iterdir())
    assert (runtime / 'native-delivery/session-nd4').stat().st_mode & 0o777 == 0o700
    assert not (runtime / 'native-delivery/capture-nd4').exists()
    again = subprocess.run([sys.executable, str(PROBE / 'prepare-native-delivery-4.py')],
                           capture_output=True, text=True, timeout=30)
    assert again.returncode != 0 and 'already exists' in again.stderr

    # Actual standalone entry refuses a changed receipt BEFORE creating any
    # evidence. Mutate only an isolated tool copy, never a committed receipt.
    isolated = root / 'isolated'
    (isolated / 'results').mkdir(parents=True)
    for name in ('prepare-native-delivery-4.py', 'prepare-native-delivery-2.py',
                 'join-native.sh'):
        shutil.copyfile(PROBE / name, isolated / name)
    (isolated / 'results/native-delivery-candidate-4.json').write_bytes(receipt + b'\n')
    bad_runtime = root / 'bad-runtime'
    bad_runtime.mkdir()
    rejected = subprocess.run([sys.executable, str(isolated / 'prepare-native-delivery-4.py')],
                              env={**os.environ, 'GEMINI_RUNTIME_ROOT': str(bad_runtime)},
                              capture_output=True, text=True, timeout=30)
    assert rejected.returncode != 0 and 'ND4 receipt changed' in rejected.stderr
    assert not list(bad_runtime.iterdir())

    installer = load('install-native-4.py')
    engine = installer.INSTALLER
    assert engine.TOOL_NAME == 'install-native-4.py'
    assert engine.CANDIDATE_RECEIPT == 'results/native-delivery-candidate-4.json'
    assert engine.MANIFEST_SHA == installer.ADAPTER.MANIFEST_SHA == SHA
    assert engine.RECEIPT_NAME == 'mt6797-wifi-native-delivery-deployment-4'
    assert installer.ADAPTER.PREDECESSOR_SHA == installer.PREDECESSOR_SHA == \
        '7b61241a89c9d8472885c93d654ecda6f63a188f154b2a7bfc69dd5caaf9dc06'
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
    assert str(PROBE / 'install-native-4.py') in derived
    assert engine.digest((PROBE / 'install-native-4.py').read_bytes()) in derived
    assert 'mt6797-wifi-native-delivery-deployment-4' in derived
    assert str(PROBE / 'install-native-3.py') not in derived
    bad = subprocess.run([sys.executable, str(PROBE / 'install-native-4.py'), 'validate',
                          '--previous-gemian-boot', os.environ['GEMINI_WIFI_SSH_BOOT'],
                          '--candidate', str(root / 'absent')], capture_output=True,
                         text=True, timeout=30)
    assert bad.returncode == 2 and 'CONSYS installer refused' in bad.stderr

    capture = load('laptop-capture-native-4.py').CAP
    assert capture.MANIFEST_SHA == capture.WMT.CAPTURE.MANIFEST_SHA == SHA
    assert capture.WMT.CAPTURE.CAPTURE == runtime / 'native-delivery/capture-nd4'
    assert capture.WMT.CAPTURE.DEPLOYMENT == runtime / 'native-delivery/session-nd4/deployment-summary.txt'
    assert capture.WMT.CAPTURE.RECEIPT == PROBE / 'results/native-delivery-candidate-4.json'

    standalone = load('passive-host-native-4.py').load_host()
    assert standalone.ROOT == runtime / 'native-delivery/session-nd4'
    assert standalone.PH.HOST.HERE == PROBE / 'runtime-nd4'
    assert standalone.PH.CAPTURE == runtime / 'native-delivery/capture-nd4'

    session = load('laptop-session-native-4.py')
    host = session.GLOBALS['NH']
    ph = host.PH
    expected_root = runtime / 'native-delivery/session-nd4'
    expected_capture = runtime / 'native-delivery/capture-nd4'
    for module in (host, ph, ph.SCAN, ph.SCAN.PARENT, ph.HOST,
                   ph.HOST.DOMAIN, ph.HOST.DOMAIN.HOST):
        assert module.ROOT == expected_root
    for module in (host, ph, ph.SCAN, ph.SCAN.PARENT, ph.HOST):
        assert module.CAPTURE == expected_capture
    assert ph.HOST.HERE == PROBE / 'runtime-nd4'
    assert ph.HELPER.receipt_path == ph.WIFI_SSH_RECEIPT == expected_root / 'wifi-ssh-receipt.json'
    assert ph.HELPER.record['receipt'] == str(ph.WIFI_SSH_RECEIPT)
    actual = runpy.run_path(str(PHASE_B / 'passive-session.py'))
    globals_ = actual['prepare'].__globals__
    assert globals_ is actual['check_ram_root'].__globals__
    assert globals_['_CANDIDATE'] == 'native-delivery-candidate-4'
    assert globals_['_RECEIPT'] == json.loads(receipt)
    assert globals_['SUPPLICANT_REQUIRED'] and globals_['CLI_REQUIRED']
    routed = runpy.run_path(str(PHASE_B / 'install-passive.py'))
    assert routed['MANIFEST_SHA'] == SHA and routed['INSTALLER'].TOOL_NAME == 'install-native-4.py'

print('ND4 actual binding/preparation/refusal tests: PASS (no device or deployment receipt)')
