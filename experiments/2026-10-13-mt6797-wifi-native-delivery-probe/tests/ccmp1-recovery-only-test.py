#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Actual recovery-only flow with host mocks; no reseal, probe, private RAM or device."""
import hashlib
import json
from pathlib import Path
import runpy
import tempfile
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent.parent
M = runpy.run_path(str(HERE / 'recover-ccmp1-preserved.py'))
assert len(M['scope']()['files']) == 39 and len(M['scope']()['directories']) == 5
G = M['execute'].__globals__
original_scope, original_proof = G['scope'], G['available_proof']
encoded = lambda value: (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
with tempfile.TemporaryDirectory(prefix='ccmp1-recovery-only-', dir='/tmp/opencode') as tmp:
    for case in ('available-incomplete-log', 'incomplete-available', 'bad-request', 'failed-return'):
        root = Path(tmp) / case; root.mkdir()
        inventory = json.loads(json.dumps(original_scope()))
        for directory in inventory['directories']:
            (root / directory).mkdir()
        for name, identity in inventory['files'].items():
            body = ('fixture:' + name).encode(); (root / name).write_bytes(body)
            identity.update(bytes=len(body), sha256=hashlib.sha256(body).hexdigest())
        G['scope'] = lambda: inventory
        calls = []
        def write(path, raw):
            with path.open('xb') as f:
                f.write(raw)
        def snapshot(directory, manifest):
            lines = manifest.decode().splitlines()
            for line in lines:
                expected, name = line.split('  ', 1)
                assert hashlib.sha256((directory / name).read_bytes()).hexdigest() == expected
            return {line.split('  ', 1)[1]: b'verified' for line in lines}
        proof = {'available_preservation_complete': True, 'log_complete': False}
        def recheck(prepared):
            if case == 'incomplete-available':
                raise ValueError('available evidence incomplete')
            return proof
        G['available_proof'] = recheck
        def invoke(prepared, label, script, **kwargs):
            assert label == 'native-reboot' and not (root / 'native-reboot').exists()
            calls.append(label); (root / label).mkdir()
            assert len((root / 'CCMP1_AVAILABLE_RECOVERY_SHA256SUMS').read_text().splitlines()) == 39
            return b'requested', b'', {'exit_status': 0}
        def parse_request(*args):
            if case == 'bad-request':
                raise ValueError('identity refusal')
            return {'request_count': 1}
        def watch(context):
            calls.append('original-return')
            return {'recovery_confirmed': case != 'failed-return',
                    'boot_id': '929b50a1-229e-434a-8c54-83dd6c3b7db2'}
        prepared = {'root': root,
            'collector': SimpleNamespace(write_new=write, regular=lambda p, limit: p.read_bytes()),
            'finish': SimpleNamespace(sync_directory=lambda p: None, verified_snapshot=snapshot,
                                       parse_recovery_request=parse_request),
            'network': SimpleNamespace(require_ready=lambda: {'ready': True}),
            'steps': SimpleNamespace(recovery_script=lambda c, b: ('identity/tool-bound:' + b).encode()),
            'context': {'candidate': {}}, 'candidate_path': root / 'synthetic-candidate',
            'binding': {'SOURCE_PINS': {'finish-baseline.py': 'fixture'}},
            'returning': SimpleNamespace(prepare=lambda c: {}, watch=watch)}
        if case == 'incomplete-available':
            try:
                M['execute'](prepared, invoke, encoded, proof)
            except ValueError:
                pass
            else:
                raise AssertionError('incomplete available proof admitted')
            assert calls == [] and M['admit'](root)
            continue
        result = M['execute'](prepared, invoke, encoded, proof)
        assert result['regression_pass'] is False and result['ccmp_compatibility_pass'] is False
        assert result['preservation']['log_complete'] is False and calls.count('native-reboot') == 1
        if case == 'available-incomplete-log':
            assert result['recovery_confirmed'] and result['classification'] == 'returned-with-incomplete-log'
        elif case == 'bad-request':
            assert result['recovery_requested'] is None and calls == ['native-reboot']
        else:
            assert not result['recovery_confirmed']
        for name, identity in inventory['files'].items():
            assert hashlib.sha256((root / name).read_bytes()).hexdigest() == identity['sha256']
        previous = list(calls)
        try:
            M['execute'](prepared, invoke, encoded, proof)
        except ValueError:
            pass
        else:
            raise AssertionError('second request admitted')
        assert calls == previous
G['scope'], G['available_proof'] = original_scope, original_proof
print('CCMP1 recovery-only: PASS39 preservation, available/incomplete-log recovery, no renewed phases/false-pass, unknown request/no retry (host-only)')
