#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Real S1 namespace/helper/installer bindings; fake spawn and no transport."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]

def load(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

with tempfile.TemporaryDirectory(prefix='core-disconnect-binding-') as temporary:
    root = Path(temporary).resolve()
    private, runtime, keys = (root / n for n in ['private', 'runtime', 'keys'])
    (private / 'artifacts/credentials').mkdir(parents=True)
    runtime.mkdir(); keys.mkdir()
    script = root / 'join.sh'
    script.write_bytes(b'TARGET_SSID=fixture\nWPA_PSK_HEX=' + b'0' * 64 +
                       b'\nTARGET_SSID_HEX=66697874757265\n' + (HERE / 'join-ccmp-gtk7.sh').read_bytes())
    script.chmod(0o600)
    os.environ.update(GEMINI_PRIVATE_REPO=str(private), GEMINI_RUNTIME_ROOT=str(runtime),
                      GEMINI_JOIN_SCRIPT=str(script), GEMINI_WIFI_SSH_KEYS=str(keys),
                      GEMINI_WIFI_SSH_BOOT='c3c13385-7138-493e-b7df-6fe5673c6739')
    command = [sys.executable, str(HERE / 'prepare-ccmp-core-disconnect.py')]
    prepared = subprocess.run(command, capture_output=True, check=True, text=True)
    result = json.loads(prepared.stdout)
    assert result['candidate_manifest_sha256'] == 'dd6fff6ee66b68bc0b77daca07e77df29de4f2dbf6189ad272a36b72de6c9273'
    assert result['created'] == ['session-ccmp-gtk8-s1']
    assert not list((runtime / 'ccmp-stable-monitor/session-ccmp-gtk8-s1').iterdir())
    assert not (runtime / 'ccmp-stable-monitor/capture-ccmp-gtk8-s1').exists()
    assert subprocess.run(command, capture_output=True).returncode != 0
    calls = []
    def spawn(argv, **kwargs):
        calls.append((argv, kwargs))
        return SimpleNamespace(pid=12345)
    with patch('subprocess.Popen', spawn):
        host = load('s1_host_binding', 'passive-host-ccmp-core-disconnect.py').load_host()
    assert host.ROOT == runtime / 'ccmp-stable-monitor/session-ccmp-gtk8-s1'
    assert host.CAPTURE == runtime / 'ccmp-stable-monitor/capture-ccmp-gtk8-s1'
    assert host.CCMP_CLASSIFIER == HERE / 'classify-ccmp-core-disconnect.py'
    assert host.PH.HOST.HERE == HERE / 'runtime-ccmp-gtk8-s1'
    assert (host.PH.HOST.HERE / 'results/candidate.json').read_bytes() == \
        (HERE / 'results/ccmp-stable-monitor-candidate-gtk8.json').read_bytes()
    helper = host.PH.HELPER
    helper.start(); helper.start()
    assert len(calls) == 1
    argv, kwargs = calls[0]
    assert argv[1] == str(HERE / 'laptop-wifi-ssh-core-disconnect.py')
    assert argv[argv.index('--receipt') + 1] == str(host.ROOT / 'wifi-ssh-receipt.json')
    assert kwargs['start_new_session'] is True and helper.pgid == 12345
    # Remote ownership is an additional gate; local process-group success alone
    # must never allow sealing/recovery of an unconfirmed remote stream.
    module = load('s1_remote_gate_binding', 'passive-host-ccmp-core-disconnect.py')
    with patch('subprocess.Popen', spawn):
        gated = module.BASE.load_host()
    gated.PH.HELPER.join_and_record = lambda active: None
    module.bind_core_disconnect(gated)
    gated.PH.HELPER.record['started'] = True
    records = []
    active = {'collector': SimpleNamespace(write_new=lambda path, data: records.append((path, data)))}
    path = gated.PH.WIFI_SSH_RECEIPT
    path.write_text(json.dumps({'s1_remote_stream_quiescence': {'quiesced': False}}))
    try:
        gated.PH.HELPER.join_and_record(active)
    except RuntimeError as error:
        assert 'refusing export, seal and recovery' in str(error)
    else:
        raise AssertionError('unconfirmed remote stream passed the seal gate')
    path.write_text(json.dumps({'s1_remote_stream_quiescence': {'quiesced': True}}))
    gated.PH.HELPER.join_and_record(active)
    assert len(records) == 2
    installer = load('s1_installer_binding', 'install-ccmp-core-disconnect.py')
    assert installer.INSTALLER.TOOL_NAME == 'install-ccmp-core-disconnect.py'
    assert installer.INSTALLER.RECEIPT_NAME.endswith('-gtk8-s1')
    assert installer.INSTALLER.CANDIDATE_RECEIPT == 'results/ccmp-stable-monitor-candidate-gtk8.json'
    assert installer.validate.__code__ == installer.BASE.validate.__code__
    assert installer.sources.__code__ == installer.BASE.sources.__code__
    assert installer.ADAPTER.PREDECESSOR_SHA == installer.PREDECESSOR_SHA == \
        json.loads((HERE / 'results/ccmp-stable-monitor-candidate-gtk8.json').read_text())['files']['boot2-padded.img']['sha256']
    assert not list((private / 'artifacts/credentials').iterdir())
print('S1 actual bindings: PASS fresh namespace, unchanged image/leaf, once-only owned helper and guarded installer; no device')
