#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""prepare-runtime.py must leave the capture directory for the capture to claim.

Runs the entry point in a throwaway copy with a synthetic receipt and filled
slots, then asserts the inherited capture precondition
(`require(not CAPTURE_DIR.exists(), 'capture already claimed')`) holds for
`<runtime>/wifi-phase-b/capture-18` while `session-18` exists as mode 0700.
"""
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='mt6797-prepare-2-') as directory:
    work = Path(directory)
    copy = work / 'experiment'
    copy.mkdir()
    (copy / 'results').mkdir()
    for name in ('prepare-runtime.py', 'join-once.sh', 'install-passive.py',
                 'capture-private.py'):
        shutil.copy(HERE / name, copy / name)
    source = (copy / 'prepare-runtime.py').read_text()
    pins = {k: re.search(r"^" + k + r" = '([^']+)'$", source, re.M).group(1)
            for k in ('COMMIT', 'PACKAGE', 'RELEASE')}
    receipt = {'kernel_build_commit': pins['COMMIT'], 'kernel_package_sha256': pins['PACKAGE'],
               'kernel_release': pins['RELEASE'], 'physical_admission': False,
               'files': {'boot2-padded.img': {'sha256': '00' * 32, 'bytes': 16777216}}}
    data = json.dumps(receipt, indent=2).encode() + b'\n'
    (copy / 'results/candidate-17.json').write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    for name in ('install-passive.py', 'capture-private.py'):
        text = (copy / name).read_text()
        text, count = re.subn(r"^MANIFEST_SHA = .*$", "MANIFEST_SHA = '" + digest + "'",
                              text, flags=re.M)
        assert count == 1, name
        (copy / name).write_text(text)
    private = work / 'private'
    (private / 'artifacts/credentials').mkdir(parents=True)
    runtime = work / 'runtime'
    runtime.mkdir()
    bound = work / 'bound.sh'
    prefix = b'TARGET_SSID=x\nTARGET_BSSID=y\nexport TARGET_SSID TARGET_BSSID\n'
    bound.write_bytes(prefix + (copy / 'join-once.sh').read_bytes())
    bound.chmod(0o600)
    env = dict(os.environ, GEMINI_PRIVATE_REPO=str(private), GEMINI_RUNTIME_ROOT=str(runtime),
               GEMINI_JOIN_SCRIPT=str(bound))
    # Runtime 13 requires the PSK-bound C2 script; the Phase C1 binding is refused.
    refused = subprocess.run([sys.executable, str(copy / 'prepare-runtime.py')], env=env,
                             capture_output=True, text=True, timeout=30)
    assert refused.returncode != 0 and 'PSK-bound' in refused.stderr and not (runtime / 'wifi-phase-b').exists()
    bound.write_bytes(prefix + b'TARGET_SSID_HEX=78\nWPA_PSK_HEX=' + b'0' * 64 +
                      b'\nexport TARGET_SSID_HEX WPA_PSK_HEX\n' + (copy / 'join-once.sh').read_bytes())
    run = subprocess.run([sys.executable, str(copy / 'prepare-runtime.py')], env=env,
                         capture_output=True, text=True, timeout=30)
    assert run.returncode == 0, run.stderr
    root = runtime / 'wifi-phase-b'
    capture_dir = root / 'capture-18'
    # The inherited one-attempt guard, evaluated exactly as the capture does.
    assert not capture_dir.exists(), 'prepare must not pre-create the capture directory'
    session = root / 'session-18'
    assert session.is_dir() and stat.S_IMODE(session.stat().st_mode) == 0o700
    assert stat.S_IMODE(root.stat().st_mode) == 0o700
    out = json.loads(run.stdout)
    assert out['created'] == ['session-18'] and out['left_absent_for_capture_claim'] == 'capture-18'
    assert out['candidate_manifest_sha256'] == digest and out['device_action'] == 'none'
    # A second run refuses: the session directory already exists.
    again = subprocess.run([sys.executable, str(copy / 'prepare-runtime.py')], env=env,
                           capture_output=True, text=True, timeout=30)
    assert again.returncode != 0 and 'already exists' in again.stderr
print('prepare-runtime: PASS (capture-18 left for the capture claim; session-18 0700; fresh-root refusal)')
