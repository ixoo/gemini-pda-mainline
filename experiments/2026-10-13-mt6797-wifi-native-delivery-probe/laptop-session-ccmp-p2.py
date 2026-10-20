#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fresh P2 host/no-scan/private64/installer binding; completed hosts unchanged."""
from pathlib import Path
import os
import hashlib
import runpy

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'laptop-session-ccmp.py'))
GLOBALS = BASE['reviewed_run_path'].__globals__
BIND = GLOBALS['ORIGINAL_RUN_PATH'](str(HERE / 'passive-host-ccmp-p2.py'))
BIND['bind_ccmp_p2'](GLOBALS['NH'])
GLOBALS['NATIVE_CANDIDATE'] = 'ccmp-stable-monitor-candidate-p2'

# Current public recovery sources were sanitized after their reviewed pins.
# Reuse the existing source-only remapper with an optional retained cohort;
# credentials, calibration, candidate and evidence roots stay in their original
# namespaces. Every inherited source and recovery identity check still applies.
if 'GEMINI_SESSION_SOURCE_ROOT' in os.environ:
    source_root = Path(os.environ['GEMINI_SESSION_SOURCE_ROOT']).resolve(strict=True)
    if source_root.is_relative_to(GLOBALS['REPO']):
        raise ValueError('retained session sources must be outside the active checkout')
    GLOBALS['PRIVATE_REPO'] = source_root
    GLOBALS['DOMAIN'].RETURN_V2 = source_root / \
        'experiments/2026-09-09-standard-kernel-package/a53-ram-return-v2.py'
    GLOBALS['DOMAIN'].HOST.SERVICE = source_root / \
        'experiments/2026-09-09-standard-kernel-package'
    GLOBALS['DOMAIN'].HOST.BASELINE = source_root / \
        'experiments/2026-09-05-owner-away-experiment-preparation/baseline/scripts'
    GLOBALS['rebind'](GLOBALS['DOMAIN'], set())


CONTRACT = HERE / 'ten-minute-envelope.py'
CONTRACT_SHA = 'dbafdb83b95edf261a99fe118cabe1cbdf799d9e4a949cdcd1f809691d27da62'
if hashlib.sha256(CONTRACT.read_bytes()).hexdigest() != CONTRACT_SHA:
    raise ValueError('P2 host/log contract changed')
P2 = GLOBALS['ORIGINAL_RUN_PATH'](str(CONTRACT))


def bind_log_loader(result):
    state = result['prepare'].__globals__
    original = state['load']
    def load(name, path):
        module = original(name, path)
        if Path(path).name == 'session_steps.py':
            P2['log_contract'](module, Path(path))
        if Path(path).name == 'finish-baseline.py':
            P2['log_contract'](module.S, Path(path).with_name('session_steps.py'))
        return module
    state['load'] = load


def reviewed_run_path(path, *args, **kwargs):
    if Path(path).resolve() == GLOBALS['PHASE_B'] / 'install-passive.py':
        return GLOBALS['ORIGINAL_RUN_PATH'](str(HERE / 'install-ccmp-p2.py'), *args, **kwargs)
    result = BASE['reviewed_run_path'](path, *args, **kwargs)
    if Path(path).resolve() == GLOBALS['PHASE_B'] / 'passive-session.py':
        bind_log_loader(result)
    if Path(path).name == 'session_steps.py':
        P2['log_contract'](result, Path(path))
    return result


runpy.run_path = reviewed_run_path

if __name__ == '__main__':
    raise SystemExit(GLOBALS['NH'].main())
