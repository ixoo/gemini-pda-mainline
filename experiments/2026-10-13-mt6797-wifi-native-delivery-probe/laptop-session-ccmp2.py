#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fresh CCMP2 host/no-scan/private64/installer binding; frozen CCMP1 unchanged."""
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'laptop-session-ccmp.py'))
GLOBALS = BASE['reviewed_run_path'].__globals__
BIND = GLOBALS['ORIGINAL_RUN_PATH'](str(HERE / 'passive-host-ccmp2.py'))
BIND['bind_ccmp2'](GLOBALS['NH'])
GLOBALS['NATIVE_CANDIDATE'] = 'ccmp-stable-monitor-candidate-2'


def reviewed_run_path(path, *args, **kwargs):
    if Path(path).resolve() == GLOBALS['PHASE_B'] / 'install-passive.py':
        return GLOBALS['ORIGINAL_RUN_PATH'](str(HERE / 'install-ccmp2.py'), *args, **kwargs)
    return BASE['reviewed_run_path'](path, *args, **kwargs)


runpy.run_path = reviewed_run_path

if __name__ == '__main__':
    raise SystemExit(GLOBALS['NH'].main())
