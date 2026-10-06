#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""capture-private.py main() returns the inherited capture's status offline.

Without --execute the inherited capture only prepares and claims no directory,
so main() must return its status instead of failing on the absent log. With
--execute the unchanged branch still classifies the captured log. The
inherited main is replaced by a stub here; no device or capture runs.
"""
import importlib.util
import os
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='mt6797-capture-status-') as directory:
    work = Path(directory)
    (work / 'private/artifacts/credentials').mkdir(parents=True)
    (work / 'runtime').mkdir()
    os.environ.update(GEMINI_PRIVATE_REPO=str(work / 'private'), GEMINI_RUNTIME_ROOT=str(work / 'runtime'))
    spec = importlib.util.spec_from_file_location('phase_b_capture', HERE / 'capture-private.py')
    capture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(capture)
    status = {'rc': 0}
    capture.WMT.main = lambda: status['rc']
    sys.argv = ['capture-private.py', '--candidate', str(work / 'candidate-x')]
    assert capture.main() == 0, 'offline preparation must return the capture status 0'
    status['rc'] = 3
    assert capture.main() == 3, 'offline preparation must pass the capture status through'
    assert not capture.WMT.CAPTURE_DIR.exists(), 'offline preparation claims no capture directory'
    status['rc'] = 0
    sys.argv.append('--execute')
    assert capture.main() == 1, 'execute without a captured log still fails'
    log = capture.WMT.CAPTURE_DIR / 'log-after-start/stdout.txt'
    log.parent.mkdir(parents=True)
    log.write_bytes(b'')
    assert capture.main() == 1 and (capture.WMT.CAPTURE_DIR / 'phase-a-result.json').is_file(), \
        'execute with an unready log classifies and fails'
print('capture status: PASS (offline returns capture status; execute branch unchanged)')
