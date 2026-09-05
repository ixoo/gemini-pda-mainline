#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline derivation and deployment-receipt refusal tests; no device IO."""
from pathlib import Path
import runpy
import subprocess
import tempfile
from v4_installer_guard import derive, GUARD_SHA256
from v4_deployment_receipt import receipt

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
source = (REPO / 'experiments/2026-08-14-mt6797-runtime-provenance-observer/scripts/install-boot2.sh').read_text()
guard = (REPO / 'scripts/boot2-device-guard.sh').read_bytes()
derived = derive(source, guard)
with tempfile.TemporaryDirectory(prefix='gemini-v4-guard-', dir='/tmp') as root:
    script = Path(root) / 'installer.sh'
    script.write_text(derived)
    subprocess.run(['bash', '-n', str(script)], check=True)
    subprocess.run(['shellcheck', str(script)], check=True)

for text, library in (
    (source, guard + b'\n'),
    (source.replace('root="$(readlink -f', 'root="$(readlink -e', 1), guard),
    (source.replace('\tdd if="$EXPECTED_STAGE"', '\tdd if="other"', 1), guard),
):
    try:
        derive(text, library)
    except ValueError:
        pass
    else:
        raise AssertionError('changed derivation source admitted')

fixture = runpy.run_path(str(HERE / 'test-observation-protocol.py'))
fields = dict(fixture['receipt_fields'], boot2_device_guard='passed',
              boot2_device_guard_sha256=GUARD_SHA256,
              target_major_minor='179:30', root_major_minor='179:29')


def encode(values):
    return ''.join(k + '=' + v + '\n' for k, v in values.items())


assert receipt(encode(fields), fixture['CANDIDATE']) == fixture['deploy']
# An observed root need not be the historically hard-coded p29.
assert receipt(encode(dict(fields, root='/dev/mmcblk0p28', root_major_minor='179:28')),
               fixture['CANDIDATE']) == fixture['deploy']
mutations = []
for key in ('boot2_device_guard', 'boot2_device_guard_sha256', 'root',
            'root_major_minor', 'target_major_minor'):
    changed = dict(fields)
    del changed[key]
    mutations.append(encode(changed))
    mutations.append(encode(dict(fields, **{key: ''})))
    mutations.append(encode(fields) + key + '=' + fields[key] + '\n')
for key, value in (
    ('boot2_device_guard', 'failed'), ('boot2_device_guard_sha256', '0' * 64),
    ('root', fields['target']), ('root', '/dev/root/../unknown'),
    ('root_major_minor', fields['target_major_minor']),
    ('root_major_minor', '0:29'), ('root_major_minor', '179:029'),
    ('target_major_minor', '4096:30'), ('target_major_minor', '179:1048576'),
):
    mutations.append(encode(dict(fields, **{key: value})))
for raw in mutations:
    try:
        receipt(raw, fixture['CANDIDATE'])
    except ValueError:
        pass
    else:
        raise AssertionError('bad block-identity receipt admitted')
print(f'guard_derivation_mutations=3 receipt_mutations={len(mutations)} syntax=pass shellcheck=pass device_access=none')
