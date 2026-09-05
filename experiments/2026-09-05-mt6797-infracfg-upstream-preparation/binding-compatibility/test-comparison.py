#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Synthetic refusal tests of actual classifier/guards, never DT tools."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import compare

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('runner', HERE / 'run-fixtures.py')
runner = importlib.util.module_from_spec(spec); spec.loader.exec_module(runner)
cases = compare.load_cases(HERE / 'fixtures.json')
rows = []
for variant in ('mandatory', 'optional'):
    for case in cases:
        valid = case['expected_valid'] and (variant, case['name']) != ('mandatory', 'mt6797-old-absent')
        error = {'schema': compare.SCHEMA_ID, 'path': [], 'schema_path': ['then', 'required'],
                 'validator': 'required', 'message': "'#reset-cells' is a required property"}
        if case['name'] == 'mt6797-unknown-property':
            error.update(schema_path=['additionalProperties'], validator='additionalProperties', message="Additional properties are not allowed ('unreviewed-property' was unexpected)")
        elif not case['name'].endswith('absent'):
            error.update(path=['#reset-cells'], schema_path=['properties', '#reset-cells', 'const'], validator='const', message='1 was expected')
        rows.append({'variant': variant, 'case': case['name'], 'valid': valid, 'errors': [] if valid else [error],
                     'node': '/infracfg@10001000', 'compatible': 'mediatek,' + case['name'].split('-')[0] + '-infracfg'})
assert compare.classify(rows, cases)['rows'] == 50
rejected = 0

def refuse(call):
    global rejected
    try:
        call()
    except (ValueError, OSError):
        rejected += 1
    else:
        raise AssertionError('unsafe fixture admitted')

for change in [lambda r:r.pop(), lambda r:r.append(r[0]), lambda r:r.__setitem__(1,copy.deepcopy(r[0])),
               lambda r:r[0].update(valid=True,errors=[]), lambda r:r[25].update(valid=False,errors=copy.deepcopy(rows[0]['errors'])),
               lambda r:r[0].update(errors=[]), lambda r:r[0].update(node='/wrong'),
               lambda r:r[0].update(compatible='mediatek,wrong'), lambda r:r[0].update(valid=0),
               lambda r:r[0]['errors'][0].update(schema='wrong'),
               lambda r:r[0]['errors'][0].update(validator='crash'),
               lambda r:r[0]['errors'][0].update(path=['reg'],schema_path=['properties','reg'],message='wrong property'),
               lambda r:r[0]['errors'][0].update(message='')]:
    mutated = copy.deepcopy(rows);change(mutated)
    refuse(lambda:compare.classify(mutated,cases))
facts = {'returncode': 0, 'stop_reason': None, 'cleanup': {'group_absent': True}, 'elapsed_seconds': 1, 'timeout_seconds': 5}
runner.retained.accepted_command(facts)
for bad in [dict(facts, returncode=1), dict(facts, stop_reason='log-limit'), dict(facts, cleanup={'group_absent':False}), dict(facts, elapsed_seconds=6)]:
    refuse(lambda:runner.retained.accepted_command(bad))
refuse(lambda:runner.optional(b'unpinned schema'))
runner.dtc_diagnostics({'name':'mt6797-byte'}, "mt6797-byte.dts:9.1: Warning (resets_is_cell): /infracfg@10001000:#reset-cells: property is not a single cell\nmt6797-byte.dtb: Warning (resets_property): Failed prerequisite 'resets_is_cell'\n", Path('mt6797-byte.dts'))
refuse(lambda:runner.dtc_diagnostics({'name':'mt6797-new-one'}, 'warning', Path('fixture.dts')))
refuse(lambda:runner.dtc_diagnostics({'name':'mt6797-byte'}, 'Traceback: decoder failed', Path('fixture.dts')))
with tempfile.TemporaryDirectory(prefix='gemini-binding-guards-') as temporary:
    root=Path(temporary)/'owned';work=runner.scratch_root(root);work.mkdir();(work/'stale').write_text('synthetic')
    assert runner.scratch_root(root)==work and not work.exists()
    unowned=Path(temporary)/'unowned';unowned.mkdir(mode=0o700);keep=unowned/'keep';keep.write_text('preserve')
    refuse(lambda:runner.scratch_root(unowned))
    link=Path(temporary)/'link';link.symlink_to(root,target_is_directory=True)
    refuse(lambda:runner.scratch_root(link))
    work.symlink_to(unowned,target_is_directory=True)
    refuse(lambda:runner.scratch_root(root));assert keep.read_text()=='preserve'
    fixture=Path(temporary)/'fixtures.json';fixture.write_text('{}')
    refuse(lambda:compare.load_cases(fixture))
print(json.dumps({'synthetic_complete_comparison':'pass','unsafe_cases_rejected':rejected,
 'owned_stale_recovery':'pass','schema_DTC_backend_device_execution':False},indent=2))
