#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise retained recovery-source routing without a device or transport."""
import hashlib
import os
from pathlib import Path
import runpy
import subprocess
import tempfile
import sys

probe = Path(__file__).resolve().parents[1]
retained = Path(sys.argv[1]).resolve(strict=True)
relative = Path('experiments/2026-09-09-standard-kernel-package')
pins = {
    'a53-ram-return-v2.py': '4ef45cd11071a9de2e0c0b6cefbc9dfb1b5f75b6ca2b68f264bcf6f7e3522fe6',
    'a53-ram-return.py': '0f6f20c324dc7bb4911c34a8e793b09a0af819ed46474ee996b723930bf5d081',
    'a53-ram-host.py': 'edba94181863d4e49ca9d7c5d3a6e5b8e638d8e6f140144f7d9238c0468e1bf0',
}
with tempfile.TemporaryDirectory(prefix='ccmp-p2-session-sources-') as directory:
    root = Path(directory).resolve()
    private, history, runtime, keys = (root / n for n in ('private', 'history', 'runtime', 'keys'))
    (private / 'artifacts/credentials').mkdir(parents=True)
    (history / relative).mkdir(parents=True)
    runtime.mkdir()
    keys.mkdir()
    script = root / 'join.sh'
    script.write_bytes(b'TARGET_SSID=fixture\nWPA_PSK_HEX=' + b'0' * 64 +
                       b'\nTARGET_SSID_HEX=66697874757265\n' + (probe / 'join-ccmp-p2.sh').read_bytes())
    script.chmod(0o600)
    for name, digest in pins.items():
        data = (retained / relative / name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == digest
        (history / relative / name).write_bytes(data)
    os.environ.update(GEMINI_PRIVATE_REPO=str(private), GEMINI_SESSION_SOURCE_ROOT=str(history),
                      GEMINI_RUNTIME_ROOT=str(runtime), GEMINI_JOIN_SCRIPT=str(script),
                      GEMINI_WIFI_SSH_KEYS=str(keys),
                      GEMINI_WIFI_SSH_BOOT='c3c13385-7138-493e-b7df-6fe5673c6739')
    module = runpy.run_path(str(probe / 'laptop-session-ccmp-p2.py'))
    g = module['GLOBALS']
    domain = g['DOMAIN']
    assert g['PRIVATE_REPO'] == history
    assert domain.RETURN_V2 == history / relative / 'a53-ram-return-v2.py'
    assert domain.HOST.SERVICE == history / relative
    assert domain.HOST.BASELINE == history / 'experiments/2026-09-05-owner-away-experiment-preparation/baseline/scripts'
    assert domain.HOST.REPO == private  # credential root is not the history store
    assert g['NH'].ROOT == runtime / 'ccmp-stable-monitor/session-ccmp-p2'
    assert g['NH'].PH.HELPER.record['started'] is False

    # Both actual decoder loading routes used by preparation/seal must carry
    # the new contract; original on-disk source pins remain unchanged.
    steps_file = retained / 'experiments/2026-09-05-owner-away-experiment-preparation/baseline/scripts/session_steps.py'
    steps = g['ORIGINAL_RUN_PATH'](str(steps_file))
    assert not hasattr(steps['classify_log'], 'p2_logger_deadline_ms')
    adapted = module['reviewed_run_path'](str(steps_file))
    assert adapted['classify_log'].p2_logger_deadline_ms == 900000
    phase = module['reviewed_run_path'](str(probe.parent / '2026-10-07-mt6797-wifi-phase-b-join/passive-session.py'))
    loader = phase['prepare'].__globals__['load']
    actual_steps = loader('p2_actual_steps', steps_file)
    assert actual_steps.classify_log.p2_logger_deadline_ms == 900000
    actual_finish = loader('p2_actual_finish', steps_file.with_name('finish-baseline.py'))
    assert actual_finish.S['classify_log'].p2_logger_deadline_ms == 900000
    assert hashlib.sha256(steps_file.read_bytes()).hexdigest() == module['P2']['STEPS_SHA']
    assert os.environ['GEMINI_PRIVATE_REPO'] == str(private)

    class ReachedPinnedHost(Exception):
        pass

    def pinned_host(_candidate):
        raise ReachedPinnedHost  # never construct or execute a device action

    domain.HOST.prepare = pinned_host
    try:
        domain.prepare(root / 'absent-candidate')
    except ReachedPinnedHost:
        pass
    else:
        raise AssertionError('valid recovery source did not reach the host preflight')
    domain.RETURN_V2.write_bytes(domain.RETURN_V2.read_bytes() + b'\n')
    try:
        domain.prepare(root / 'absent-candidate')
    except ValueError as error:
        assert 'Gemian return v2 source changed' in str(error)
    else:
        raise AssertionError('changed recovery source accepted')
    assert not list(private.joinpath('artifacts/credentials').iterdir())
    rejected = subprocess.run(
        [sys.executable, '-c', 'import runpy,sys; runpy.run_path(sys.argv[1])',
         str(probe / 'laptop-session-ccmp-p2.py')],
        env={**os.environ, 'GEMINI_SESSION_SOURCE_ROOT': str(probe.parents[1])},
        capture_output=True, text=True, timeout=30)
    assert rejected.returncode != 0 and 'must be outside the active checkout' in rejected.stderr
print('P2 session sources: PASS retained routing, separate credentials/evidence, unchanged recovery pin refusal')
