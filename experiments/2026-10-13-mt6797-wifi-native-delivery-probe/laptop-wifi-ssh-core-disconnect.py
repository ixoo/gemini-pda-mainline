#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""S1: one bounded SSH stream and one guarded standard core disconnect.

Keep the existing 25 s Wi-Fi acquisition, 10 s ConnectTimeout, 90 s poll,
periodic leaf, owned-process group and evidence/recovery mechanics. New control
uses an already available three-second BusyBox timeout and one <=15 s USB call.
"""
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('core_disconnect_retained_client',
                                            HERE / 'laptop-wifi-ssh-retain.py')
R = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(R)
M = R.D.O.C.M
WPA_CLI_SHA = '04fdf3ae5615f7831461028331bcc6c62d7c6d6974c2676f5b3a93960e5afd22'
SESSION = 'session-ccmp-gtk8-s1'
TICK = re.compile(rb'S1_STREAM ordinal=([0-4]) boot=([0-9a-f-]{36}) pm_offset_ns=(\d+) clock_resolution_ns=10000000$')


def stream_command(boot):
    if not M.BOOT_ID.fullmatch(boot):
        raise ValueError('invalid stream boot')
    # PTY output keeps the frozen boot/ready fields and adds independent ticks.
    script = r'''
BB=/bin/busybox
[ -t 0 ] && [ -t 1 ] && [ -t 2 ] || exit 30
owner=$$
# shellcheck disable=SC2046  # trusted proc-stat tail fields require splitting
set -- $($BB sed 's/^.*) //' /proc/$$/stat)
[ "$3" = "$owner" ] && [ "$4" = "$owner" ] && [ "$6" = "$owner" ] || exit 36
# This is only our verified foreground PTY session, never another PID/group.
trap 'trap - HUP TERM; kill -TERM 0; exit 37' HUP TERM
# shellcheck disable=SC2016  # literal awk fields
p=$(dmesg | $BB awk '/one-shot WLAN PM credit clock: / {for(i=1;i<=NF;i++) if($i ~ /^ns=[0-9]+$/) {v=substr($i,4); n++}} END {if(n==1) print v; else exit 1}') || exit 34
# shellcheck disable=SC2016  # literal awk fields
n=$($BB awk '{printf "%.0f\n", $1 * 1000000000}' /proc/uptime)
[ "$n" -ge "$p" ] && [ "$((n-p))" -le 5000000000 ] || exit 38
$BB printf 'S1_OWNED_TTY boot=%s owned_group=1 tag=%s\n' EXPECTED_BOOT STREAM_TAG

i=0
while [ "$i" -le 4 ]; do
    [ "$(cat /proc/sys/kernel/random/boot_id)" = EXPECTED_BOOT ] || exit 31
    d=$(dmesg) || exit 32
    if printf '%s' "$d" | $BB grep -Eq FATAL_PATTERN; then exit 33; fi
    # shellcheck disable=SC2016  # literal awk fields
    p=$(printf '%s\n' "$d" | $BB awk '/one-shot WLAN PM credit clock: / {for(i=1;i<=NF;i++) if($i ~ /^ns=[0-9]+$/) {v=substr($i,4); n++}} END {if(n==1) print v; else exit 1}') || exit 34
    # shellcheck disable=SC2016  # literal awk fields
    n=$($BB awk '{printf "%.0f\n", $1 * 1000000000}' /proc/uptime)
    [ "$n" -ge "$p" ] || exit 35
    $BB printf 'S1_STREAM ordinal=%s boot=%s pm_offset_ns=%s clock_resolution_ns=10000000\n' "$i" EXPECTED_BOOT "$((n-p))" >&2
    [ "$i" = 4 ] || $BB sleep 5
    i=$((i+1))
done
'''.replace('EXPECTED_BOOT', shlex.quote(boot)).replace('STREAM_TAG', shlex.quote('S1_STREAM_OWNER_' + boot)).replace('FATAL_PATTERN', shlex.quote(M.FATAL_RE))
    # The frozen command formatter expands only its {ready} placeholder.
    start_guard = r''';
[ -t 0 ] && [ -t 1 ] && [ -t 2 ] || exit 30
[ "$(cat /proc/sys/kernel/random/boot_id)" = EXPECTED_BOOT ] || exit 31
# shellcheck disable=SC2016  # literal awk fields
p=$(printf '%s\n' "$d" | /bin/busybox awk '/one-shot WLAN PM credit clock: / {for(i=1;i<=NF;i++) if($i ~ /^ns=[0-9]+$/) {v=substr($i,4); n++}} END {if(n==1) print v; else exit 1}') || exit 34
# shellcheck disable=SC2016  # literal awk fields
n=$(/bin/busybox awk '{printf "%.0f\n", $1 * 1000000000}' /proc/uptime)
[ "$n" -ge "$p" ] && [ "$((n-p))" -le 5000000000 ] || exit 38
# shellcheck disable=SC2016  # expand the quoted program only in its child shell
exec /bin/busybox timeout 22 /bin/busybox sh -c '''.replace('EXPECTED_BOOT', shlex.quote(boot))
    wrapped = start_guard + shlex.quote(script)
    command = M.COMMAND + wrapped.replace('{', '{{').replace('}', '}}')
    if len(command.encode()) > 4096:
        raise ValueError('stream command exceeds process-observation cap')
    return command


def stream_observation(output, boot):
    records = [m for line in output.splitlines() if (m := TICK.fullmatch(line))]
    if len(records) != 5 or sum(line.startswith(b'S1_STREAM') for line in output.splitlines()) != 5:
        return {'pass': False, 'reason': 'missing or malformed stream tick'}
    owned = ('S1_OWNED_TTY boot=' + boot + ' owned_group=1 tag=S1_STREAM_OWNER_' + boot).encode()
    if output.splitlines().count(owned) != 1:
        return {'pass': False, 'reason': 'owned PTY group not verified'}
    offsets = [int(m[3]) for m in records]
    valid = ([int(m[1]) for m in records] == list(range(5)) and
             all(m[2].decode() == boot for m in records) and
             all(a < b for a, b in zip(offsets, offsets[1:])) and
             offsets[-1] - offsets[0] >= 20_000_000_000 and
             offsets[-1] > 9_000_000_000)
    return {'pass': valid, 'pm_offsets_ns': offsets, 'clock_resolution_ns': 10000000,
            'planned_stream_ms': 20000, 'owned_pty_group': True,
            'scope': 'authenticated SSH PTY output; raw stdout retained, frozen identity fields verified separately'}


def disconnect_argument(boot, pm):
    if not M.BOOT_ID.fullmatch(boot) or not isinstance(pm, int) or pm <= 0:
        raise ValueError('invalid disconnect identity')
    # No remote sleep or retry. The command may end the data phase intentionally.
    return r'''set -eu
BB=/bin/busybox
[ "$(cat /proc/sys/kernel/random/boot_id)" = BOOT_VALUE ] || exit 41
[ "$(uname -r)" = 7.1.3-gemini-a53-wifi-ccmp-stable-monitor ] || exit 42
[ "$($BB sha256sum /bin/wpa_cli | $BB cut -d' ' -f1)" = CLI_SHA ] || exit 43
d=$(dmesg)
printf '%s' "$d" | $BB grep -q 'one-shot WLAN native-diag: state=2 ' || exit 44
if printf '%s' "$d" | $BB grep -Eq FATAL_PATTERN; then exit 45; fi
if printf '%s' "$d" | $BB grep -q 'one-shot WLAN join data phase end:'; then exit 46; fi
# shellcheck disable=SC2016  # literal awk fields
p=$(printf '%s\n' "$d" | $BB awk '/one-shot WLAN PM credit clock: / {for(i=1;i<=NF;i++) if($i ~ /^ns=[0-9]+$/) {v=substr($i,4); n++}} END {if(n==1) print v; else exit 1}') || exit 47
[ "$p" = PM_VALUE ] || exit 48
# shellcheck disable=SC2016  # literal awk fields
n=$($BB awk '{printf "%.0f\n", $1 * 1000000000}' /proc/uptime)
o=$((n-p))
[ "$o" -ge 55000000000 ] && [ "$o" -le 56000000000 ] || exit 49
printf 'S1_DISCONNECT boot=%s before_pm_offset_ns=%s\n' BOOT_VALUE "$o"
rc=0
reply=$($BB timeout 3 /bin/wpa_cli -p /tmp/wpa -i wlan0 disconnect) || rc=$?
# shellcheck disable=SC2016  # literal awk fields
n=$($BB awk '{printf "%.0f\n", $1 * 1000000000}' /proc/uptime)
[ "$(cat /proc/sys/kernel/random/boot_id)" = BOOT_VALUE ] || exit 50
printf 'S1_DISCONNECT_RESULT exit=%s after_pm_offset_ns=%s reply_ok=' "$rc" "$((n-p))"
if [ "$reply" = OK ]; then printf '1\n'; else printf '0\n'; fi
[ "$rc" = 0 ] && [ "$reply" = OK ]
'''.replace('BOOT_VALUE', shlex.quote(boot)).replace('CLI_SHA', WPA_CLI_SHA).replace(
        'PM_VALUE', str(pm)).replace('FATAL_PATTERN', shlex.quote(M.FATAL_RE))


def remote_quiescence_argument(boot):
    if not M.BOOT_ID.fullmatch(boot):
        raise ValueError('invalid stream observation boot')
    # Construct the tag on device so this query cannot match its own argv.
    script = r'''set -eu
BB=/bin/busybox
b=BOOT_VALUE
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$b" ] || exit 61
[ "$(uname -r)" = 7.1.3-gemini-a53-wifi-ccmp-stable-monitor ] || exit 62
d=$(dmesg)
# shellcheck disable=SC2016  # literal awk fields
p=$(printf '%s\n' "$d" | $BB awk '/one-shot WLAN PM credit clock: / {for(i=1;i<=NF;i++) if($i ~ /^ns=[0-9]+$/) {v=substr($i,4); n++}} END {if(n==1) print v; else exit 1}') || exit 63
# shellcheck disable=SC2016  # literal awk fields
n=$($BB awk '{printf "%.0f\n", $1 * 1000000000}' /proc/uptime)
[ "$n" -ge "$p" ] && [ "$((n-p))" -ge 6000000000 ] || exit 64
tag=S1_STREAM_OWNER_
tag=$tag$b
owners=0
seen=0
for f in /proc/[0-9]*/cmdline; do
    [ -e "$f" ] || continue
    seen=$((seen+1))
    [ "$seen" -le 512 ] || exit 65
    v=$({ $BB head -c 4096 "$f" 2>/dev/null; printf '\nS1_PROC_READ=%s\n' "$?"; } | $BB tr '\000' ' ')
    status=$(printf '%s\n' "$v" | $BB tail -n 1)
    if [ "$status" != S1_PROC_READ=0 ]; then
        [ ! -e "$f" ] && continue
        exit 66
    fi
    case "$v" in *"$tag"*) owners=$((owners+1)) ;; esac
done
printf 'S1_REMOTE boot=%s pm_offset_ns=%s owner_count=%s proc_cap=512 cmd_cap=4096\n' "$b" "$((n-p))" "$owners"
'''.replace('BOOT_VALUE', shlex.quote(boot))
    if ('S1_STREAM_OWNER_' + boot) in script:
        raise ValueError('observation would match itself')
    return script


def remote_quiescence(root, keys, boot, result, captured, overall_end,
                      runner, monotonic, sleep):
    attempted = any(c.get('ssh_attempted') for c in result.get('cycles', []))
    record = {'quiesced': not attempted, 'stream_admission_cutoff_pm_ns': 5_000_000_000,
              'observation_not_before_pm_ns': 6_000_000_000, 'queries': [],
              'scope': 'tagged stream command/timeout owners absent; late stream starts refused'}
    if not attempted:
        return record
    deadline = min(overall_end, monotonic() + 20)
    fields = captured.get('fields', {})
    if re.fullmatch(r'[1-9][0-9]*', fields.get('S1_PM_NS', '')) and \
            re.fullmatch(r'[0-9]+', fields.get('S1_NOW_NS', '')):
        offset = int(fields['S1_NOW_NS']) - int(fields['S1_PM_NS'])
        target = captured['returned'] + max(0, (6_000_000_000 - offset) / 1e9) + 0.1
        while monotonic() < target and monotonic() < deadline:
            sleep(max(0, min(0.2, target - monotonic())))
    with (root.parent / 'remote-stream-quiescence.raw').open('xb') as output:
        while monotonic() < deadline:
            raw, error = b'', b''
            query = {'exit': None, 'owner_count': None, 'timeout': False}
            try:
                response = runner(M.usb_command(keys, remote_quiescence_argument(boot)),
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  timeout=min(15, deadline - monotonic()))
                raw, error = response.stdout, response.stderr
                query['exit'] = response.returncode
                match = re.fullmatch(rb'S1_REMOTE boot=' + boot.encode() +
                    rb' pm_offset_ns=(\d+) owner_count=(\d+) proc_cap=512 cmd_cap=4096\n', raw)
                if response.returncode == 0 and match and int(match[1]) >= 6_000_000_000:
                    query.update(pm_offset_ns=int(match[1]), owner_count=int(match[2]))
                    record['quiesced'] = int(match[2]) == 0
            except subprocess.TimeoutExpired as exc:
                raw, error = exc.output or b'', exc.stderr or b''
                query['timeout'] = True
            except OSError as exc:
                query['error'] = type(exc).__name__
            record['queries'].append(query)
            output.write(('query=' + str(len(record['queries'])) + '\nstdout_begin\n').encode())
            output.write(raw); output.write(b'\nstderr_begin\n'); output.write(error); output.write(b'\nquery_end\n')
            if record['quiesced'] or query['owner_count'] is None:
                break  # never retry an unknown/failed acquisition
            sleep(0.2)
    return record


def held_stdin_runner(argv, **kwargs):
    if not any(a.startswith('HostKeyAlias=') for a in argv):
        return subprocess.run(argv, **kwargs)
    options = dict(kwargs)
    timeout = options.pop('timeout')
    if options.pop('stdout') != subprocess.PIPE or not 0 < timeout <= 25 or 'stdin' in options:
        raise ValueError('unexpected stream acquisition options')
    with tempfile.TemporaryFile() as output:
        proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=output, **options)
        try:
            try:
                proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired as exc:
                    raise RuntimeError('owned SSH child did not terminate; parent custody gate must hold') from exc
                total = output.seek(0, 2)
                output.seek(0)
                error = subprocess.TimeoutExpired(argv, timeout, output=output.read(65536))
                error.s1_stdout_total = total
                raise error
            total = output.seek(0, 2)
            output.seek(0)
            result = subprocess.CompletedProcess(argv, proc.returncode, stdout=output.read(65536))
            result.s1_stdout_total = total
            return result
        finally:
            if proc.stdin is not None:
                proc.stdin.close()


def run(root, keys, boot, cycles, poll, runner=held_stdin_runner,
        monotonic=time.monotonic, sleep=time.sleep):
    started = monotonic()
    captured = {}
    original = M.COMMAND
    M.COMMAND = stream_command(boot)

    def invoke(argv, **kwargs):
        if any(x.startswith('HostKeyAlias=') for x in argv):
            if argv.count('-T') != 1:
                raise ValueError('unexpected Wi-Fi TTY options')
            argv = ['-tt' if x == '-T' else x for x in argv]
            try:
                response = runner(argv, **kwargs)
            except subprocess.TimeoutExpired as exc:
                captured['ssh_output'] = {'actual_bytes': getattr(exc, 's1_stdout_total', len(exc.output or b'')),
                                          'retained_bytes': len(exc.output or b''), 'limit_bytes': 65536}
                captured['ssh_output']['truncated'] = captured['ssh_output']['actual_bytes'] > captured['ssh_output']['retained_bytes']
                raise
            captured['ssh_output'] = {'actual_bytes': getattr(response, 's1_stdout_total', len(response.stdout)),
                                      'retained_bytes': len(response.stdout), 'limit_bytes': 65536}
            captured['ssh_output']['truncated'] = captured['ssh_output']['actual_bytes'] > captured['ssh_output']['retained_bytes']
            return response
        if 'DATA_ENDED=' in argv[-1] and not any(x.startswith('HostKeyAlias=') for x in argv):
            suffix = ('; printf "S1_PM_NS=%s\\n" "$(printf "%s\\n" "$d" | /bin/busybox awk '
                      "'/one-shot WLAN PM credit clock: / {for(i=1;i<=NF;i++) if($i ~ /^ns=[0-9]+$/) {v=substr($i,4); n++}} END {if(n==1) print v; else exit 1}')\"; "
                      'printf "S1_NOW_NS=%s\\n" "$(/bin/busybox awk '\
                      "'{printf \"%.0f\\n\", $1 * 1000000000}' /proc/uptime)\"")
            argv = [*argv[:-1], argv[-1] + suffix]
            response = runner(argv, **kwargs)
            captured.update(fields=M.parse_block(response.stdout.decode('ascii', 'replace')),
                            returned=monotonic())
            return response
        return runner(argv, **kwargs)

    try:
        result = R.run(root, keys, boot, cycles, poll, runner=invoke)
    finally:
        M.COMMAND = original
    stream = stream_observation((root / 'stdout.bin').read_bytes(), boot) if root.exists() else {'pass': False, 'reason': 'SSH not reached'}
    if root.exists():
        process = json.loads((root / 'process.json').read_text())
        stream['host_elapsed_ns'] = process['ended_ns'] - process['started_ns']
        stream['pass'] = bool(stream['pass'] and stream['host_elapsed_ns'] >= 20_000_000_000 and
                              captured.get('ssh_output', {}).get('actual_bytes', 65537) <= 65536 and
                              process['exit'] == 0 and not process['timeout'] and
                              result['cycles'][0]['boot_match'])
    remote = remote_quiescence(root, keys, boot, result, captured, started + poll,
                               runner, monotonic, sleep)
    control = {'attempted': False, 'accepted': False, 'reason': 'no freshly verified open-window snapshot'}
    fields = captured.get('fields', {})
    if remote['quiesced'] and result.get('driver_window_after_client', {}).get('driver_data_window') == 'open' and \
            fields.get('BOOT') == boot and re.fullmatch(r'[1-9][0-9]*', fields.get('S1_PM_NS', '')) and \
            re.fullmatch(r'[0-9]+', fields.get('S1_NOW_NS', '')):
        pm, now = int(fields['S1_PM_NS']), int(fields['S1_NOW_NS'])
        if pm <= now < pm + 55_000_000_000:
            target = captured['returned'] + (55_000_000_000 - (now - pm)) / 1e9 + 0.2
            while monotonic() < target and monotonic() < started + poll - 15:
                sleep(max(0, min(0.2, target - monotonic())))
            if monotonic() >= target and monotonic() < started + poll - 15:
                control.update(attempted=True, reason=None)
                raw, error = b'', b''
                try:
                    response = runner(M.usb_command(keys, disconnect_argument(boot, pm)),
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
                    raw = response.stdout
                    control.update(exit=response.returncode, stderr_bytes=len(response.stderr))
                    error = response.stderr
                    before = re.fullmatch(rb'S1_DISCONNECT boot=' + boot.encode() + rb' before_pm_offset_ns=(\d+)', raw.splitlines()[0]) if raw.splitlines() else None
                    after = re.fullmatch(rb'S1_DISCONNECT_RESULT exit=0 after_pm_offset_ns=(\d+) reply_ok=1', raw.splitlines()[1]) if len(raw.splitlines()) == 2 else None
                    control['accepted'] = bool(response.returncode == 0 and before and after and
                                               55_000_000_000 <= int(before[1]) <= 56_000_000_000 and
                                               int(before[1]) <= int(after[1]) < 60_000_000_000)
                    if before:
                        control['before_pm_offset_ns'] = int(before[1])
                    if after:
                        control['after_pm_offset_ns'] = int(after[1])
                    if not control['accepted']:
                        control['reason'] = 'guard or bounded standard disconnect refused'
                except subprocess.TimeoutExpired as exc:
                    raw, error = exc.output or b'', exc.stderr or b''
                    control.update(timeout=True, reason='bounded control call timed out')
                except OSError as exc:
                    control.update(reason=type(exc).__name__)
                with (root.parent / 'core-disconnect.stdout').open('xb') as output:
                    output.write(raw)
                with (root.parent / 'core-disconnect.stderr').open('xb') as output:
                    output.write(error)
    result['s1_stream'] = stream
    result['s1_remote_stream_quiescence'] = remote
    result['s1_ssh_option_change'] = '-T to -tt; owned stdin pipe held open without data; authentication/host-key/route options unchanged'
    result['s1_ssh_output'] = captured.get('ssh_output')
    result['s1_core_disconnect'] = control
    result['s1_planned_stop_pm_offset_ns'] = 55_000_000_000
    result['s1_60s_budget_pass_claimed'] = False
    result['all_pass'] = bool(result['all_pass'] and stream['pass'] and remote['quiesced'] and control['accepted'])
    return result


def main():
    os.umask(0o077)
    if sys.platform != 'darwin' or sys.argv.count('--receipt') != 1:
        raise ValueError('custodian laptop and one owned receipt required')
    receipt = Path(sys.argv[sys.argv.index('--receipt') + 1])
    runtime = Path(os.environ['GEMINI_RUNTIME_ROOT']).resolve(strict=True)
    expected = runtime / 'ccmp-stable-monitor' / SESSION / 'wifi-ssh-receipt.json'
    if receipt != expected or receipt.parent.resolve(strict=True) != receipt.parent:
        raise ValueError('receipt outside S1 namespace')
    M.run = lambda keys, boot, cycles, poll: run(
        receipt.parent / 'ssh-client-observation', keys, boot, cycles, poll)
    return M.main()


if __name__ == '__main__':
    raise SystemExit(main())
