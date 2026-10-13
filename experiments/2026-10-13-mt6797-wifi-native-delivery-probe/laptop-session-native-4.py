#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""ND4 session binding; preserve frozen private-source and recovery gates."""
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'laptop-session-native-3.py'))
GLOBALS = BASE['GLOBALS']
BIND = GLOBALS['ORIGINAL_RUN_PATH'](str(HERE / 'passive-host-native-4.py'))
BIND['bind_nd4'](GLOBALS['NH'])
GLOBALS['NATIVE_CANDIDATE'] = 'native-delivery-candidate-4'


def reviewed_run_path(path, *args, **kwargs):
    if Path(path).resolve() == GLOBALS['PHASE_B'] / 'install-passive.py':
        return GLOBALS['ORIGINAL_RUN_PATH'](str(HERE / 'install-native-4.py'),
                                            *args, **kwargs)
    return BASE['reviewed_run_path'](path, *args, **kwargs)


runpy.run_path = reviewed_run_path

if __name__ == '__main__':
    raise SystemExit(GLOBALS['NH'].main())
