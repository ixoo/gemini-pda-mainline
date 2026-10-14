#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Actual continuation append order/refusals; host mocks, no device/private RAM."""
import hashlib
import json
from pathlib import Path
import runpy
import tempfile
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent.parent
M = runpy.run_path(str(HERE / 'continue-ccmp1-no-scan.py'))
assert len(M['scope']()['files']) == 14 and M['scope']()['directories'] == ['observation', 'probe']
G = M['execute'].__globals__
real_scope = G['scope']
encoded = lambda value: (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()

with tempfile.TemporaryDirectory(prefix='ccmp1-continuation-', dir='/tmp/opencode') as tmp:
    parent = Path(tmp)
    def fixture(name):
        root = parent / name; root.mkdir()
        inventory = json.loads(json.dumps(real_scope()))
        for directory in inventory['directories']:
            (root / directory).mkdir()
        for path, identity in inventory['files'].items():
            data = ('host-fixture:' + path).encode()
            (root / path).write_bytes(data)
            identity.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
        G['scope'] = lambda: inventory
        return root, inventory
    root, inventory = fixture('admission')
    assert M['admit'](root)
    (root / 'probe/stdout.txt').write_bytes(b'changed')
    try:
        M['admit'](root)
    except ValueError:
        pass
    else:
        raise AssertionError('changed original evidence admitted')
    for pending in ('passive-scan', 'log-export', 'native-reboot', 'wifi-ssh-helper.json',
                    'ccmp1-continuation-claim.json', 'PRE_RECOVERY_SHA256SUMS'):
        root, _ = fixture('reject-' + pending.replace('.', '-'))
        (root / pending).write_bytes(b'existing')
        try:
            M['admit'](root)
        except ValueError:
            pass
        else:
            raise AssertionError('claimed or launched phase admitted: ' + pending)

    for case in ('healthy', 'incomplete-seal', 'bad-request', 'changed-evidence', 'failed-return'):
        root, inventory = fixture(case)
        calls = []
        def write_new(path, data):
            with path.open('xb') as f:
                f.write(data)
        collector = SimpleNamespace(write_new=write_new)
        def invoke(prepared, label, script, **kwargs):
            assert label in M['PENDING'] and label not in ('observation', 'probe', 'passive-scan')
            calls.append(label)
            directory = root / label; directory.mkdir()
            (directory / 'command.sh').write_bytes(script)
            if case == 'changed-evidence' and label == 'log-export':
                (root / 'probe/stdout.txt').write_bytes(b'changed')
            return b'framed', b'', {'exit_status': 0}
        def snapshot(prepared, boot):
            assert boot == M['BOOT'] and calls == ['log-export']
            assert (root / 'kmsg.log').read_bytes() == b'unique-log'
            for label in ('wiphy-probe', 'provider-probe'):
                invoke(prepared, label, b'reviewed-read-only')
            calls.append('full-snapshot')
            return {'log_complete': case != 'incomplete-seal', 'manifest_sha256': 'host-fixture'}
        def request(*args):
            calls.append('request-identity-validation')
            if case == 'bad-request':
                raise ValueError('request identity refused')
            return {'accepted': True}
        def watch(active):
            calls.append('reviewed-return')
            return {'recovery_confirmed': case != 'failed-return',
                    'boot_id': '929b50a1-229e-434a-8c54-83dd6c3b7db2'}
        finish = SimpleNamespace(EXPORT_FILES=('kmsg.log',), sync_directory=lambda p: None,
                                 parse_recovery_request=request)
        prepared = {'root': root, 'collector': collector, 'finish': finish,
            'network': SimpleNamespace(require_ready=lambda: {'ready': True}),
            'context': {'candidate': {}}, 'candidate_path': parent / 'synthetic-candidate',
            'binding': {'SOURCE_PINS': {'finish-baseline.py': 'host-fixture'}},
            'steps': SimpleNamespace(seal_script=lambda c, b: ('seal:' + b).encode(),
                parse_log_export=lambda *a: {'files': {'kmsg.log': b'unique-log'}, 'result': {}},
                recovery_script=lambda c, b: ('reviewed-recovery:' + b).encode()),
            'returning': SimpleNamespace(prepare=lambda c: {}, watch=watch)}
        result = M['execute'](prepared, invoke, snapshot, encoded)
        assert result['ccmp_compatibility_pass'] is False and result['scan_attempted'] is False
        assert 'execution-claim.json' in inventory['files']
        assert not (root / 'wifi-ssh-helper.json').exists()
        if case == 'healthy':
            assert result['regression_pass'] and result['recovery_confirmed']
            assert calls == ['log-export', 'wiphy-probe', 'provider-probe', 'full-snapshot',
                             'native-reboot', 'request-identity-validation', 'reviewed-return']
            M['unchanged'](root, inventory)
        elif case in ('incomplete-seal', 'changed-evidence'):
            assert 'native-reboot' not in calls and result['recovery_requested'] is False
        elif case == 'bad-request':
            assert result['recovery_requested'] is None and 'reviewed-return' not in calls
        else:
            assert result['recovery_requested'] and not result['regression_pass']
        before = list(calls)
        try:
            M['execute'](prepared, invoke, snapshot, encoded)
        except ValueError:
            pass
        else:
            raise AssertionError('second continuation admitted')
        assert calls == before
G['scope'] = real_scope
print('CCMP1 continuation: PASS exact admission mutations, append-only pending order, full-seal-before-one-recovery, unknown-request/no-retry (host-only)')
