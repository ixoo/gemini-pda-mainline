#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise actual generator guards without backend or network access."""
import os
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
SOURCE = (HERE / 'generate-on-buildbox').read_text()
GUARDS, entry = SOURCE.split('# Entry point:', 1)
assert 'verify_published "$revision" "$published_ref"' in entry
assert entry.index('prepare_scratch "$scratch_root"') < entry.index('trap cleanup EXIT') < entry.index('mkdir "$work" "$partial"')
REV = 'a' * 40
REF = 'refs/heads/fixture'
checks = 0


def run(body, args, env, success):
    global checks
    result = subprocess.run(['bash', '-c', GUARDS + '\n' + body, 'guard-fixture', *args],
                            env=env, capture_output=True, text=True, timeout=5)
    assert (result.returncode == 0) == success, (result.returncode, result.stderr)
    checks += 1


with tempfile.TemporaryDirectory(prefix='gemini-cleanup-guards-') as temporary:
    base = Path(temporary)
    tools = base / 'bin'
    tools.mkdir()
    (tools / 'timeout').write_text('#!/bin/sh\n[ "$1" = --kill-after=5 ] && [ "$2" = 30 ] || exit 91\nshift 2\nexec "$@"\n')
    (tools / 'git').write_text('''#!/bin/sh
[ "$#" = 5 ] && [ "$1" = ls-remote ] && [ "$2" = --exit-code ] &&
[ "$3" = --refs ] && [ "$4" = https://github.com/ixoo/gemini-pda-mainline.git ] &&
[ "$5" = refs/heads/fixture ] || exit 92
printf '%s' "$FIXTURE_RESPONSE"
exit "$FIXTURE_STATUS"
''')
    for tool in tools.iterdir():
        tool.chmod(0o700)
    env = dict(os.environ, PATH=str(tools) + os.pathsep + os.environ['PATH'])
    exact = REV + '\t' + REF + '\n'
    for response, status, success in [
        (exact, '0', True), ('b' * 40 + '\t' + REF, '0', False),
        ('', '2', False), (exact + exact, '0', False), (exact, '124', False),
        (REV + '\trefs/heads/wrong', '0', False), ('', '0', False),
    ]:
        run('verify_published "$1" "$2"', [REV, REF],
            dict(env, FIXTURE_RESPONSE=response, FIXTURE_STATUS=status), success)
    root = base / 'owned'
    run('prepare_scratch "$1"', [str(root)], env, True)
    work = root / 'run'
    work.mkdir()
    (work / 'interrupted-source').write_text('synthetic stale run')
    run('prepare_scratch "$1"', [str(root)], env, True)
    assert not work.exists() and (root / '.owner').is_file()
    unknown = base / 'unknown'
    unknown.mkdir(mode=0o700)
    sentinel = unknown / 'preserve'
    sentinel.write_text('not owned')
    run('prepare_scratch "$1"', [str(unknown)], env, False)
    assert sentinel.read_text() == 'not owned'
    root.chmod(0o755)
    run('prepare_scratch "$1"', [str(root)], env, False)
    root.chmod(0o700)
    link = base / 'symlink'
    link.symlink_to(root, target_is_directory=True)
    run('prepare_scratch "$1"', [str(link)], env, False)
    work.symlink_to(unknown, target_is_directory=True)
    run('prepare_scratch "$1"', [str(root)], env, False)
    assert sentinel.read_text() == 'not owned'
    work.unlink()
    marker = root / '.owner'
    marker.unlink()
    marker.symlink_to(sentinel)
    run('prepare_scratch "$1"', [str(root)], env, False)
    assert sentinel.read_text() == 'not owned'
print(f'generator_guards=pass cases={checks} backend_execution=false network_access=false')
