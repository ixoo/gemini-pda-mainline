#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""The Phase B installer reads its pinned inputs from GEMINI_PRIVATE_REPO.

Loads install-passive.py with a throwaway private root, calls its sources()
and asserts that pinned_sources is bound to that root while derive and the
pin table are the reviewed originals. With the pinned bytes placed in the
throwaway root (install-boot2.sh at its pinned revision from history, the
guard and deriver from this checkout) pinned_sources succeeds; with a
modified copy it refuses. No device action.
"""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parents[1]
REPO = HERE.parents[1]
BASE = 'experiments/2026-08-14-mt6797-runtime-provenance-observer/scripts/install-boot2.sh'
PINNED_REVISION = 'cac47380'

with tempfile.TemporaryDirectory(prefix='mt6797-installer-sources-') as directory:
    private = Path(directory) / 'private'
    (private / 'artifacts/credentials').mkdir(parents=True)
    os.environ['GEMINI_PRIVATE_REPO'] = str(private)
    spec = importlib.util.spec_from_file_location('phase_b_installer', HERE / 'install-passive.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    installer, parser = module.ADAPTER.INSTALLER.sources()
    pinned = installer['pinned_sources']
    assert pinned.__defaults__ == (private,), 'pinned_sources must default to the private root'
    # ORIGINAL_SOURCES() re-executes the baseline module, so compare code, not identity.
    original, _ = module.ORIGINAL_SOURCES()
    assert installer['derive'].__code__ == original['derive'].__code__
    assert installer['digest'].__code__ == original['digest'].__code__
    assert installer['PINS'] == original['PINS']
    assert set(installer['PINS']) == {BASE, 'experiments/2026-09-04-mt6797-thermal-snapshot/scripts/v4_installer_guard.py',
                                      'scripts/boot2-device-guard.sh'}
    # Missing private inputs refuse by the original check.
    try:
        pinned()
    except ValueError as error:
        assert 'reviewed installer input changed' in str(error)
    else:
        raise AssertionError('pinned_sources accepted a root without the inputs')
    # Place the pinned bytes: guard and deriver from this checkout, the base
    # script from its pinned revision in history (skipped if history is absent).
    for relative in installer['PINS']:
        target = private / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if relative == BASE:
            shown = subprocess.run(['git', '-C', str(REPO), 'show', PINNED_REVISION + ':' + relative],
                                   capture_output=True)
            if shown.returncode:
                print('installer sources: PASS (binding only; pinned history unavailable here)')
                sys.exit(0)
            target.write_bytes(shown.stdout)
        else:
            shutil.copy(REPO / relative, target)
    sources = pinned()
    assert set(sources) == set(installer['PINS'])
    for relative, sha in installer['PINS'].items():
        assert installer['digest'](sources[relative]) == sha, relative
    # The modified public copy of the base script still refuses.
    (private / BASE).write_bytes((REPO / BASE).read_bytes())
    try:
        pinned()
    except ValueError as error:
        assert BASE in str(error)
    else:
        raise AssertionError('a changed base script was accepted')
print('installer sources: PASS (pinned inputs bound to GEMINI_PRIVATE_REPO; pins, digest and derive unchanged)')
