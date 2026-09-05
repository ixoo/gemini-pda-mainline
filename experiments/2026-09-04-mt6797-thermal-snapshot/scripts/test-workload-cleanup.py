#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Real shell child cancellation/reaping with injected RAM-operation adapters."""
from pathlib import Path
import re
import os
import json
import shlex
import signal
import time
import subprocess
import tempfile
from workload_cleanup import STOP, SOURCE, transform, materialize

SHELL=json.loads(os.environ.get('GEMINI_TEST_SHELL','["sh"]'))
assert isinstance(SHELL,list) and SHELL and all(isinstance(v,str) for v in SHELL)
SHELL_TEXT=shlex.join(SHELL)
text=materialize()
# Undo exactly the reviewed inline additions: every original worker byte survives.
original=SOURCE.read_text()
old_bodies=re.findall(r"\$BB taskset (?:100|200) \$BB sh -c '(.*?)\n' sh (?:writer|reader)[89]",original,re.S)
new_bodies=re.findall(r"\$BB taskset (?:100|200) \$BB sh -c '(.*?)\n' sh (?:writer|reader)[89]",text,re.S)
assert len(old_bodies)==len(new_bodies)==4
for old,new in zip(old_bodies,new_bodies):
    restored=new.replace('cancel=/run/.gemini-a72-concurrent-cancel\n','').replace('\t[ ! -e "$cancel" ] || exit 24\n','')
    assert restored==old
assert 'ROUNDS=4\nSPIN_LIMIT=1000000\n' in text
assert not re.search(r'\bkill\b',text)
try:transform(original.replace('ROUNDS=4','ROUNDS=5'))
except ValueError:pass
else:raise AssertionError('source mutation admitted')
with tempfile.TemporaryDirectory(prefix='gemini-cleanup-fixtures-',dir='/tmp') as tmp:
    root=Path(tmp)
    script=root/'materialized.sh';script.write_text(text)
    subprocess.run(SHELL+['-n',str(script)],check=True)
    subprocess.run(['shellcheck',str(script)],check=True)
    # Live children use the actual worker bodies. Only platform/operation adapters
    # change: host paths, proc affinity inputs, and a held finite RAM operation.
    adapter=root/'bb'
    adapter.write_text('''#!/bin/sh
case "$1" in
 dd|sha256sum)
  if [ "${HOLD_OPERATION:-0}" = 1 ]; then
   : > "$READY"
   n=0
   while [ ! -e "$CANCEL" ] && [ "$n" -lt 100 ]; do sleep .01; n=$((n+1)); done
   sleep .05
  fi
  ;;
esac
command=$1; shift
if [ -n "${GEMINI_TEST_BUSYBOX:-}" ]; then exec "$GEMINI_TEST_BUSYBOX" "$command" "$@"; fi
exec "$command" "$@"
''');adapter.chmod(0o700)
    for index in range(4):
        for phase in ('barrier','active','completed'):
            case=root/f'{index}-{phase}';case.mkdir()
            payload=case/'payload';payload.write_bytes(b'bounded payload\n')
            import hashlib
            sha=hashlib.sha256(payload.read_bytes()).hexdigest()
            cancel=case/'cancel';start=case/'start';ready=case/'ready';done=case/'done';target=case/'target'
            target.write_bytes(payload.read_bytes())
            body=new_bodies[index].replace("'\\''", "'")
            body=body.replace('BB=/bin/busybox',f'BB={adapter}').replace('cancel=/run/.gemini-a72-concurrent-cancel',f'cancel={cancel}')
            body=re.sub(r'affinity=\$\(.*?\)\nprocessor=\$\(.*?\)\n','affinity=8\nprocessor=8\n',body)
            worker=case/'worker.sh';worker.write_text(f"#!/bin/sh\ntrap 'touch {done}' EXIT\n"+body+'\n')
            args=f'writer {payload} {target} {start} 4 {sha} 1000000' if index<2 else f'reader {target} {start} 4 {sha} 1000000'
            if phase!='barrier':start.touch()
            harness=case/'parent.sh'
            harness.write_text(f'''#!/bin/sh
set -u
BB={adapter}
CANCEL={cancel}
export CANCEL
READY={ready}
export READY
HOLD_OPERATION={'1' if phase=='active' else '0'}
export HOLD_OPERATION
{STOP}
{SHELL_TEXT} {worker} {args} >{case/'output'} 2>&1 &
pid8=$!
'''+ (f'while [ ! -e {ready} ]; do sleep .01; done\n' if phase=='active' else f'wait "$pid8" || :; pid8=\n' if phase=='completed' else '')+f'''
stop_workers || exit 90
[ -e {done} ] || exit 91
[ -z "$pid8$pid9$reader_pid8$reader_pid9" ] || exit 92
rm -f {target}
sleep .02
[ ! -e {target} ] || exit 93
''')
            subprocess.run(SHELL+[str(harness)],check=True,timeout=5)
    # All four handles must be reaped, including mixed already-finished/live children.
    multi=root/'four-children.sh'
    multi.write_text(f"""#!/bin/sh
BB=/usr/bin/env
CANCEL={root/'four-cancel'}
{STOP}
(sleep .02; touch {root/'four-done-1'}) &
pid8=$!
(sleep .04; touch {root/'four-done-2'}) &
pid9=$!
(sleep .06; touch {root/'four-done-3'}) &
reader_pid8=$!
(sleep .08; touch {root/'four-done-4'}) &
reader_pid9=$!
stop_workers || exit 96
"""+''.join(f'[ -e {root/f"four-done-{n}"} ] || exit 97\n' for n in range(1,5)))
    subprocess.run(SHELL+[str(multi)],check=True,timeout=5)
    # Exercise the materialized signal traps and cleanup body, not a rewrite.
    cleanup=text[text.index('cleanup()\n'):text.index('file_state()\n')]
    traps=text[text.index('trap cleanup EXIT\n'):text.index("$BB printf '%s\\n' __GEMINI_A72_CONCURRENT_MULTILINE_BEGIN__")]
    for sig,code in ((signal.SIGHUP,129),(signal.SIGINT,130),(signal.SIGTERM,143),(signal.SIGPIPE,141)):
        case=root/f'signal-{sig}';case.mkdir()
        values='\n'.join(f'{key}={case/key}' for key in ('CANCEL','FILE8','FILE9','OUT8','OUT9','READ8','READ9','START_WRITE','START_READ'))
        harness=case/'parent.sh'
        harness.write_text(f"""#!/bin/sh
set -u
BB=/usr/bin/env
{values}
{STOP}
{cleanup}
{traps}
( n=0; while [ ! -e "$CANCEL" ] && [ "$n" -lt 200 ]; do sleep .01; n=$((n+1)); done
  touch "$FILE8"; touch {case/'done'} ) &
pid8=$!
touch {case/'ready'}
while :; do sleep .01; done
""")
        child=subprocess.Popen(SHELL+[str(harness)])
        try:
            deadline=time.monotonic()+3
            while not (case/'ready').exists() and time.monotonic()<deadline:time.sleep(.01)
            assert (case/'ready').exists()
            child.send_signal(sig)
            assert child.wait(timeout=5)==code
            assert (case/'done').exists() and not (case/'FILE8').exists()
        finally:
            if child.poll() is None:child.kill();child.wait()
    # Deliver TERM in the exact fork-to-registration gap: it must defer exit.
    gap=root/'spawn-gap';gap.mkdir()
    harness=gap/'parent.sh'
    values='\n'.join(f'{key}={gap/key}' for key in ('CANCEL','FILE8','FILE9','OUT8','OUT9','READ8','READ9','START_WRITE','START_READ'))
    harness.write_text(f"""#!/bin/sh
BB=/usr/bin/env
{values}
{STOP}
{cleanup}
{traps}
spawn_in_progress=1
( n=0; while [ ! -e "$CANCEL" ] && [ "$n" -lt 200 ]; do sleep .01; n=$((n+1)); done
  touch "$FILE8"; touch {gap/'done'} ) &
kill -TERM $$
pid8=$!
spawn_in_progress=0
[ "$pending_exit" = 0 ] || exit "$pending_exit"
exit 98
""")
    assert subprocess.run(SHELL+[str(harness)],timeout=5).returncode==143
    assert (gap/'done').exists() and not (gap/'FILE8').exists()
    # A failed cancellation publication still waits for finite owned children.
    failed=root/'failed-publication.sh'
    failed.write_text(f'''#!/bin/sh
BB=/usr/bin/false
CANCEL={root/'absent'}
{STOP}
(sleep .05; touch {root/'finite-done'}) &
pid8=$!
stop_workers && exit 94
[ -e {root/'finite-done'} ] || exit 95
''')
    subprocess.run(SHELL+[str(failed)],check=True,timeout=5)
    # Remove each essential half and prove the oracle refuses the mutant.
    for name,mutant in [('no-wait',STOP.replace('wait "$pid8" || :;',':;')),
                        ('no-cancel',STOP.replace('$BB touch "$CANCEL" || cancel_status=1',':'))]:
        case=root/name;case.mkdir()
        harness=case/'parent.sh'
        harness.write_text(f'''#!/bin/sh
BB=/usr/bin/env
CANCEL={case/'cancel'}
{mutant}
( n=0; while [ ! -e "$CANCEL" ] && [ "$n" -lt 50 ]; do sleep .01; n=$((n+1)); done
  [ -e "$CANCEL" ] || exit 24
  sleep .05; touch {case/'done'} ) &
pid8=$!
saved_pid=$pid8
stop_workers
[ -e {case/'done'} ]; result=$?
wait "$saved_pid" 2>/dev/null || :
exit "$result"
''')
        assert subprocess.run(SHELL+[str(harness)],timeout=5).returncode!=0
print('actual_worker_body_cases=12 signal_cleanup_cases=4 spawn_registration_signal_cases=1 simultaneous_children=4 cancellation_publication_failure=1 negative_cleanup_mutations=2 source_identity_mutations=1 original_worker_payload_bytes=preserved device_action=none')
