#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Validate the new thermal contract without changing the rejected protocol."""
import importlib.util
from pathlib import Path
import tempfile

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


m = load('cold_rise', HERE / 'compare-cold-rise.py')
p = load('pretrigger_fixtures', HERE / 'test-production-pretrigger.py')
base = m.fields(m.BASE.read_text())
valid = dict(base, boot_id=m.TARGET_BOOT)
for label in ('before', 'during', 'after'):
    key = f'{label}_temperature_millicelsius'
    valid[key] = str(int(base[key]) - 18800)
m.compare(base, valid, 34000)
m.compare(base, dict(base, boot_id=m.TARGET_BOOT), 52800)
# Cold offsets translate all four samples together; no warm-start requirement.
for initial in (0, 15000, 30000, 45000):
    translated = dict(valid)
    for label in ('before', 'during', 'after'):
        key = f'{label}_temperature_millicelsius'
        translated[key] = str(initial + int(base[key]) - 52800)
    m.compare(base, translated, initial)

mutations = []
for key in valid:
    missing = dict(valid)
    del missing[key]
    mutations.append((missing, 34000))
    changed = dict(valid)
    changed[key] = '0' if key.endswith('_accounting_delta') else '999999'
    mutations.append((changed, 34000))
mutations += [(dict(valid, unexpected='1'), 34000),
              (dict(valid, boot_id=m.OLD_BOOT), 34000),
              (dict(valid, boot_id=m.RECOVERY_BOOT), 34000),
              (dict(valid, before_temperature_millicelsius='39701'), 34000),
              (dict(valid, before_temperature_millicelsius='29699'), 34000),
              (dict(valid, before_temperature_millicelsius='29700',
                    after_temperature_millicelsius='39700'), 34000),
              (valid, -1), (valid, 58501)]
for fixture, initial in mutations:
    try:
        m.compare(base, fixture, initial)
    except ValueError:
        continue
    raise SystemExit('unsafe summary mutation accepted')

with tempfile.TemporaryDirectory(prefix='gemini-cold-rise-', dir='/tmp') as name:
    root = Path(name)
    m.RECEIPT = root / 'receipt.txt'
    receipt = (f'boot_id={m.RECOVERY_BOOT}\nkernel_release=3.18.41+\n'
               'shutdown_requested=yes\nssh_disconnect_observed=yes\n'
               f'boot2_sha256={p.validator.CANDIDATE}\n'
               'partition_write=none\nbackup_created=no\nreboot_requested=no\n')
    m.RECEIPT.write_text(receipt)
    (root / 'deployment-summary.txt').write_text(p.deployment())
    pristine = p.baseline().replace(p.RUNTIME_BOOT, m.TARGET_BOOT).replace('36500', '34000')
    (root / 'pretrigger.txt').write_text(pristine)
    assert m.gate(root) == (m.TARGET_BOOT, 34000)
    fixtures = [pristine.replace('34000', '-1'), pristine.replace('34000', '58501'),
                pristine.replace('trigger_executions=0', 'trigger_executions=1'),
                pristine.replace('frequency_log_count=0', 'frequency_log_count=1'),
                pristine.replace(m.TARGET_BOOT, m.OLD_BOOT),
                pristine.replace(m.TARGET_BOOT, m.RECOVERY_BOOT),
                pristine.replace(m.TARGET_BOOT, p.RUNTIME_BOOT),
                pristine.replace(p.validator.RECORD_IDENTITY, '0' * 64)]
    for fixture in fixtures:
        (root / 'pretrigger.txt').write_text(fixture)
        try:
            m.gate(root)
        except ValueError:
            continue
        raise SystemExit('unsafe pristine mutation accepted')
    (root / 'pretrigger.txt').write_text(pristine)
    for bad in (receipt.replace('shutdown_requested=yes', 'shutdown_requested=no'),
                receipt.replace(p.validator.CANDIDATE, '0' * 64),
                receipt.replace(m.RECOVERY_BOOT, m.OLD_BOOT)):
        m.RECEIPT.write_text(bad)
        try:
            m.gate(root)
        except ValueError:
            continue
        raise SystemExit('unsafe cycle receipt accepted')
print(f'comparison_mutations_rejected={len(mutations)}')
print('gate_mutations_rejected=11')
print('positive_thermal_translations=6')
print('result=pass')

# Exercise CLI orchestration and inherited raw lifecycle/load classification.
import contextlib
import io
import sys
runtime = load('runtime_fixtures', HERE / 'test-production-runtime.py')
with tempfile.TemporaryDirectory(prefix='gemini-cold-rise-raw-', dir='/tmp') as name:
    root = Path(name)
    m.RECEIPT = root / 'receipt.txt'
    m.RECEIPT.write_text(receipt)
    (root / 'deployment-summary.txt').write_text(p.deployment())
    (root / 'pretrigger.txt').write_text(pristine)
    (root / 'runtime-events.txt').write_text(
        f'boot_id={m.TARGET_BOOT}\nnetcat_sessions=1\nretries=0\nclassification=pass\n'
        'native_reboot_command_sent=no\ndevice_left_running=yes\n')
    raw = runtime.passing_capture().replace(runtime.BOOT_ID, m.TARGET_BOOT)
    raw = raw.replace('thermal_before_millicelsius=36000', 'thermal_before_millicelsius=34700')
    raw = raw.replace('thermal_during_millicelsius=37000', 'thermal_during_millicelsius=34700')
    raw = raw.replace('thermal_after_millicelsius=36500', 'thermal_after_millicelsius=34900')
    sys.argv = ['compare-cold-rise.py', 'compare', '--capture', str(root)]
    def classify(text):
        (root / 'runtime.txt').write_text(text)
        with contextlib.redirect_stdout(io.StringIO()):
            return m.main()
    assert classify(raw) == 0
    changes = [('thermal_after_millicelsius=34900', 'thermal_after_millicelsius=40900'),
               ('writer8_rounds_completed=4', 'writer8_rounds_completed=5'),
               ('restore_last_stage=18', 'restore_last_stage=17'),
               ('frequency_log_count=3', 'frequency_log_count=4'),
               ('__A72_FREQUENCY_THERMAL_END__', ''),
               (m.TARGET_BOOT, m.OLD_BOOT)]
    for old, new in changes:
        assert old in raw
        assert classify(raw.replace(old, new)) != 0
print('raw_orchestration_positive=1')
print('raw_orchestration_mutations_rejected=6')
