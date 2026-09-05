#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Classify only the 25 reviewed binding cases in two exact schema variants."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURES_SHA256 = '163afec1f1edbd09dac325453a21b5bdcf2a87765184724bab6ab505099f371d'
SCHEMA_ID = 'http://devicetree.org/schemas/clock/mediatek,infracfg.yaml'


def require(ok, why):
    if not ok:
        raise ValueError(why)


def load_cases(path):
    raw = Path(path).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == FIXTURES_SHA256, 'wrong complete fixture input')
    return json.loads(raw)['cases']


def classify(rows, cases):
    expected = {(variant, case['name']): case for variant in ('mandatory', 'optional') for case in cases}
    require(len(cases) == 25 and len(expected) == 50, 'fixture inventory')
    require(isinstance(rows, list) and len(rows) == 50, 'missing/extra rows')
    seen = set()
    for row in rows:
        require(isinstance(row, dict), 'invalid row')
        key = (row.get('variant'), row.get('case'))
        require(key in expected and key not in seen, 'wrong/duplicate row identity')
        seen.add(key)
        case = expected[key]
        require(row.get('node') == '/infracfg@10001000', 'wrong diagnostic node')
        require(row.get('compatible') == 'mediatek,' + case['name'].split('-')[0] + '-infracfg', 'wrong node compatible')
        want = case['expected_valid'] and key != ('mandatory', 'mt6797-old-absent')
        require(type(row.get('valid')) is bool and row['valid'] == want, 'wrong outcome')
        errors = row.get('errors')
        require(isinstance(errors, list) and len(errors) <= 8, 'missing/excess diagnostics')
        require(bool(errors) != want, 'unattributed outcome')
        for error in errors:
            require(isinstance(error, dict), 'invalid diagnostic')
            require(error.get('schema') == SCHEMA_ID, 'wrong diagnostic schema')
            require(isinstance(error.get('path'), list) and isinstance(error.get('schema_path'), list), 'missing diagnostic paths')
            require(isinstance(error.get('message'), str) and 0 < len(error['message']) < 4096, 'missing/large diagnostic message')
            if case['name'] == 'mt6797-unknown-property':
                require(error.get('validator') == 'additionalProperties' and 'unreviewed-property' in error['message'], 'unrelated property rejection')
            else:
                require(error.get('validator') in ('required', 'const', 'type', 'maxItems', 'minItems', 'typeSize'), 'unexpected rejection kind')
                require('#reset-cells' in error['path'] + error['schema_path'] or
                        (error['validator'] == 'required' and error['message'] == "'#reset-cells' is a required property"), 'unrelated property rejection')
    return {'classification': 'focused-schema-comparison-pass', 'rows': 50,
            'changed_outcomes': ['mt6797-old-absent'], 'kernel_execution': False}


def child(work, fixtures):
    # Imports only in the admitted pinned schema Python child.
    import dtschema
    work = Path(work)
    cases = load_cases(fixtures)
    rows = []
    hashes = {}
    for variant in ('mandatory', 'optional'):
        schema = work / variant / 'processed.json'
        validator = dtschema.DTValidator([str(schema)])
        require(SCHEMA_ID in validator.schemas, 'missing selected schema')
        hashes[variant] = hashlib.sha256(schema.read_bytes()).hexdigest()
        for case in cases:
            dtb = work / (case['name'] + '.dtb')
            trees = validator.decode_dtb(dtb.read_bytes())
            require(len(trees) == 1, 'unexpected decoded roots')
            nodes = [(name, node) for name, node in trees[0].items() if isinstance(node, dict)]
            require(len(nodes) == 1 and nodes[0][0] == 'infracfg@10001000', 'wrong decoded node')
            name, node = nodes[0]
            require(validator.compat_map.get(node['compatible'][0]) == SCHEMA_ID, 'fixture did not select binding')
            node['$nodename'] = [name]
            errors = []
            for error in validator.iter_errors(node, filter=[SCHEMA_ID]):
                require(len(errors) < 8, 'diagnostic ceiling')
                errors.append({'schema': error.schema_file.rstrip('#'), 'path': list(error.path),
                               'schema_path': list(error.schema_path), 'validator': error.validator,
                               'message': error.message})
            rows.append({'variant': variant, 'case': case['name'], 'valid': not errors,
                         'errors': errors, 'node': '/infracfg@10001000', 'compatible': node['compatible'][0], 'dtb_sha256': hashlib.sha256(dtb.read_bytes()).hexdigest()})
    print(json.dumps({'processed_sha256': hashes, 'rows': rows}, sort_keys=True))


if __name__ == '__main__':
    import sys
    require(len(sys.argv) == 4 and sys.argv[1] == '--child', 'child invocation only')
    child(sys.argv[2], sys.argv[3])
