#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Known-good-OS receipt and real recovery entrypoint fixtures; no device IO."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import runpy
import subprocess
import sys
import tempfile
from unittest.mock import patch

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


host = load('gemian_host', HERE / 'run-gemian-recovery.py')
f = load('runtime_fixture', HERE / 'test-recovery-runtime.py')
sf = runpy.run_path(str(HERE / 'test-observation-state.py'))
pre = sf['raw'].replace('record_identity=' + sf['record'],
                       'record_identity=' + host.CORE.module('observation_protocol').RECORD).replace(sf['boot'], f.BOOT)
raw_receipt = (HERE.parent / 'results/no-workload-deployment.txt').read_text().replace(
    'd9c1a1b3-72bc-43cb-99b4-e78b809592ce', host.GEMIAN_BOOT)
real_run = subprocess.run
real_module = host.CORE.module
base = real_module('run-observation')
base.interface = lambda: 'fixture'


def modules(name):
    return base if name == 'run-observation' else real_module(name)


def write_receipt(directory, raw):
    path = directory / 'deployment-summary.txt'
    path.write_text(raw); path.chmod(0o600)
    manifest = directory / 'SHA256SUMS'
    manifest.write_text(hashlib.sha256(raw.encode()).hexdigest() + '  deployment-summary.txt\n')
    manifest.chmod(0o600)
    return path


def main():
    host.sources()
    with tempfile.TemporaryDirectory(prefix='gemini-recovery-gemian-', dir='/tmp') as tmp:
        root = Path(tmp); root.chmod(0o700)
        directory = root / 'deployment'; directory.mkdir(mode=0o700)
        path = write_receipt(directory, raw_receipt)
        receipt_mutations = []
        for line in raw_receipt.splitlines():
            key, _ = line.split('=', 1)
            receipt_mutations.append(re.sub(r'^' + key + '=.*$', key + '=wrong', raw_receipt, flags=re.M))
        receipt_mutations += [raw_receipt + 'boot_id=' + host.GEMIAN_BOOT + '\n',
                              raw_receipt.replace('reboot=no\n', '')]
        with patch.object(host, 'RECEIPT', path):
            assert host.receipt()[0] == raw_receipt
            # The matching-image branch is also accepted, with exact predecessor.
            skipped = re.sub(r'^predecessor_sha256=.*$',
                             'predecessor_sha256=' + real_module('observation_protocol').CANDIDATE,
                             raw_receipt, flags=re.M).replace('write-synced-flushed-full-readback-verified',
                                                             'skipped-already-matching')
            write_receipt(directory, skipped); assert host.receipt()[0] == skipped
            for raw in receipt_mutations:
                write_receipt(directory, raw)
                try: host.receipt()
                except ValueError: pass
                else: raise AssertionError('bad receipt admitted')
            write_receipt(directory, raw_receipt)
            (directory / 'extra').touch()
            try: host.receipt()
            except ValueError: pass
            else: raise AssertionError('extra evidence admitted')
            (directory / 'extra').unlink()
            path.chmod(0o644)
            try: host.receipt()
            except ValueError: pass
            else: raise AssertionError('unsafe mode admitted')
            path.chmod(0o600)
            (directory / 'SHA256SUMS').write_text('invalid\n')
            try: host.receipt()
            except ValueError: pass
            else: raise AssertionError('invalid manifest admitted')
            write_receipt(directory, raw_receipt)
        scenarios = ('observed', 'comparison-reject', 'pre-Gemian-boot', 'pre-consumed', 'pre-hot',
                     'runtime-timeout', 'runtime-truncated', 'runtime-nonzero', 'interrupt',
                     'post-timeout', 'post-boot', 'post-hot', 'post-accounting', 'post-missing')
        for scenario in scenarios:
            case = root / scenario; case.mkdir(mode=0o700)
            calls = []
            runtime = f.capture(41900 if scenario == 'comparison-reject' else 36500)
            terminal = f.classifier.scalar(runtime, 'post_status')
            def fake_run(args, **kwargs):
                if args[0] == 'git' and 'check-ignore' in args:
                    return subprocess.CompletedProcess(args, 0)
                if args[0] != 'nc': return real_run(args, **kwargs)
                calls.append(args); n = len(calls)
                if n == 1:
                    raw = pre
                    if scenario == 'pre-Gemian-boot': raw = raw.replace(f.BOOT, host.GEMIAN_BOOT)
                    if scenario == 'pre-consumed': raw = raw.replace(f.BOOT, host.CORE.SOURCE_BOOT)
                    if scenario == 'pre-hot': raw = re.sub('thermal_temperature_millicelsius=[0-9]+', 'thermal_temperature_millicelsius=59000', raw)
                elif n == 2:
                    assert (case / 'run/workload.requested').read_text() == 'requested=yes\n'
                    assert (case / 'run/program.sh').is_file() and kwargs['timeout'] == 125
                    if scenario == 'runtime-timeout': raise subprocess.TimeoutExpired(args, 125, output=b'partial')
                    if scenario == 'interrupt': raise KeyboardInterrupt()
                    if scenario == 'runtime-nonzero': return subprocess.CompletedProcess(args, 1, b'partial', b'')
                    raw = runtime[:100] if scenario == 'runtime-truncated' else runtime
                else:
                    assert n == 3
                    if scenario == 'post-timeout': raise subprocess.TimeoutExpired(args, 20, output=b'partial')
                    raw = pre
                    for key, value in {'cpu_online': '0-9', 'cpu_offline': '', 'frequency_log_count': '3',
                                       'live_status': terminal, 'thermal_snapshot_status': 'abi=1 attempts=3 limit=3'}.items():
                        raw = re.sub('^' + key + '=.*$', key + '=' + value, raw, flags=re.M)
                    if scenario == 'post-boot': raw = raw.replace(f.BOOT, host.GEMIAN_BOOT)
                    if scenario == 'post-hot': raw = re.sub('thermal_temperature_millicelsius=[0-9]+', 'thermal_temperature_millicelsius=59000', raw)
                    if scenario == 'post-accounting': raw = raw.replace('frequency_log_count=3', 'frequency_log_count=2')
                    if scenario == 'post-missing': raw = raw.replace('cpu_present=0-9\n', '')
                return subprocess.CompletedProcess(args, 0, raw.encode(), b'')
            with patch.object(host, 'RECEIPT', path), patch.object(host, 'RUN', case / 'run'), \
                 patch.object(host.CORE, 'module', side_effect=modules), \
                 patch.object(subprocess, 'run', side_effect=fake_run), \
                 patch.object(sys, 'argv', ['runner', '--execute']):
                try: result = host.main()
                except (ValueError, KeyboardInterrupt): assert scenario not in ('observed', 'comparison-reject'), scenario
                else: assert result == (3 if scenario == 'comparison-reject' else 0) and scenario in ('observed', 'comparison-reject'), scenario
                assert len(calls) <= 3
                assert (case / 'run/workload.requested').exists() == (not scenario.startswith('pre-'))
                for line in (case / 'run/SHA256SUMS').read_text().splitlines():
                    sha, name = line.split('  '); assert hashlib.sha256((case / 'run' / name).read_bytes()).hexdigest() == sha
                count = len(calls)
                try: host.main()
                except FileExistsError: pass
                else: raise AssertionError('capture reopened')
                assert len(calls) == count
    print(f'Gemian_receipt_positive=2 receipt_mutations_rejected={len(receipt_mutations)} '
          f'evidence_boundary_refusals=3 host_scenarios={len(scenarios)} '
          f'restart_refusals={len(scenarios)} device_action=none')


if __name__ == '__main__':
    main()
