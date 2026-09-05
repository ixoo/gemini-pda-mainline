#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""One harmless fixture run; persist failure bytes before removing temporary state."""
import argparse
import json
import os
from pathlib import Path
import runpy
import struct
import time

HERE = Path(__file__).resolve().parent
P = runpy.run_path(str(HERE / 'duration-proof.py'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--compiler', required=True)
    parser.add_argument('--qemu', required=True)
    parser.add_argument('--tool-inputs', required=True)
    parser.add_argument('--musl-archive', required=True)
    parser.add_argument('--library-root', required=True)
    parser.add_argument('--work-root', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--cleanup-receipt', required=True)
    args = parser.parse_args()
    os.umask(0o077)
    output = Path(args.output)
    output.mkdir(mode=0o700)  # Never overwrite an earlier measurement.
    os.environ.update(MONITOR_TEST_CC=args.compiler, MONITOR_TEST_QEMU=args.qemu,
                      MONITOR_TEST_WORK_ROOT=args.work_root, MONITOR_TEST_FULL_DURATION='1',
                      MONITOR_TEST_FIXTURE_ONLY='1')
    module = runpy.run_path(str(HERE / 'test-monitor.py'))
    cls = module['MonitorTests']
    case = cls('runTest')
    error, binary, completed = None, b'', False
    inputs = {'schema': 'keyboard-duration-inputs-v1', 'sources': P['sources'](),
              'mode': 'harmless-ignore-production-duration-arm64-qemu',
              'musl_archive_sha256': P['sha'](Path(args.musl_archive).read_bytes()),
              'tool_inputs_sha256': P['sha'](Path(args.tool_inputs).read_bytes()),
              'tools': {key: P['sha'](Path(value).resolve().read_bytes())
                        for key, value in [('compiler', args.compiler), ('qemu', args.qemu)]},
              'library': {str(p.relative_to(args.library_root)): P['sha'](p.read_bytes())
                          for p in sorted(Path(args.library_root).rglob('*')) if p.is_file()}}
    try:
        cls.setUpClass()
        binary = cls.fixture.read_bytes()
        P['require'](binary[:6] == b'\x7fELF\x02\x01' and
                     struct.unpack_from('<H', binary, 18)[0] == 183, 'fixture ARM64 ELF')
        phoff = struct.unpack_from('<Q', binary, 32)[0]
        size, count = struct.unpack_from('<HH', binary, 54)
        P['require'](size == 56 and count > 0 and phoff + size * count <= len(binary), 'ELF headers')
        P['require'](all(struct.unpack_from('<I', binary, phoff + i * size)[0] not in (2, 3)
                         for i in range(count)), 'fixture must be static')
        case.setUp()
        case.run_case('ignore')
        P['require'](P['sources']() == inputs['sources'] and cls.fixture.read_bytes() == binary,
                     'source/fixture changed during measurement')
        completed = True
    except Exception as exc:
        error = type(exc).__name__ + ': ' + str(exc)[:1024]
    finally:
        # No cleanup on preservation failure or uncertain terminal state. The
        # fixture-only harness uses explicit directories without auto-finalizers.
        last = getattr(case, 'last_run', {})
        process = {'returncode': last['process'].returncode if last else None,
                   'elapsed_seconds': time.monotonic() - last['start'] if last else 0,
                   'error': error}
        inputs['fixture_sha256'] = P['sha'](binary)
        values = {'inputs.json': (json.dumps(inputs, sort_keys=True) + '\n').encode(),
                  'process.json': (json.dumps(process, sort_keys=True) + '\n').encode(),
                  'fixture': binary, 'stdout': bytes(last.get('stdout', b'')),
                  'stderr': bytes(last.get('stderr', b''))}
        for name in ('observer.stdout', 'observer.stderr', 'monitor.status'):
            path = case.root / 'keyboard-attempt' / name if hasattr(case, 'root') else None
            values[name] = P['read'](path, 131072) if path and path.exists() else b''
        for name, raw in values.items():
            P['write'](output / name, raw)
        P['seal'](output)
        P['require'](completed and process['returncode'] is not None,
                     'sealed proof retained with original stage: terminal state uncertain')
        P['require'](case.doCleanups(), 'fixture cleanup failed; retain stage')
        cls.doClassCleanups()
        P['require'](not cls.tearDown_exceptions, 'build cleanup failed; retain stage')
        P['write'](Path(args.cleanup_receipt), b'sealed-terminal-cleanup-complete\n')
    # Structurally complete failed runs are publishable evidence, never a pass.
    print(json.dumps(P['classify'](output, inputs['sources']), sort_keys=True))


if __name__ == '__main__':
    main()
