#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Runtime-33 wiring consistency: every active host path, pin, predecessor and
receipt/deployment name resolves to candidate 32 / runtime 33 / capture-33 /
session-33, not a stale earlier runtime. This is the check the per-tool fixtures
missed: it reads the committed sources and the real candidate-32 receipt, and it
also runs prepare-runtime.py end to end against them so a divergent pin is caught
offline, without a device or a build.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
RECEIPT = HERE / 'results/candidate-32.json'
DIGEST = hashlib.sha256(RECEIPT.read_bytes()).hexdigest()
PREDECESSOR = '54791b439791339fb1f6a2fec970b008569f9b1fa8883e3d7c3cb8a7a5da64f2'  # installed candidate 31
receipt = json.loads(RECEIPT.read_bytes())
assert receipt['kernel_build_commit'] == '5d6323e11edcddad6ca5574c0a225b1c23a32255'
assert receipt['kernel_package_sha256'] == 'fba8f3160888341e3d638b3e3f8f052b345d3900adf5f715b1072d8197716038'
assert receipt['wpa_cli'] is not None and receipt['physical_admission'] is False

def src(name):
    return (HERE / name).read_text()

def slot(name):
    return re.search(r"^MANIFEST_SHA = '([0-9a-f]{64})'$", src(name), re.M).group(1)

# The runtime-33 alias is a byte copy of the committed receipt.
assert (HERE / 'runtime-33/results/candidate.json').read_bytes() == RECEIPT.read_bytes()

# install-passive: predecessor, receipt name, published receipt and MANIFEST_SHA.
ip = src('install-passive.py')
assert slot('install-passive.py') == DIGEST, 'install MANIFEST_SHA not candidate-32'
assert ("PREDECESSOR_SHA = '" + PREDECESSOR + "'") in ip, 'install predecessor not candidate-31'
assert "deployment-32" in ip and "deployment-31" not in ip, 'install receipt name stale'
assert "results/candidate-32.json" in ip and "results/candidate-31.json" not in ip, 'install reads a stale receipt'

# capture-private: capture-33, session-33, candidate-32, MANIFEST_SHA.
cp = src('capture-private.py')
assert slot('capture-private.py') == DIGEST, 'capture MANIFEST_SHA not candidate-32'
assert "capture-33" in cp and "capture-32" not in cp, 'capture dir stale'
assert "session-33" in cp and "session-32" not in cp, 'capture deployment dir stale'
assert "results/candidate-32.json" in cp and "results/candidate-31.json" not in cp, 'capture reads a stale receipt'

# passive-host: session-33 / capture-33 roots.
ph = src('passive-host.py')
assert "wifi-phase-b/session-33" in ph and "wifi-phase-b/session-32" not in ph, 'host ROOT stale'
assert "wifi-phase-b/capture-33" in ph and "wifi-phase-b/capture-32" not in ph, 'host CAPTURE stale'

# passive-session: reads candidate-32 for the declared members.
ps = src('passive-session.py')
assert "results/candidate-32.json" in ps and "results/candidate-31.json" not in ps, 'session reads a stale receipt'

# prepare-runtime: candidate-32 receipt, capture-33/session-33, predecessor candidate-31.
pr = src('prepare-runtime.py')
assert "results/candidate-32.json" in pr and "results/candidate-31.json" not in pr
assert "'capture-33'" in pr and "'session-33'" in pr and "capture-32" not in pr and "session-32" not in pr
assert PREDECESSOR in pr, 'prepare predecessor not candidate-31'

# End-to-end offline prepare-runtime dry-run against the REAL committed receipt and pins.
with tempfile.TemporaryDirectory(prefix='mt6797-rt33-wiring-') as directory:
    work = Path(directory)
    (work / 'private/artifacts/credentials').mkdir(parents=True)
    runtime = work / 'runtime'; runtime.mkdir()
    bound = work / 'bound.sh'
    prefix = (b'TARGET_SSID=x\nTARGET_BSSID=y\nexport TARGET_SSID TARGET_BSSID\n'
              b'TARGET_SSID_HEX=78\nWPA_PSK_HEX=' + b'0' * 64 + b'\nexport TARGET_SSID_HEX WPA_PSK_HEX\n')
    bound.write_bytes(prefix + (HERE / 'join-twice.sh').read_bytes()); bound.chmod(0o600)
    env = dict(os.environ, GEMINI_PRIVATE_REPO=str(work / 'private'),
               GEMINI_RUNTIME_ROOT=str(runtime), GEMINI_JOIN_SCRIPT=str(bound))
    run = subprocess.run([sys.executable, str(HERE / 'prepare-runtime.py')], env=env,
                         capture_output=True, text=True, timeout=30)
    assert run.returncode == 0, run.stderr
    out = json.loads(run.stdout)
    assert out['created'] == ['session-33'] and out['left_absent_for_capture_claim'] == 'capture-33'
    assert out['candidate_manifest_sha256'] == DIGEST
    assert out['predecessor_sha256'] == PREDECESSOR and out['deployment_receipt'] == 'deployment-32'
    assert (runtime / 'wifi-phase-b/session-33').is_dir()

print('runtime-33 wiring: PASS (active paths, predecessor, receipt/deployment names and MANIFEST_SHA all candidate-32/runtime-33; prepare-runtime dry-run against the real receipt)')
