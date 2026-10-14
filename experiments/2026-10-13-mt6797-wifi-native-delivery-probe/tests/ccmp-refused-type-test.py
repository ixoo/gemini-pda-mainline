#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Reuse the existing actual-HIF fixture/compiler for the failure-only hint review."""
import argparse
import ast
import hashlib
from pathlib import Path
import re
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('parent', type=Path)
parser.add_argument('child', type=Path)
args = parser.parse_args()
rel = Path('drivers/net/wireless/mediatek/mt6797')
parent, child = args.parent / rel, args.child / rel
fixtures = Path(__file__).resolve().parent
repo = fixtures.parents[2]
for name, digest in {
    'hif.c': '07763b3ba8f48ae71c2a629dcbe558c06a59b675d1fb7f57615ed148286e3769',
    'hif.h': 'e7f6415f630390b7b8317fc535b339b8708705630587888676a5f2ba40775618',
    'mac.c': '261a159513497d6e541831f1db442ddbd4974f781173fac4d3c718d095cc6139',
}.items():
    assert hashlib.sha256((parent / name).read_bytes()).hexdigest() == digest, name

old = {p.name: p.read_text() for p in parent.iterdir() if p.is_file()}
new = {p.name: p.read_text() for p in child.iterdir() if p.is_file()}
assert old.keys() == new.keys()
for name in old.keys() - {'hif.c', 'hif.h', 'mac.c'}:
    assert old[name] == new[name], name
addition = '''	/* Already-staged framing hint on header-length refusal only; untrusted. */
	u16 refused_type_word;
	bool refused_type_valid;
'''
assert new['hif.h'].replace(addition, '') == old['hif.h']
start = new['hif.c'].index('\t\tif (result->rx_setup && result->rx_complete && result->header_valid &&')
end = new['hif.c'].index('\t\terror = -EPROTO;', start)
assert new['hif.c'][:start] + new['hif.c'][end:] == old['hif.c']
assert new['mac.c'].replace(
    ' refused_type_valid=%u refused_type_word=0x%04x', '').replace(
    'rx.staging_bytes, rx.post_valid, rx.post_wrplr,\n'
    '\t\t\t\t\t rx.refused_type_valid, rx.refused_type_word);',
    'rx.staging_bytes, rx.post_valid, rx.post_wrplr);') == old['mac.c']

# Reuse the existing compiler and actual logging extraction, not a new I/O model.
source = fixtures / 'run-native-metadata-test.py'
tree = ast.parse(source.read_text())
definitions = [node for node in ast.walk(tree)
               if isinstance(node, ast.FunctionDef) and node.name in ('function', 'run')]
namespace = {'fixtures': fixtures, 'repo': repo, 'subprocess': __import__('subprocess')}
exec(compile(ast.Module(body=definitions, type_ignores=[]), str(source), 'exec'), namespace)
with tempfile.TemporaryDirectory(prefix='ccmp-refused-type-', dir='/tmp/opencode') as directory:
    namespace.update(tmp=Path(directory), errors={})
    outputs = {}
    for label, driver, text in (('parent', parent, old['mac.c']),
                                ('child', child, new['mac.c'])):
        begin = text.index('if (ret == -EPROTO && rx.protocol_refusal')
        finish = text.index('\n#endif', begin)
        (namespace['tmp'] / 'metadata-hif-log.h').write_text(
            'static void logged_refusal(int ret, unsigned int port, '
            'struct mt6797_hif_rx_result rx) {\n' + text[begin:finish] + '\n}\n')
        defines = ['-DCONFIG_MT6797_NATIVE_DELIVERY_DIAG', '-DIS_ENABLED(x)=1', '-DTEST_METADATA']
        if label == 'child':
            defines.append('-DTEST_REFUSED_TYPE')
        outputs[label] = namespace['run']('native-metadata-hif-test.c', driver, label, defines)
    assert outputs['parent'] == outputs['child'], 'results/transport counts changed'
    # Only the two admitted scalar fields differ in the actual log formatter.
    logs = namespace['errors']
    assert re.sub(r' refused_type_valid=[01] refused_type_word=0x[0-9a-f]{4}',
                  '', logs['child']) == logs['parent']
    assert 'length=76 delta=4294967248' in outputs['child']
    assert 'length=80 delta=4294967248' in outputs['child']
    print('Actual HIF parent/child: PASS 76/28,80/32, equal-size positives, both ports, all I/O faults')
    print('PASS unchanged call/result tables; poison/no-copy/post-unread; poisoned second call has no I/O/report')
    print('PASS failure-only hint validity/absence, two-field logging/privacy; ASan/UBSan; exact delta reversal')
