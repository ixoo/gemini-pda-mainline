#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Confirm the native installer binds its REAL program (install-native.py), not the
baseline install-passive.py name: the adapt() derivation points validate/receipt and
the embedded sha check at install-native.py, and the prepare/validate/receipt CLI runs
as the native program. No device action; no real ND1 artifacts needed."""
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROBE = HERE.parent
os.environ.setdefault('GEMINI_PRIVATE_REPO', os.environ.get('NPRIV', '/tmp'))
spec = importlib.util.spec_from_file_location('install_native', PROBE / 'install-native.py')
IN = importlib.util.module_from_spec(spec)
spec.loader.exec_module(IN)
INSTALLER = IN.ADAPTER.INSTALLER

# 1. The base now carries the native program name, and the program exists.
assert INSTALLER.TOOL_NAME == 'install-native.py', INSTALLER.TOOL_NAME
assert (PROBE / 'install-native.py').is_file()
# The tool derivation lives in the consys-rails base adapt (region19 wraps it).
ORIGINAL_ADAPT = IN.ADAPTER.ORIGINAL_ADAPT
assert 'TOOL_NAME' in __import__('inspect').getsource(ORIGINAL_ADAPT), 'base adapt not parameterized'

# 2. adapt() derivation binds install-native.py (+ its digest), never install-passive.py.
BASELINE = INSTALLER.BASELINE
digest = INSTALLER.digest
import shlex
candidate = Path('/tmp/candidate-deadbeef')
validator = BASELINE / 'validate-candidate.py'
receipt_tool = BASELINE / 'deployment_receipt.py'


def check(path):
    return ('[[ "$(sha256sum ' + shlex.quote(str(path)) + " | awk '{print $1}')\" == " +
            digest(path.read_bytes()) + " ]] || die 'validation tool changed'\n")


a1 = shlex.join(['python3', str(validator), '--foundation', str(candidate), '--userspace', str(candidate)])
a3 = shlex.join(['python3', str(receipt_tool), '--candidate-sha256'])
anchor = "[[ \"$initial_boot_id\" =~ ^[0-9a-f-]{36}$ ]] || die 'malformed initial boot ID'\n"
synthetic = (a1 + '\n' + check(validator) +
             'a53-authenticated-baseline-deployment-2 ' * 3 + '\n' +
             "printf 'experiment=a53-authenticated-baseline\\n" + '\n' + a3 + '\n' + anchor)
previous = 'c3c13385-7138-493e-b7df-6fe5673c6739'
out = ORIGINAL_ADAPT(synthetic, candidate, previous)
native_tool = str(PROBE / 'install-native.py')
assert native_tool in out, 'adapt did not reference install-native.py'
assert digest((PROBE / 'install-native.py').read_bytes()) in out, 'adapt did not pin install-native.py sha'
assert str(PROBE / 'install-passive.py') not in out, 'adapt still references install-passive.py'
assert ('python3 ' + shlex.quote(native_tool) + ' validate') in out
assert ('python3 ' + shlex.quote(native_tool) + ' receipt') in out
assert IN.RELEASE and 'mt6797-wifi-native-delivery-deployment-1' in out
assert previous in out  # the preceding-Gemian-boot guard is injected

# 3. The CLI runs as the native program: validate refuses a nonexistent candidate (exit 2),
#    proving prepare/validate/receipt are wired through install-native.py itself.
env = dict(os.environ, GEMINI_PRIVATE_REPO=os.environ.get('NPRIV', '/tmp'))
r = subprocess.run([sys.executable, str(PROBE / 'install-native.py'), 'validate',
                    '--previous-gemian-boot', previous, '--candidate', '/tmp/no-such-candidate-xyz'],
                   capture_output=True, text=True, env=env, timeout=30)
assert r.returncode == 2 and 'CONSYS installer refused' in (r.stdout + r.stderr), (r.returncode, r.stdout, r.stderr)
# and the subcommands exist
h = subprocess.run([sys.executable, str(PROBE / 'install-native.py'), '--help'],
                   capture_output=True, text=True, env=env, timeout=30)
assert all(c in h.stdout for c in ('prepare', 'validate', 'receipt')), h.stdout

print('install-native-cli: PASS (TOOL_NAME binds install-native.py; adapt pins the real '
      'program + sha for validate/receipt, never install-passive.py; CLI prepare/validate/'
      'receipt run as the native program; validate refuses a bad candidate with exit 2)')
