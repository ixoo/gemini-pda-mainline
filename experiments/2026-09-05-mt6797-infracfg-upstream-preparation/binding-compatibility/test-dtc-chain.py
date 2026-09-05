#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Replay the retained pinned-dtc diagnostic through the actual corrected guard."""
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('runner', HERE/'run-fixtures.py')
runner = importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
raw=(HERE/'results/attempt-1-1e2d7e05/dtc-mt6797-two-cells.stderr').read_bytes()
assert hashlib.sha256(raw).hexdigest()=='5b70bc81cdd4b35c69d2b72cb9930f67aa3d79a60b0869a3317d41b86092139d'
text=raw.decode();source=Path('/workspace/gemini-pda/tmp/infracfg-binding-compatibility/run/mt6797-two-cells.dts')
case={'name':'mt6797-two-cells'}
runner.dtc_diagnostics(case,text,source)
for name in ['mt6797-string','mt6797-byte','mt6797-boolean']:
    runner.dtc_diagnostics({'name':name}, text.replace(case['name'],name), source.with_name(name+'.dts'))
runner.dtc_diagnostics({'name':'mt6797-new-one'},'',Path('mt6797-new-one.dts'))
lines=text.splitlines(keepends=True)
mutants=['',lines[0],lines[1],text+lines[0],lines[1]+lines[0],text+'unrelated warning\n',
         text.replace('/infracfg@10001000', '/other@10001000'),
         text.replace('#reset-cells', '#clock-cells'),
         text.replace('resets_is_cell','reset_cells_is_cell'),
         text.replace('resets_property','clocks_property'),
         text.replace("Failed prerequisite 'resets_is_cell'", "Failed prerequisite 'phandle_references'"),
         text.replace('mt6797-two-cells.dtb','unrelated.dtb'),
         text.replace('mt6797-two-cells.dts','unrelated.dts'),
         text.rstrip('\n'),text+'\n']
rejected=0
for mutated in mutants:
    try:runner.dtc_diagnostics(case,mutated,source)
    except ValueError:rejected+=1
    else:raise AssertionError('unsafe chain accepted')
for wrong_case,wrong_source in [({'name':'mt6797-new-one'},source), (case,source.with_name('wrong.dts'))]:
    try:runner.dtc_diagnostics(wrong_case,text,wrong_source)
    except ValueError:rejected+=1
    else:raise AssertionError('wrong fixture accepted')
print(json.dumps({'observed_chain_replay':'pass','synthetic_other_malformed_case_attribution':'pass',
 'positive_no_diagnostic':'pass','unsafe_chains_rejected':rejected,
 'observed_diagnostic_sha256':hashlib.sha256(raw).hexdigest(),
 'backend_DTC_schema_execution':False},indent=2))
