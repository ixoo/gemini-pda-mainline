#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise the actual periodic leaf and bound both SSH server envelopes."""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent.parent
source = (HERE / 'join-ccmp-p2.sh').read_text()
server = re.search(r'\$BB timeout (\d+) /bin/dropbear .*? -T 2', source, re.S)
assert server is not None
options = server[0]
maximum = int(re.search(r' -M (\d+)', options)[1])
idle = int(re.search(r' -I (\d+)', options)[1])
assert 625 < maximum <= int(server[1]) == 660 and idle == 30
assert source.count("periodic_progress cycle=%s ordinal=%s exit=%s replies=%s\\n") == 1
# Actual leaf code, with only its evidence directory relocated. Dependencies
# supply deterministic successful ping observations and advance the clock to
# each declared slot; neither network nor device access is performed.
body = source.split('periodic_data_checks() {\n', 1)[1].split('\nstage=target_input', 1)[0]
body = 'periodic_data_checks() {\n' + body
anchor = 'pc_dir="/tmp/mt6797-wifi-phase-b-1/c$pc_cyc"'
assert body.count(anchor) == 1
body = body.replace(anchor, 'pc_dir="$TEST_ROOT/c$pc_cyc"')
busybox = shutil.which('busybox')
if busybox is None:
    raise SystemExit('Linux fixture requires busybox; static server-envelope checks passed')
with tempfile.TemporaryDirectory(prefix='connected-leaf-') as td:
    root = Path(td)
    (root / 'c1').mkdir()
    (root / 'c1/router').write_text('192.0.2.1\n')
    wrapper = root / 'bb'
    wrapper.write_text('#!/bin/sh\nif [ "$1" = dmesg ]; then\n'
                       ' printf "one-shot WLAN PM credit clock: ns=1000000000\\n"\n'
                       'else exec ' + busybox + ' "$@"; fi\n')
    wrapper.chmod(0o700)
    script = '''set -eu
BB="$1"
TEST_ROOT="$2"
EXPECTED_BOOT=$($BB cat /proc/sys/kernel/random/boot_id)
deadline=780
now_s() { echo 1; }
window_ok() { return 0; }
periodic_now_ns() { echo "$((pc_clock + pc_sec * 1000000000 + 1000000))"; }
run_bounded() {
    printf '64 bytes from fixture: seq=0 ttl=64 time=1.000 ms\n1 packets transmitted, 1 packets received\n' > "$3"
}
''' + body + '\nperiodic_data_checks 1\n'
    result = subprocess.run(['/bin/sh', '-s', '--', str(wrapper), str(root)],
                            input=script.encode(), capture_output=True, timeout=10)
    assert result.returncode == 0 and not result.stderr, result.stderr
    expected = ''.join('periodic_progress cycle=1 ordinal=%d exit=0 replies=1\n' % n
                       for n in range(1, 60))
    assert result.stdout.decode() == expected
    log = (root / 'c1/ping.log').read_text()
    assert len(re.findall(r'^periodic_ping ', log, re.M)) == 59
    assert [int(n) for n in re.findall(r'scheduled_offset_ns=(\d+)', log)] == list(range(10**10, 591*10**9, 10**10))
print('Actual leaf: 660-second server envelope, 59 bounded numeric progress records and unchanged scheduled probes PASS')

# Exercise the actual terminal wait on a deterministic host clock, including
# its negative path. These are read-only fake observations, not a device test.
wait_body = 'wait_record() {\n' + source.split('wait_record() {\n', 1)[1].split(
    '\n# Wait for the ATTRIBUTABLE', 1)[0]
with tempfile.TemporaryDirectory(prefix='connected-terminal-wait-') as td:
    root = Path(td)
    wrapper = root / 'bb'
    wrapper.write_text('''#!/bin/sh
case "$1" in
 dmesg)
  case "$TEST_CASE" in
   fatal) printf 'one-shot WLAN join stopped: fixture\n' ;;
   reached) printf 'fixture-terminal\n' ;;
  esac ;;
 sleep)
  n=$(cat "$TEST_CLOCK")
  printf '%s\n' "$((n+1))" > "$TEST_CLOCK" ;;
 *) exec ''' + busybox + ''' "$@" ;;
esac
''')
    wrapper.chmod(0o700)
    for case, expected_rc in [('waiting', 1), ('fatal', 3), ('reached', 0), ('boot', 2)]:
        clock = root / 'clock'
        clock.write_text('0\n')
        script = '''set -eu
BB="$1"
TEST_CLOCK="$2"
TEST_CASE="$3"
export TEST_CLOCK TEST_CASE
EXPECTED_BOOT=$($BB cat /proc/sys/kernel/random/boot_id)
[ "$TEST_CASE" != boot ] || EXPECTED_BOOT=not-this-boot
deadline=35
now_s() { cat "$TEST_CLOCK"; }
''' + wait_body + '''
rc=0
wait_record fixture-terminal 1 || rc=$?
printf 'result=%s\n' "$rc" >&2
'''
        result = subprocess.run(['/bin/sh', '-s', '--', str(wrapper), str(clock), case],
                                input=script.encode(), capture_output=True, timeout=10)
        assert result.returncode == 0 and result.stderr == ('result=%d\n' % expected_rc).encode()
        expected = ''.join('record_wait_progress expected_count=1 observed_count=0 elapsed_s=%d\n' % n
                           for n in [10, 20, 30]) if case == 'waiting' else ''
        assert result.stdout.decode() == expected
        assert int(clock.read_text()) == (35 if case == 'waiting' else 0)
print('Actual terminal wait: bounded numeric progress; unchanged wall, fatal, reached and boot refusals PASS')

# The ACK wait can also last until the unchanged P2 wall after a negative
# client result; keep that same USB command observable without sending traffic.
ack_body='wait_host_ack() {\n'+source.split('wait_host_ack() {\n',1)[1].split('\nterminal_re=',1)[0]
anchor='ack="/tmp/mt6797-wifi-phase-b-1/c$1/host-ack"'
assert ack_body.count(anchor)==1
ack_body=ack_body.replace(anchor,'ack="$TEST_ROOT/c$1/host-ack"')
with tempfile.TemporaryDirectory(prefix='p2-ack-wait-') as td:
    root=Path(td);(root/'c1').mkdir();wrapper=root/'bb'
    wrapper.write_text('''#!/bin/sh
case "$1" in
 dmesg)
  [ "$TEST_CASE" != terminal ] || printf 'one-shot WLAN join cleanup: stage=3 credits=returned slots=retired deauth=1\n' ;;
 sleep) n=$(cat "$TEST_CLOCK"); printf '%s\n' "$((n+1))" > "$TEST_CLOCK" ;;
 *) exec '''+busybox+''' "$@" ;;
esac
''');wrapper.chmod(0o700)
    for case,rc in [('waiting',1),('ack',0),('boot',2),('fatal',3),('terminal',4),('window',4)]:
        clock=root/'clock';clock.write_text('0\n');ack=root/'c1/host-ack'
        if ack.exists():ack.unlink()
        script='''set -eu
BB="$1"; TEST_ROOT="$2"; TEST_CLOCK="$3"; TEST_CASE="$4"
export TEST_ROOT TEST_CLOCK TEST_CASE
EXPECTED_BOOT=$($BB cat /proc/sys/kernel/random/boot_id)
[ "$TEST_CASE" != ack ] || printf 'host_ack boot=%s cycle=1 ssh_exit=0\n' "$EXPECTED_BOOT" > "$TEST_ROOT/c1/host-ack"
[ "$TEST_CASE" != boot ] || EXPECTED_BOOT=not-this-boot
deadline=35
now_s() { cat "$TEST_CLOCK"; }
fatal_record() { [ "$TEST_CASE" = fatal ]; }
window_ok() { [ "$TEST_CASE" != window ]; }
'''+ack_body+'''
rc=0
wait_host_ack 1 || rc=$?
printf 'result=%s\n' "$rc" >&2
'''
        got=subprocess.run(['/bin/sh','-s','--',str(wrapper),str(root),str(clock),case],input=script.encode(),capture_output=True,timeout=10)
        assert got.returncode==0 and got.stderr==('result=%d\n'%rc).encode(),got.stderr
        expected=''.join('ack_wait_progress cycle=1 elapsed_s=%d\n'%n for n in [10,20,30]) if case=='waiting' else ''
        assert got.stdout.decode()==expected
        assert int(clock.read_text())==(35 if case=='waiting' else 0)
print('Actual P2 ACK wait: bounded progress with unchanged wall/ACK/boot/fatal/terminal/window gates PASS')
