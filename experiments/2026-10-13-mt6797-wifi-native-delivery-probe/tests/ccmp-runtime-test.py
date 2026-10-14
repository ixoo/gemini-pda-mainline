#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Host-only CCMP classifier/helper/ACTIVE-window negatives; no SSH or device."""
import copy
import json
from pathlib import Path
import runpy
import subprocess
import tempfile
import os
import sys
import importlib.util

HERE = Path(__file__).resolve().parent
P = HERE.parent
# Reuse the existing helper's shared boot/address/marker/exchange negatives.
fixture = (HERE / 'wifi-ssh-native-test.py').read_text().replace(
    'laptop-wifi-ssh-native.py', 'laptop-wifi-ssh-ccmp.py').replace(
    'native-delivery', 'ccmp-stable-monitor')
namespace = {'__file__': str(HERE / 'wifi-ssh-native-test.py')}
exec(compile(fixture, 'reused-wifi-helper-fixture', 'exec'), namespace)
N = namespace['N']
try:
    N.run(Path('/unused'), namespace['BOOT'], 2, 90)
except ValueError:
    pass
else:
    raise AssertionError('two-cycle helper admitted')
assert 'native-diag: state=[34]' in N.M.FATAL_RE
for log, expect in [
    ('one-shot WLAN native-diag: state=2 act=0', 0),
    ('one-shot WLAN native-diag: state=1 act=1', 15),
    ('one-shot WLAN native-diag: state=2 act=0\none-shot WLAN native-diag: state=3 act=2', 16),
    ('one-shot WLAN native-diag: state=2 act=0\none-shot WLAN native-diag: state=4 act=0', 16),
    ('one-shot WLAN native-diag: state=2 act=0\none-shot WLAN join stopped:', 16),
]:
    prefix = ('dmesg() { printf %s ' + __import__('shlex').quote(log) + '; }; '
              'uname() { echo 7.1.3-gemini-a53-wifi-ccmp-stable-monitor; }; '
              'cat() { echo synthetic; }; ')
    result = subprocess.run(['sh', '-c', prefix + N.M.COMMAND.format(ready='/dev/null')],
                            capture_output=True, timeout=3)
    assert result.returncode == expect, (log, result)

classifier = runpy.run_path(str(P / 'classify-ccmp.py'))
C = classifier['classify']
boot = namespace['BOOT']
leaf = (
    'boot_before=' + boot + '\nkernel=7.1.3-gemini-a53-wifi-ccmp-stable-monitor\n'
    '__IW_PASSIVE_BEGIN__\n__JOIN_BEGIN__\n'
    'cycle=1 dhcp_exit=0 dhcp_bound=1 dhcp_prefix=24 lease_written=1 '
    'dropbear_digest_ok=1 wifi_sshd_started=1 wifi_sshd_ready=1 '
    'ping_transmitted=3 ping_received=3\ncycle=1 host_ack=present\n'
    'supplicant_exit=0\n__JOIN_END__\nconnect_exit=0\ncycles_completed=1\n'
    'rearms_observed=0\nterminals_observed=1\noverall_rc=0\n'
    '__IW_PASSIVE_END__\nboot_after=' + boot + '\n').encode()
payloads = {'hook-status': b'bound', 'prefix': b'24', 'lease': b'192.0.2.55',
            'router': b'192.0.2.1', 'udhcpc.log': b'fixture lease\n', 'dropbear.log': b'',
            'ping.log': b'fixture 3/3\n', 'ready': ('boot=' + boot + '\ncycle=1\n').encode(),
            'host-ack': ('host_ack boot=' + boot + ' cycle=1 ssh_exit=0\n').encode()}
exported = ('__CYCLES_BEGIN__\nboot=' + boot + '\n').encode()
for name in classifier['C2']['CYCLE_FILES']:
    body = payloads[name]
    exported += ('__FILE__ path=/tmp/mt6797-wifi-phase-b-1/c1/' + name +
                 ' bytes=' + str(len(body)) + '\n').encode() + body + b'\n__END__\n'
exported += ('__CYCLES_END__\nboot_after=' + boot + '\n').encode()
def process(raw):
    return {'exit_status': 0, 'reason': None, 'stdin_complete': True,
            'stdout_bytes': len(raw), 'stderr_bytes': 0}
def protocol(l=leaf, e=exported, lp=None, ep=None):
    return classifier['protocol_result'](l, b'', process(l) if lp is None else lp,
                                         e, b'', process(e) if ep is None else ep, boot)
complete_protocol = protocol()
assert complete_protocol['protocol_pass'], complete_protocol
assert complete_protocol['cycle_export_complete']
assert complete_protocol['cycle_export']['complete'] is False  # inherited two-cycle rule
lines = [
    'one-shot WLAN native-diag: state=1 act=1 total=0 native=0 bytes=0',
    'one-shot WLAN native-diag: state=2 act=0 total=0 native=0 bytes=0',
    'one-shot WLAN ccmp-stable RX: first ethernet_bytes=100 flags=0x40200512',
    'one-shot WLAN native-diag: state=3 act=2 total=100 native=0 bytes=10000',
    'one-shot WLAN native-diag: state=4 act=0 total=100 native=0 bytes=10000',
    'one-shot WLAN ccmp-stable end: queued=64 no_reuse=1',
    'one-shot WLAN join cleanup: stage=3 credits=returned slots=retired deauth=1',
]
kmsg = ('\n'.join(lines) + '\n').encode()
receipt = {'boot_id': boot, 'cycles': [{'cycle': 1, 'ssh_exit': 0, 'boot_match': True,
    'ready_seen': True, 'ack_written': True, 'marker_after_active': True,
    'marker_mode': 'ccmp-stable-monitor', 'marker_boot': boot}]}
good = C(kmsg, receipt, boot, complete_protocol)
assert good['provisional_ccmp_compatibility_pass'] and good['ccmp_ethernet_queued'] == 64
assert not good['maintained_wifi_support'] and not good['hardware_replay_proven']
assert not good['key_deletion_proven'] and good['native_ciphertext_queued'] == 0
for mutation in [
    b'', kmsg.replace(b'queued=64', b'queued=0'), kmsg.replace(b'queued=64', b'queued=65'),
    kmsg.replace(b'flags=0x40200512', b'flags=0x0'), kmsg.replace(b'native=0', b'native=1'),
    kmsg.replace(b'total=100', b'total=513'), kmsg.replace(b'bytes=10000', b'bytes=1048577'),
    kmsg.replace(lines[6].encode(), b''), kmsg + b'one-shot WLAN join stopped: status=-71\n',
    kmsg.replace(lines[2].encode(), b''), kmsg + lines[2].encode() + b'\n',
    kmsg.replace(b'state=4 act=0', b'state=4 act=3'),
    kmsg.replace(b'flags=0x40200512', b'flags=garbled'),
]:
    assert not C(mutation, receipt, boot, complete_protocol)['provisional_ccmp_compatibility_pass'], mutation
for key, value in [('cycle', 2), ('marker_mode', 'native-delivery'), ('marker_after_active', False),
                   ('ack_written', False), ('ssh_exit', 1), ('marker_boot', 'old-boot')]:
    bad = copy.deepcopy(receipt); bad['cycles'][0][key] = value
    assert not C(kmsg, bad, boot, complete_protocol)['provisional_ccmp_compatibility_pass']
assert not C(kmsg, receipt, None)['provisional_ccmp_compatibility_pass']
assert C(b'', None, None)['ccmp_ethernet_queued'] is None  # absence is not zero
assert C(kmsg, receipt, boot)['authenticated']  # partial SSH remains named separately
assert not C(kmsg, receipt, boot)['provisional_ccmp_compatibility_pass']
# SSH/ack success cannot overrule missing/failed/short-window network proof.
for l, e, lp, ep in [
    (b'', exported, None, None),
    (leaf.replace(b'ping_received=3', b'ping_received=0'), exported, None, None),
    (leaf.replace(b'ping_transmitted=3', b'ping_transmitted=2'), exported, None, None),
    (leaf.replace(b'dhcp_bound=1', b'dhcp_bound=0'), exported, None, None),
    (leaf.replace(b'dhcp_exit=0', b'dhcp_exit=137'), exported, None, None),
    (leaf.replace(b'cycle=1 host_ack=present\n', b''), exported, None, None),
    (leaf.replace(b'overall_rc=0', b'overall_rc=1'), exported, None, None),
    (leaf.replace(b'__JOIN_END__', b'cycle=1 data_checks_failed=1\n__JOIN_END__'), exported, None, None),
    (leaf.replace(boot.encode(), b'deadbeef-0000-0000-0000-000000000000'), exported, None, None),
    (leaf.replace(b'cycle=1 ', b'cycle=2 '), exported, None, None),
    (leaf[:-40], exported, None, None),
    (leaf, b'', None, None),
    (leaf, exported[:-40], None, None),
    (leaf, exported.replace(b'/c1/', b'/c2/'), None, None),
    (leaf, exported.replace(boot.encode(), b'deadbeef-0000-0000-0000-000000000000'), None, None),
    (leaf, exported.replace(b'fixture 3/3\n', b'short'), None, None),
    (leaf, exported, {**process(leaf), 'exit_status': 1}, None),
    (leaf, exported, {**process(leaf), 'reason': 'timeout'}, None),
    (leaf, exported, {**process(leaf), 'stdin_complete': False}, None),
    (leaf, exported, None, {**process(exported), 'stdout_bytes': 1}),
    (leaf, exported, {}, None), (leaf, exported, None, {}),
]:
    result = C(kmsg, receipt, boot, protocol(l, e, lp, ep))
    assert result['eligible_ccmp_queue'] and result['authenticated']
    assert not result['provisional_ccmp_compatibility_pass'], result
wrong_protocol = {**complete_protocol, 'verified_boot': 'old-boot'}
assert not C(kmsg, receipt, boot, wrong_protocol)['provisional_ccmp_compatibility_pass']
with tempfile.TemporaryDirectory(prefix='ccmp-leaf-proof-', dir='/tmp/opencode') as tmp:
    root = Path(tmp)
    assert classifier['read_protocol'](root, boot)['leaf_cycle'] is None
    for directory in ('passive-scan', 'cycles-export'):
        (root / directory).mkdir()
    for name, content in [('passive-scan/stdout.txt', leaf), ('passive-scan/stderr.txt', b''),
                          ('cycles-evidence.raw', exported), ('cycles-export/stderr.txt', b'')]:
        (root / name).write_bytes(content)
    (root / 'passive-scan/process.json').write_text(json.dumps(process(leaf)))
    (root / 'cycles-export/process.json').write_text(json.dumps(process(exported)))
    assert classifier['read_protocol'](root, boot)['protocol_pass']
    (root / 'cycles-evidence.raw').unlink()
    assert not classifier['read_protocol'](root, boot)['protocol_pass']

# The ACTUAL host main must not turn inherited rc1 + early SSH into full pass.
# Only the scan executor is mocked; there are no device or SSH operations.
with tempfile.TemporaryDirectory(prefix='ccmp-host-verdict-', dir='/tmp/opencode') as tmp:
    root = Path(tmp); private = root / 'private'; runtime = root / 'runtime'; keys = root / 'keys'
    (private / 'artifacts/credentials').mkdir(parents=True); runtime.mkdir(); keys.mkdir()
    binder = root / 'join.sh'
    binder.write_bytes(b'TARGET_SSID=fixture\nWPA_PSK_HEX=' + b'0' * 64 +
                       b'\nTARGET_SSID_HEX=66697874757265\n' + (P / 'join-ccmp.sh').read_bytes())
    binder.chmod(0o600)
    os.environ.update(GEMINI_PRIVATE_REPO=str(private), GEMINI_RUNTIME_ROOT=str(runtime),
                      GEMINI_JOIN_SCRIPT=str(binder), GEMINI_WIFI_SSH_KEYS=str(keys),
                      GEMINI_WIFI_SSH_BOOT=boot)
    spec = importlib.util.spec_from_file_location('actual_ccmp_verdict_host', P / 'passive-host-ccmp.py')
    host = importlib.util.module_from_spec(spec); spec.loader.exec_module(host)
    host.PH.SCAN.main = lambda: 1
    host.PH.phase_b_scan_success = lambda *args: False
    host.ROOT.mkdir(parents=True); host.CAPTURE.mkdir(parents=True)
    (host.CAPTURE / 'phase-a-result.json').write_text(json.dumps({'ready_for_scan': True}))
    (host.ROOT / 'deferred-start-result.json').write_text(json.dumps({
        'preservation': {'log_complete': True}, 'regression_pass': True,
        'recovery_confirmed': True, 'mainline_boot': boot}))
    (host.ROOT / 'kmsg.log').write_bytes(kmsg)
    host.PH.WIFI_SSH_RECEIPT.write_text(json.dumps(receipt))
    for directory in ('passive-scan', 'cycles-export'):
        (host.ROOT / directory).mkdir()
    (host.ROOT / 'passive-scan/stderr.txt').write_bytes(b'')
    (host.ROOT / 'cycles-export/stderr.txt').write_bytes(b'')
    (host.ROOT / 'cycles-evidence.raw').write_bytes(exported)
    (host.ROOT / 'cycles-export/process.json').write_text(json.dumps(process(exported)))
    for current_leaf, expected in [(leaf.replace(b'ping_received=3', b'ping_received=0'), 1), (leaf, 0)]:
        (host.ROOT / 'passive-scan/stdout.txt').write_bytes(current_leaf)
        (host.ROOT / 'passive-scan/process.json').write_text(json.dumps(process(current_leaf)))
        sys.argv = [str(P / 'passive-host-ccmp.py'), '--candidate', str(root / 'synthetic-candidate'), '--execute']
        assert host.main() == expected
        combined = json.loads((host.ROOT / 'ccmp-session-result.json').read_bytes())
        assert combined['ccmp_compatibility']['authenticated']
        assert combined['ccmp_compatibility']['provisional_ccmp_compatibility_pass'] == (expected == 0)
        (host.ROOT / 'ccmp-session-result.json').unlink()

script = (P / 'join-ccmp.sh').read_text()
assert script.index('prepare_data_checks "$cyc"') < script.index('sel=$(wpa_cli select_network')
assert '$BB ping -I wlan0 -c 3 -W 2' in script
assert 'mode=ccmp-stable-monitor' in script and 'mac.ccmp_stable_epoch' not in script
assert 'window_ok "$1" || return 4' in script[script.index('wait_host_ack()'):]
functions = []
for name in ['now_s', 'fatal_record', 'window_ok']:
    start = script.index(name + '() {')
    end = script.index('\n}', start) + 2 if name != 'now_s' else script.index('\n', start)
    functions.append(script[start:end])
for log, expected in [
    ('one-shot WLAN native-diag: state=2 act=0', 0),
    ('', 1), ('one-shot WLAN native-diag: state=1 act=1', 1),
    ('one-shot WLAN native-diag: state=2 act=0\none-shot WLAN native-diag: state=3 act=2', 1),
    ('one-shot WLAN native-diag: state=2 act=0\none-shot WLAN join data phase end: reason=budget', 1),
    ('one-shot WLAN native-diag: state=2 act=0\none-shot WLAN join stopped: status=-71', 1),
]:
    body = ('BB=bb; EXPECTED_BOOT=synthetic; deadline=150; '
            'bb() { case "$1" in cat) echo synthetic;; cut) echo 100;; '
            'dmesg) printf %s ' + __import__('shlex').quote(log) + ';; *) "$@";; esac; };\n' +
            '\n'.join(functions) + '\nwindow_ok 1')
    result = subprocess.run(['sh', '-c', body], capture_output=True, timeout=3)
    assert result.returncode == expected, (log, result)
print(json.dumps({'host_only': True, 'classifier_negative_cases': 20,
                  'active_window_cases': 6, 'ssh_command_guard_cases': 5,
                  'leaf_export_negative_cases': 23,
                  'normal_dhcp_no_fallback': True, 'result': 'pass'}))
