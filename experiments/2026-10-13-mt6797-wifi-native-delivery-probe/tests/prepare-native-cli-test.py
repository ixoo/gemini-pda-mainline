#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise the REAL prepare-native-delivery.py CLI with a synthetic mode-0600
private-prefix + the CURRENT native leaf and the committed receipt (no secrets, no
device): a binder that wraps join-native.sh is accepted and leaves the capture
directory absent for the capture to claim; a binder that wraps the old join-once
leaf (or any non-native suffix) is refused."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROBE = HERE.parent
PREPARE = PROBE / 'prepare-native-delivery.py'
NATIVE_LEAF = (PROBE / 'join-native.sh').read_bytes()
PHASE_B = PROBE.parent / '2026-10-07-mt6797-wifi-phase-b-join'
# A synthetic private binder prefix: the shape prepare requires (TARGET_SSID= ...,
# WPA_PSK_HEX=, TARGET_SSID_HEX=), with a FAKE psk/ssid -- no real secret.
PREFIX = (b'TARGET_SSID=TestNet\nWPA_PSK_HEX=' + b'00' * 32 +
          b'\nTARGET_SSID_HEX=0011\n')


def binder(suffix_bytes):
    fd, path = tempfile.mkstemp(suffix='.sh')
    os.write(fd, PREFIX + suffix_bytes)
    os.close(fd)
    os.chmod(path, 0o600)
    return path


def run_prepare(join_script):
    runtime = Path(tempfile.mkdtemp(prefix='native-rt-'))
    priv = Path(tempfile.mkdtemp(prefix='native-priv-'))
    (priv / 'artifacts' / 'credentials').mkdir(parents=True)
    env = dict(os.environ, GEMINI_PRIVATE_REPO=str(priv), GEMINI_RUNTIME_ROOT=str(runtime),
               GEMINI_JOIN_SCRIPT=join_script)
    r = subprocess.run([sys.executable, '-I', str(PREPARE)], capture_output=True, text=True,
                       env=env, timeout=30)
    return r, runtime


# POSITIVE: a binder wrapping the current native leaf is accepted; session created,
# capture left absent for the capture to claim.
jn = binder(NATIVE_LEAF)
try:
    r, runtime = run_prepare(jn)
    assert r.returncode == 0, r.stdout + r.stderr
    out = json.loads(r.stdout)
    assert out['created'] == ['session-nd1'] and out['left_absent_for_capture_claim'] == 'capture-nd1', out
    root = runtime / 'native-delivery'
    assert (root / 'session-nd1').is_dir(), 'session-nd1 not created'
    assert not (root / 'capture-nd1').exists(), 'capture-nd1 must be left absent for the capture claim'
    assert out['device_action'] == 'none'
finally:
    os.unlink(jn)

# NEGATIVE: the old join-once leaf (or any non-native suffix) is refused.
old = PHASE_B / 'join-once.sh'
wrong_suffix = old.read_bytes() if old.is_file() else (NATIVE_LEAF + b'\n# tampered\n')
jo = binder(wrong_suffix)
try:
    r, _ = run_prepare(jo)
    assert r.returncode != 0 and 'join-native.sh' in (r.stdout + r.stderr), (r.returncode, r.stdout, r.stderr)
finally:
    os.unlink(jo)

# NEGATIVE: a non-0600 binder is refused (the private input must be mode 0600).
jn2 = binder(NATIVE_LEAF)
os.chmod(jn2, 0o644)
try:
    r, _ = run_prepare(jn2)
    assert r.returncode != 0 and 'mode-0600' in (r.stdout + r.stderr), (r.returncode, r.stdout, r.stderr)
finally:
    os.unlink(jn2)

print('prepare-native-cli: PASS (native-leaf binder accepted, session-nd1 created + capture '
      'left absent; old join-once/non-native suffix refused; non-0600 binder refused)')
