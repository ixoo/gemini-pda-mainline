#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fresh GTK7 host/no-scan/private64/installer binding; completed hosts unchanged."""
from pathlib import Path
import os
import runpy

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'laptop-session-ccmp.py'))
GLOBALS = BASE['reviewed_run_path'].__globals__
BIND = GLOBALS['ORIGINAL_RUN_PATH'](str(HERE / 'passive-host-ccmp-gtk7.py'))
BIND['bind_ccmp_gtk7'](GLOBALS['NH'])
GLOBALS['NATIVE_CANDIDATE'] = 'ccmp-stable-monitor-candidate-gtk7'

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


def reviewed_run_path(path, *args, **kwargs):
    if Path(path).resolve() == GLOBALS['PHASE_B'] / 'install-passive.py':
        return GLOBALS['ORIGINAL_RUN_PATH'](str(HERE / 'install-ccmp-gtk7.py'), *args, **kwargs)
    return BASE['reviewed_run_path'](path, *args, **kwargs)


runpy.run_path = reviewed_run_path

if __name__ == '__main__':
    raise SystemExit(GLOBALS['NH'].main())
