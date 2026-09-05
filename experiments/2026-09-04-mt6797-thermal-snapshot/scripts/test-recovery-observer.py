#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run the generated snapshot function with files instead of hardware."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('fixtures', HERE / 'test-recovery-runtime.py')
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)
SHELL = json.loads(os.environ.get('GEMINI_TEST_SHELL', '["sh"]'))


def main():
    program = f.builder.build(f.BOOT)
    fragment = program[program.index('recovery_snapshot()\n'):
                       program.index("$BB printf '%s\\n' __A72_FREQUENCY_THERMAL_BEGIN__")]
    cases = [('before', 1, 'valid'), ('after', 2, 'valid'), ('recovery', 3, 'valid')]
    cases += [('recovery', 3, kind) for kind in ('hot', 'fraction', 'mask', 'winner',
                                               'truncated', 'stale', 'post-count', 'read-failed')]
    with tempfile.TemporaryDirectory(prefix='gemini-recovery-observer-', dir='/tmp') as tmp:
        root = Path(tmp)
        adapter = root / 'bb'
        adapter.write_text('''#!/bin/sh
if [ "$1" = cat ] && [ "$2" = "$SNAPSHOT" ]; then
 printf 'read\\n' >> "$COUNT"
 printf 'abi=1 attempts=%s limit=3\\n' "$NEXT" > "${SNAPSHOT}_status"
 [ "$KIND" != read-failed ] || exit 1
fi
if [ -n "${GEMINI_TEST_BUSYBOX:-}" ]; then exec "$GEMINI_TEST_BUSYBOX" "$@"; fi
exec "$@"
''')
        adapter.chmod(0o700)
        for label, n, kind in cases:
            snapshot = root / 'snapshot'; count = root / 'count'; count.write_text('')
            data = f.record(n, 59000 if kind == 'hot' else 37501 if kind == 'fraction' else 37500)
            if kind == 'mask': data = data.replace('valid_mask=127', 'valid_mask=126')
            if kind == 'winner': data = data.replace('winner=6', 'winner=0')
            if kind == 'truncated': data = data[:100]
            snapshot.write_text(data)
            Path(str(snapshot) + '_status').write_text(f'abi=1 attempts={3 if kind == "stale" else n-1} limit=3\n')
            script = f'''BB={adapter}
SNAPSHOT={snapshot}
COUNT={count}
KIND={kind}
NEXT={n+1 if kind == 'post-count' else n}
export SNAPSHOT COUNT KIND NEXT
frequency_reject() {{ printf 'refused=%s\\n' "$1"; exit 3; }}
{fragment}
recovery_snapshot {label}
'''
            outcome = subprocess.run(SHELL, input=script, text=True, capture_output=True)
            assert outcome.returncode == (0 if kind == 'valid' else 3), (kind, outcome.stderr)
            assert len(count.read_text().splitlines()) == (0 if kind == 'stale' else 1)
    print(f'generated_recovery_observer_cases={len(cases)} device_action=none')


if __name__ == '__main__':
    main()
