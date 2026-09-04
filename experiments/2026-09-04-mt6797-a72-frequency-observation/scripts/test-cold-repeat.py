#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Mutation fixtures for the additional boot-to-boot comparison boundary."""
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('comparison', HERE / 'compare-cold-repeat.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
baseline = m.fields(m.BASE.read_text())
valid = dict(baseline, boot_id='22222222-2222-4222-8222-222222222222')
m.compare(baseline, valid)
mutations = [dict(valid, boot_id=m.OLD_BOOT)]
for key in valid:
    missing = dict(valid)
    del missing[key]
    mutations.append(missing)
    if key != 'boot_id':
        changed = dict(valid)
        changed[key] = '0' if key.endswith('_accounting_delta') else '999999'
        mutations.append(changed)
mutations.append(dict(valid, unexpected_field='1'))
mutations.append(dict(valid, before_temperature_millicelsius='48500',
                      after_temperature_millicelsius='58700'))
for index, fixture in enumerate(mutations):
    try:
        m.compare(baseline, fixture)
    except ValueError:
        continue
    raise SystemExit(f'mutation {index} accepted')
try:
    m.fields('boot_id=one\nboot_id=two\n')
except ValueError:
    pass
else:
    raise SystemExit('duplicate field accepted')
print(f'comparison_mutations_rejected={len(mutations) + 1}')
print('result=pass')

# Exercise the actual pre-action gate with synthetic frames and cycle receipt.
import tempfile
spec = importlib.util.spec_from_file_location('pretest', HERE / 'test-production-pretrigger.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
with tempfile.TemporaryDirectory(prefix='gemini-cold-repeat-', dir='/tmp') as name:
    root = Path(name)
    m.RECEIPT = root / 'shutdown.txt'
    receipt = (f'boot_id={m.RECOVERY_BOOT}\nkernel_release=3.18.41+\n'
               'shutdown_requested=yes\nssh_disconnect_observed=yes\n'
               f'boot2_sha256={p.validator.CANDIDATE}\n'
               'partition_write=none\nbackup_created=no\nreboot_requested=no\n')
    m.RECEIPT.write_text(receipt)
    deployment = p.deployment()
    (root / 'deployment-summary.txt').write_text(deployment)
    pristine = p.baseline().replace('36500', '53500')
    (root / 'pretrigger.txt').write_text(pristine)
    assert m.gate(root) == p.RUNTIME_BOOT
    cases = [
        pristine.replace(p.RUNTIME_BOOT, m.OLD_BOOT),
        pristine.replace(p.RUNTIME_BOOT, m.RECOVERY_BOOT),
        pristine.replace('frequency_log_count=0', 'frequency_log_count=1'),
        pristine.replace('trigger_executions=0', 'trigger_executions=1'),
        pristine.replace('53500', '58501'),
        pristine.replace('53500', '48499'),
        pristine.replace('kernel_release=', 'missing_release='),
    ]
    for fixture in cases:
        (root / 'pretrigger.txt').write_text(fixture)
        try:
            m.gate(root)
        except ValueError:
            continue
        raise SystemExit('unsafe pretrigger accepted')
    (root / 'pretrigger.txt').write_text(pristine)
    for bad_deployment, bad_receipt in [
        (deployment.replace(p.validator.CANDIDATE, '0' * 64), receipt),
        (deployment, receipt.replace('ssh_disconnect_observed=yes', 'ssh_disconnect_observed=no')),
        (deployment, receipt.replace(m.RECOVERY_BOOT, p.RUNTIME_BOOT)),
        (deployment, receipt.replace(p.validator.CANDIDATE, '0' * 64)),
    ]:
        (root / 'deployment-summary.txt').write_text(bad_deployment)
        m.RECEIPT.write_text(bad_receipt)
        try:
            m.gate(root)
        except ValueError:
            continue
        raise SystemExit('unsafe candidate/cycle accepted')
print('cold_gate_mutations_rejected=11')
