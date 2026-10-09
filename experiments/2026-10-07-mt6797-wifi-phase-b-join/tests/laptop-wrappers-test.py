#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""The laptop wrappers remap exactly the roots the private reference wrappers did.

Loads both wrappers with a throwaway private root and asserts that every
remapped attribute lands under it at the same relative path, that nothing
else moved, and that the installer stays the public adapter. No device action.
"""
import importlib.util
import os
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parents[1]
REPO = HERE.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


with tempfile.TemporaryDirectory(prefix='mt6797-laptop-wrappers-') as directory:
    work = Path(directory)
    private = work / 'private'
    (private / 'artifacts/credentials').mkdir(parents=True)
    (work / 'runtime').mkdir()
    bound = work / 'bound.sh'
    bound.write_bytes(b'TARGET_SSID=x\n' + (HERE / 'join-once.sh').read_bytes())
    bound.chmod(0o600)
    os.environ.update(GEMINI_PRIVATE_REPO=str(private), GEMINI_RUNTIME_ROOT=str(work / 'runtime'),
                      GEMINI_JOIN_SCRIPT=str(bound))

    capture = load('laptop_capture', HERE / 'laptop-capture.py')
    baseline = capture.CAPTURE.WMT.CAPTURE.BASELINE
    assert baseline == private / 'experiments/2026-09-05-owner-away-experiment-preparation', baseline
    assert capture.CAPTURE.WMT.CAPTURE_DIR == work / 'runtime/wifi-phase-b/capture-10'
    assert capture.CAPTURE.WMT.CAPTURE.DEPLOYMENT == work / 'runtime/wifi-phase-b/session-10/deployment-summary.txt'
    assert capture.CAPTURE.WMT.CAPTURE.RECEIPT == HERE / 'results/candidate-10.json'

    session = load('laptop_session', HERE / 'laptop-session.py')
    domain = session.DOMAIN
    assert domain.RETURN_V2 == private / 'experiments/2026-09-09-standard-kernel-package/a53-ram-return-v2.py'
    assert domain.HOST.SERVICE == private / 'experiments/2026-09-09-standard-kernel-package'
    assert domain.HOST.BASELINE == private / 'experiments/2026-09-05-owner-away-experiment-preparation/baseline/scripts'
    assert domain.HOST.REPO == private, 'the public host maps the credential root itself'
    assert domain.HOST.HERE == HERE and domain.HOST.ROOT == work / 'runtime/wifi-phase-b/session-10'
    assert session.HOST.CAPTURE == work / 'runtime/wifi-phase-b/capture-10'
    assert session.HOST.SCAN.SCAN_SOURCE == bound
    # The installer stays the public adapter at this experiment's own path.
    assert (HERE / 'install-passive.py').is_file() and domain.HOST.HERE / 'install-passive.py' == HERE / 'install-passive.py'
    # The session rebind reaches BASELINE/SERVICE in the module tree it loads.
    import runpy
    result = runpy.run_path(str(HERE / 'passive-session.py'))
    seen, moved = set(), []
    def walk(module):
        if id(module) in seen:
            return
        seen.add(id(module))
        for name in ('BASELINE', 'SERVICE'):
            value = getattr(module, name, None)
            if isinstance(value, Path):
                assert value.is_relative_to(private), (module.__name__, name, value)
                moved.append(name)
        import types
        for value in vars(module).values():
            if isinstance(value, types.ModuleType) and str(getattr(value, '__file__', '')).startswith(str(private)) or \
               isinstance(value, types.ModuleType) and str(getattr(value, '__file__', '')).startswith(str(REPO)):
                walk(value)
    walk(result['SESSION'])
    assert 'BASELINE' in moved and 'SERVICE' in moved, moved
print('laptop wrappers: PASS (capture BASELINE; host RETURN_V2/SERVICE/BASELINE; session tree; installer unwrapped)')
