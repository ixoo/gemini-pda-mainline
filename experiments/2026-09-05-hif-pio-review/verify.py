#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compile exact project headers and bounded independent host fixtures."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REVISION = '54c9caac9aa947774b312107e1cb57904c912f50'
PREFIX = 'experiments/2026-09-05-mt6797-wifi-contract/src/'
files = ['hif_pio.h', 'hif_command.h', 'hif_transfer_size.h', 'hif_pio_test.c']
inputs = {name: subprocess.check_output(['git', '-C', str(ROOT), 'show', REVISION + ':' + PREFIX + name]) for name in files}
mutations = {
    'tx-byte-order': ('hif_pio.h', '<< (byte * 8)', '<< ((3 - byte) * 8)'),
    'rx-byte-order': ('hif_pio.h', '>> (byte * 8)', '>> ((3 - byte) * 8)'),
    'wrong-setup-offset': ('hif_pio.h', 'io->context, 0, command.word', 'io->context, 4, command.word'),
    'failed-read-stored': ('hif_pio.h', 'if (!error)\n', 'if (1)\n'),
    'capacity-check-removed': ('hif_transfer_size.h', 'bytes > capacity', '((void)capacity, false)'),
}
result = {'reviewed_commit': REVISION, 'scope': 'host scalar-callback behavior only',
          'input_sha256': {name: hashlib.sha256(data).hexdigest() for name, data in inputs.items()},
          'compiler': subprocess.check_output(['clang', '--version'], text=True).splitlines()[0],
          'mutants': {}}
with tempfile.TemporaryDirectory(prefix='hif-pio-review-', dir='/tmp') as temporary:
    work = Path(temporary)
    for name, data in inputs.items(): (work / name).write_bytes(data)
    (work / 'boundary-test.c').write_bytes((HERE / 'boundary-test.c').read_bytes())
    def compile_run(source):
        binary = work / 'test'
        subprocess.run(['clang', '-std=c11', '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined',
                        '-fno-sanitize-recover=all', '-g', str(work / source), '-o', str(binary)],
                       check=True, capture_output=True, timeout=30)
        return subprocess.run([str(binary)], capture_output=True, text=True, timeout=30)
    for source in ('hif_pio_test.c', 'boundary-test.c'):
        run = compile_run(source)
        assert run.returncode == 0 and not run.stderr, (source, run.stderr)
        result[source] = run.stdout.strip()
    for name, (file, before, after) in mutations.items():
        original = inputs[file].decode()
        assert original.count(before) == 1
        (work / file).write_text(original.replace(before, after))
        run = compile_run('boundary-test.c')
        assert run.returncode != 0 and ('Assertion failed' in run.stderr or 'Assertion' in run.stderr or 'AddressSanitizer' in run.stderr), (name, run.stderr)
        result['mutants'][name] = 'attributable assertion/sanitizer refusal'
        (work / file).write_bytes(inputs[file])
result['result'] = 'PASS'
print(json.dumps(result, indent=2))
