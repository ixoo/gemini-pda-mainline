#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compile exact source bodies with stub framework calls; no kernel build.

Only --fetch-source reads the pinned public file. No source is persisted: the
translation unit goes to the host C compiler on stdin, with a bounded temporary
binary. No retained Buildbox source, package or device is touched.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import platform
from pathlib import Path
import shutil
import subprocess
import tempfile
import urllib.request

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('cleanup_derivation', HERE / 'derive.py')
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)


def run(raw):
    corrected = d.derive(raw)
    harness = (HERE / 'harness.c').read_text()
    marker = '/* SOURCE_FUNCTIONS: inserted from the exact hashed upstream source in memory. */'
    assert harness.count(marker) == 1
    compiler = shutil.which('cc')
    if not compiler:
        raise RuntimeError('host C compiler required')
    cases = {'corrected': corrected, 'original-regression': raw,
             'wrong-publication-failure-unwind': corrected.replace(
                 b'of_clk_add_hw_provider(node, of_clk_hw_onecell_get, clk_data);\n\tif (r)\n\t\tgoto unregister_clks;',
                 b'of_clk_add_hw_provider(node, of_clk_hw_onecell_get, clk_data);\n\tif (r)\n\t\tgoto unregister_provider;'),
             'late-removal-after-free': corrected.replace(
                 b'unregister_provider:\n\tof_clk_del_provider(node);',
                 b'unregister_provider:').replace(
                 b'free_data:\n\tmtk_free_clk_data(clk_data);',
                 b'free_data:\n\tmtk_free_clk_data(clk_data);\n\tof_clk_del_provider(node);')}
    results = {}
    with tempfile.TemporaryDirectory(prefix='gemini-clk-cleanup-', dir='/tmp') as scratch:
        for name, source in cases.items():
            if name not in ('corrected', 'original-regression') and source == corrected:
                raise AssertionError('mutation failed to change source')
            unit = harness.replace(marker, d.functions(source))
            binary = str(Path(scratch) / name)
            build = subprocess.run([compiler, '-std=c11', '-Wall', '-Wextra', '-Werror',
                                    '-x', 'c', '-', '-o', binary],
                                   input=unit, text=True, capture_output=True, timeout=15,
                                   env={**os.environ, 'LC_ALL': 'C'})
            if build.returncode:
                raise RuntimeError(build.stderr)
            result = subprocess.run([binary], text=True, capture_output=True, timeout=5)
            expect = name == 'corrected'
            if (result.returncode == 0) != expect:
                raise AssertionError(f'{name}: {result.stdout}\n{result.stderr}')
            results[name] = {'returncode': result.returncode, 'stdout': result.stdout,
                             'stderr': result.stderr}
    # Reject wrong complete input bytes rather than apply a guessed hunk.
    for bad in (raw[:-1], raw + b'\n', raw.replace(b'rst_desc', b'bad_desc', 1)):
        try:
            d.derive(bad)
        except ValueError:
            pass
        else:
            raise AssertionError('wrong input accepted')
    return {'source_sha256': d.SOURCE_SHA256,
            'corrected_source_sha256': hashlib.sha256(corrected).hexdigest(),
            'host_compiler': Path(compiler).name,
            'host_platform': platform.system() + '/' + platform.machine(),
            'compiler_version': subprocess.check_output([compiler, '--version'], text=True, timeout=5).splitlines()[0],
            'cases': results,
            'wrong_inputs_rejected': 3,
            'scope': 'exact probe/remove C bodies with stub framework calls; not kernel integration',
            'kernel_build': False, 'device_action': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch-source', action='store_true')
    args = parser.parse_args()
    if not args.fetch_source:
        parser.exit(message='No execution requested. Use --fetch-source for the pinned host-only fixture.\n')
    with urllib.request.urlopen(d.SOURCE_URL, timeout=15) as stream:
        source = stream.read(d.SOURCE_BYTES + 1)
    print(json.dumps(run(source), indent=2, sort_keys=True))
