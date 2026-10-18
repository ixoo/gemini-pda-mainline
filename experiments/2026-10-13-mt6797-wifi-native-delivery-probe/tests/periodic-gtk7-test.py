#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Actual periodic shell function with synthetic clock/network; no device."""
from pathlib import Path
import os
import re
import subprocess
import tempfile

source = Path(__file__).resolve().parents[1] / 'join-ccmp-gtk7.sh'
text = source.read_text()
start = text.index('periodic_now_ns() {')
end = text.index('\nstage=target_input', start)
body = text[start:end]
anchor = 'pc_dir="/tmp/mt6797-wifi-phase-b-1/c$pc_cyc"'
assert body.count(anchor) == 1
body = body.replace(anchor, 'pc_dir="$TEST_ROOT/c$pc_cyc"')  # filesystem-only adapter
assert 'for pc_sec in 10 20 30 40 50;' in body
assert text.index('pc_result=0; periodic_data_checks') < text.index('wr=0; wait_host_ack "$cyc"')
shim = r'''
set -eu
BB=bb
EXPECTED_BOOT=00000000-0000-4000-8000-000000000001
CLOCK_NS=$START_NS
PM_NS=100000000000
CALLS=0
deadline=300
now_s() { printf '0\n'; }
window_ok() { [ "$CLOCK_NS" -lt "$END_NS" ]; }
bb() {
    applet=$1; shift
    case "$applet" in
      dmesg)
        case "$CLOCK_MODE" in
          missing) : ;;
          duplicate) printf 'one-shot WLAN PM credit clock: ns=%s\none-shot WLAN PM credit clock: ns=%s\n' "$PM_NS" "$PM_NS" ;;
          *) printf 'one-shot WLAN PM credit clock: ns=%s\n' "$PM_NS" ;;
        esac ;;
      awk)
        if [ "$#" = 2 ] && [ "$2" = /proc/uptime ]; then
            printf '%s.%02d\n' "$((CLOCK_NS / 1000000000))" "$(((CLOCK_NS % 1000000000) / 10000000))" > "$TEST_ROOT/uptime"
            command awk "$1" "$TEST_ROOT/uptime"
        else command awk "$@"; fi ;;
      cat)
        if [ "$1" = /proc/sys/kernel/random/boot_id ]; then
            if [ "$CHANGED_BOOT" = 1 ]; then printf '00000000-0000-4000-8000-000000000002\n'; else printf '%s\n' "$EXPECTED_BOOT"; fi
        else command cat "$@"; fi ;;
      sleep) [ "$1" = 0.2 ]; CLOCK_NS=$((CLOCK_NS + 200000000)) ;;
      printf) printf "$@" ;;
      sed|head|rm) command "$applet" "$@" ;;
      *) printf 'unexpected applet %s\n' "$applet" >&2; return 99 ;;
    esac
}
run_bounded() {
    [ "$1" = 1 ] && [ "$2" = 3 ]; output=$3; shift 3
    [ "$*" = 'bb ping -I wlan0 -c 1 -W 2 192.0.2.1' ]
    CALLS=$((CALLS + 1))
    printf 'ordinal=%s start_ns=%s\n' "$pc_n" "$CLOCK_NS" >> "$TEST_ROOT/calls"
    if [ "$CALLS" = "$FAIL_CALL" ]; then
        CLOCK_NS=$((CLOCK_NS + 2000000000))
        printf '1 packets transmitted, 0 packets received, 100%% packet loss\n' > "$output"
        return 1
    fi
    CLOCK_NS=$((CLOCK_NS + 100000000))
    printf '64 bytes from 192.0.2.1: seq=0 ttl=64 time=12.300 ms\n1 packets transmitted, 1 packets received, 0%% packet loss\n' > "$output"
}
'''


def run_case(name, *, start_ns=103_000_000_000, end_ns=160_000_000_000,
             router='192.0.2.1', clock_mode='normal', changed=False, fail_call=0):
    with tempfile.TemporaryDirectory(prefix='gtk7-periodic-') as directory:
        root = Path(directory).resolve()
        (root / 'c1').mkdir()
        (root / 'c1/router').write_text(router + '\n')
        initial = b'initial-three-pings-retained\n'
        (root / 'c1/ping.log').write_bytes(initial)
        env = {**os.environ, 'TEST_ROOT': str(root), 'START_NS': str(start_ns),
               'END_NS': str(end_ns), 'CLOCK_MODE': clock_mode, 'CHANGED_BOOT': str(int(changed)),
               'FAIL_CALL': str(fail_call)}
        script = shim + '\n' + body + '\nrc=0; periodic_data_checks 1 || rc=$?\nprintf "rc=%s calls=%s\\n" "$rc" "$CALLS"\n'
        result = subprocess.run(['/bin/sh'], input=script, text=True, capture_output=True, env=env, timeout=12)
        assert result.returncode == 0 and not result.stderr, (name, result.returncode, result.stderr)
        m = re.fullmatch(r'rc=(\d+) calls=(\d+)\n', result.stdout); assert m, name
        log = (root / 'c1/ping.log').read_bytes(); assert log.startswith(initial)
        rows = [dict(re.findall(r'(\w+)=([^ ]+)', line)) for line in log.decode().splitlines() if line.startswith('periodic_ping ')]
        calls = (root / 'calls').read_text().splitlines() if (root / 'calls').exists() else []
        assert len(calls) == int(m[2]) and not (root / 'c1/periodic-current.log').exists()
        return int(m[1]), rows, calls, log


rc, rows, calls, log = run_case('five-success')
assert rc == 0 and len(rows) == len(calls) == 5
for i, row in enumerate(rows, 1):
    assert int(row['ordinal']) == i and int(row['scheduled_offset_ns']) == i * 10_000_000_000
    assert row['attempted'] == '1' and row['exit'] == '0' and row['replies'] == '1'
    assert row['statistics_known'] == row['rtt_known'] == '1' and float(row['rtt_ms']) == 12.3
    assert int(row['start_offset_ns']) >= i * 10_000_000_000
    assert int(row['completion_offset_ns']) - int(row['start_offset_ns']) == 100_000_000
    assert row['clock_resolution_ns'] == '10000000'
assert log.count(b'periodic_raw ordinal=') == 10
rc, rows, calls, _ = run_case('one-failed-probe', fail_call=2)
assert rc == 1 and len(calls) == 5 and rows[1]['exit'] == '1' and rows[1]['replies'] == '0'
rc, rows, calls, _ = run_case('late-start', start_ns=125_000_000_000)
assert rc == 1 and len(calls) == 3 and [r['attempted'] for r in rows] == ['0', '0', '1', '1', '1']
rc, rows, calls, _ = run_case('window-closed', end_ns=125_000_000_000)
assert rc == 3 and len(calls) == len(rows) == 2
for name, options in [('changed-boot', {'changed': True}), ('missing-clock', {'clock_mode': 'missing'}),
                      ('duplicate-clock', {'clock_mode': 'duplicate'}), ('name-target', {'router': 'example.invalid'}),
                      ('multi-target', {'router': '192.0.2.1\n198.51.100.1'})]:
    rc, rows, calls, _ = run_case(name, **options)
    assert rc != 0 and not rows and not calls, name
print('GTK7 periodic leaf: PASS five fixed probes, clock offsets, raw retention, failure without retry, missed slots, window/boot/clock/numeric-target refusals; host simulation only')
