#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Actual future no-scan branch: never-started route and started-child refusals."""
import json
from pathlib import Path
import runpy
import tempfile
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent.parent
M = runpy.run_path(str(HERE / 'ccmp-no-scan.py'))
with tempfile.TemporaryDirectory(prefix='ccmp-no-scan-', dir='/tmp/opencode') as tmp:
    root = Path(tmp)
    calls = []
    helper = SimpleNamespace(record={'owned': True, 'started': False, 'safe': False}, proc=None, pgid=None)
    original = dict(helper.record)
    def prepare(candidate):
        calls.append('underlying-no-leaf-private-preparation')
        def execute(prepared):
            calls.extend(['one-original-claim', 'observation', 'probe', 'seal', 'regression', 'one-recovery'])
            return {'regression_pass': True, 'recovery_confirmed': True}
        return {'finish': SimpleNamespace(sync_directory=lambda p: None), 'execute': execute}
    ph = SimpleNamespace(HELPER=helper, WIPHY_PREPARE=prepare, PRIVATE_REPO=root, ROOT=root,
        HOST=SimpleNamespace(DOMAIN=SimpleNamespace(HOST=SimpleNamespace(
            encoded=lambda value: json.dumps(value).encode()))))
    assert M['run_without_scan'](ph, root / 'synthetic-candidate') == 0
    assert helper.record == original  # no safe=True or quiescence fabrication
    assert not set(calls) & {'helper-start', 'supplicant-log', 'quiescence', 'cycles-export'}
    assert json.loads((root / 'failure-session-result.json').read_bytes())['scan_attempted'] is False
    for started, proc, pgid in [(True, None, None), (False, object(), None),
                               (False, None, 1234), (None, None, None)]:
        calls.clear(); helper.record['started'] = started; helper.proc = proc; helper.pgid = pgid
        try:
            M['run_without_scan'](ph, root / 'synthetic-candidate')
        except RuntimeError:
            pass
        else:
            raise AssertionError('started/uncertain child shortcut admitted')
        assert not calls and helper.record['safe'] is False
print('future genuine no-scan: PASS underlying failure route, no phantom exports/safe receipt; started/uncertain helper guards not bypassed (host-only)')
