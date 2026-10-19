#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""S1: reuse GTK8 kernel/leaf and source-remapped custody/recovery unchanged."""
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'laptop-session-ccmp-gtk8.py'))
GLOBALS = BASE['GLOBALS']
BIND = GLOBALS['ORIGINAL_RUN_PATH'](str(HERE / 'passive-host-ccmp-core-disconnect.py'))
BIND['bind_core_disconnect'](GLOBALS['NH'])
ORIGINAL_RUN_PATH = runpy.run_path


def reviewed_run_path(path, *args, **kwargs):
    if Path(path).resolve() == GLOBALS['PHASE_B'] / 'install-passive.py':
        return GLOBALS['ORIGINAL_RUN_PATH'](str(HERE / 'install-ccmp-core-disconnect.py'),
                                            *args, **kwargs)
    return ORIGINAL_RUN_PATH(path, *args, **kwargs)


runpy.run_path = reviewed_run_path

if __name__ == '__main__':
    raise SystemExit(GLOBALS['NH'].main())
