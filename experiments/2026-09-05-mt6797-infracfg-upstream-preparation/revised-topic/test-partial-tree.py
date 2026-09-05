#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Synthetic local Git partial-clone check; no Linux source or network."""
import ast
import json
import os
from pathlib import Path
import subprocess
import tempfile

# Both real revised call sites must use the tested option.
source = Path(__file__).resolve().parent.parent / 'scripts/derive-topic.py'
node = next(n for n in ast.parse(source.read_text()).body if isinstance(n, ast.FunctionDef) and n.name == 'revised_generate')
commands = [n for n in ast.walk(node) if isinstance(n, ast.List) and n.elts and isinstance(n.elts[0], ast.Constant) and n.elts[0].value == 'write-tree']
assert len(commands) == 2 and all(ast.literal_eval(n) == ['write-tree', '--missing-ok'] for n in commands)

with tempfile.TemporaryDirectory(prefix='infracfg-partial-tree-', dir='/tmp') as temporary:
    root = Path(temporary)
    env = dict(os.environ, HOME=str(root), GIT_CONFIG_NOSYSTEM='1', GIT_TERMINAL_PROMPT='0',
               GIT_AUTHOR_NAME='Synthetic fixture', GIT_AUTHOR_EMAIL='fixture@example.invalid',
               GIT_COMMITTER_NAME='Synthetic fixture', GIT_COMMITTER_EMAIL='fixture@example.invalid')
    # Keep user Git environment outside this independent repository fixture.
    for key in list(env):
        if key.startswith('GIT_') and key not in {'GIT_CONFIG_NOSYSTEM', 'GIT_TERMINAL_PROMPT',
             'GIT_AUTHOR_NAME', 'GIT_AUTHOR_EMAIL', 'GIT_COMMITTER_NAME', 'GIT_COMMITTER_EMAIL'}:
            del env[key]
    def git(repo, *args, data=None, okay=True):
        run = subprocess.run(['git', '--git-dir=' + str(repo), *args], input=data,
                             capture_output=True, text=True, env=env, timeout=10)
        if okay: assert run.returncode == 0, (args, run.stderr)
        return run
    origin = root / 'origin.git'
    git(origin, 'init', '--bare', '--quiet')
    git(origin, 'config', 'uploadpack.allowFilter', 'true')
    git(origin, 'config', 'uploadpack.allowAnySHA1InWant', 'true')
    before = git(origin, 'hash-object', '-w', '--stdin', data='before\n').stdout.strip()
    unrelated = git(origin, 'hash-object', '-w', '--stdin', data='unrelated\n' * 4096).stdout.strip()
    after = git(origin, 'hash-object', '-w', '--stdin', data='after\n').stdout.strip()
    for path, oid in [('target.txt', before), ('unrelated.bin', unrelated)]:
        git(origin, 'update-index', '--add', '--cacheinfo', '100644', oid, path)
    parent_tree = git(origin, 'write-tree').stdout.strip()
    parent = git(origin, 'commit-tree', parent_tree, data='synthetic parent\n').stdout.strip()
    git(origin, 'update-ref', 'refs/heads/main', parent)
    git(origin, 'update-index', '--cacheinfo', '100644', after, 'target.txt')
    expected = git(origin, 'write-tree').stdout.strip()
    results = {}
    for name, flags in [('ordinary', []), ('missing-ok', ['--missing-ok'])]:
        repo = root / (name + '.git')
        git(repo, 'init', '--bare', '--quiet')
        git(repo, 'remote', 'add', 'origin', origin.as_uri())
        git(repo, 'fetch', '--quiet', '--filter=blob:none', '--depth=1', 'origin', 'refs/heads/main')
        git(repo, 'read-tree', 'FETCH_HEAD')
        assert git(repo, 'hash-object', '-w', '--stdin', data='after\n').stdout.strip() == after
        git(repo, 'update-index', '--cacheinfo', '100644', after, 'target.txt')
        def local_objects():
            # --batch-all-objects enumerates the local database without lazy fetch.
            return set(git(repo, 'cat-file', '--batch-all-objects', '--batch-check=%(objectname)').stdout.split())
        assert unrelated not in local_objects()
        tree = git(repo, 'write-tree', *flags).stdout.strip()
        assert tree == expected
        fetched = unrelated in local_objects()
        assert fetched == (name == 'ordinary')
        results[name] = {'tree_matches_full_object_oracle': True, 'unrelated_blob_fetched': fetched}
        if flags:
            # A separate index reproduces the full tree with the same omitted blob.
            env['GIT_INDEX_FILE'] = str(root / 'replay-index')
            git(repo, 'read-tree', 'FETCH_HEAD')
            git(repo, 'update-index', '--cacheinfo', '100644', after, 'target.txt')
            assert git(repo, 'write-tree', '--missing-ok').stdout.strip() == expected
            assert unrelated not in local_objects()
            # The option is not an integrity oracle: a wrong reference makes a
            # different tree; explicit source materialization still rejects it.
            missing = '1' * 40
            git(repo, 'update-index', '--cacheinfo', '100644', missing, 'target.txt')
            mutated = git(repo, 'write-tree', '--missing-ok').stdout.strip()
            assert mutated != expected
            assert git(repo, 'show', mutated + ':target.txt', okay=False).returncode != 0
            results[name]['replay_matches'] = True
            results[name]['missing_changed_blob_rejected_by_materialization'] = True
            # An unrelated reference mutation also differs from full-tree oracle.
            git(repo, 'update-index', '--cacheinfo', '100644', after, 'target.txt')
            git(repo, 'update-index', '--cacheinfo', '100644', after, 'unrelated.bin')
            assert git(repo, 'write-tree', '--missing-ok').stdout.strip() != expected
            results[name]['unrelated_reference_mutation_changes_tree'] = True
            del env['GIT_INDEX_FILE']
    print(json.dumps({'result': 'PASS', 'scope': 'synthetic host Git only; not backend replay',
                      'git_version': subprocess.check_output(['git', '--version'], text=True).strip(),
                      'cases': results}, indent=2))
