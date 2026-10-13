#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Actual real-receipt runtime35 wiring and offline refusal tests; no device."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import runpy
import shlex
import sys
import tempfile

HERE = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='runtime35-binding-') as temporary:
    root = Path(temporary)
    (root / 'private/artifacts/credentials').mkdir(parents=True)
    (root / 'runtime').mkdir()
    (root / 'keys').mkdir()
    os.environ.update(GEMINI_PRIVATE_REPO=str(root / 'private'),
                      GEMINI_RUNTIME_ROOT=str(root / 'runtime'),
                      GEMINI_JOIN_SCRIPT=str(HERE / 'join-twice.sh'),
                      GEMINI_WIFI_SSH_KEYS=str(root / 'keys'),
                      GEMINI_WIFI_SSH_BOOT='c3c13385-7138-493e-b7df-6fe5673c6739')
    spec = importlib.util.spec_from_file_location('runtime35_session', HERE / 'laptop-session-35.py')
    session = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(session)
    host = session.GLOBALS['HOST']
    expected_root = root / 'runtime/wifi-phase-b/session-35'
    expected_capture = root / 'runtime/wifi-phase-b/capture-35'
    for module in (host, host.SCAN, host.SCAN.PARENT, host.HOST,
                   host.HOST.DOMAIN, host.HOST.DOMAIN.HOST):
        assert module.ROOT == expected_root
    for module in (host, host.SCAN, host.SCAN.PARENT, host.HOST):
        assert module.CAPTURE == expected_capture
    assert host.HOST.HERE == HERE / 'runtime-35'
    assert host.HELPER.receipt_path == host.WIFI_SSH_RECEIPT == expected_root / 'wifi-ssh-receipt.json'
    assert host.HELPER.record['receipt'] == str(host.WIFI_SSH_RECEIPT)
    assert host.HELPER.cycles == 2
    result = subprocess.run([sys.executable, str(HERE / 'passive-host-35.py')],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode != 0 and 'use laptop-session-35.py' in result.stderr
    assert not expected_root.exists() and not expected_capture.exists()

    sha = '8505a4867cdaaa20d2e9bd687f40958f8ec900ceb7467588e51a7e214cf5b3b3'
    receipt = (HERE / 'results/candidate-34.json').read_bytes()
    assert hashlib.sha256(receipt).hexdigest() == sha
    assert (HERE / 'runtime-35/results/candidate.json').read_bytes() == receipt
    actual = runpy.run_path(str(HERE / 'passive-session.py'))
    namespace = actual['prepare'].__globals__
    assert namespace is actual['check_ram_root'].__globals__
    assert namespace['_CANDIDATE'] == 'candidate-34'
    assert namespace['_RECEIPT'] == json.loads(receipt)
    assert namespace['SUPPLICANT_REQUIRED'] and namespace['CLI_REQUIRED']
    routed = runpy.run_path(str(HERE / 'install-passive.py'))
    installer = routed['INSTALLER']
    adapter = routed['ADAPTER']
    assert installer.MANIFEST_SHA == adapter.MANIFEST_SHA == sha
    assert adapter.PREDECESSOR_SHA == \
        '7b61241a89c9d8472885c93d654ecda6f63a188f154b2a7bfc69dd5caaf9dc06'
    assert installer.CANDIDATE_RECEIPT == 'results/candidate-34.json'
    assert installer.TOOL_NAME == 'install-passive-35.py'
    assert installer.RECEIPT_NAME == 'mt6797-wifi-phase-b-deployment-34'
    assert installer.validate is routed['validate']
    validator = installer.BASELINE / 'validate-candidate.py'
    receipt_tool = installer.BASELINE / 'deployment_receipt.py'
    candidate = root / 'candidate-fixture'
    check = ('[[ "$(sha256sum ' + shlex.quote(str(validator)) + " | awk '{print $1}')\" == " +
             installer.digest(validator.read_bytes()) + " ]] || die 'validation tool changed'\n")
    synthetic = (shlex.join(['python3', str(validator), '--foundation', str(candidate),
                            '--userspace', str(candidate)]) + '\n' + check +
                 'a53-authenticated-baseline-deployment-2 ' * 3 + '\n' +
                 "printf 'experiment=a53-authenticated-baseline\\n" + '\n' +
                 shlex.join(['python3', str(receipt_tool), '--candidate-sha256']) + '\n' +
                 "[[ \"$initial_boot_id\" =~ ^[0-9a-f-]{36}$ ]] || die 'malformed initial boot ID'\n")
    derived = adapter.ORIGINAL_ADAPT(synthetic, candidate, os.environ['GEMINI_WIFI_SSH_BOOT'])
    assert str(HERE / 'install-passive-35.py') in derived
    assert installer.digest((HERE / 'install-passive-35.py').read_bytes()) in derived
    assert 'mt6797-wifi-phase-b-deployment-34' in derived
    bad = subprocess.run([sys.executable, str(HERE / 'install-passive-35.py'), 'validate',
                          '--previous-gemian-boot', os.environ['GEMINI_WIFI_SSH_BOOT'],
                          '--candidate', str(root / 'absent')], capture_output=True,
                         text=True, timeout=30)
    assert bad.returncode == 2 and 'CONSYS installer refused' in bad.stderr
    capture = session.GLOBALS['ORIGINAL_RUN_PATH'](str(HERE / 'capture-private-35.py'))
    wmt = capture['WMT']
    assert capture['MANIFEST_SHA'] == wmt.CAPTURE.MANIFEST_SHA == sha
    assert wmt.CAPTURE_DIR == wmt.CAPTURE.CAPTURE == expected_capture
    assert wmt.CAPTURE.DEPLOYMENT == expected_root / 'deployment-summary.txt'
    assert wmt.CAPTURE.RECEIPT == HERE / 'results/candidate-34.json'
    assert wmt.CAPTURE.BASELINE.is_relative_to(root / 'private')

    script = root / 'join.sh'
    script.write_bytes(b'TARGET_SSID=fixture\nWPA_PSK_HEX=' + b'0' * 64 +
                       b'\nTARGET_SSID_HEX=66697874757265\n' + (HERE / 'join-twice.sh').read_bytes())
    script.chmod(0o600)
    os.environ['GEMINI_JOIN_SCRIPT'] = str(script)
    prepared = subprocess.run([sys.executable, str(HERE / 'prepare-runtime-35.py')],
                              check=True, capture_output=True, text=True, timeout=30)
    output = json.loads(prepared.stdout)
    assert output['candidate_manifest_sha256'] == sha and output['created'] == ['session-35']
    assert expected_root.is_dir() and not expected_capture.exists()
    reused = subprocess.run([sys.executable, str(HERE / 'prepare-runtime-35.py')],
                            capture_output=True, text=True, timeout=30)
    assert reused.returncode != 0 and 'already exists' in reused.stderr

print('runtime35 actual receipt/namespace/installer derivation/preparation: PASS (no device/deployment claim)')
