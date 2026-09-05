#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Recovery program structure and combined transcript mutations; no hardware."""
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = load('recovery_builder', HERE / 'build-recovery-runtime.py')
classifier = load('recovery_classifier', HERE / 'classify-recovery-runtime.py')
fixture = load('frequency_fixture', ROOT / 'experiments/2026-09-04-mt6797-a72-frequency-observation/scripts/test-production-runtime.py')
BOOT = fixture.BOOT_ID
SHELL = json.loads(os.environ.get('GEMINI_TEST_SHELL', '["sh"]'))


def record(n, maximum):
    start = (1_000_000_000, 2_000_000_000, 4_000_010_000)[n - 1]
    values = [maximum - 600 + i * 100 for i in range(7)]
    return (f'abi=1 attempt={n} error=0 complete=1 count=7 valid_mask=127 winner=6 maximum={maximum} '
            f'start_ns={start} end_ns={start + 10000}\n' + ''.join(
                f'slot={i} bank={b} sensor={s} temperature={v} valid=1\n'
                for i, (b, s, v) in enumerate(zip((0, 1, 2, 2, 3, 4, 5),
                                                 (0, 3, 1, 2, 1, 1, 1), values))))


def snapshot(label, n, maximum):
    return (f'__THERMAL_RECOVERY_{label}_BEGIN__\n' + record(n, maximum) +
            f'__THERMAL_RECOVERY_{label}_END__\nthermal_{label}_millicelsius={maximum}\n'
            f'snapshot_{label}_attempt={n}\n')


def capture(complete=41900):
    raw = fixture.passing_capture().replace(fixture.CURRENT_RELEASE, classifier.RELEASE)
    raw = re.sub(r'thermal_during_millicelsius=[0-9]+\n', '', raw)
    for n, label, maximum in ((1, 'before', 36300), (2, 'after', complete)):
        raw = re.sub('thermal_' + label + r'_millicelsius=[0-9]+\n',
                     lambda _: snapshot(label, n, maximum), raw)
    recovery = ('recovery_workers_before=quiescent\nrecovery_files_before=absent\n'
                'recovery_sleep_requested_seconds=2\nrecovery_workers_after=quiescent\n'
                'recovery_files_after=absent\n' + snapshot('recovery', 3, 37500) +
                'recovery_timing=within-declared-window\n')
    raw = raw.replace('cleanup_file8=absent\n', recovery + 'cleanup_file8=absent\n')
    return raw.replace('__GEMINI_A72_CONCURRENT_MULTILINE_END__',
                       'owned_workers_reaped=yes\ncancellation_file=absent\nsnapshot_final_attempts=3\n'
                       '__GEMINI_A72_CONCURRENT_MULTILINE_END__')


def main():
    program = builder.build(BOOT)
    original = builder.parent().build(BOOT)
    # Compare complete real child bodies, including affinity and round loops.
    bodies = lambda text: re.findall(r'\$BB taskset (?:100|200) \$BB sh -c (.*?) >', text, re.S)
    assert len(bodies(program)) == 4 and bodies(program) == bodies(original)
    assert program.count('spawn_in_progress=1\n') == 4
    assert program.count('$BB sleep 2') == 1
    assert program.count('cat "$SNAPSHOT"') == 1
    assert 'thermal_during' not in program and 'attribution_observe' not in program
    assert 'ROUNDS=4\nSPIN_LIMIT=1000000\n' in program
    assert '/dev/mmcblk' not in program and 'poweroff' not in program
    ordered = ['recovery_snapshot before\n', 'spawn_in_progress=1\n',
               'recovery_frequency during\n', 'touch "$START_WRITE"',
               'reader9_status=$?; reader_pid9=', 'recovery_snapshot after\n',
               'cleanup || finish_failure recovery-cleanup-failed',
               'recovery_workers_before=quiescent', '$BB sleep 2',
               'recovery_workers_after=quiescent', 'recovery_snapshot recovery\n']
    positions = [program.index(marker) for marker in ordered]
    assert positions == sorted(positions)
    for boot in classifier.CLOSED_BOOTS:
        try:
            builder.build(boot)
        except ValueError:
            continue
        raise AssertionError('consumed boot accepted')
    valid = capture()
    result = classifier.classify(valid, BOOT, 35100)
    assert result['classification'] == 'bounded-recovery-comparison-rejected'
    assert result['thermal']['slots'][6]['response'] == 'decreased'
    assert result['full_integrated_repeatability'] == 'not-established'
    assert classifier.classify(capture(36500), BOOT, 35100)['classification'] == 'bounded-recovery-observed'
    mutations = []
    for old, new in [('recovery_workers_before=quiescent', 'recovery_workers_before=active'),
                     ('recovery_workers_after=quiescent', 'recovery_workers_after=active'),
                     ('recovery_files_before=absent', 'recovery_files_before=present'),
                     ('recovery_files_after=absent', 'recovery_files_after=present'),
                     ('recovery_sleep_requested_seconds=2', 'recovery_sleep_requested_seconds=3'),
                     ('start_ns=4000010000', 'start_ns=4000009999'),
                     ('start_ns=4000010000', 'start_ns=5000010001'),
                     ('reader9_status=0', 'reader9_status=1'),
                     ('writer8_alive_after_observation=1', 'writer8_alive_after_observation=0'),
                     ('cleanup_file8=absent', 'cleanup_file8=present'),
                     ('owned_workers_reaped=yes', 'owned_workers_reaped=no'),
                     ('snapshot_after_attempt=2', 'snapshot_after_attempt=3'),
                     ('thermal_recovery_millicelsius=37500', 'thermal_recovery_millicelsius=37600'),
                     ('valid_mask=127', 'valid_mask=126'),
                     ('rounds=4', 'rounds=5'),
                     ('kernel_release=' + classifier.RELEASE, 'kernel_release=wrong')]:
        assert old in valid, old
        mutations.append(valid.replace(old, new, 1))
    mutations += [valid + 'snapshot_final_attempts=3\n',
                  valid + 'thermal_during_millicelsius=36000\n',
                  valid.replace('recovery_workers_after=quiescent\n', '') + 'recovery_workers_after=quiescent\n',
                  valid.replace('frequency_after=', 'frequency_after_missing=', 1)]
    for raw in mutations:
        try:
            classifier.classify(raw, BOOT, 35100)
        except ValueError:
            continue
        raise AssertionError('mutated runtime admitted')
    with tempfile.TemporaryDirectory(prefix='gemini-recovery-runtime-', dir='/tmp') as tmp:
        path = Path(tmp) / 'program.sh'; path.write_text(program)
        subprocess.run(SHELL + ['-n', str(path)], check=True)
        subprocess.run(['shellcheck', str(path)], check=True)
        for raw, expected in ((valid, 3), (capture(36500), 0), (mutations[0], 1)):
            path = Path(tmp) / 'capture.txt'; path.write_text(raw)
            result = subprocess.run([sys.executable, str(HERE / 'classify-recovery-runtime.py'),
                                     str(path), '--boot-id', BOOT, '--initial', '35100'],
                                    capture_output=True, text=True)
            assert result.returncode == expected, result.stderr
    print(f'recovery_builder=pass unchanged_worker_bodies=4 combined_cases=2 '
          f'combined_mutations_rejected={len(mutations)} consumed_boots_rejected=4 '
          'cli_cases=3 device_action=none')


if __name__ == '__main__':
    main()
