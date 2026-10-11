#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""join-once.sh names the failing prerequisite on stderr and gates NO-IR after the scan.

Runs a test copy of the script under busybox ash with a stub busybox so that
early prerequisites fail in a controlled order, asserting an empty stdout and a
single __STAGE_FAIL__ line on stderr naming the stage. Static assertions keep
the success path's stdout prefix unchanged, keep 'no IR' out of the pre-scan
gate (channel 40 is NO-IR under the world domain until a beacon is found) and
require the post-scan NO-IR gate before any connect. No device action.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
SOURCE = (HERE / 'join-once.sh').read_text()
# Phase C2 secrecy: the PSK variable is consumed only by the configuration
# heredoc, unset right after, never printed, and no trace is enabled.
psk_lines = [line.strip() for line in SOURCE.splitlines() if '"$WPA_PSK_HEX"' in line]
assert psk_lines == ["printf %s \"$WPA_PSK_HEX\" | $BB grep -Eq '^[0-9a-f]{64}$'",
                     "printf '\\tproto=RSN\\n\\tkey_mgmt=WPA-PSK\\n\\tpairwise=CCMP\\n\\tgroup=CCMP\\n\\tieee80211w=0\\n\\tpsk=%s\\n}\\n' \"$WPA_PSK_HEX\""], psk_lines
assert 'unset WPA_PSK_HEX' in SOURCE and 'set -x' not in SOURCE
assert '-K' not in SOURCE.split('/bin/wpa_supplicant ')[1].split('&')[0]
# The pinned static supplicant implements no -f (no CONFIG_DEBUG_FILE): the
# debug stream is redirected, with stderr, into the private RAM log instead.
invocation = [l.strip() for l in SOURCE.splitlines() if l.strip().startswith('/bin/wpa_supplicant ')]
assert len(invocation) == 1 and invocation[0].endswith('-d > "$wpa_log" 2>&1 &'), invocation
invocation = invocation[0]
assert ' -f ' not in invocation, invocation
assert '-Dnl80211 -iwlan0 -c "$conf"' in invocation
assert 'CONFIG_DEBUG_FILE' not in (HERE / 'helper/wpa_supplicant.config').read_text()
assert SOURCE.index('umask 077') < SOURCE.index('/bin/wpa_supplicant ')
# The supplicant's exit, whatever it is, is collected under set +e and the
# configuration is removed only after that exit; the framed result follows.
c2 = SOURCE.split('stage=supplicant_config')[1].split('stage=boot_after')[0]
waited = c2.index('wait "$supplicant_pid"')
assert c2.rfind('set -e', 0, waited) < c2.rfind('set +e', 0, waited) < waited < c2.index('supplicant_exit=$?') < c2.index('set -e', waited) < c2.index('rm -f "$conf"')
assert 'sleep 1\n    $BB rm -f "$conf"' not in SOURCE and c2.index('rm -f "$conf"') < c2.index('supplicant_phrases')
assert 'ssid=%s' in c2 and 'ssid="' not in c2 and '"$TARGET_SSID_HEX"' in c2
# The wait ends only at the exact terminal record (final cleanup stage 3 with
# credits returned and slots retired, or the stopped record), never at an
# intermediate cleanup stage, and the lifecycle is recorded without aborting.
terminal_re = re.search(r"terminal_re='([^']+)'", c2).group(1)
assert terminal_re == 'one-shot WLAN join (cleanup: stage=3 credits=returned slots=retired deauth=[01]|stopped:)'
assert 'grep -Eq "$terminal_re"' in c2 and "cleanup:|stopped:" not in c2
killed = c2.index('kill "$supplicant_pid"')
assert c2.index('terminal=1') < c2.rfind('set +e', 0, killed) < killed
assert 'lifecycle=intermediate' in c2 and 'join_lifecycle=%s' in SOURCE
for line, matches in ((b'one-shot WLAN join cleanup: stage=3 credits=returned slots=retired deauth=1', True),
                      (b'one-shot WLAN join cleanup: stage=3 credits=returned slots=retired deauth=0', True),
                      (b'one-shot WLAN join stopped: first_error=-5 stage=1', True),
                      (b'one-shot WLAN join cleanup: stage=0 submitted sequence=9', False),
                      (b'one-shot WLAN join cleanup: stage=2 submitted sequence=11', False),
                      (b'one-shot WLAN join cleanup: stage=3 credits=pending slots=retired deauth=1', False),
                      (b'one-shot WLAN join key removal: pairwise submitted sequence=8', False)):
    assert bool(re.search(terminal_re.encode(), line)) is matches, line
# The channel-40 flag is 1 only for a successful query with exactly one line
# and no flag word; the query status, line count and words are recorded.
flag = re.search(r'channel40_flag\(\) \{\n.*?\n    \}\n', SOURCE, re.DOTALL).group(0)
assert 'channel40=1' in flag and 'channel40_query_exit=$?' in flag and 'echo' not in flag
assert "channel40_ir_after_beacon=%s\\nchannel40_query_exit=%s\\nchannel40_lines=%s\\nchannel40_words=%s\\n" in SOURCE
# Phrases: only lines the supplicant writes to its debug log; the one scan is
# the nl80211 driver's line, the handshake messages are the WPA debug lines.
phrases = re.search(r"for phrase in (.*?); do", SOURCE).group(1)
assert 'CTRL-EVENT-SCAN-RESULTS' not in phrases and "'nl80211: Received scan results'" in phrases
for required in ("'WPA: RX message 1 of 4-Way Handshake'", "'WPA: Sending EAPOL-Key 2/4'",
                 "'RX message 3 of 4-Way Handshake'", "'WPA: Sending EAPOL-Key 4/4'",
                 "'WPA: Installing PTK'", "'WPA: Installing GTK'",
                 "'WPA: Key negotiation completed'", "'CTRL-EVENT-CONNECTED'"):
    assert required in phrases, required
assert "tr 'A-Z: /-' 'a-z____'" in SOURCE and "grep -cF -- 'nl80211: Received scan results'" in SOURCE
assert "'WPA: RX message 3" not in phrases, 'message 3 carries the RSN: prefix on the WPA2 path'
# The channel-40 state is sampled every tick of the wait and the during-join
# observation is reported next to the after-exit state.
loop = c2.split('while [ "$tick" -lt 100 ]; do')[1].split('done')[0]
# Phase C3: the data checks run once when the driver records the open data phase,
# every step bounded by busybox timeout; the hook admits only wlan0, a dotted
# address and a prefix length 1..32 (no guessed /24) and writes the lease only
# after the address operation succeeded; the second Dropbear is the retained
# binary by digest on wlan0's leased address only, password and forwarding
# disabled, finite idle/connection/auth limits, pid owned, the readiness marker
# written last and the listener stopped and waited for at the terminal; only
# statuses, counts and the prefix length are printed, never an address.
assert 'data_checks' in loop and "grep -q 'one-shot WLAN join data phase: budget_ms='" in loop
# Runtime 23: a keepalive line every 20 ticks inside the wait (the USB listener's idle
# timeout is 60 s); fixed name and the tick only.
assert "if [ $((tick % 20)) -eq 0 ]; then" in loop and "$BB printf 'keepalive=%s\\n' \"$tick\"" in loop
checks = c2.split('data_checks() {')[1].split('\n    }\n')[0]
assert '$BB timeout 20 $BB udhcpc -i wlan0 -f -n -q -t 4 -T 3 -s' in checks and '$BB timeout 12 $BB ping -c 3 -W 2' in checks
hook = re.search(r"\$BB printf '(#!/bin/sh.*?)' \"\$data_dir\" > \"\$data_dir/dhcp.sh\"", checks).group(1)
assert '[ "$interface" = wlan0 ] || { status interface; exit 0; }' in hook
assert 'grep -Eq "^([0-9]{1,3}\\\\.){3}[0-9]{1,3}$" || { status address; exit 0; }' in hook
assert '[ "$mask" -ge 1 ] && [ "$mask" -le 32 ] || { status prefix; exit 0; }' in hook and 'mask=24' not in hook
assert '$BB ip addr add "$ip/$mask" dev wlan0 || { status addr-failed; exit 0; }' in hook
assert hook.index('ip addr add') < hook.index('> "$dir/prefix"') < hook.index('> "$dir/lease"') < hook.index('status bound')
assert '[ "$hook_status" = bound ] && [ -f "$data_dir/lease" ] && [ -f "$data_dir/prefix" ]' in checks
listener = [l.strip() for l in checks.splitlines() if '/bin/dropbear -F' in l]
assert len(listener) == 1, listener
assert listener[0].startswith('$BB timeout 90 /bin/dropbear -F -s -j -k -l wlan0 -p "$($BB cat "$data_dir/lease"):22" -D /root/.ssh \\')
assert '-r /etc/dropbear/host_key -P "$data_dir/sshd-pid" -I 30 -M 60 -T 2 2> "$data_dir/dropbear.log" &' in checks
assert 'dropbear_sha256=10663dd45019bc1391730c36d779e6a5e4433fd86311543a714f1a198629bc54' in SOURCE
assert '[ "$($BB sha256sum /bin/dropbear | $BB cut -c1-64)" = "$dropbear_sha256" ]' in checks
assert checks.index('dropbear_digest_ok=1') < checks.index('/bin/dropbear -F') < checks.index('wifi_sshd_pid=$!')
assert '/bin/dropbear' not in SOURCE.replace('$BB timeout 90 /bin/dropbear -F', '').replace('sha256sum /bin/dropbear', ''), 'one launch, one digest check'
assert checks.index('''[ "$($BB cat "$data_dir/sshd-pid")" = "$wifi_sshd_pid" ] && kill -0 "$wifi_sshd_pid"''') < checks.index('> "$data_dir/wifi-ssh"') < checks.index('wifi_sshd_ready=1')
assert '-p "$($BB cat "$data_dir/lease"):22"' in checks and '-p 22' not in checks and '0.0.0.0' not in checks
stop = re.search(r'^stop_wifi_sshd\(\) \{\n(.*?)\n\}\n', SOURCE, re.M | re.DOTALL).group(1)
# busybox timeout execs Dropbear in place: $! is its pid; one signal, one wait, the status, the pid cleared, no later signal.
assert stop.count('kill ') == 1 and stop.index('kill "$wifi_sshd_pid"') < stop.index('wait "$wifi_sshd_pid"') < stop.index('wifi_sshd_exit=$?') < stop.index('wifi_sshd_pid=')
assert 'sshd-pid' not in stop
on_exit = re.search(r'^on_exit\(\) \{\n(.*?)\n\}\n', SOURCE, re.M | re.DOTALL).group(1)
assert on_exit.splitlines()[1].strip() == 'stop_wifi_sshd', on_exit
assert SOURCE.index('stop_wifi_sshd() {') < SOURCE.index('on_exit() {') < SOURCE.index('trap on_exit EXIT')
assert SOURCE.rindex('    stop_wifi_sshd\n') > SOURCE.index('kill "$supplicant_pid"')
printed = ''.join(re.findall(r"data_phase_seen=%s.*?\n|dropbear_digest_ok=%s.*?\n", SOURCE))
assert printed.count('%s') == 14 and '$data_dir/lease' not in printed and 'router' not in printed and '$ip' not in printed, printed
for name in ('lease', 'router', 'prefix', 'dhcp.sh', 'wifi-ssh', 'sshd-pid', 'hook-status'):
    assert '"$data_dir/%s"' % name in c2.split('stop_wifi_sshd\n')[1].split('\n')[0], name
assert c2.index('rm -f "$data_dir/lease" "$data_dir/router" "$data_dir/prefix" "$data_dir/dhcp.sh"') < c2.index('supplicant_phrases')
assert 'channel40_flag' in loop and 'channel40_ir_during_join=1' in loop and 'channel40_ir_ticks=$((channel40_ir_ticks + 1))' in loop
assert "channel40_ir_during_join=%s\\nchannel40_ir_ticks=%s\\n" in SOURCE
# The key derivation maps exactly the separators ':', ' ', '/' and '-' to '_'.
import subprocess as _sp
_tr = _sp.run(['sh', '-c', "printf %s 'WPA: Sending EAPOL-Key 2/4' | tr 'A-Z: /-' 'a-z____'"], capture_output=True)
assert _tr.stdout == b'wpa__sending_eapol_key_2_4', _tr.stdout
assert 'if info=$(iw phy phy0 info 2>/dev/null); then' in flag and 'channel40_query_exit=$?' in flag

# Static review.
assert SOURCE.count('BB=/bin/busybox\n') == 1
pre = SOURCE[SOURCE.index('stage=channel40_pre_scan'):SOURCE.index('stage=wlan0_add')]
assert "grep -Eq 'disabled|radar detection'" in pre and 'no IR' not in pre
post = SOURCE[SOURCE.index('stage=channel40_ir_after_beacon'):SOURCE.index('stage=join_readiness')]
assert "grep -Eq 'disabled|no IR|radar detection'" in post and 'exit 1' in post
assert SOURCE.index('stage=channel40_ir_after_beacon') < SOURCE.index('/bin/join-connect wlan0')
assert SOURCE.index('__IW_PASSIVE_BEGIN__') < SOURCE.index('stage=channel40_ir_after_beacon')
# Only the exit trap prints the stage marker, and only to stderr.
markers = [m.start() for m in re.finditer('__STAGE_FAIL__', SOURCE)]
assert len(markers) == 1 and SOURCE[markers[0]:].split('\n')[0].rstrip().endswith('>&2')
before_begin = SOURCE[:SOURCE.index("__IW_PASSIVE_BEGIN__")]
prints = [l for l in before_begin.splitlines() if re.match(r'\s*(\$BB )?printf', l) and '>&2' not in l]
assert all('wc -c' in l or 'grep' in l or 'TARGET_BSSID' in l for l in prints), prints
# An absent target is reported as bss_match, distinct from a failed passive scan.
assert SOURCE.index('[ "$scan_exit" = 0 ]') < SOURCE.index('stage=bss_match') < SOURCE.index('$BB awk -v target')
# The connect's diagnostics stay inside the framed stdout body, so a refused
# join cannot be read as a failed scan by the inherited stderr check.
connect = [l for l in SOURCE.splitlines() if '/bin/join-connect wlan0' in l]
assert len(connect) == 1 and connect[0].rstrip().endswith('2>&1'), connect
assert 'iw dev wlan0 connect' not in SOURCE and 'key' not in connect[0], 'no iw connect, no key'
assert ' 5200 "$TARGET_BSSID"' in connect[0] and 'timeout 3' in connect[0]
# The helper is pinned with the other userspace tools before use.
sums = SOURCE[SOURCE.index("<<'SUMS'"):SOURCE.index('\nSUMS\n')]
assert sums.count('  bin/join-connect') == 1 and SOURCE.index('bin/join-connect\nSUMS') < SOURCE.index('/bin/join-connect wlan0')
stages = re.findall(r'^stage=([a-z0-9_]+)$', SOURCE, re.M)
assert all(re.fullmatch(r'[a-z0-9_]+', s) for s in stages) and len(set(stages)) == len(stages)
assert stages[:4] == ['start', 'target_input', 'kernel_release', 'boot_identity'] and 'connect' in stages

busybox = shutil.which('busybox')
if not busybox or subprocess.run([busybox, 'ash', '-c', 'true']).returncode:
    print('join-once: PASS (static only; busybox ash unavailable here)')
    sys.exit(0)

with tempfile.TemporaryDirectory(prefix='mt6797-join-once-') as directory:
    work = Path(directory)
    stub = work / 'busybox'
    stub.write_text('#!/bin/sh\n'
                    'cmd=$1; shift\n'
                    'case $cmd in\n'
                    '  uname) printf "%s\\n" "$FAKE_RELEASE" ;;\n'
                    '  cat) printf "%s\\n" "$FAKE_BOOT" ;;\n'
                    '  *) exec ' + busybox + ' "$cmd" "$@" ;;\n'
                    'esac\n')
    stub.chmod(0o700)
    script = work / 'join-once.sh'
    script.write_text(SOURCE.replace('BB=/bin/busybox\n', 'BB=' + str(stub) + '\n', 1))
    env = dict(os.environ, TARGET_SSID='x', TARGET_BSSID='02:00:00:00:00:01',
               FAKE_RELEASE='7.1.3-gemini-a53-wifi-phase-b-compile', FAKE_BOOT='boot-a')

    def run(**overrides):
        e = dict(env, **overrides)
        e.pop('EXPECTED_BOOT', None) if overrides.get('EXPECTED_BOOT') == '' else None
        return subprocess.run([busybox, 'ash', str(script)], env=e, capture_output=True, timeout=30)

    # The channel-40 flag function under busybox ash with a stub iw.
    iw_dir = work / 'iw'
    iw_dir.mkdir()
    flag_script = work / 'flag.sh'
    # Runs with set -e, as the join script does: a failed query must not abort.
    flag_script.write_text('set -e\nBB=' + str(busybox) + '\n' + flag +
                           'channel40_flag\nprintf "%s %s %s %s\\n" "$channel40" "$channel40_query_exit" "$channel40_lines" "$channel40_words"\n')
    def flag_for(output, status=0):
        (iw_dir / 'iw').write_text('#!/bin/sh\nprintf %s "' + output + '"\nexit ' + str(status) + '\n')
        (iw_dir / 'iw').chmod(0o700)
        env = dict(os.environ, PATH=str(iw_dir) + ':' + os.environ['PATH'])
        return subprocess.run([busybox, 'ash', str(flag_script)], env=env, capture_output=True, timeout=10).stdout
    one = '\t\t\t* 5200 MHz [40] (20.0 dBm)\n'
    assert flag_for(one) == b'1 0 1 none\n'
    assert flag_for(one + '\t\t\t* 5200 MHz [40] (20.0 dBm)\n') == b'0 0 2 none\n', 'duplicate line'
    assert flag_for('\t\t\t* 5180 MHz [36] (20.0 dBm)\n') == b'0 0 0 none\n', 'missing line'
    assert flag_for('') == b'0 0 0 none\n'
    assert flag_for(one, status=1) == b'0 1 0 none\n', 'failed query'
    assert flag_for('\t\t\t* 5200 MHz [40] (20.0 dBm) (no IR)\n') == b'0 0 1 no_IR\n'
    assert flag_for('\t\t\t* 5200 MHz [40] (disabled)\n') == b'0 0 1 disabled\n'
    assert flag_for('\t\t\t* 5200 MHz [40] (no IR, radar detection)\n') == b'0 0 1 no_IR,radar_detection\n'

    def expect(result, stage):
        assert result.returncode != 0 and result.stdout == b'', result
        lines = result.stderr.splitlines()
        assert lines[-1] == ('__STAGE_FAIL__ stage=%s rc=%d' % (stage, result.returncode)).encode(), result.stderr
        assert sum(b'__STAGE_FAIL__' in l for l in lines) == 1

    expect(run(EXPECTED_BOOT=''), 'target_input')
    expect(run(EXPECTED_BOOT='boot-a', FAKE_RELEASE='other'), 'kernel_release')
    expect(run(EXPECTED_BOOT='boot-b'), 'boot_identity')
    # With identity satisfied the next gate needs /sys/class/ieee80211/phy0, absent here.
    result = run(EXPECTED_BOOT='boot-a')
    expect(result, 'single_phy0')
print('join-once: PASS (stage marker on stderr only, empty stdout; NO-IR gated after the beacon)')
