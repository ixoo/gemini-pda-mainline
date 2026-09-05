#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Pure local patch-input checks; no schema, compiler, builder or device run."""
import hashlib
import json
from pathlib import Path
import derive

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
raw = (ROOT / derive.PATCH).read_bytes()
payload = derive.derive(raw)
header_lines = [line[1:] for line in payload.decode().splitlines()
                if line.startswith('+') and not line.startswith('+++')]
assert len(header_lines) == 8
assert '#define MT6797_INFRA_THERM_CTRL_RST\t0' in header_lines
assert '#define MT6797_INFRA_PMIC_WRAP_RST\t1' in header_lines
assert len([line for line in header_lines if line.startswith('#define MT6797_')]) == 2
for bad in [raw + b'\n', raw.replace(b'MT6797_INFRA_PMIC_WRAP_RST\t1', b'MT6797_INFRA_PMIC_WRAP_RST\t2'), raw.replace(b'+          - mediatek,mt6797-infracfg\n', b'')]:
    try:
        derive.derive(bad)
    except ValueError:
        pass
    else:
        raise AssertionError('changed input admitted')
fixtures = json.loads((HERE / 'fixtures.json').read_text())['cases']
assert len(fixtures) == 25 and len({f['name'] for f in fixtures}) == 25
assert sum(f['expected_valid'] for f in fixtures) == 10
print(json.dumps({'derivation':'pass','input_sha256':derive.PATCH_SHA256,
 'derived_git_diff_sha256':hashlib.sha256(payload).hexdigest(),
 'derived_git_diff_bytes':len(payload),'header_bytes_preserved':True,
 'changed_input_refusals':3,'prepared_schema_cases':len(fixtures),
 'schema_cases_executed':0,'backend_actions':False},indent=2))
