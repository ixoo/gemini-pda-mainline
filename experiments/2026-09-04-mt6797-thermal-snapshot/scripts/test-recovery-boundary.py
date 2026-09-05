#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Execute the actual recovery boundary with injected sleep/snapshot adapters."""
import importlib.util
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('builder', HERE / 'build-recovery-runtime.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
SHELL = json.loads(os.environ.get('GEMINI_TEST_SHELL', '["sh"]'))


def main():
    cases = ['pass', 'handle', 'spawn', 'pending', 'residue', 'symlink',
             'sleep-failed', 'post-residue', 'early', 'late', 'HUP', 'INT', 'TERM', 'PIPE']
    with tempfile.TemporaryDirectory(prefix='gemini-recovery-boundary-', dir='/tmp') as tmp:
        root = Path(tmp)
        adapter = root / 'bb'
        adapter.write_text('''#!/bin/sh
if [ "$1" = sleep ]; then
 printf 'sleep=%s\\n' "$2"
 case "$CASE" in
  sleep-failed) exit 1;;
  post-residue) touch "$RESIDUE";;
  HUP|INT|TERM|PIPE) kill -"$CASE" "$PPID";;
 esac
 exit 0
fi
if [ -n "${GEMINI_TEST_BUSYBOX:-}" ]; then exec "$GEMINI_TEST_BUSYBOX" "$@"; fi
exec "$@"
''')
        adapter.chmod(0o700)
        for case in cases:
            residue = root / 'residue'
            if residue.exists() or residue.is_symlink():
                residue.unlink()
            if case == 'residue':
                residue.touch()
            if case == 'symlink':
                residue.symlink_to(root / 'missing')
            names = ('FILE8', 'FILE9', 'OUT8', 'OUT9', 'READ8', 'READ9',
                     'START_WRITE', 'START_READ', 'CANCEL')
            assignments = '\n'.join(name + '=' + shlex.quote(str(residue)) for name in names)
            gap = 1_999_999_999 if case == 'early' else 3_000_000_001 if case == 'late' else 2_000_000_000
            script = f'''BB={shlex.quote(str(adapter))}
CASE={case}
RESIDUE={shlex.quote(str(residue))}
export CASE RESIDUE
{assignments}
pid8={'owned' if case == 'handle' else ''}
pid9=
reader_pid8=
reader_pid9=
spawn_in_progress={1 if case == 'spawn' else 0}
pending_exit={143 if case == 'pending' else 0}
completion_end_ns=2000010000
request_exit() {{ exit "$1"; }}
finish_failure() {{ printf 'refused=%s\\n' "$1"; exit 3; }}
recovery_snapshot() {{
 printf 'snapshot-called=%s\\n' "$1"
 snapshot_record='abi=1 attempt=3 error=0 complete=1 count=7 valid_mask=127 winner=0 maximum=37500 start_ns={2000010000+gap} end_ns={2000020000+gap}'
}}
{builder.RECOVERY}
'''
            outcome = subprocess.run(SHELL, input=script, text=True, capture_output=True)
            expected = {'pass': 0, 'HUP': 129, 'INT': 130, 'TERM': 143, 'PIPE': 141}.get(case, 3)
            assert outcome.returncode == expected, (case, outcome.stdout, outcome.stderr)
            calls = outcome.stdout.count('snapshot-called=')
            assert calls == (1 if case in ('pass', 'early', 'late') else 0), (case, outcome.stdout)
            if case == 'pass':
                assert outcome.stdout.index('recovery_workers_before=') < outcome.stdout.index('sleep=2')
                assert outcome.stdout.index('sleep=2') < outcome.stdout.index('recovery_workers_after=')
                assert outcome.stdout.index('recovery_workers_after=') < outcome.stdout.index('snapshot-called=')
    print(f'recovery_boundary_cases={len(cases)} caught_signals=4 '
          'no_snapshot_after_quiescence_or_sleep_refusal=pass device_action=none')


if __name__ == '__main__':
    main()
