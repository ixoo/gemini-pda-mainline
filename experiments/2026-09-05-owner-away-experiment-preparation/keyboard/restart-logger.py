#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare one same-boot logger restart after verified preservation; no transport."""
import json
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
M = runpy.run_path(str(HERE/'capture.py'))
C, S, require, sha = (M[k] for k in ('C', 'S', 'require', 'sha'))


def prepare(session, seal='seal', retry_id=None):
    require(seal in ('seal', 'restarted-seal'), 'seal source')
    require(retry_id is None or (type(retry_id) is str and C['UUID'].fullmatch(retry_id)), 'retry identity')
    session = Path(session)
    admission = json.loads(C['regular'](session/'proof-admission.json', 65536))
    dependency = M['L']['completed_baseline'](admission['dependency'])
    candidate = dependency['prepared']['candidate']
    boot = admission['boot_id']
    result = json.loads(C['regular'](session/seal/'result.json', 65536))
    require(result['preservation_complete'] and result['logger_terminal'] and
            result['classification'] == 'complete-log-through-seal', 'original log unpreserved')
    files = {}
    for name in ('kmsg.log', 'kmsg.status', 'kmsg-exit'):
        raw = C['regular'](session/seal/name, 2097152)
        require(sha(raw) == result['files'][name]['sha256'], 'original evidence drift')
        files[name] = raw
    require(files['kmsg-exit'] == b'0\n' and
            S['fields'](files['kmsg.status'])['reason'] == 'sealed-on-sigterm',
            'original logger not successfully sealed')
    text = S['identity_script'](candidate, boot) + S['ram_guard_script']()
    text += '''$BB df -Pk /run | $BB awk 'NR == 2 {ok=($4 >= 3072)} END {if (!ok) exit 1}'
umask 077
set -C
[ ! -e /run/a53/keyboard-logger-prior ] && [ ! -L /run/a53/keyboard-logger-prior ]
[ ! -e /run/a53/keyboard-logger-clock ] && [ ! -L /run/a53/keyboard-logger-clock ]
[ ! -e /run/a53/kmsg.status.partial ] && [ ! -L /run/a53/kmsg.status.partial ]
count=0
for exe in /proc/[0-9]*/exe; do
  count=$((count+1)); [ "$count" -le 512 ]
  target=$($BB readlink "$exe") || continue
  [ "$target" != /bin/kmsg-capture ]
done
for name in kmsg.log kmsg.status kmsg-exit kmsg-pid; do
  path=/run/a53/$name
  [ -f "$path" ] && [ ! -L "$path" ]
  [ "$($BB stat -c %u:%a "$path")" = 0:600 ]
done
[ "$($BB stat -c %s /run/a53/kmsg-pid)" -le 11 ]
'''
    for name, raw in files.items():
        text += f'h=$($BB sha256sum /run/a53/{name}); [ "${{h%% *}}" = {sha(raw)} ]\n'
    # The directory is the once-only restart claim. Never clear it on failure.
    text += '''$BB mkdir -m 700 /run/a53/keyboard-logger-prior
for name in kmsg.log kmsg.status kmsg-exit kmsg-pid; do
  $BB mv /run/a53/$name /run/a53/keyboard-logger-prior/$name
done
'''
    for name, raw in files.items():
        text += f'h=$($BB sha256sum /run/a53/keyboard-logger-prior/{name}); [ "${{h%% *}}" = {sha(raw)} ]\n'
    if retry_id is not None:
        text = text.replace('/run/a53/keyboard-logger-prior', '/run/a53/keyboard-logger-prior-' + retry_id)
        absent = '[ ! -e /run/a53/keyboard-logger-clock ] && [ ! -L /run/a53/keyboard-logger-clock ]'
        clock = C['regular'](session/'logger-clock.txt', 128)
        require(len(clock.split()) == 3 and clock.split()[0].decode() == boot, 'prior clock identity')
        text = text.replace(absent, '[ -f /run/a53/keyboard-logger-clock ] && [ ! -L /run/a53/keyboard-logger-clock ]\n'
            '[ "$($BB stat -c %u:%a /run/a53/keyboard-logger-clock)" = 0:600 ]\n'
            f'h=$($BB sha256sum /run/a53/keyboard-logger-clock); [ "${{h%% *}}" = {sha(clock)} ]')
        text += f'$BB mv /run/a53/keyboard-logger-clock /run/a53/keyboard-logger-prior-{retry_id}/keyboard-logger-clock\n'
    text += f'''started=$($BB awk '{{print $1}}' /proc/uptime)
# The connection stays open and owns/reaps this child; no daemon or PID 1 change.
/bin/kmsg-capture </dev/null >/dev/null &
logger_pid=$!
interrupted=0
stop_logger() {{ trap '' HUP INT TERM; interrupted=1; /bin/kmsg-seal || :; }}
trap stop_logger HUP INT TERM
$BB printf '%s\\n' "$logger_pid" >/run/a53/kmsg-pid
$BB printf '%s %s %s\\n' '{boot}' "$logger_pid" "$started" >/run/a53/keyboard-logger-clock
$BB printf '__KEYBOARD_LOGGER_STARTED__\\n'
set +e
# Dropbear's channel-idle limit ignores SSH-level keepalives. Preserve the
# 600-second logger bound; reap within five seconds of its terminal state.
ticks=0
while [ "$ticks" -lt 120 ] && kill -0 "$logger_pid" 2>/dev/null; do
  ticks=$((ticks+1))
  if [ "$((ticks % 4))" -eq 1 ]; then $BB printf '__KEYBOARD_LOGGER_WAIT__\\n'; fi
  $BB sleep 5
done
wait "$logger_pid"
status=$?
# A trapped signal may interrupt wait before the child is terminal.
if [ "$interrupted" -eq 1 ]; then
  wait "$logger_pid"
  waited=$?
  [ "$waited" -eq 127 ] || status=$waited
fi
trap - HUP INT TERM
$BB printf '%s\\n' "$status" >/run/a53/kmsg-exit
$BB printf '__KEYBOARD_LOGGER_EXIT__=%s\\n' "$status"
exit "$status"
'''
    return {'command': text.encode(), 'boot_id': boot, 'candidate': candidate,
            'keys': dependency['prepared']['keys'],
            'original_files': {name: sha(raw) for name, raw in files.items()}}
