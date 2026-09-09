#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare an explicit same-boot retry, preserving the completed attempt in RAM."""
import json
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
M = runpy.run_path(str(HERE/'capture.py'))
C, S, require, sha = (M[k] for k in ('C', 'S', 'require', 'sha'))


def prepare(session, context):
    session = Path(session)
    admission = context['admission']
    retry_id = admission['runtime']['retry_id']
    require(type(retry_id) is str and C['UUID'].fullmatch(retry_id), 'retry identity')
    previous = json.loads(C['regular'](session/'capture-admission.json', 65536))
    require(previous['id'] == admission['id'] and previous['boot_id'] == admission['boot_id']
            and previous['monitor_sha256'] == admission['monitor_sha256'], 'same session retry')
    root = M['attempt_root'](previous)
    require(json.loads(C['regular'](root/'export/admission.json', 65536)) == previous,
            'previous export binding')
    raw = C['regular'](root/'export/stdout.txt', 278528)
    M['L']['process_ok'](raw, C['regular'](root/'export/stderr.txt', 16384),
        json.loads(C['regular'](root/'export/process.json', 16384)), 30, 278528)
    files = M['parse_export'](raw)
    require(all(value is not None for value in files.values()), 'previous files incomplete')
    status = S['fields'](files['monitor.status'])
    require(status.get('reaped') == '1' and status.get('identity_lost') == '0'
            and files['observer.stderr'] == b''
            and files['observer.stdout'].endswith(b'incomplete reason=capture-or-preflight restored=1\n'),
            'previous observer not restored and reaped')
    candidate = context['dependency']['prepared']['candidate']
    text = S['identity_script'](candidate, admission['boot_id']) + S['ram_guard_script']()
    text += M['console_guard'](candidate) + M['reader_guard']()
    destination = '/a53-keyboard-delivery-prior-' + retry_id
    text += f'[ ! -e {destination} ] && [ ! -L {destination} ]\n'
    text += "[ \"$($BB awk '$2 == \"/a53-keyboard-delivery\" || index($2, \"/a53-keyboard-delivery/\") == 1 {n++} END {print n+0}' /proc/mounts)\" = 0 ]\n"
    for name in ('', '/licenses', '/keyboard-attempt'):
        path = '/a53-keyboard-delivery' + name
        text += f'[ -d {path} ] && [ ! -L {path} ]\n[ "$($BB stat -c %u:%a {path})" = 0:700 ]\n'
    text += '''count=0
for exe in /proc/[0-9]*/exe; do
  count=$((count+1)); [ "$count" -le 512 ]
  target=$($BB readlink "$exe") || continue
  case "$target" in /a53-keyboard-delivery/*|/bin/keyboard-observe) exit 1;; esac
done
'''
    expected = {**context['delivery_files'], **{'keyboard-attempt/'+k:v for k,v in files.items()}}
    for name, value in expected.items():
        path = '/a53-keyboard-delivery/' + name
        mode = '700' if name == 'keyboard-monitor' else '600'
        text += f'[ -f {path} ] && [ ! -L {path} ]\n'
        text += f'[ "$($BB stat -c %u:%a:%h {path})" = 0:{mode}:1 ]\n'
        text += f'h=$($BB sha256sum {path}); [ "${{h%% *}}" = {sha(value)} ]\n'
    text += f'$BB mv /a53-keyboard-delivery {destination}\n'
    for name, value in expected.items():
        text += f'h=$($BB sha256sum {destination}/{name}); [ "${{h%% *}}" = {sha(value)} ]\n'
    logger = runpy.run_path(str(HERE/'restart-logger.py'))['prepare'](
        session, seal='restarted-seal', retry_id=retry_id)
    # No deletion or replacement of prior evidence or consumed seal claims.
    return {**logger, 'command': text.encode() + logger['command']}
