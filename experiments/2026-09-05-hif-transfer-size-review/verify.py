#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Review exact published helper bytes without editing the author's checkout."""
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
REVISION = 'b3e056c7f661ebd4533061d39c62d6bbb2b7efda'
PREFIX = 'experiments/2026-09-05-mt6797-wifi-contract/src/'
PINS = {'hif_transfer_size.h': '1c4542d509330474382d522924a2cb72795d2a806eae081d0c9f525699b3bd95',
        'hif_transfer_size_test.c': '3982e5152066562614e09e06adbe81e0d03217ad2bf3393ca250daf91b0f28ff'}


def limits():
    resource.setrlimit(resource.RLIMIT_FSIZE, (16 * 1024 * 1024,) * 2)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def run(args, work):
    with (work / 'stdout').open('w+b') as out, (work / 'stderr').open('w+b') as err:
        process = subprocess.Popen(args, stdout=out, stderr=err, start_new_session=True, preexec_fn=limits)
        try:
            code = process.wait(timeout=30)
        finally:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
        assert out.tell() <= 65536 and err.tell() <= 65536
        out.seek(0); err.seek(0)
        return code, out.read().decode(), err.read().decode()


def main():
    root = HERE.parents[1] / 'artifacts' / 'hif-transfer-size-review'
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    assert not root.is_symlink()
    with tempfile.TemporaryDirectory(prefix='review-', dir=root) as tmp:
        work = Path(tmp)
        for name, digest in PINS.items():
            data = subprocess.check_output(['git', 'show', REVISION + ':' + PREFIX + name], timeout=10)
            assert hashlib.sha256(data).hexdigest() == digest
            (work / name).write_bytes(data)
        (work / 'exhaustive.c').write_bytes((HERE / 'exhaustive.c').read_bytes())
        result = {'reviewed_revision': REVISION, 'input_sha256': PINS}
        code, out, err = run(['cc', '--version'], work)
        assert code == 0 and not err
        result['compiler'] = out.splitlines()[0]
        for source in ['hif_transfer_size_test.c', 'exhaustive.c']:
            code, out, err = run(['cc', '-std=c11', '-O1', '-Wall', '-Wextra', '-Werror', '-pedantic',
                                  '-fsanitize=address,undefined', '-I', str(work), str(work / source), '-o', str(work / 'fixture')], work)
            assert code == 0 and not out and not err
            code, out, err = run([str(work / 'fixture')], work)
            assert code == 0 and not err and 'result=pass' in out
            result[source] = out.strip()
        header = (work / 'hif_transfer_size.h').read_text()
        mutations = {'capacity-check-removed': (' || bytes > capacity', ''),
                     'count-512-admitted': ('count > 511U', 'count > 512U'),
                     'late-block-mode': ('bytes >= 512U', 'payload_bytes >= 512U'),
                     'failure-output-not-cleared': ('*result = (struct mt6797_hif_transfer_size) { 0 };', '')}
        refused = {}
        for name, (old, new) in mutations.items():
            assert header.count(old) == 1
            (work / 'hif_transfer_size.h').write_text(header.replace(old, new))
            code, out, err = run(['cc', '-std=c11', '-O1', '-I', str(work), str(work / 'exhaustive.c'), '-o', str(work / 'fixture')], work)
            assert code == 0 and not out and not err
            code, out, err = run([str(work / 'fixture')], work)
            assert code == 1 and not err and out.startswith('failure payload=')
            refused[name] = out.strip()
        result.update(mutations_refused=refused, kernel_backend_device_access=False,
                      temporary_files_removed=True)
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
