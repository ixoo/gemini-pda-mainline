#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Use immutable attempt-2 errors with explicitly synthetic per-case captures."""
import copy
import hashlib
import json
from pathlib import Path
import compare

HERE=Path(__file__).resolve().parent
receipt=HERE/'results/attempt-2-b522e5e7'
raw=(receipt/'compare.stdout').read_bytes();stderr=(receipt/'compare.stderr').read_text()
assert hashlib.sha256(raw).hexdigest()=='3853dbc027ea0d4633aaa954f34f3957904d9443b162a1bfeab2273a0cc5082c'
assert hashlib.sha256(stderr.encode()).hexdigest()=='fc95e32cb76dce3832e66cd3c6ee1b088a6f26810eb385deca692b2ef7120c37'
original=json.loads(raw)['rows'];rows=copy.deepcopy(original)
cases=compare.load_cases(HERE/'fixtures.json');by_name={c['name']:c for c in cases}
synthetic_captures=[]
for row in rows:
    case=by_name[row['case']];prop=compare.raw_expected(case)
    captured=f'#reset-cells: size ({len(prop)}) error for type uint32\n' if prop is not None and len(prop) in (1,2) else ''
    synthetic_captures.append(captured)
    decoded_valid=row['valid']
    wire_valid=prop is None or len(prop)==4
    diagnostics=compare.decoder_record(case,prop,captured)
    row.update(decoded_schema_valid=decoded_valid, raw_reset_cells=compare.raw_record(prop),
               raw_width_valid=wire_valid, decoder_stderr=captured, decoder_diagnostics=diagnostics,
               valid=wire_valid and not diagnostics and decoded_valid)
# This partition agrees with retained ordering and audited decoder fallback,
# but it is not represented as new backend per-case evidence.
assert ''.join(synthetic_captures)==stderr
assert compare.classify(rows,cases)['rows']==50
assert all(row['decoded_schema_valid'] and not row['valid'] for row in rows if row['case']=='mt6797-byte')
rejected=0

def refuse(call):
    global rejected
    try:call()
    except ValueError:rejected+=1
    else:raise AssertionError('unsafe attribution accepted')

refuse(lambda:compare.classify(original,cases))
index=next(i for i,r in enumerate(rows) if r['case']=='mt6797-byte')
for edit in [lambda r:r[index].update(valid=True),
             lambda r:r[index].update(decoded_schema_valid=False),
             lambda r:r[index].update(raw_width_valid=True),
             lambda r:r[index].update(decoder_stderr=''),
             lambda r:r[index].update(decoder_stderr=stderr),
             lambda r:r[index].update(decoder_diagnostics=[]),
             lambda r:r[index]['decoder_diagnostics'][0].update(node='/wrong'),
             lambda r:r[index]['decoder_diagnostics'][0].update(property='#clock-cells'),
             lambda r:r[index]['raw_reset_cells'].update(bytes=4),
             lambda r:r[index]['raw_reset_cells'].update(hex='02'),
             lambda r:r[index].update(decoder_stderr='#reset-cells: size (2) error for type uint32\n'),
             lambda r:r[index].update(decoder_stderr='#clock-cells: size (1) error for type uint32\n'),
             lambda r:r[index].update(decoder_stderr=r[index]['decoder_stderr']+'unexpected\n'),
             lambda r:r[index].update(decoder_stderr='Traceback: failure\n'),
             lambda r:r[1].update(decoder_stderr='#reset-cells: size (4) error for type uint32\n')]:
    mutated=copy.deepcopy(rows);edit(mutated);refuse(lambda:compare.classify(mutated,cases))
unknown=next(i for i,r in enumerate(rows) if r['case']=='mt6797-unknown-property' and r['variant']=='mandatory')
for keep in [0,1]:
    mutated=copy.deepcopy(rows);mutated[unknown]['errors']=[mutated[unknown]['errors'][keep]]
    refuse(lambda:compare.classify(mutated,cases))
mutated=copy.deepcopy(rows);mutated[unknown]['errors'].append(copy.deepcopy(mutated[unknown]['errors'][0]));refuse(lambda:compare.classify(mutated,cases))
with compare.DecoderStderr() as captured:
    captured.write('x'*4096);refuse(lambda:captured.write('x'))
print(json.dumps({'retained_schema_errors_preserved':True,'synthetic_per_case_partition_matches_retained_aggregate':True,
 'corrected_classifier_with_retained_errors_and_synthetic_raw_capture':'pass',
 'malformed_byte_decoded_schema_valid_but_full_validation_invalid':True,
 'unsafe_attributions_rejected':rejected,'new_backend_decoder_or_schema_execution':False},indent=2))
