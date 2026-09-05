#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Classify only the 25 reviewed binding cases in two exact schema variants."""
import contextlib
import hashlib
import io
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURES_SHA256 = '163afec1f1edbd09dac325453a21b5bdcf2a87765184724bab6ab505099f371d'
SCHEMA_ID = 'http://devicetree.org/schemas/clock/mediatek,infracfg.yaml'
NODE = '/infracfg@10001000'
DECODER_MODULES = {
    'dtb.py': '93f07555d95c3850f23faae8226512c30c1f896bc0e452766f3afa32d2814b54',
    'validator.py': 'c18a2356934d4bd5c6018646dc4c83754e5ddfb0d110e84b7518ada82e23af56',
    '__init__.py': 'c3dc9040f30f37e6da33b34c5498a2b23fc630ce36225cd451ed3b410244788b',
}


def require(ok, why):
    if not ok:
        raise ValueError(why)


def load_cases(path):
    raw = Path(path).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == FIXTURES_SHA256, 'wrong complete fixture input')
    return json.loads(raw)['cases']


def raw_expected(case):
    # Exact wire inputs of the pinned DTS fixtures, not a general DT decoder.
    name = case['name']
    if name.endswith('-absent') or name == 'mt6797-unknown-property':
        return None
    return {'mt6797-zero': b'\0\0\0\0', 'mt6797-two': b'\0\0\0\2',
            'mt6797-two-cells': b'\0\0\0\1\0\0\0\1',
            'mt6797-string': b'1\0', 'mt6797-byte': b'\1',
            'mt6797-boolean': b''}.get(name, b'\0\0\0\1')


def raw_record(raw):
    return {'node': NODE, 'property': '#reset-cells', 'present': raw is not None,
            'bytes': None if raw is None else len(raw), 'hex': None if raw is None else raw.hex()}


def decoder_record(case, raw, stderr):
    require(raw == raw_expected(case), 'raw fixture property differs from pinned DTS')
    expected = ''
    if raw is not None and len(raw) in (1, 2):
        expected = f'#reset-cells: size ({len(raw)}) error for type uint32\n'
    require(stderr == expected, 'missing/extra/unexpected per-case decoder diagnostic')
    return ([] if not stderr else [{'node': NODE, 'property': '#reset-cells',
             'raw_bytes': len(raw), 'expected_type': 'uint32', 'message': stderr.rstrip('\n')}])


class DecoderStderr(io.StringIO):
    def write(self, value):
        require(self.tell() + len(value) <= 4096, 'decoder diagnostic ceiling')
        return super().write(value)


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
        require(row.get('node') == NODE, 'wrong diagnostic node')
        require(row.get('compatible') == 'mediatek,' + case['name'].split('-')[0] + '-infracfg', 'wrong node compatible')
        raw = raw_expected(case)
        raw_evidence = row.get('raw_reset_cells')
        require(isinstance(raw_evidence, dict) and type(raw_evidence.get('present')) is bool, 'invalid raw property record')
        require(raw_evidence.get('bytes') is None if raw is None else type(raw_evidence.get('bytes')) is int, 'invalid raw byte count')
        require(raw_evidence == raw_record(raw), 'wrong/missing raw property evidence')
        stderr = row.get('decoder_stderr')
        require(isinstance(stderr, str), 'missing per-case decoder capture')
        diagnostics = decoder_record(case, raw, stderr)
        require(row.get('decoder_diagnostics') == diagnostics, 'wrong decoder attribution')
        wire_valid = raw is None or len(raw) == 4
        require(type(row.get('raw_width_valid')) is bool and row['raw_width_valid'] == wire_valid, 'wrong raw width classification')
        errors = row.get('errors')
        require(isinstance(errors, list) and len(errors) <= 8, 'missing/excess diagnostics')
        require(type(row.get('decoded_schema_valid')) is bool and row['decoded_schema_valid'] == (not errors), 'wrong decoded-schema validity')
        full_valid = wire_valid and not diagnostics and not errors
        want = case['expected_valid'] and key != ('mandatory', 'mt6797-old-absent')
        require(type(row.get('valid')) is bool and row['valid'] == full_valid == want, 'wrong full validation outcome')
        # Retain schema evidence for all ordinary invalid cases. Byte fallback is
        # rejected independently, without inventing a YAML error for decoded 1.
        if not want and case['name'] != 'mt6797-byte':
            require(bool(errors), 'missing expected decoded-schema rejection')
        if case['name'] == 'mt6797-unknown-property':
            kinds = [e.get('validator') for e in errors if isinstance(e, dict)]
            require(sorted(kinds) == (['additionalProperties', 'required'] if key[0] == 'mandatory' else ['additionalProperties']), 'wrong compound diagnostic set')
        for error in errors:
            require(isinstance(error, dict), 'invalid diagnostic')
            require(error.get('schema') == SCHEMA_ID, 'wrong diagnostic schema')
            require(isinstance(error.get('path'), list) and isinstance(error.get('schema_path'), list), 'missing diagnostic paths')
            require(isinstance(error.get('message'), str) and 0 < len(error['message']) < 4096, 'missing/large diagnostic message')
            if case['name'] == 'mt6797-unknown-property' and error['validator'] == 'additionalProperties':
                require(error['path'] == [] and error['schema_path'] == ['additionalProperties'] and 'unreviewed-property' in error['message'], 'unrelated property rejection')
            elif case['name'] == 'mt6797-unknown-property':
                require(error['validator'] == 'required' and error['path'] == [] and error['schema_path'] == ['then', 'required'] and error['message'] == "'#reset-cells' is a required property", 'unrelated compound rejection')
            else:
                require(error.get('validator') in ('required', 'const', 'type', 'maxItems', 'minItems', 'typeSize'), 'unexpected rejection kind')
                require('#reset-cells' in error['path'] + error['schema_path'] or
                        (error['validator'] == 'required' and error['message'] == "'#reset-cells' is a required property"), 'unrelated property rejection')
    return {'classification': 'focused-DTB-and-schema-comparison-pass', 'rows': 50,
            'changed_outcomes': ['mt6797-old-absent'], 'kernel_execution': False}


def decoder_modules(dtschema):
    package = Path(dtschema.__file__).parent
    hashes = {name: hashlib.sha256((package / name).read_bytes()).hexdigest() for name in DECODER_MODULES}
    require(hashes == DECODER_MODULES, 'audited decoder module bytes changed')
    return hashes


def child(work, fixtures):
    import dtschema
    import libfdt
    work = Path(work)
    cases = load_cases(fixtures)
    modules = decoder_modules(dtschema)
    rows, hashes = [], {}
    for variant in ('mandatory', 'optional'):
        schema = work / variant / 'processed.json'
        validator = dtschema.DTValidator([str(schema)])
        require(SCHEMA_ID in validator.schemas, 'missing selected schema')
        hashes[variant] = hashlib.sha256(schema.read_bytes()).hexdigest()
        for case in cases:
            dtb = (work / (case['name'] + '.dtb')).read_bytes()
            require(0 < len(dtb) <= 65536, 'fixture DTB ceiling')
            fdt = libfdt.Fdt(dtb)
            offset = fdt.path_offset(NODE)
            prop = fdt.getprop(offset, '#reset-cells', quiet=(libfdt.NOTFOUND,))
            if isinstance(prop, int):
                require(prop == -libfdt.NOTFOUND, 'unexpected property lookup error')
                raw = None
            else:
                raw = bytes(prop)
            require(raw == raw_expected(case), 'wrong raw property input')
            # A decode exception remains a child failure; only exact size
            # diagnostics from a completed decode can be classified below.
            with DecoderStderr() as captured:
                with contextlib.redirect_stderr(captured):
                    trees = validator.decode_dtb(dtb)
                stderr = captured.getvalue()
            diagnostics = decoder_record(case, raw, stderr)
            require(len(trees) == 1, 'unexpected decoded roots')
            nodes = [(name, node) for name, node in trees[0].items() if isinstance(node, dict)]
            require(len(nodes) == 1 and nodes[0][0] == NODE[1:], 'wrong decoded node')
            name, node = nodes[0]
            require(validator.compat_map.get(node['compatible'][0]) == SCHEMA_ID, 'fixture did not select binding')
            node['$nodename'] = [name]
            errors = []
            for error in validator.iter_errors(node, filter=[SCHEMA_ID]):
                require(len(errors) < 8, 'diagnostic ceiling')
                errors.append({'schema': error.schema_file.rstrip('#'), 'path': list(error.path),
                               'schema_path': list(error.schema_path), 'validator': error.validator,
                               'message': error.message})
            wire_valid = raw is None or len(raw) == 4
            rows.append({'variant': variant, 'case': case['name'], 'valid': wire_valid and not diagnostics and not errors,
                         'raw_reset_cells': raw_record(raw), 'raw_width_valid': wire_valid,
                         'decoder_stderr': stderr, 'decoder_diagnostics': diagnostics, 'decoded_schema_valid': not errors,
                         'errors': errors, 'node': NODE, 'compatible': node['compatible'][0],
                         'dtb_sha256': hashlib.sha256(dtb).hexdigest()})
    require(decoder_modules(dtschema) == modules, 'decoder modules changed during child')
    print(json.dumps({'processed_sha256': hashes, 'decoder_modules_sha256': modules, 'rows': rows}, sort_keys=True))


if __name__ == '__main__':
    import sys
    require(len(sys.argv) == 4 and sys.argv[1] == '--child', 'child invocation only')
    child(sys.argv[2], sys.argv[3])
