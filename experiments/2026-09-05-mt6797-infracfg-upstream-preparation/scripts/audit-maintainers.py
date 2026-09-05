#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run pinned upstream maintainer discovery on the exact review patches on Buildbox."""
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import tempfile
import urllib.request

HERE = Path(__file__).resolve().parent
UPSTREAM = '4d7d9486c04d917265f64c55bd23b2cc4fe7749c'
PINS = {
    'scripts/get_maintainer.pl': '103c295e5c6cb557d2026a2b45ba7e9df9e09fd360339810f5f1e7f7309801cb',
    'MAINTAINERS': '39e65935b8f213dfa9b7a49a7341565855c6aec851288f0f32a0b2afcb35558a',
}
PACKAGE = Path('/workspace/gemini-pda/review-packages/infracfg-upstream/aa9828f93fe111ff80abec73d5a79c1af2873ae6')
OPTIONS = ['--json', '--no-tree', '--no-git', '--no-git-fallback', '--no-git-blame',
           '--no-file-emails', '--no-mailmap', '--no-fixes', '--roles', '--no-rolestats', '--scm']


def main():
    if platform.system() != 'Linux' or not str(HERE).startswith('/workspace/gemini-pda/'):
        raise ValueError('run from a Git-fetched project checkout on Buildbox')
    receipt = json.loads((HERE.parent / 'results/coherent-topic-generation.json').read_text())
    if receipt['upstream_commit'] != UPSTREAM or receipt['patch_count'] != 6:
        raise ValueError('unexpected topic receipt')
    patches = receipt['patches']
    for entry in patches:
        name = entry['name']
        if Path(name).name != name or not name.endswith('.patch'):
            raise ValueError('unsafe patch name')
        path = PACKAGE / 'patches' / name
        if path.is_symlink() or not path.is_file():
            raise ValueError('missing or unsafe review patch')
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError('review patch identity mismatch')
    results = []
    with tempfile.TemporaryDirectory(prefix='infracfg-maintainers.',
                                     dir='/workspace/gemini-pda/tmp') as temporary:
        root = Path(temporary)
        for name, sha in PINS.items():
            url = f'https://raw.githubusercontent.com/torvalds/linux/{UPSTREAM}/{name}'
            with urllib.request.urlopen(url, timeout=30) as response:
                if response.status != 200 or response.url != url:
                    raise ValueError('unexpected source response')
                data = response.read(2 * 1024 * 1024)
            if hashlib.sha256(data).hexdigest() != sha:
                raise ValueError('maintainer input identity mismatch')
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        # These empty local files prevent discovery from the invoking account.
        for name in ('.get_maintainer.conf', '.get_maintainer.ignore'):
            (root / name).write_text('')
        for entry in patches:
            modes = {}
            for keyword in (False, True):
                flag = '--keywords' if keyword else '--no-keywords'
                command = ['perl', str(root / 'scripts/get_maintainer.pl'),
                           *OPTIONS, flag, str(PACKAGE / 'patches' / entry['name'])]
                process = subprocess.run(command, cwd=root, text=True,
                                         capture_output=True, check=True, timeout=30)
                if process.stderr:
                    raise ValueError('maintainer discovery emitted a diagnostic')
                parsed = json.loads(process.stdout)
                if set(parsed) != {'maintainers', 'scm'}:
                    raise ValueError('unexpected maintainer JSON fields')
                if not isinstance(parsed['maintainers'], list) or not parsed['maintainers']:
                    raise ValueError('missing maintainer result')
                modes['paths-and-keywords' if keyword else 'paths-only'] = parsed
            results.append({'patch': entry['name'], 'sha256': entry['sha256'], 'modes': modes})
    print(json.dumps({'upstream_commit': UPSTREAM, 'tool_inputs': PINS,
                      'options': OPTIONS, 'local_configuration': 'empty config and ignore files',
                      'results': results, 'submission': 'not sent',
                      'limits': 'pinned MAINTAINERS and patch matching only; no Git history, mailmap or live mailing-list overlap search'},
                     indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
