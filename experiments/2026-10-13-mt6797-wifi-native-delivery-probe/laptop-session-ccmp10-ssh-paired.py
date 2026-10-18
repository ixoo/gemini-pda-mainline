#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Original C10 session with the predeclared A/conditional-ping/B helper."""
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(HERE / 'laptop-session-ccmp10.py'))
HOST = BASE['GLOBALS']['NH']


def paired_spawn(spawn, argv, **kwargs):
    if len(argv) < 2 or argv[1] != str(HERE / 'laptop-wifi-ssh-ccmp.py'):
        raise ValueError('unexpected owned helper command')
    return spawn([argv[0], str(HERE / 'laptop-wifi-ssh-paired.py'), *argv[2:]], **kwargs)


helper = HOST.PH.HELPER
if helper is not None:
    original_spawn = helper.spawn
    helper.spawn = lambda argv, **kwargs: paired_spawn(original_spawn, argv, **kwargs)

if __name__ == '__main__':
    raise SystemExit(HOST.main())
