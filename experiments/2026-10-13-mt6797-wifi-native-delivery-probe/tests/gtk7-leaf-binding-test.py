#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reviewed-leaf routing against the real GTK6 receipt; no fabricated image."""
from pathlib import Path
import contextlib
import hashlib
import io
import json
import os
import runpy
import tempfile

here = Path(__file__).resolve().parents[1]
module = runpy.run_path(str(here / 'prepare-ccmp.py'))
main = module['main']
g = main.__globals__
assert g['REVIEWED_JOIN_SCRIPT'] == here / 'join-ccmp.sh'
receipt = here / 'results/ccmp-stable-monitor-candidate-gtk6.json'
g['RECEIPT'] = receipt
g['MANIFEST_SHA'] = hashlib.sha256(receipt.read_bytes()).hexdigest()
g['REVIEWED_JOIN_SCRIPT'] = here / 'join-ccmp-gtk7.sh'
with tempfile.TemporaryDirectory(prefix='gtk7-leaf-binding-') as directory:
    root = Path(directory).resolve()
    private, runtime = root / 'private', root / 'runtime'
    (private / 'artifacts/credentials').mkdir(parents=True)
    runtime.mkdir()
    bound = root / 'bound.sh'
    prefix = b'TARGET_SSID=fixture\nWPA_PSK_HEX=' + b'0' * 64 + b'\nTARGET_SSID_HEX=66697874757265\n'
    os.environ.update(GEMINI_PRIVATE_REPO=str(private), GEMINI_RUNTIME_ROOT=str(runtime), GEMINI_JOIN_SCRIPT=str(bound))
    bound.write_bytes(prefix + (here / 'join-ccmp.sh').read_bytes()); bound.chmod(0o600)
    try:
        main()
    except SystemExit as error:
        assert 'reviewed one-cycle join-ccmp-gtk7.sh' in str(error)
    else:
        raise AssertionError('GTK7 accepted the old leaf')
    assert not list(runtime.iterdir())
    bound.write_bytes(prefix + g['REVIEWED_JOIN_SCRIPT'].read_bytes()); bound.chmod(0o600)
    assert bound.stat().st_size <= 32768
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        main()
    result = json.loads(out.getvalue())
    assert result['device_action'] == 'none' and result['kernel_build_commit'] == json.loads(receipt.read_text())['kernel_build_commit']
    assert not list((private / 'artifacts/credentials').iterdir())
print('GTK7 leaf binding: PASS default historical leaf, explicit new reviewed body, old-body refusal, unchanged size/credential isolation; offline only')
