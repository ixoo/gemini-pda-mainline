#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Exercise the EXACT finite-wait helpers extracted from join-native.sh with
injected children, under the real `set -eu` environment:

  * quiesce_owned: normal exit, SIGTERM-dies, SIGTERM-ignoring (SIGKILL needed,
    readiness-synchronized, owned PID is the trap-holding blocker so there is no
    orphan and the actual signal-9 exit 137 is asserted), and a KILL-resistant
    child (kill stubbed) whose fault must be recorded without hanging;
  * run_bounded: window-closure quiesce and normal completion;
  * on_exit: the actual extracted trap handler, driven by a real SIGTERM to a
    shell that owns a live bounded helper, asserting the owned child is gone and
    the boot-bound quiescence record is written with the right faults line
    (empty => quiesced; non-empty => recovery held). Its device record path is
    redirected to an isolated test directory; nothing else is altered.

It also asserts the helper bodies are byte-identical in the native leaf and the
frozen R34 shared leaf, so this coverage speaks for both.
"""
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent / 'join-native.sh'
R34 = HERE.parents[1] / '2026-10-07-mt6797-wifi-phase-b-join' / 'join-twice.sh'
src = NATIVE.read_text()


def extract_from(text, name):
    i = text.index('\n' + name + '() {\n')
    j = text.index('\n}\n', i)
    return text[i + 1:j + 3]


# The coverage is only meaningful for both leaves if the helper bodies match.
r34 = R34.read_text()
for name in ('quiesce_owned', 'run_bounded', 'on_exit', 'stop_wifi_sshd'):
    assert extract_from(src, name) == extract_from(r34, name), \
        '%s differs between the native leaf and the frozen R34 leaf' % name

QUIESCE = extract_from(src, 'quiesce_owned')
RUN_BOUNDED = extract_from(src, 'run_bounded')
STOP_SSHD = extract_from(src, 'stop_wifi_sshd')
ON_EXIT = extract_from(src, 'on_exit')

BB = shutil.which('busybox') or '/bin/busybox'
if not Path(BB).exists():
    print('run-leaf-wait: SKIP (busybox not present)')
    sys.exit(0)

PRELUDE = ('#!/bin/sh\nset -eu\nBB=%s\nowned_exit=255\nquiesce_faults=\nrb_pid=\n'
           'supplicant_pid=\nwifi_sshd_pid=\nwifi_sshd_exit=255\nstage=test\n' % BB)


def run(body, funcs=QUIESCE + RUN_BOUNDED):
    with tempfile.NamedTemporaryFile('w', suffix='.sh', delete=False) as f:
        f.write(PRELUDE + funcs + '\n' + body + '\n')
        path = f.name
    try:
        return subprocess.run(['/bin/sh', path], capture_output=True, text=True, timeout=60)
    finally:
        Path(path).unlink()


# 1. Normal exit: the child exits on its own; quiesce_owned reaps it, no fault.
r = run('sleep 1 & c=$!; sleep 2; rc=0; quiesce_owned "$c" t || rc=$?; '
        'echo RC=$rc GONE=$owned_exit; echo FAULTS=[$quiesce_faults]')
assert 'RC=0 GONE=0' in r.stdout and 'FAULTS=[]' in r.stdout, r.stdout + r.stderr

# 2. SIGTERM-dies: owned PID is the sleeper itself (no wrapper, no orphan); it
#    dies on SIGTERM and is reaped (143), no fault.
r = run('sleep 100 & c=$!; rc=0; quiesce_owned "$c" t || rc=$?; '
        'echo RC=$rc EXIT=$owned_exit; echo FAULTS=[$quiesce_faults]')
assert 'RC=0 EXIT=143' in r.stdout and 'FAULTS=[]' in r.stdout, r.stdout + r.stderr

# 3. SIGKILL needed: the owned PID is itself the process that installs trap "" TERM
#    and then blocks on a reader (no child, so no orphan). Readiness is
#    synchronized before quiesce_owned runs, so SIGTERM cannot arrive before the
#    trap is installed. The child must survive SIGTERM and die only on SIGKILL,
#    so the asserted reaped status is 137 (128+9). exec is deliberately NOT used
#    to "keep the sleeper at the owned PID" because exec resets the TERM trap.
r = run('rdy=$($BB mktemp); fifo=$($BB mktemp -u); $BB mkfifo "$fifo"; '
        'sh -c \'trap "" TERM; echo r > "$1"; read _ < "$2"\' sh "$rdy" "$fifo" & c=$!; '
        'i=0; while [ ! -s "$rdy" ] && [ "$i" -lt 100 ]; do $BB sleep 0.02; i=$((i+1)); done; '
        'rc=0; quiesce_owned "$c" t || rc=$?; '
        'echo RC=$rc EXIT=$owned_exit; echo FAULTS=[$quiesce_faults]; $BB rm -f "$rdy" "$fifo"')
assert 'RC=0 EXIT=137' in r.stdout and 'FAULTS=[]' in r.stdout, r.stdout + r.stderr

# 4. KILL-resistant: kill is stubbed so the child never dies (kill -0 stays true);
#    quiesce_owned must record the fault (identity preserved) and return 1, never hang.
r = run('kill() { return 0; }\n'
        'c=4242; rc=0; quiesce_owned "$c" wpa-supplicant || rc=$?; '
        'echo RC=$rc; echo FAULTS=[$quiesce_faults]')
assert 'RC=1' in r.stdout and 'FAULTS=[4242:wpa-supplicant]' in r.stdout, r.stdout + r.stderr
assert '__QUIESCE_FAIL__ pid=4242 name=wpa-supplicant' in r.stderr, r.stderr

# 5. run_bounded window close: the window closes mid-run; the owned child is
#    quiesced, rb_pid cleared, 137 returned.
r = run('window_ok() { return 1; }\nrc=0; run_bounded 1 30 /dev/null sleep 100 || rc=$?; '
        'echo RC=$rc; echo RBPID=[$rb_pid] FAULTS=[$quiesce_faults]')
assert 'RC=137' in r.stdout and 'RBPID=[]' in r.stdout and 'FAULTS=[]' in r.stdout, r.stdout + r.stderr

# 6. run_bounded normal completion: child exits inside the window; status returned, rb_pid cleared.
r = run('window_ok() { return 0; }\nrc=0; run_bounded 1 30 /dev/null true || rc=$?; '
        'echo RC=$rc; echo RBPID=[$rb_pid]')
assert 'RC=0' in r.stdout and 'RBPID=[]' in r.stdout, r.stdout + r.stderr


def on_exit_harness(stub_kill):
    """Build a shell that installs the ACTUAL traps, owns a live bounded helper,
    and blocks until a real SIGTERM arrives. The device record path is redirected
    to $REC (the only test-only change to on_exit). With stub_kill, quiesce_owned
    cannot terminate the owned child, so on_exit must record the fault."""
    on_exit = ON_EXIT.replace('/tmp/mt6797-wifi-phase-b-1', '$REC')
    body = (('kill() { return 0; }\n' if stub_kill else '')
            + STOP_SSHD + QUIESCE + on_exit
            + '\ntrap on_exit EXIT\ntrap \'exit 1\' HUP INT TERM\n'
            + 'sleep 100 & rb_pid=$!\n$BB printf \'%s\' "$rb_pid" > "$RBPIDFILE"\n'
            + ': > "$READYFILE"\nread _ < "$FIFO" || true\n')
    return PRELUDE + body


def run_on_exit(stub_kill):
    d = Path(tempfile.mkdtemp(prefix='leaf-onexit-'))
    rec = d / 'rec'
    rec.mkdir()
    rbf = d / 'rbpid'
    ready = d / 'ready'
    fifo = d / 'fifo'
    os.mkfifo(fifo)
    script = d / 'h.sh'
    script.write_text(on_exit_harness(stub_kill))
    env = dict(os.environ, REC=str(rec), RBPIDFILE=str(rbf), READYFILE=str(ready), FIFO=str(fifo))
    p = subprocess.Popen(['/bin/sh', str(script)], env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(200):
            if ready.exists() and rbf.exists() and rbf.read_text():
                break
            time.sleep(0.02)
        rb = int(rbf.read_text())
        os.kill(p.pid, signal.SIGTERM)       # real signal, from the parent
        p.wait(timeout=40)
        record = (rec / 'quiescence').read_text() if (rec / 'quiescence').exists() else ''
        rb_alive = True
        try:
            os.kill(rb, 0)
        except OSError:
            rb_alive = False
        return record, rb_alive, rb
    finally:
        try:
            p.kill()
        except OSError:
            pass
        try:
            os.kill(rb, signal.SIGKILL)       # the stubbed-kill case leaves it alive
        except (OSError, UnboundLocalError, ValueError):
            pass
        shutil.rmtree(d, ignore_errors=True)


# 7. on_exit on a real SIGTERM: the owned bounded helper is quiesced, the record
#    is written with an empty faults line, and the owned child is gone.
record, rb_alive, _ = run_on_exit(stub_kill=False)
assert 'faults=\n' in record or record.rstrip().endswith('faults='), 'record=%r' % record
assert 'boot=' in record, 'record=%r' % record
assert not rb_alive, 'on_exit left the owned bounded helper alive'

# 8. on_exit when the owned child cannot be quiesced (kill stubbed): the record
#    names the fault, so the host holds the RAM-wiping recovery (recovery hold).
record, _, rb = run_on_exit(stub_kill=True)
assert ('faults=%d:bounded-helper' % rb) in record, 'record=%r rb=%s' % (record, rb)

print('run-leaf-wait: PASS (normal exit, SIGTERM-dies, SIGKILL-needed exit137, '
      'KILL-resistant fault, window-close quiesce, normal completion, on_exit signal '
      'quiesce + record, on_exit recovery-hold; helper bodies identical across both leaves)')
