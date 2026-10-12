#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise the ACTUAL phase-b passive-session prepare/check_ram_root identity binding:
laptop-session-native.rebind_native_session must re-point the namespace those functions
read (result['prepare'].__globals__) from candidate-32 / phase-b-compile to the ND1
receipt (e1) and the native release, and must PRESERVE the required wpa+cli 64-member
checks from the inherited C32 parent (the e1 receipt carries no supplicant/wpa_cli keys),
without editing e1. Loads the real passive-session via runpy -- not a fake module."""
import importlib.util
import os
import runpy
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROBE = HERE.parent
PHASE_B = PROBE.parent / '2026-10-07-mt6797-wifi-phase-b-join'
rt = tempfile.mkdtemp(prefix='sess-rt-')
priv = tempfile.mkdtemp(prefix='sess-priv-')
(Path(priv) / 'artifacts' / 'credentials').mkdir(parents=True)
os.environ.update(GEMINI_PHASE_B_SESSION='33', GEMINI_RUNTIME_ROOT=rt, GEMINI_PRIVATE_REPO=priv,
                  GEMINI_JOIN_SCRIPT=str(PROBE / 'join-native.sh'),
                  GEMINI_WIFI_SSH_KEYS=tempfile.mkdtemp(prefix='sess-keys-'),
                  GEMINI_WIFI_SSH_BOOT='c3c13385-7138-493e-b7df-6fe5673c6739')
spec = importlib.util.spec_from_file_location('lsn', PROBE / 'laptop-session-native.py')
LSN = importlib.util.module_from_spec(spec)
spec.loader.exec_module(LSN)

NATIVE = '7.1.3-gemini-a53-wifi-native-delivery-diag'
PHASE_B_REL = '7.1.3-gemini-a53-wifi-phase-b-compile'
ND1 = __import__('json').loads((PROBE / 'results/native-delivery-candidate.json').read_bytes())

# Load the REAL passive-session WITHOUT the native rebind (the saved original runpy).
result = LSN.ORIGINAL_RUN_PATH(str(PHASE_B / 'passive-session.py'))
pg = result['prepare'].__globals__
cg = result['check_ram_root'].__globals__
assert pg is cg, 'prepare and check_ram_root must share one namespace'
# Inherited phase-b identity before the rebind.
assert pg['RELEASE'] == PHASE_B_REL and pg['_CANDIDATE'] == 'candidate-32'

LSN.rebind_native_session(result)

# The namespace prepare()/check_ram_root() actually read is now native.
assert pg['RELEASE'] == NATIVE, pg['RELEASE']
assert pg['_CANDIDATE'] == 'native-delivery-candidate', pg['_CANDIDATE']
assert pg['HERE'] == PROBE, pg['HERE']
assert pg['_RECEIPT'] == ND1 and pg['_RECEIPT']['kernel_release'] == NATIVE
# Required wpa+cli 64-member checks preserved from the inherited C32 parent, NOT from e1.
assert pg['SUPPLICANT_REQUIRED'] is True and pg['CLI_REQUIRED'] is True, (pg['SUPPLICANT_REQUIRED'], pg['CLI_REQUIRED'])
# e1 itself is untouched (still has no supplicant/wpa_cli keys).
assert ND1.get('supplicant') is None and ND1.get('wpa_cli') is None
# check_ram_root sees the same native release (shared namespace).
assert cg['RELEASE'] == NATIVE
# the nested lower firmware-probe module's release is native too.
assert result['SESSION'].RELEASE == NATIVE
# no phase-b identity remains in the namespace prepare reads.
assert PHASE_B_REL not in (pg['RELEASE'], cg['RELEASE']) and pg['_CANDIDATE'] != 'candidate-32'

# Integration: loading passive-session through the native wrapper's patched runpy
# applies the rebind automatically (the real session code path).
auto = runpy.run_path(str(PHASE_B / 'passive-session.py'))
assert auto['prepare'].__globals__['RELEASE'] == NATIVE and \
    auto['prepare'].__globals__['_CANDIDATE'] == 'native-delivery-candidate'

print('session-native-rebind: PASS (real passive-session prepare/check_ram_root namespace '
      're-pointed to ND1 receipt + native release; wpa+cli REQUIRED preserved from the C32 '
      'parent; e1 untouched; patched runpy applies it automatically)')
