#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Real C34/R35 session binding; private-source and 64-member gates unchanged.

ND3 precedes this separately compiled step in the device queue. Actual private
dry run and fresh deployment/boot identity remain the custodian's gates.
"""
import json
import os
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
os.environ['GEMINI_PHASE_B_SESSION'] = '33'
BASE = runpy.run_path(str(HERE / 'laptop-session.py'))
GLOBALS = BASE['reviewed_run_path'].__globals__
BIND = GLOBALS['ORIGINAL_RUN_PATH'](str(HERE / 'passive-host-35.py'))
BIND['bind_runtime35'](GLOBALS['HOST'])


def reviewed_run_path(path, *args, **kwargs):
    path = Path(path).resolve()
    if path == HERE / 'install-passive.py':
        return GLOBALS['ORIGINAL_RUN_PATH'](str(HERE / 'install-passive-35.py'),
                                            *args, **kwargs)
    result = BASE['reviewed_run_path'](path, *args, **kwargs)
    if path == HERE / 'passive-session.py':
        namespace = result['prepare'].__globals__
        namespace['_CANDIDATE'] = 'candidate-34'
        namespace['_RECEIPT'] = json.loads((HERE / 'results/candidate-34.json').read_bytes())
        parent = json.loads((HERE / 'results/candidate-32.json').read_bytes())
        namespace['SUPPLICANT_REQUIRED'] = parent.get('supplicant') is not None
        namespace['CLI_REQUIRED'] = parent.get('wpa_cli') is not None
    return result


runpy.run_path = reviewed_run_path

if __name__ == '__main__':
    if not (HERE / 'runtime-35/results/candidate.json').is_file():
        raise SystemExit('runtime35 refused: real candidate-34 binding not published')
    raise SystemExit(GLOBALS['HOST'].main())
