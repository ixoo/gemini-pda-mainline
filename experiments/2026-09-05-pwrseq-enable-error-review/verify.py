#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check the existing upstream proposal against exact public source functions."""
import base64
import hashlib
import json
import os
import resource
from pathlib import Path
import signal
import subprocess
import tempfile
import urllib.request

HERE = Path(__file__).resolve().parent
EXPECTED = '86fe4cb3e77f1eeece1bd065ba7378bb5892499f344fb9de8af1761e449eda78'
PINS = [
    ('project-upstream', 'https://raw.githubusercontent.com/torvalds/linux/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/power/sequencing/core.c', EXPECTED),
    ('observed-mainline', 'https://raw.githubusercontent.com/torvalds/linux/0d9ff90a5422cc7509258aaaba1e7481df4d332a/drivers/power/sequencing/core.c', EXPECTED),
    ('pwrseq-for-current', 'https://kernel.googlesource.com/pub/scm/linux/kernel/git/brgl/linux/+/3b54dbd119805361695cb50ca6a875f4c7518b74/drivers/power/sequencing/core.c?format=TEXT', EXPECTED),
    ('pwrseq-for-next', 'https://kernel.googlesource.com/pub/scm/linux/kernel/git/brgl/linux/+/3b04e9b8056e868c3e9a04cc74168c7c9a18746a/drivers/power/sequencing/core.c?format=TEXT', EXPECTED),
    ('project-stable', 'https://kernel.googlesource.com/pub/scm/linux/kernel/git/stable/linux/+/199c9959d3a9b53f346c221757fc7ac507fbac50/drivers/power/sequencing/core.c?format=TEXT', '22550b6d006a42afc61c8f69e89ff6d0a2a3e545366dc317b8e2eff8f79f74f2'),
]

def require(ok, why):
    if not ok:
        raise ValueError(why)


def read_source(url, digest):
    with urllib.request.urlopen(url, timeout=15) as response:
        data = response.read(131073)
    require(len(data) <= 131072, 'source response ceiling')
    if url.endswith('?format=TEXT'):
        data = base64.b64decode(data, validate=True)
    require(hashlib.sha256(data).hexdigest() == digest, 'source identity')
    return data.decode()


def extract(source):
    name = 'pwrseq_enable' if 'int pwrseq_enable(' in source else 'pwrseq_power_on'
    start = source.index('int ' + name + '(')
    end = source.index('\nEXPORT_SYMBOL_GPL(' + name + ');', start)
    function = source[start:end]
    require(function.endswith('\n}'), 'function extraction boundary')
    return function, name


def apply_posted_fix(function):
    # Exact two-line change already posted by Bartosz Golaszewski on Sep 3.
    anchor = '\t\tif (!ret)\n\t\t\tdesc->powered_on = true;\n\t}\n\n\tif (target->post_enable) {'
    require(function.count(anchor) == 1, 'posted hunk applicability')
    return function.replace(anchor, anchor.replace('\n\n\tif (target', '\n\tif (ret)\n\t\treturn ret;\n\n\tif (target'))


def file_limit():
    resource.setrlimit(resource.RLIMIT_FSIZE, (1048576, 1048576))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def command(args, work):
    # Fixed trusted compiler/fixture commands; file capture avoids PIPE buffering.
    with (work / 'stdout').open('w+b') as out, (work / 'stderr').open('w+b') as err:
        process = subprocess.Popen(args, cwd=work, stdout=out, stderr=err, start_new_session=True, preexec_fn=file_limit)
        try:
            code = process.wait(timeout=15)
        finally:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
        require(out.tell() <= 65536 and err.tell() <= 65536, 'command capture ceiling')
        out.seek(0); err.seek(0)
        return code, out.read().decode(), err.read().decode()


def main():
    sources, functions = [], []
    for label, url, digest in PINS:
        source = read_source(url, digest)
        function, name = extract(source)
        functions.append(function.replace('pwrseq_power_on(', 'pwrseq_enable('))
        sources.append({'label': label, 'url': url, 'sha256': digest, 'function': name,
                        'posted_hunk_applies': apply_posted_fix(function) != function})
    require(len(set(functions)) == 1, 'reviewed function control flow changed')
    original = functions[0]
    fixed = apply_posted_fix(original)
    template = (HERE / 'fault-fixture.c').read_text()
    require(template.count('/* ACTUAL_FUNCTION */') == 1, 'fixture marker')
    root = HERE.parents[1] / 'artifacts' / 'pwrseq-enable-error-review'
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    require(not root.is_symlink(), 'managed temporary root is a symlink')
    results = {}
    with tempfile.TemporaryDirectory(prefix='fault-', dir=root) as tmp:
        work = Path(tmp)
        version_code, version, version_err = command(['cc', '--version'], work)
        require(version_code == 0 and not version_err, 'compiler identity')
        variants = {'original': original, 'posted-fix': fixed,
                    'wrong-success-return': fixed.replace('\tif (ret)\n\t\treturn ret;', '\tif (ret)\n\t\treturn 0;')}
        for label, function in variants.items():
            source = work / 'fixture.c'
            source.write_text(template.replace('/* ACTUAL_FUNCTION */', function))
            code, out, err = command(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', str(source), '-o', str(work / 'fixture')], work)
            require(code == 0 and not out and not err, 'fixture compilation failure')
            code, out, err = command([str(work / 'fixture')], work)
            require(not err and code in (0, 1), 'fixture crash/diagnostic')
            rows = dict(line.split('=') for line in out.splitlines())
            require(len(rows) == 10 and len(out.splitlines()) == 10, 'missing/duplicate fixture result')
            failed = sorted(k for k, value in rows.items() if value == 'fail')
            expected = {'original': ['unit-fail-post-error', 'unit-fail-post-success'],
                        'posted-fix': [],
                        'wrong-success-return': ['unit-fail-no-post', 'unit-fail-post-error', 'unit-fail-post-success']}[label]
            require(failed == expected and code == bool(failed), 'unexpected fault result')
            require(all(v in ('pass', 'fail') for v in rows.values()), 'invalid case status')
            results[label] = rows
    print(json.dumps({'sources': sources, 'compiler': version.splitlines()[0],
                      'stable_function_name_only_normalized': True, 'results': results,
                      'temporary_files_removed': True, 'kernel_build_or_device_access': False,
                      'scope': 'actual enable function; unit operations/device/locks stubbed; no concurrency or provider-lifetime proof'}, indent=2))

if __name__ == '__main__':
    main()
