#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Actual fresh-host failure main/ownership guard, executor mocked; no device."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent.parent
with tempfile.TemporaryDirectory(prefix='ccmp2-failure-host-', dir='/tmp/opencode') as tmp:
    root = Path(tmp); private = root / 'private'; runtime = root / 'runtime'; keys = root / 'keys'
    (private / 'artifacts/credentials').mkdir(parents=True); runtime.mkdir(); keys.mkdir()
    binder = root / 'join.sh'
    binder.write_bytes(b'TARGET_SSID=fixture\nWPA_PSK_HEX=' + b'0' * 64 +
                       b'\nTARGET_SSID_HEX=66697874757265\n' + (HERE / 'join-ccmp.sh').read_bytes())
    binder.chmod(0o600)
    os.environ.update(GEMINI_PRIVATE_REPO=str(private), GEMINI_RUNTIME_ROOT=str(runtime),
                      GEMINI_JOIN_SCRIPT=str(binder), GEMINI_WIFI_SSH_KEYS=str(keys),
                      GEMINI_WIFI_SSH_BOOT='c3c13385-7138-493e-b7df-6fe5673c6739')
    spec = importlib.util.spec_from_file_location('ccmp2_failure_loader', HERE / 'passive-host-ccmp2.py')
    loader = importlib.util.module_from_spec(spec); spec.loader.exec_module(loader)
    host = loader.load_host(); ph = host.PH
    assert host.ROOT == runtime / 'ccmp-stable-monitor/session-ccmp2'
    assert host.CAPTURE == runtime / 'ccmp-stable-monitor/capture-ccmp2'
    assert ph.HOST.HERE == HERE / 'runtime-ccmp2'
    assert ph.HELPER.record['owned'] and not ph.HELPER.record['safe'] and not ph.HELPER.record['started']
    original_record = dict(ph.HELPER.record)
    host.ROOT.mkdir(parents=True); host.CAPTURE.mkdir(parents=True)
    (host.CAPTURE / 'phase-a-result.json').write_text(json.dumps({'ready_for_scan': False}))
    calls = []
    def forbidden(*args, **kwargs):
        raise AssertionError('helper/scan/C2 exports must not run')
    ph.HELPER.start = forbidden
    ph.SCAN.main = forbidden
    def underlying(candidate):
        calls.append('underlying-private/no-leaf-preparation')
        def execute(prepared):
            calls.extend(['one-original-claim', 'observation', 'probe', 'seal', 'regression', 'one-recovery'])
            return {'regression_pass': False, 'recovery_confirmed': True}
        return {'finish': SimpleNamespace(sync_directory=lambda p: None), 'execute': execute}
    ph.WIPHY_PREPARE = underlying
    sys.argv = [str(HERE / 'passive-host-ccmp2.py'), '--candidate', str(root / 'synthetic'), '--execute']
    assert host.main() == 1  # recovered failure stays a failed compatibility test
    assert ph.HELPER.record == original_record
    assert calls[0] == 'underlying-private/no-leaf-preparation' and calls.count('one-recovery') == 1
    result = json.loads((host.ROOT / 'ccmp-session-result.json').read_bytes())
    assert result['scan_attempted'] is False
    assert result['ccmp_compatibility']['provisional_ccmp_compatibility_pass'] is False
    ph.HELPER.record['started'] = True
    calls.clear()
    try:
        ph.run_without_scan(root / 'synthetic')
    except RuntimeError:
        pass
    else:
        raise AssertionError('real started-child shortcut admitted')
    assert not calls and ph.HELPER.record['safe'] is False
print('CCMP2 actual no-scan host main: PASS recovered failure stays false, no helper/C2 effects, started-child guard preserved (host-only)')
