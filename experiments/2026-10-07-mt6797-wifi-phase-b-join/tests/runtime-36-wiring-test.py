#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Actual C35/R36 receipt, namespace and offline safety checks; no device."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import runpy
import shlex
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parents[1]
SHA = 'dcb3db4be44f8fbd6df9ea231de62ec8e6a6c9709dd8e12cb26a6c3c903638a2'


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), HERE / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


with tempfile.TemporaryDirectory(prefix='runtime36-wiring-') as temporary:
    root = Path(temporary)
    private, runtime, keys = (root / name for name in ('private', 'runtime', 'keys'))
    (private / 'artifacts/credentials').mkdir(parents=True)
    runtime.mkdir(); keys.mkdir()
    script = root / 'join.sh'
    script.write_bytes(b'TARGET_SSID=fixture\nWPA_PSK_HEX=' + b'0' * 64 +
                       b'\nTARGET_SSID_HEX=66697874757265\n' + (HERE / 'join-twice.sh').read_bytes())
    script.chmod(0o600)
    os.environ.update(GEMINI_PRIVATE_REPO=str(private), GEMINI_RUNTIME_ROOT=str(runtime),
                      GEMINI_JOIN_SCRIPT=str(script), GEMINI_WIFI_SSH_KEYS=str(keys),
                      GEMINI_WIFI_SSH_BOOT='c3c13385-7138-493e-b7df-6fe5673c6739')
    receipt = (HERE / 'results/candidate-35.json').read_bytes()
    assert hashlib.sha256(receipt).hexdigest() == SHA
    assert (HERE / 'runtime-36/results/candidate.json').read_bytes() == receipt
    prepare = load('prepare-runtime-36.py')
    bad_receipt = root / 'bad-receipt.json'
    bad_receipt.write_bytes(receipt + b' ')
    prepare.GLOBALS['RECEIPT'] = bad_receipt
    try:
        prepare.main()
        raise AssertionError('exact receipt digest was not checked')
    except SystemExit as error:
        assert 'real C35 receipt changed' in str(error)
    assert not list(runtime.iterdir())
    prepared = subprocess.run([sys.executable, str(HERE / 'prepare-runtime-36.py')],
                              check=True, capture_output=True, text=True, timeout=30)
    output = json.loads(prepared.stdout)
    assert output['candidate_manifest_sha256'] == SHA and output['created'] == ['session-36']
    expected_root = runtime / 'wifi-phase-b/session-36'
    expected_capture = runtime / 'wifi-phase-b/capture-36'
    assert expected_root.is_dir() and not expected_capture.exists()
    reused = subprocess.run([sys.executable, str(HERE / 'prepare-runtime-36.py')],
                            capture_output=True, text=True, timeout=30)
    assert reused.returncode != 0 and 'already exists' in reused.stderr

    session = load('laptop-session-36.py')
    host = session.GLOBALS['HOST']
    for module in (host, host.SCAN, host.SCAN.PARENT, host.HOST,
                   host.HOST.DOMAIN, host.HOST.DOMAIN.HOST):
        assert module.ROOT == expected_root
    for module in (host, host.SCAN, host.SCAN.PARENT, host.HOST):
        assert module.CAPTURE == expected_capture
    assert host.HOST.HERE == HERE / 'runtime-36'
    assert host.HELPER.receipt_path == host.WIFI_SSH_RECEIPT == expected_root / 'wifi-ssh-receipt.json'
    assert host.HELPER.record['receipt'] == str(host.WIFI_SSH_RECEIPT) and host.HELPER.cycles == 2
    actual = runpy.run_path(str(HERE / 'passive-session.py'))
    namespace = actual['prepare'].__globals__
    assert namespace is actual['check_ram_root'].__globals__
    assert namespace['_CANDIDATE'] == 'candidate-35' and namespace['_RECEIPT'] == json.loads(receipt)
    assert namespace['SUPPLICANT_REQUIRED'] and namespace['CLI_REQUIRED']
    routed = runpy.run_path(str(HERE / 'install-passive.py'))
    installer, adapter = routed['INSTALLER'], routed['ADAPTER']
    assert installer.MANIFEST_SHA == adapter.MANIFEST_SHA == SHA
    assert adapter.PREDECESSOR_SHA == \
        '7b61241a89c9d8472885c93d654ecda6f63a188f154b2a7bfc69dd5caaf9dc06'
    assert installer.TOOL_NAME == 'install-passive-36.py'
    assert installer.CANDIDATE_RECEIPT == 'results/candidate-35.json'
    assert installer.RECEIPT_NAME == 'mt6797-wifi-phase-b-deployment-35'
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
    assert str(HERE / 'install-passive-36.py') in derived
    assert installer.digest((HERE / 'install-passive-36.py').read_bytes()) in derived
    assert 'mt6797-wifi-phase-b-deployment-35' in derived
    assert str(HERE / 'install-passive-35.py') not in derived
    bad = subprocess.run([sys.executable, str(HERE / 'install-passive-36.py'), 'validate',
                          '--previous-gemian-boot', os.environ['GEMINI_WIFI_SSH_BOOT'],
                          '--candidate', str(root / 'absent')], capture_output=True,
                         text=True, timeout=30)
    assert bad.returncode == 2 and 'CONSYS installer refused' in bad.stderr
    capture = session.GLOBALS['ORIGINAL_RUN_PATH'](str(HERE / 'capture-private-36.py'))
    wmt = capture['WMT']
    assert capture['MANIFEST_SHA'] == capture['GLOBALS']['MANIFEST_SHA'] == wmt.CAPTURE.MANIFEST_SHA == SHA
    assert wmt.CAPTURE_DIR == wmt.CAPTURE.CAPTURE == expected_capture
    assert wmt.CAPTURE.DEPLOYMENT == expected_root / 'deployment-summary.txt'
    assert wmt.CAPTURE.RECEIPT == HERE / 'results/candidate-35.json'
    assert wmt.CAPTURE.BASELINE.is_relative_to(private)

print('R36 actual receipt/namespace/installer/digest/reuse/refusal wiring: PASS (no device/deployment claim)')
