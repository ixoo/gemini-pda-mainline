#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run passive-host.py from a checkout without private artifacts.

Environment: GEMINI_PRIVATE_REPO, GEMINI_RUNTIME_ROOT and GEMINI_JOIN_SCRIPT.
The public host already takes the credential root from GEMINI_PRIVATE_REPO.
This wrapper additionally loads the pinned return workflow, the service
scripts and the baseline scripts from the private checkout's copies, because
those scripts derive the credential root from their own location. The session
module tree gets the same treatment when the host loads passive-session.py.
The installer is the public install-passive.py; its reviewed adapt step already
rewrites the repository root to GEMINI_PRIVATE_REPO. Pinned digests still apply
to every remapped file, so the private copies must be identical.
"""

import importlib.util
import os
from pathlib import Path
import runpy
import types

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PRIVATE_REPO = Path(os.environ['GEMINI_PRIVATE_REPO']).resolve(strict=True)
SPEC = importlib.util.spec_from_file_location('wifi_phase_b_host', HERE / 'passive-host.py')
HOST = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HOST)
DOMAIN = HOST.HOST.DOMAIN


def remap(path):
    path = Path(path)
    if not path.is_relative_to(REPO):
        raise ValueError('path outside this checkout: ' + str(path))
    return PRIVATE_REPO / path.relative_to(REPO)


DOMAIN.RETURN_V2 = remap(DOMAIN.RETURN_V2)
DOMAIN.HOST.SERVICE = remap(DOMAIN.HOST.SERVICE)
DOMAIN.HOST.BASELINE = remap(DOMAIN.HOST.BASELINE)
ORIGINAL_RUN_PATH = runpy.run_path


def rebind(module, seen):
    """Remap BASELINE and SERVICE through the loaded session module tree once."""
    if id(module) in seen:
        return
    seen.add(id(module))
    for name in ('BASELINE', 'SERVICE'):
        value = getattr(module, name, None)
        if isinstance(value, Path) and value.is_relative_to(REPO):
            setattr(module, name, remap(value))
    for value in vars(module).values():
        if isinstance(value, types.ModuleType) and \
                str(getattr(value, '__file__', '')).startswith(str(REPO)):
            rebind(value, seen)


def reviewed_run_path(path, *args, **kwargs):
    result = ORIGINAL_RUN_PATH(path, *args, **kwargs)
    if Path(path).resolve() == HERE / 'passive-session.py':
        rebind(result['SESSION'], set())
    return result


runpy.run_path = reviewed_run_path

if __name__ == '__main__':
    raise SystemExit(HOST.main())
