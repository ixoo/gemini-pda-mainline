#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Real C35/R36 session binding; unchanged private/source/tools/recovery gates."""
import json
import os
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
os.environ['GEMINI_PHASE_B_SESSION'] = '33'
BASE = runpy.run_path(str(HERE / 'laptop-session.py'))
GLOBALS = BASE['reviewed_run_path'].__globals__
BIND = GLOBALS['ORIGINAL_RUN_PATH'](str(HERE / 'passive-host-36.py'))
BIND['bind_runtime36'](GLOBALS['HOST'])


def reviewed_run_path(path, *args, **kwargs):
    path = Path(path).resolve()
    if path == HERE / 'install-passive.py':
        return GLOBALS['ORIGINAL_RUN_PATH'](str(HERE / 'install-passive-36.py'),
                                            *args, **kwargs)
    result = BASE['reviewed_run_path'](path, *args, **kwargs)
    if path == HERE / 'passive-session.py':
        namespace = result['prepare'].__globals__
        namespace['_CANDIDATE'] = 'candidate-35'
        namespace['_RECEIPT'] = json.loads((HERE / 'results/candidate-35.json').read_bytes())
        parent = json.loads((HERE / 'results/candidate-32.json').read_bytes())
        namespace['SUPPLICANT_REQUIRED'] = parent.get('supplicant') is not None
        namespace['CLI_REQUIRED'] = parent.get('wpa_cli') is not None
    return result


runpy.run_path = reviewed_run_path

if __name__ == '__main__':
    if not (HERE / 'runtime-36/results/candidate.json').is_file():
        raise SystemExit('runtime36 refused: real candidate-35 binding not published')
    raise SystemExit(GLOBALS['HOST'].main())
