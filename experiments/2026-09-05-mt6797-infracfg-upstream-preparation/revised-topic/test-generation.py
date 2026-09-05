#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Host-only checks of revised admission; no backend or kernel source checkout."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPT = HERE.parent / 'scripts/derive-topic.py'
spec = importlib.util.spec_from_file_location('derive', SCRIPT)
derive = importlib.util.module_from_spec(spec)
spec.loader.exec_module(derive)
checks = []


def refuses(name, action):
    try:
        action()
    except (ValueError, FileNotFoundError):
        checks.append(name)
    else:
        raise AssertionError('accepted mutation: ' + name)


raw = (HERE / 'proposal.json').read_bytes()
read = lambda name: (ROOT / name).read_bytes()
proposal = derive.revised_inputs(raw, read)
for label, mutation in [('order', lambda p: p['ordered_inputs'].reverse()),
                        ('missing-input', lambda p: p['ordered_inputs'].pop()),
                        ('expanded-input', lambda p: p['ordered_inputs'].append(p['ordered_inputs'][0]))]:
    changed = copy.deepcopy(proposal)
    mutation(changed)
    refuses(label, lambda: derive.revised_inputs(json.dumps(changed).encode(), read))
paths = sorted({e[key] for e in proposal['ordered_inputs'] for key in ('original_path', 'selected_path')})
for path in paths:
    refuses('changed:' + Path(path).name,
            lambda path=path: derive.revised_inputs(raw, lambda name: read(name) + (b'x' if name == path else b'')))
refuses('missing-patch', lambda: derive.revised_inputs(raw, lambda name: (_ for _ in ()).throw(FileNotFoundError(name))))
header_input = proposal['ordered_inputs'][2]
refuses('mandatory-hunk-restored', lambda: derive.revised_inputs(raw, lambda name:
        read(header_input['original_path']) if name == header_input['selected_path'] else read(name)))
expected = proposal['expected_final_source_sha256']
changed_paths = sorted(set(expected) - {derive.SCHEMA})
derive.revised_final(proposal, dict(expected), changed_paths)
for path in expected:
    bad = dict(expected); bad[path] = '0' * 64
    refuses('source:' + path, lambda: derive.revised_final(proposal, bad, changed_paths))
for label, paths in [('missing-path', changed_paths[:-1]), ('extra-path', changed_paths + ['unrelated']),
                     ('schema-changed', changed_paths + [derive.SCHEMA]), ('duplicate-path', changed_paths + changed_paths[:1])]:
    refuses(label, lambda: derive.revised_final(proposal, expected, paths))
for label, hashes in [('missing-hash', dict(list(expected.items())[1:])), ('extra-hash', dict(expected, unrelated='0' * 64))]:
    refuses(label, lambda: derive.revised_final(proposal, hashes, changed_paths))
with tempfile.TemporaryDirectory(prefix='infracfg-generation-', dir='/tmp') as temporary:
    base = Path(temporary)
    root = base / 'owned'
    run = derive.revised_scratch(root)
    run.mkdir(); (run / 'stale').write_text('disposable')
    assert derive.revised_scratch(root) == run and not run.exists()
    sentinel = base / 'sentinel'; sentinel.mkdir(); (sentinel / 'keep').write_text('preserve')
    run.symlink_to(sentinel, target_is_directory=True)
    refuses('symlink-run', lambda: derive.revised_scratch(root)); run.unlink()
    linked = base / 'linked'; linked.symlink_to(root, target_is_directory=True)
    refuses('symlink-root', lambda: derive.revised_scratch(linked))
    root.chmod(0o755)
    refuses('public-root', lambda: derive.revised_scratch(root)); root.chmod(0o700)
    marker = root / '.owner'; good = marker.read_text(); marker.write_text('foreign')
    refuses('foreign-marker', lambda: derive.revised_scratch(root)); marker.unlink()
    marker.symlink_to(sentinel / 'keep')
    refuses('symlink-marker', lambda: derive.revised_scratch(root)); marker.unlink(); marker.write_text(good)
    (root / 'foreign').write_text('preserve')
    refuses('unknown-content', lambda: derive.revised_scratch(root))
    assert (sentinel / 'keep').read_text() == 'preserve' and (root / 'foreign').read_text() == 'preserve'
refuses('host-is-not-buildbox', lambda: derive.revised_generate('a' * 40, 'refs/heads/main'))
# Compare actual historical executable bodies, not a copied implementation.
baseline = '78318abe188f488b12e0016781a5bbf249a79735'
relative = SCRIPT.relative_to(ROOT).as_posix()
old = subprocess.check_output(['git', '-C', str(ROOT), 'show', baseline + ':' + relative], text=True)
old_ast, new_ast = ast.parse(old), ast.parse(SCRIPT.read_text())
for node in old_ast.body:
    if isinstance(node, ast.FunctionDef):
        current = next(n for n in new_ast.body if isinstance(n, ast.FunctionDef) and n.name == node.name)
        if node.name == 'main':
            # Only the explicit revised dispatch precedes the historical parser.
            current.body = current.body[2:]
        assert ast.dump(node) == ast.dump(current), node.name
shell = HERE.parent / 'scripts/generate-on-buildbox'
old_shell = subprocess.check_output(['git', '-C', str(ROOT), 'show', baseline + ':' + shell.relative_to(ROOT).as_posix()], text=True)
marker = '[[ $# == 1 && $1 =~'
assert old_shell[old_shell.index(marker):] == shell.read_text()[shell.read_text().index(marker):]
print(json.dumps({'result': 'PASS', 'scope': 'host input/final-source/scratch refusals and historical-body preservation; no backend execution',
                  'refusal_count': len(checks), 'refusals': checks, 'historical_baseline': baseline}, indent=2))
