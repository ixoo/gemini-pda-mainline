#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""P1: one bounded SSH stream and one guarded standard core disconnect.

Use a 135 s Wi-Fi acquisition, unchanged 10 s ConnectTimeout, 210 s poll,
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
import inspect
import selectors
import time

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('core_disconnect_retained_client',
                                            HERE / 'laptop-wifi-ssh-retain.py')
R = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(R)
M = R.D.O.C.M

M.FATAL_RE += '|one-shot WLAN join data phase end: '
FROZEN_CYCLE = inspect.getsource(M.run_cycle)
FROZEN_MAIN = inspect.getsource(M.main)
if FROZEN_CYCLE.count('min(25.0, remaining)') != 1 or FROZEN_MAIN.count('120') != 3:
    raise ValueError('frozen host limit anchors changed')
exec(compile(FROZEN_CYCLE.replace('min(25.0, remaining)', 'min(135.0, remaining)'),
             '<P1 exchange bound>', 'exec'), M.__dict__)
exec(compile(FROZEN_MAIN.replace('120','210'), '<P1 poll bound>', 'exec'), M.__dict__)
WPA_CLI_SHA = '04fdf3ae5615f7831461028331bcc6c62d7c6d6974c2676f5b3a93960e5afd22'
SESSION = 'session-ccmp-p1'
TICK = re.compile(rb'P1_STREAM ordinal=(0|[1-9][0-9]{0,2}) boot=([0-9a-f-]{36}) pm_offset_ns=(\d+) clock_resolution_ns=10000000$')



def stream_command(boot):
    if not M.BOOT_ID.fullmatch(boot):
        raise ValueError('invalid stream boot')
    script = r"""
BB=/bin/busybox
[ -t 0 ] && [ -t 1 ] && [ -t 2 ] || exit 30
owner=$$
# shellcheck disable=SC2046  # trusted proc-stat tail fields require splitting
set -- $($BB sed 's/^.*) //' /proc/$$/stat)
[ "$3" = "$owner" ] && [ "$4" = "$owner" ] && [ "$6" = "$owner" ] || exit 36
trap 'trap - HUP TERM; kill -TERM 0; exit 37' HUP TERM
# shellcheck disable=SC2016  # literal awk fields
p=$(dmesg | $BB awk '/one-shot WLAN PM credit clock: / {for(i=1;i<=NF;i++) if($i ~ /^ns=[0-9]+$/) {v=substr($i,4); n++}} END {if(n==1) print v; else exit 1}') || exit 34
$BB printf 'P1_OWNED_TTY boot=%s owned_group=1 tag=%s\n' EXPECTED_BOOT STREAM_TAG
i=0
while [ "$i" -le 242 ]; do
    if [ "$i" -gt 0 ]; then
        target=$((start+i*500000000))
        while :; do
            # shellcheck disable=SC2016  # literal awk fields
            n=$($BB awk '{printf "%.0f\n", $1*1000000000}' /proc/uptime)
            [ "$n" -lt "$target" ] || break
            $BB sleep 0.05
        done
    fi
    [ "$(cat /proc/sys/kernel/random/boot_id)" = EXPECTED_BOOT ] || exit 31
    d=$(dmesg) || exit 32
    if printf '%s' "$d" | $BB grep -Eq FATAL_PATTERN; then exit 33; fi
    # shellcheck disable=SC2016  # literal awk fields
    n=$($BB awk '{printf "%.0f\n", $1*1000000000}' /proc/uptime)
    [ "$n" -ge "$p" ] || exit 35
    if [ "$i" = 0 ]; then
        [ "$((n-p))" -le 5000000000 ] || exit 38
        start=$n
    else
        [ "$((n-target))" -le 400000000 ] || exit 39
    fi
    $BB printf 'P1_STREAM ordinal=%s boot=%s pm_offset_ns=%s clock_resolution_ns=10000000\n' "$i" EXPECTED_BOOT "$((n-p))" >&2
    i=$((i+1))
done
""".replace('EXPECTED_BOOT', shlex.quote(boot)).replace('STREAM_TAG', shlex.quote('P1_STREAM_OWNER_'+boot)).replace('FATAL_PATTERN', shlex.quote(M.FATAL_RE))
    start_guard = r""";
[ -t 0 ] && [ -t 1 ] && [ -t 2 ] || exit 30
[ "$(cat /proc/sys/kernel/random/boot_id)" = EXPECTED_BOOT ] || exit 31
# shellcheck disable=SC2016  # literal awk fields
p=$(printf '%s\n' "$d" | /bin/busybox awk '/one-shot WLAN PM credit clock: / {for(i=1;i<=NF;i++) if($i ~ /^ns=[0-9]+$/) {v=substr($i,4); n++}} END {if(n==1) print v; else exit 1}') || exit 34
# shellcheck disable=SC2016  # literal awk fields
n=$(/bin/busybox awk '{printf "%.0f\n", $1*1000000000}' /proc/uptime)
[ "$n" -ge "$p" ] && [ "$((n-p))" -le 5000000000 ] || exit 38
# shellcheck disable=SC2016  # expand this quoted program only in its child
exec /bin/busybox timeout 125 /bin/busybox sh -c """.replace('EXPECTED_BOOT', shlex.quote(boot))
    command = M.COMMAND+(start_guard+shlex.quote(script)).replace('{','{{').replace('}','}}')
    if len(command.encode()) > 4096:
        raise ValueError('stream command exceeds process-observation cap')
    return command



def stream_observation(output, boot):
    records = [m for line in output.splitlines() if (m := TICK.fullmatch(line))]
    if len(records) != 243 or sum(line.startswith(b'P1_STREAM') for line in output.splitlines()) != 243:
        return {'pass': False, 'reason': 'missing or malformed stream tick'}
    owned = ('P1_OWNED_TTY boot='+boot+' owned_group=1 tag=P1_STREAM_OWNER_'+boot).encode()
    if output.splitlines().count(owned) != 1:
        return {'pass': False, 'reason': 'owned PTY group not verified'}
    offsets = [int(m[3]) for m in records]
    valid = ([int(m[1]) for m in records] == list(range(243)) and
             all(m[2].decode() == boot for m in records) and 0 <= offsets[0] <= 5_000_000_000 and
             all(a < b for a,b in zip(offsets,offsets[1:])) and
             all(0 <= value-offsets[0]-i*500_000_000 <= 400_000_000
                 for i,value in enumerate(offsets)) and
             offsets[-1]-offsets[0] >= 121_000_000_000)
    return {'pass': valid, 'pm_offsets_ns': offsets, 'clock_resolution_ns': 10000000,
            'required_stream_ms': 120000, 'scheduled_stream_ms': 121000,
            'owned_pty_group': True, 'scope': 'boot-bound authenticated SSH PTY output, raw bytes retained'}


def disconnect_argument(boot, pm, early_abort=False):
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
[ "$o" -ge LOWER_BOUND ] && [ "$o" -le 135000000000 ] || exit 49
printf 'P1_DISCONNECT boot=%s before_pm_offset_ns=%s\n' BOOT_VALUE "$o"
rc=0
reply=$($BB timeout 3 /bin/wpa_cli -p /tmp/wpa -i wlan0 disconnect) || rc=$?
# shellcheck disable=SC2016  # literal awk fields
n=$($BB awk '{printf "%.0f\n", $1 * 1000000000}' /proc/uptime)
[ "$(cat /proc/sys/kernel/random/boot_id)" = BOOT_VALUE ] || exit 50
printf 'P1_DISCONNECT_RESULT exit=%s after_pm_offset_ns=%s reply_ok=' "$rc" "$((n-p))"
if [ "$reply" = OK ]; then printf '1\n'; else printf '0\n'; fi
[ "$rc" = 0 ] && [ "$reply" = OK ]
'''.replace('BOOT_VALUE', shlex.quote(boot)).replace('CLI_SHA', WPA_CLI_SHA).replace('LOWER_BOUND', '6000000000' if early_abort else '120000000000').replace(
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
tag=P1_STREAM_OWNER_
tag=$tag$b
owners=0
seen=0
for f in /proc/[0-9]*/cmdline; do
    [ -e "$f" ] || continue
    seen=$((seen+1))
    [ "$seen" -le 512 ] || exit 65
    v=$({ $BB head -c 4096 "$f" 2>/dev/null; printf '\nP1_PROC_READ=%s\n' "$?"; } | $BB tr '\000' ' ')
    status=$(printf '%s\n' "$v" | $BB tail -n 1)
    if [ "$status" != P1_PROC_READ=0 ]; then
        [ ! -e "$f" ] && continue
        exit 66
    fi
    case "$v" in *"$tag"*) owners=$((owners+1)) ;; esac
done
printf 'P1_REMOTE boot=%s pm_offset_ns=%s owner_count=%s proc_cap=512 cmd_cap=4096\n' "$b" "$((n-p))" "$owners"
'''.replace('BOOT_VALUE', shlex.quote(boot))
    if ('P1_STREAM_OWNER_' + boot) in script:
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
    if re.fullmatch(r'[1-9][0-9]*', fields.get('P1_PM_NS', '')) and \
            re.fullmatch(r'[0-9]+', fields.get('P1_NOW_NS', '')):
        offset = int(fields['P1_NOW_NS']) - int(fields['P1_PM_NS'])
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
                match = re.fullmatch(rb'P1_REMOTE boot=' + boot.encode() +
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
    if options.pop('stdout') != subprocess.PIPE or not 0 < timeout <= 135 or 'stdin' in options or options.get('stderr') == subprocess.PIPE:
        raise ValueError('unexpected stream acquisition options')
    begun = time.monotonic_ns()
    retained, partial = bytearray(), bytearray()
    total, tick_count, overlong, discard_line = 0, 0, False, False
    ticks = []
    proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, **options)
    with selectors.DefaultSelector() as selector:
        selector.register(proc.stdout, selectors.EVENT_READ)

        def consume(data):
            nonlocal total, tick_count, partial, overlong, discard_line
            now = time.monotonic_ns()-begun
            total += len(data)
            retained.extend(data[:max(0,65536-len(retained))])
            if discard_line:
                end = data.find(b'\n')
                if end < 0:
                    return
                data = data[end+1:]
                discard_line = False
            partial.extend(data)
            while b'\n' in partial:
                line, _, rest = partial.partition(b'\n')
                partial = bytearray(rest)
                match = TICK.fullmatch(bytes(line).rstrip(b'\r'))
                if match:
                    tick_count += 1
                    if len(ticks) < 244:
                        ticks.append([int(match[1]),now])
            if len(partial) > 4096:
                overlong, discard_line = True, True
                partial.clear()

        def read_ready(wait):
            for key,_ in selector.select(wait):
                data = os.read(key.fileobj.fileno(),4096)
                if data:
                    consume(data)
                else:
                    selector.unregister(key.fileobj)

        def metadata(target):
            target.p1_stdout_total = total
            target.p1_receive_ticks = ticks
            target.p1_receive_tick_count = tick_count
            target.p1_output_overlong_line = overlong
            return target

        try:
            end = time.monotonic()+timeout
            while selector.get_map() or proc.poll() is None:
                remaining = end-time.monotonic()
                if remaining <= 0:
                    proc.kill()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired as exc:
                        raise RuntimeError('owned SSH child did not terminate; custody gate must hold') from exc
                    # Drain only immediately readable bytes; never wait for an
                    # unknown descendant. The parent still owns the whole PGID.
                    while selector.get_map() and selector.select(0):
                        read_ready(0)
                    raise metadata(subprocess.TimeoutExpired(argv,timeout,output=bytes(retained)))
                read_ready(min(0.2,remaining))
            return metadata(subprocess.CompletedProcess(argv,proc.returncode,stdout=bytes(retained)))
        finally:
            if proc.stdin is not None:
                proc.stdin.close()
            if proc.stdout is not None:
                proc.stdout.close()


def run(root, keys, boot, cycles, poll, runner=held_stdin_runner,
        monotonic=time.monotonic, sleep=time.sleep):
    if cycles != 1 or poll != 210:
        raise ValueError('P1 requires one cycle and its reviewed 210-second host poll')
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
                captured['ssh_output'] = {'actual_bytes': getattr(exc, 'p1_stdout_total', len(exc.output or b'')),
                                          'retained_bytes': len(exc.output or b''), 'limit_bytes': 65536}
                captured['ssh_output']['truncated'] = captured['ssh_output']['actual_bytes'] > captured['ssh_output']['retained_bytes']
                captured['receive_ticks'] = getattr(exc,'p1_receive_ticks',[])
                captured['receive_tick_count'] = getattr(exc,'p1_receive_tick_count',0)
                captured['overlong_line'] = getattr(exc,'p1_output_overlong_line',False)
                raise
            captured['ssh_output'] = {'actual_bytes': getattr(response, 'p1_stdout_total', len(response.stdout)),
                                      'retained_bytes': len(response.stdout), 'limit_bytes': 65536}
            captured['ssh_output']['truncated'] = captured['ssh_output']['actual_bytes'] > captured['ssh_output']['retained_bytes']
            captured['receive_ticks'] = getattr(response,'p1_receive_ticks',[])
            captured['receive_tick_count'] = getattr(response,'p1_receive_tick_count',0)
            captured['overlong_line'] = getattr(response,'p1_output_overlong_line',False)
            return response
        if 'DATA_ENDED=' in argv[-1] and not any(x.startswith('HostKeyAlias=') for x in argv):
            suffix = ('; printf "P1_PM_NS=%s\\n" "$(printf "%s\\n" "$d" | /bin/busybox awk '
                      "'/one-shot WLAN PM credit clock: / {for(i=1;i<=NF;i++) if($i ~ /^ns=[0-9]+$/) {v=substr($i,4); n++}} END {if(n==1) print v; else exit 1}')\"; "
                      'printf "P1_NOW_NS=%s\\n" "$(/bin/busybox awk '\
                      "'{printf \"%.0f\\n\", $1 * 1000000000}' /proc/uptime)\"")
            argv = [*argv[:-1], argv[-1] + suffix]
            # The retained short-session observer supplies 0.5 s. P1's declared
            # software USB envelope is the same 15 s used by its other reads;
            # keep the remote script and every control-time gate unchanged.
            if kwargs.get('timeout') != 0.5:
                raise ValueError('unexpected post-client snapshot limit')
            kwargs = {**kwargs, 'timeout': 15}
            probe_started = monotonic()
            try:
                response = runner(argv, **kwargs)
            finally:
                captured['window_probe'] = {
                    'timeout_seconds': 15,
                    'elapsed_ns': int((monotonic() - probe_started) * 1e9)}
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
        received = captured.get('receive_ticks', [])
        gaps = [b[1]-a[1] for a,b in zip(received,received[1:])]
        span = received[-1][1]-received[0][1] if len(received) == 243 else None
        stream['host_receive_ticks'] = received
        stream['host_receive_span_ns'] = span
        stream['host_receive_max_gap_ns'] = max(gaps) if gaps else None
        stream['receive_continuity_pass'] = bool(
            len(received) == captured.get('receive_tick_count') == 243 and
            [r[0] for r in received] == list(range(243)) and span >= 120_000_000_000 and
            0 <= received[0][1] <= received[-1][1] <= stream['host_elapsed_ns'] and
            all(0 <= g <= 3_000_000_000 for g in gaps) and not captured.get('overlong_line'))
        stream['pass'] = bool(stream['pass'] and stream['receive_continuity_pass'] and
                              stream['host_elapsed_ns'] >= 121_000_000_000 and
                              captured.get('ssh_output', {}).get('actual_bytes', 65537) <= 65536 and
                              process['exit'] == 0 and not process['timeout'] and
                              result['cycles'][0]['boot_match'])
    remote = remote_quiescence(root, keys, boot, result, captured, started + poll,
                               runner, monotonic, sleep)
    control = {'attempted': False, 'accepted': False, 'reason': 'no freshly verified open-window snapshot'}
    fields = captured.get('fields', {})
    if remote['quiesced'] and result.get('driver_window_after_client', {}).get('driver_data_window') == 'open' and \
            fields.get('BOOT') == boot and re.fullmatch(r'[1-9][0-9]*', fields.get('P1_PM_NS', '')) and \
            re.fullmatch(r'[0-9]+', fields.get('P1_NOW_NS', '')):
        pm, now = int(fields['P1_PM_NS']), int(fields['P1_NOW_NS'])
        early_abort = not stream.get('pass',False)
        lower = 6_000_000_000 if early_abort else 120_000_000_000
        control['kind'] = 'abort_after_incomplete_stream' if early_abort else 'after_completed_stream'
        if pm+lower <= now <= pm+135_000_000_000 and monotonic() < started+poll-15:
            control.update(attempted=True, reason=None)
            raw, error = b'', b''
            try:
                response = runner(M.usb_command(keys, disconnect_argument(boot, pm, early_abort)),
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
                raw = response.stdout
                control.update(exit=response.returncode, stderr_bytes=len(response.stderr))
                error = response.stderr
                before = re.fullmatch(rb'P1_DISCONNECT boot=' + boot.encode() + rb' before_pm_offset_ns=(\d+)', raw.splitlines()[0]) if raw.splitlines() else None
                after = re.fullmatch(rb'P1_DISCONNECT_RESULT exit=0 after_pm_offset_ns=(\d+) reply_ok=1', raw.splitlines()[1]) if len(raw.splitlines()) == 2 else None
                control['accepted'] = bool(response.returncode == 0 and before and after and
                                           lower <= int(before[1]) <= 135_000_000_000 and
                                           int(before[1]) <= int(after[1]) <= 140_000_000_000)
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
    result['p1_stream'] = stream
    result['p1_remote_stream_quiescence'] = remote
    result['p1_ssh_option_change'] = '-T to -tt; owned stdin pipe held open without data; authentication/host-key/route options unchanged'
    result['p1_ssh_output'] = captured.get('ssh_output')
    result['p1_core_disconnect'] = control
    result['p1_control_pm_interval_ns'] = [120_000_000_000,135_000_000_000]
    result['p1_post_client_probe'] = captured.get('window_probe')
    result['p1_host_limits'] = {'poll_seconds':210,'ssh_seconds':135,'remote_seconds':125,'parent_join_seconds':270,'grace_seconds':5}
    result['p1_60s_budget_pass_claimed'] = False
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
        raise ValueError('receipt outside P1 namespace')
    if receipt.exists() or receipt.is_symlink():
        raise ValueError('P1 receipt already exists')
    for option,value in [('--cycles','1'),('--poll-seconds','210')]:
        if sys.argv.count(option) != 1 or sys.argv[sys.argv.index(option)+1] != value:
            raise ValueError('P1 requires one cycle and its reviewed 210-second host poll')
    M.run = lambda keys, boot, cycles, poll: run(
        receipt.parent / 'ssh-client-observation', keys, boot, cycles, poll)
    try:
        return M.main()
    except Exception as exc:
        # Preserve an observed host failure in the already validated private
        # receipt namespace. Unknown owner state must hold parent recovery.
        if not receipt.exists():
            failure = {'boot_id': None, 'cycles_expected': 1, 'cycles': [], 'all_pass': False,
                       'p1_host_exception': {'type':type(exc).__name__,'detail':str(exc)[:4096]},
                       'p1_remote_stream_quiescence': {'quiesced':False,
                           'reason':'helper exception; remote ownership not confirmed'}}
            fd = os.open(str(receipt),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
            with os.fdopen(fd,'w') as output:
                json.dump(failure,output,sort_keys=True)
                output.write('\n')
        raise


if __name__ == '__main__':
    raise SystemExit(main())
