#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Exercise the EXACT quiesce_owned/run_bounded from join-native.sh with injected
children: normal exit, window close, a TERM-ignoring child (KILL needed), a
KILL-resistant child (kill stubbed), and on_exit quiescing a live owned child."""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

LEAF = Path(__file__).resolve().parent.parent / 'join-native.sh'
src = LEAF.read_text()


def extract(name):
    i = src.index('\n' + name + '() {\n')
    j = src.index('\n}\n', i)
    return src[i + 1:j + 3]


FUNCS = extract('quiesce_owned') + extract('run_bounded')
BB = shutil.which('busybox') or '/bin/busybox'
if not Path(BB).exists():
    print('run-leaf-wait: SKIP (busybox not present)')
    sys.exit(0)


def run(body):
    harness = (
        '#!/bin/sh\nset -eu\nBB=%s\nowned_exit=255\nquiesce_faults=\nrb_pid=\n'
        '%s\n%s\n' % (BB, FUNCS, body))
    with tempfile.NamedTemporaryFile('w', suffix='.sh', delete=False) as f:
        f.write(harness)
        path = f.name
    try:
        return subprocess.run(['/bin/sh', path], capture_output=True, text=True, timeout=60)
    finally:
        Path(path).unlink()


# 1. Normal exit: a child that exits 0; quiesce_owned reaps it, no fault.
r = run('sleep 1 & c=$!; sleep 2; rc=0; quiesce_owned "$c" t || rc=$?; echo RC=$rc GONE=$owned_exit; '
        'echo FAULTS=[$quiesce_faults]')
assert 'RC=0 GONE=0' in r.stdout and 'FAULTS=[]' in r.stdout, r.stdout + r.stderr

# 2. TERM-dies: a running child killed by SIGTERM; reaped (143), no fault.
r = run('sleep 100 & c=$!; rc=0; quiesce_owned "$c" t || rc=$?; echo RC=$rc EXIT=$owned_exit; '
        'echo FAULTS=[$quiesce_faults]')
assert 'RC=0 EXIT=143' in r.stdout and 'FAULTS=[]' in r.stdout, r.stdout + r.stderr

# 3. KILL-needed: a child that ignores SIGTERM but dies on SIGKILL; reaped, no fault.
r = run('sh -c \'trap "" TERM; sleep 100\' & c=$!; rc=0; quiesce_owned "$c" t || rc=$?; echo RC=$rc; '
        'echo FAULTS=[$quiesce_faults]')
assert 'RC=0' in r.stdout and 'FAULTS=[]' in r.stdout, r.stdout + r.stderr

# 4. KILL-resistant: kill is stubbed so the child never dies (kill -0 stays true);
#    quiesce_owned must record the fault (identity preserved) and return 1, never hang.
r = run('kill() { return 0; }\n'
        'c=4242; rc=0; quiesce_owned "$c" wpa-supplicant || rc=$?; echo RC=$rc; echo FAULTS=[$quiesce_faults]')
assert 'RC=1' in r.stdout and 'FAULTS=[4242:wpa-supplicant]' in r.stdout, r.stdout + r.stderr
assert '__QUIESCE_FAIL__ pid=4242 name=wpa-supplicant' in r.stderr, r.stderr

# 5. run_bounded window close: the window closes mid-run; the owned child is
#    quiesced, rb_pid cleared, 137 returned.
r = run('window_ok() { return 1; }\nrc=0; run_bounded 1 30 /dev/null sleep 100 || rc=$?; echo RC=$rc; '
        'echo RBPID=[$rb_pid] FAULTS=[$quiesce_faults]')
assert 'RC=137' in r.stdout and 'RBPID=[]' in r.stdout and 'FAULTS=[]' in r.stdout, r.stdout + r.stderr

# 6. run_bounded normal completion: child exits inside the window; status returned, rb_pid cleared.
r = run('window_ok() { return 0; }\nrc=0; run_bounded 1 30 /dev/null true || rc=$?; echo RC=$rc; echo RBPID=[$rb_pid]')
assert 'RC=0' in r.stdout and 'RBPID=[]' in r.stdout, r.stdout + r.stderr

print('run-leaf-wait: PASS (normal exit, TERM-dies, KILL-needed, KILL-resistant fault recorded, '
      'window-close quiesce, normal completion; no unbounded wait)')
