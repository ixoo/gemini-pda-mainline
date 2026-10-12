#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""The C2 session pieces: fixed-phrase fields, the bounded private log export's
completeness rules, the phrase cross-check and the success conjunction.
Offline; no device action."""
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parents[1]
C2 = runpy.run_path(str(HERE / 'c2-session.py'))
BOOT = '0123abcd-0123-0123-0123-0123456789ab'
OTHER = 'ffffffff-0123-0123-0123-0123456789ab'
LIMIT = C2['LOG_LIMIT']

assert C2['is_c2_script'](b'TARGET_SSID=x\nWPA_PSK_HEX=' + b'0' * 64 + b'\nexport WPA_PSK_HEX\n')
assert not C2['is_c2_script'](b'TARGET_SSID=x\nexport TARGET_SSID\n')

LOG = (b'nl80211: Received scan results (1 BSSes)\nwlan0: WPA: RX message 1 of 4-Way Handshake from x\nwlan0: WPA: Sending EAPOL-Key 2/4\nwlan0: RSN: RX message 3 of 4-Way Handshake from x\nwlan0: WPA: Installing PTK to the driver\nwlan0: WPA: Installing GTK to the driver\nwlan0: WPA: Sending EAPOL-Key 4/4\nwlan0: Associated with 00:00:00:00:00:00\n'
       b'wlan0: WPA: Key negotiation completed with 00:00:00:00:00:00 [PTK=CCMP GTK=CCMP]\n'
       b'wlan0: CTRL-EVENT-CONNECTED - Connection to 00:00:00:00:00:00 completed\n'
       b'wlan0: CTRL-EVENT-DISCONNECTED bssid=00:00:00:00:00:00 reason=3\n')
body = (b'__JOIN_BEGIN__\nsupplicant_nl80211__received_scan_results=1\nsupplicant_wpa__rx_message_1_of_4_way_handshake=1\nsupplicant_wpa__sending_eapol_key_2_4=1\nsupplicant_rx_message_3_of_4_way_handshake=1\nsupplicant_wpa__installing_ptk=1\nsupplicant_wpa__installing_gtk=1\nsupplicant_wpa__sending_eapol_key_4_4=1\nsupplicant_associated_with=1\n'
        b'supplicant_wpa__key_negotiation_completed=1\nsupplicant_ctrl_event_connected=1\n'
        b'supplicant_ctrl_event_disconnected=1\nsupplicant_exit=0\nsupplicant_log_bytes=' +
        str(len(LOG)).encode() + b'\nchannel40_ir_after_beacon=1\nchannel40_query_exit=0\nchannel40_lines=1\nchannel40_words=none\nchannel40_ir_during_join=1\nchannel40_ir_ticks=3\n__JOIN_END__\nconnect_exit=0\njoin_terminal=1\n')
fields = C2['body_fields'](body)
assert fields['framed'] and fields['supplicant_nl80211__received_scan_results'] == 1
assert fields['supplicant_wpa__key_negotiation_completed'] == 1 and fields['join_terminal'] == 1
assert fields['supplicant_log_bytes'] == len(LOG) and fields['channel40_ir_after_beacon'] == 1
assert C2['body_fields'](b'')['framed'] is False and C2['body_fields'](b'')['supplicant_exit'] is None
assert C2['body_fields'](b'supplicant_exit=99999999999\n')['supplicant_exit'] is None
assert C2['phrase_counts'](LOG) == {k: v for k, v in fields.items() if k.startswith('supplicant_') and
                                    k not in ('supplicant_exit', 'supplicant_log_bytes')}

script = C2['log_script'](BOOT)
assert script.startswith(b'#!/bin/sh\n') and b'wpa.log' in script and BOOT.encode() in script
assert str(LIMIT).encode() in script and b'oversize' in script and b'empty' in script
assert b'-K' not in script and b'rm ' not in script and b'kill' not in script and b'>' not in script.replace(b'>', b'', 0)[:0]
assert b' > ' not in script and b'>>' not in script, 'the export writes nothing on the device'
for bad in ('', 'x', OTHER + 'z', BOOT.upper()):
    try:
        C2['log_script'](bad)
    except ValueError:
        pass
    else:
        raise AssertionError(bad)

ok = {'exit_status': 0, 'reason': None, 'stdin_complete': True, 'stdout_bytes': 0, 'stderr_bytes': 0}


def raw_for(log, boot_after=BOOT, size=None, after=None, processes=0, boot=BOOT):
    size = str(len(log)) if size is None else str(size)
    after = size if after is None else str(after)
    return (b'__SUPPLICANT_LOG_BEGIN__\nboot_id=' + boot.encode() + b'\nbytes=' + size.encode() +
            b'\nsupplicant_processes=' + str(processes).encode() + b'\n' + log +
            b'\n__SUPPLICANT_LOG_END__\nbytes_after=' + after.encode() + b'\nboot_after=' +
            boot_after.encode() + b'\n')


def result_for(raw, err=b'', **process):
    return C2['log_result'](raw, err, {**ok, 'stdout_bytes': len(raw), 'stderr_bytes': len(err), **process}, BOOT)


result = result_for(raw_for(LOG))
assert result['complete'] and result['bytes'] == len(LOG) and result['supplicant_processes'] == 0
assert result['log_sha256'] and result['phrases'] == C2['phrase_counts'](LOG) and result['size_report'] == str(len(LOG))
assert LOG not in str(result).encode()
# Exactly the bound is admitted; one byte more is not copied by the script and refused here.
bounded = result_for(raw_for(b'x' * LIMIT))
assert bounded['complete'] and bounded['bytes'] == LIMIT
over = result_for(raw_for(b'x' * (LIMIT + 1)))
assert not over['complete'] and over['bytes'] == LIMIT + 1 and over['log_sha256'] is None
for label, (raw, err, process) in {
        'other boot after': (raw_for(LOG, boot_after=OTHER), b'', {}),
        'other boot before': (raw_for(LOG, boot=OTHER), b'', {}),
        'size before differs': (raw_for(LOG, size=len(LOG) + 1), b'', {}),
        'size after differs': (raw_for(LOG, after=len(LOG) + 5), b'', {}),
        'size after absent': (raw_for(LOG, after='absent'), b'', {}),
        'supplicant still running': (raw_for(LOG, processes=1), b'', {}),
        'stderr': (raw_for(LOG), b'err', {}),
        'short stdout count': (raw_for(LOG), b'', {'stdout_bytes': len(raw_for(LOG)) - 1}),
        'nonzero exit': (raw_for(LOG), b'', {'exit_status': 3}),
        'timeout': (raw_for(LOG), b'', {'reason': 'timeout'}),
        'stdin incomplete': (raw_for(LOG), b'', {'stdin_complete': False}),
        'stdin unknown': (raw_for(LOG), b'', {'stdin_complete': None}),
        'truncated': (raw_for(LOG)[:-1], b'', {}),
        'empty log': (raw_for(b''), b'', {}),
        'empty report': (raw_for(b'', size='empty', after='0'), b'', {}),
        'oversize report': (raw_for(b'', size='oversize', after=str(LIMIT + 1)), b'', {}),
        'absent': (raw_for(b'', size='absent', after='absent'), b'', {}),
        'numeric head, absent tail': (raw_for(LOG, after='absent'), b'', {}),
        'huge size field': (raw_for(LOG, size='9' * 12), b'', {}),
        'malformed size': (raw_for(LOG, size='12abc'), b'', {}),
        'malformed processes': (raw_for(LOG).replace(b'supplicant_processes=0', b'supplicant_processes=x'), b'', {}),
        'tail before head': (b'\n__SUPPLICANT_LOG_END__\nbytes_after=1\nboot_after=' + BOOT.encode() + b'\n' +
                             raw_for(LOG)[:40], b'', {}),
        'nothing': (b'', b'', {})}.items():
    merged = {**ok, 'stdout_bytes': len(raw), 'stderr_bytes': len(err), **process}
    if label == 'stdin unknown':
        del merged['stdin_complete']
    verdict = C2['log_result'](raw, err, merged, BOOT)
    assert verdict['complete'] is False, label
    assert verdict['log_sha256'] is None or label in ('other boot after', 'other boot before', 'size before differs',
                                                       'size after differs', 'size after absent', 'supplicant still running',
                                                       'stderr', 'short stdout count', 'nonzero exit', 'timeout',
                                                       'stdin incomplete', 'stdin unknown',
                                                       'numeric head, absent tail'), label
absent = result_for(raw_for(b'', size='absent', after='absent'))
assert absent['bytes'] == 0 and absent['boot_match'] and absent['size_report'] == 'absent'

join = {'driver_handshake_path_pass': True}
good = result_for(raw_for(LOG))
userspace = {'transport_complete': True, 'standard_scan_succeeded': True}
assert C2['session_pass'](join, fields, good, userspace, True)
assert C2['session_pass'](join, {**fields, 'channel40_ir_after_beacon': 0}, good, userspace, True), 'after-exit no_IR is recorded, not gated'
assert not C2['session_pass']({'driver_handshake_path_pass': False}, fields, good, userspace, True)
assert not C2['session_pass'](join, fields, good, userspace, False)
assert not C2['session_pass'](join, fields, {**good, 'complete': False}, userspace, True)
assert not C2['session_pass'](join, fields, {**good, 'bytes': len(LOG) + 1}, userspace, True)
assert not C2['session_pass'](join, fields, {**good, 'phrases': {**good['phrases'], 'supplicant_ctrl_event_connected': 2}},
                              userspace, True), 'exported log must reproduce the reported counts'
assert not C2['session_pass'](join, fields, {**good, 'phrases': None}, userspace, True)
for key, value in (('transport_complete', False), ('transport_complete', None), ('standard_scan_succeeded', False)):
    assert not C2['session_pass'](join, fields, good, {**userspace, key: value}, True), key
assert not C2['session_pass'](join, fields, good, {}, True)
for key, value in (('supplicant_nl80211__received_scan_results', 2), ('supplicant_nl80211__received_scan_results', 0),
                   ('supplicant_wpa__key_negotiation_completed', 0), ('supplicant_ctrl_event_connected', 0),
                   ('join_terminal', 0), ('join_terminal', None), ('framed', False),
                   ('supplicant_nl80211__received_scan_results', None), ('supplicant_exit', 1), ('supplicant_exit', None),
                   ('supplicant_exit', 143), ('connect_exit', 1), ('connect_exit', None),
                   ('channel40_ir_during_join', 0), ('channel40_ir_during_join', None),
                   ('supplicant_log_bytes', len(LOG) - 1), ('supplicant_log_bytes', None)):
    assert not C2['session_pass'](join, {**fields, key: value}, good, userspace, True), (key, value)
print('c2-session: PASS (fields, bounded private export completeness, phrase cross-check, session conjunction)')

# Phase C3 conjunction: the C2 pass plus the driver's data-path pass, the device's bounded
# network outcomes, the owned wlan0 listener and the laptop's boot-bound Wi-Fi SSH receipt.
c3_fields = {**fields, 'data_phase_seen': 1, 'tool_udhcpc': 1, 'tool_ping': 1, 'dhcp_exit': 0, 'dhcp_bound': 1,
             'dhcp_prefix': 24, 'lease_written': 1, 'dropbear_digest_ok': 1, 'wifi_sshd_started': 1, 'wifi_sshd_ready': 1,
             'wifi_sshd_exit': 0, 'ping_transmitted': 3, 'ping_received': 3}
c3_join = {**join, 'driver_data_path_pass': True}
wifi = {'ready_seen': True, 'ssh_exit': 0, 'boot_match': True, 'stdout_bytes': 37}
assert C2['c3_session_pass'](c3_join, c3_fields, good, userspace, True, wifi)
assert not C2['c3_session_pass'](join, c3_fields, good, userspace, True, wifi), 'the driver data-path pass is required'
assert not C2['c3_session_pass'](c3_join, c3_fields, good, userspace, False, wifi)
assert not C2['c3_session_pass'](c3_join, c3_fields, good, userspace, True, None)
for key, value in (('ready_seen', False), ('ssh_exit', 255), ('ssh_exit', None), ('boot_match', False)):
    assert not C2['c3_session_pass'](c3_join, c3_fields, good, userspace, True, {**wifi, key: value}), key
for key, value in (('data_phase_seen', 0), ('tool_udhcpc', 0), ('tool_ping', 0), ('dhcp_bound', 0), ('lease_written', 0),
                   ('dhcp_prefix', 0), ('dhcp_prefix', 7), ('dhcp_prefix', 31), ('dhcp_prefix', None),
                   ('dropbear_digest_ok', 0), ('wifi_sshd_started', 0), ('wifi_sshd_ready', 0), ('wifi_sshd_exit', None),
                   ('ping_received', 0), ('ping_received', None)):
    assert not C2['c3_session_pass'](c3_join, {**c3_fields, key: value}, good, userspace, True, wifi), (key, value)
for name in ('dropbear_digest_ok', 'wifi_sshd_started', 'wifi_sshd_ready', 'wifi_sshd_exit', 'hook_status'):
    assert name in C2['FIELDS'] or name == 'hook_status', name

# Runtime 33 two-lifetime C3 conjunction, exercised against the ACTUAL join-twice.sh stdout
# grammar (not invented scalar fields): two completed cycles, one re-arm, two terminals, both
# cycles' DHCP/listener/ping and a present host-ack, the surviving supplicant's doubled
# handshake, the kernel two-lifetime pass and the host aggregate.
PHRASES = C2['PHRASES']
counts2 = {'supplicant_' + name: 2 for name in PHRASES}
LOG2_BYTES = 2 * len(LOG)


def join_twice_stdout(cycle_line, counts, extra='', supplicant_exit=0, connect_exit=0,
                      cycles_completed=2, rearms=1, terminals=2, overall_rc=0, framed=True):
    lines = ['__JOIN_BEGIN__' if framed else '',
             'boot_before=%s' % BOOT, 'interface_created=1', 'control=explicit', 'cycles=2']
    for n in (1, 2):
        lines.append('cycle=%d select_network=OK' % n)
        lines.append(cycle_line(n))
        lines.append('cycle=%d host_ack=present' % n)
        if n == 1:
            lines.append('rearm=present')
    for key, value in counts.items():
        lines.append('%s=%d' % (key, value))
    lines.append('supplicant_exit=%s' % supplicant_exit)
    lines.append('supplicant_log_bytes=%d' % LOG2_BYTES)
    lines.append(extra) if extra else None
    lines.append('__JOIN_END__' if framed else '')
    lines += ['connect_exit=%s' % connect_exit, 'cycles_completed=%d' % cycles_completed,
              'rearms_observed=%d' % rearms, 'terminals_observed=%d' % terminals,
              'overall_rc=%d' % overall_rc]
    return ('\n'.join(l for l in lines if l != '') + '\n').encode()


def good_cycle(n):
    return ('cycle=%d dhcp_exit=0 dhcp_bound=1 dhcp_prefix=24 lease_written=1 dropbear_digest_ok=1 '
            'wifi_sshd_started=1 wifi_sshd_ready=1 ping_transmitted=3 ping_received=3' % n)


good2_log = {'complete': True, 'bytes': LOG2_BYTES, 'phrases': counts2}
lifetimes_pass = {'two_lifetime_pass': True}
agg = {'all_pass': True, 'cycles_expected': 2,
       'cycles': [{'cycle': 1, 'boot_match': True, 'ack_written': True, 'closed': False},
                  {'cycle': 2, 'boot_match': True, 'ack_written': True, 'closed': False}]}
us = {'transport_complete': True, 'standard_scan_succeeded': True}
real = C2['two_lifetime_fields'](join_twice_stdout(good_cycle, counts2))
assert real['cycles_completed'] == 2 and real['rearms_observed'] == 1 and real['terminals_observed'] == 2
assert set(real['cycles']) == {1, 2} and real['cycles'][2]['host_ack'] is True
assert real['cycles'][1]['dhcp_exit'] == '0' and real['cycles'][1]['ping_transmitted'] == 3
assert C2['two_lifetime_device_pass'](real, good2_log, us)
assert C2['c3_two_lifetime_pass'](lifetimes_pass, real, good2_log, us, True, agg)
# The kernel two-lifetime pass, the userspace transport/scan, the seal and the host aggregate each required.
assert not C2['c3_two_lifetime_pass']({'two_lifetime_pass': False}, real, good2_log, us, True, agg)
assert not C2['c3_two_lifetime_pass'](lifetimes_pass, real, good2_log, us, False, agg)
assert not C2['c3_two_lifetime_pass'](lifetimes_pass, real, good2_log, us, True, None)
assert not C2['c3_two_lifetime_pass'](lifetimes_pass, real, good2_log, us, True, {**agg, 'all_pass': False})
for bad in ({'boot_match': False}, {'ack_written': False}, {'closed': True}):
    broken = {**agg, 'cycles': [agg['cycles'][0], {**agg['cycles'][1], **bad}]}
    assert not C2['c3_two_lifetime_pass'](lifetimes_pass, real, good2_log, us, True, broken), bad
# The inherited userspace transport/scan conjunction is required (a framed stdout is not enough).
for key in ('transport_complete', 'standard_scan_succeeded'):
    assert not C2['two_lifetime_device_pass'](real, good2_log, {**us, key: False})
assert not C2['two_lifetime_device_pass'](real, good2_log, {})
# The summary tokens must be exactly right.
for kw in (dict(cycles_completed=1), dict(rearms=2), dict(terminals=1), dict(overall_rc=1),
           dict(supplicant_exit=1), dict(connect_exit=1), dict(framed=False)):
    bad = C2['two_lifetime_fields'](join_twice_stdout(good_cycle, counts2, **kw))
    assert not C2['two_lifetime_device_pass'](bad, good2_log, us), kw
# A cycle with a failed udhcpc / no lease / no listener / no ping reply fails.
def bad_dhcp(n):
    return ('cycle=%d dhcp_exit=1 dhcp_bound=0 dhcp_prefix=0 lease_written=0 dropbear_digest_ok=0 '
            'wifi_sshd_started=0 wifi_sshd_ready=0 ping_transmitted=3 ping_received=0' % n)
assert not C2['two_lifetime_device_pass'](C2['two_lifetime_fields'](join_twice_stdout(bad_dhcp, counts2)), good2_log, us)
# Only three ping attempts are the bounded protocol; a short attempt count fails.
def few_ping(n):
    return ('cycle=%d dhcp_exit=0 dhcp_bound=1 dhcp_prefix=24 lease_written=1 dropbear_digest_ok=1 '
            'wifi_sshd_started=1 wifi_sshd_ready=1 ping_transmitted=1 ping_received=1' % n)
assert not C2['two_lifetime_device_pass'](C2['two_lifetime_fields'](join_twice_stdout(few_ping, counts2)), good2_log, us)
# A missing cycle-2 host-ack fails.
no_ack = join_twice_stdout(good_cycle, counts2).replace(b'cycle=2 host_ack=present\n', b'')
assert not C2['two_lifetime_device_pass'](C2['two_lifetime_fields'](no_ack), good2_log, us)
# Single handshake counts fail the doubled requirement.
assert not C2['two_lifetime_device_pass'](C2['two_lifetime_fields'](join_twice_stdout(good_cycle, {k: 1 for k in counts2})),
                                          {'complete': True, 'bytes': LOG2_BYTES, 'phrases': {k: 1 for k in counts2}}, us)
# The exported log must reproduce the counts and the reported byte size.
assert not C2['two_lifetime_device_pass'](real, {**good2_log, 'phrases': {k: 1 for k in counts2}}, us)
assert not C2['two_lifetime_device_pass'](real, {**good2_log, 'bytes': LOG2_BYTES - 1}, us)
print('c2-session: PASS (two-lifetime C3 over the real join-twice grammar: two cycles, one rearm, two terminals, doubled handshake, host aggregate)')

# The two-cycle evidence export: a bounded read-only device script and its validating result.
BOOTX = '0123abcd-0123-0123-0123-0123456789ab'
script_x = C2['cycles_export_script'](BOOTX)
# Contract: an export script is BYTES (the caller writes it with write_bytes / as
# stdin); a str return silently produced an empty command.sh on the device and
# lost the per-cycle RAM evidence ("a bytes-like object is required, not str").
assert isinstance(script_x, bytes) and script_x.startswith(b'#!/bin/sh\n')
assert BOOTX.encode() in script_x and b'/proc/sys/kernel/random/boot_id' in script_x
assert b'host-ack' in script_x and b'/c$c/' in script_x
# Read-only: no redirection or deletion of device files (dd reads with if=, no of=).
assert b' of=' not in script_x and b'> "$f"' not in script_x and b'rm ' not in script_x
try:
    C2['cycles_export_script']('not-a-boot')
except ValueError:
    pass
else:
    raise AssertionError('a malformed boot was accepted')


def cycles_export(boot=BOOTX, c2_ack=True, c2_lease=True):
    out = ['__CYCLES_BEGIN__', 'boot=%s' % boot]
    for n in (1, 2):
        files = ['hook-status', 'prefix', 'lease', 'router', 'udhcpc.log', 'dropbear.log', 'ping.log', 'ready', 'host-ack']
        if n == 2 and not c2_ack:
            files.remove('host-ack')
        if n == 2 and not c2_lease:
            files.remove('lease')
        for f in files:
            body = b'data-' + f.encode()
            out.append('__FILE__ path=/tmp/mt6797-wifi-phase-b-1/c%d/%s bytes=%d' % (n, f, len(body)))
            out.append(body.decode())
            out.append('__END__')
    out += ['__CYCLES_END__', 'boot_after=%s' % boot]
    return ('\n'.join(out) + '\n').encode()


good_export = cycles_export()


def proc_for(raw, exit_status=0, reason=None, stdin_complete=True, stdout_bytes=None, stderr_bytes=0):
    return {'exit_status': exit_status, 'reason': reason, 'stdin_complete': stdin_complete,
            'stdout_bytes': len(raw) if stdout_bytes is None else stdout_bytes, 'stderr_bytes': stderr_bytes}


res = C2['cycles_export_result'](good_export, b'', proc_for(good_export), BOOTX)
assert res['complete'] and res['boot_match'] and res['transport_ok'] and not res['truncated']
assert set(res['cycles']) == {1, 2} and res['cycles'][1]['lease'] >= 0 and res['cycles'][2]['host-ack'] >= 0
# Identity and presence gates.
assert not C2['cycles_export_result'](good_export, b'', proc_for(good_export), 'ffffffff-0123-0123-0123-0123456789ab')['complete']
assert not C2['cycles_export_result'](cycles_export(c2_ack=False), b'', proc_for(cycles_export(c2_ack=False)), BOOTX)['complete']
assert not C2['cycles_export_result'](cycles_export(c2_lease=False), b'', proc_for(cycles_export(c2_lease=False)), BOOTX)['complete']
assert not C2['cycles_export_result'](b'garbage', b'', proc_for(b'garbage'), BOOTX)['complete']
# Transport gate: stderr, a non-zero process, an incomplete stdin or a stdout-size mismatch all fail (raw retained upstream).
assert not C2['cycles_export_result'](good_export, b'oops', proc_for(good_export), BOOTX)['complete']
assert not C2['cycles_export_result'](good_export, b'', proc_for(good_export, exit_status=1), BOOTX)['complete']
assert not C2['cycles_export_result'](good_export, b'', proc_for(good_export, stdin_complete=False), BOOTX)['complete']
assert not C2['cycles_export_result'](good_export, b'', proc_for(good_export, stdout_bytes=len(good_export) - 1), BOOTX)['complete']
assert not C2['cycles_export_result'](good_export, b'', proc_for(good_export, stderr_bytes=1), BOOTX)['complete']
# Truncation gate: a file reported above the dd cap (or an unreadable -1) is refused.
cap = C2['CYCLE_EXPORT_LIMIT']
over = good_export.replace(b'bytes=%d' % len(b'data-lease'), b'bytes=%d' % (cap + 1), 1)
r_over = C2['cycles_export_result'](over, b'', proc_for(over), BOOTX)
assert r_over['truncated'] and not r_over['complete']
minus = good_export.replace(b'bytes=%d' % len(b'data-lease'), b'bytes=-1', 1)
assert C2['cycles_export_result'](minus, b'', proc_for(minus), BOOTX)['truncated']
print('c2-session: PASS (two-cycle evidence export: read-only script, transport/process gate, truncation refusal, lease+host-ack required)')


# The boot-bound quiescence record: present + boot-bound + empty faults => quiesced;
# a named fault, a boot mismatch or a missing record => NOT quiesced (host refuses
# seal/recovery). The faults list is retained for diagnosis.
qscript = C2['quiescence_script'](BOOTX)
assert isinstance(qscript, bytes) and qscript.startswith(b'#!/bin/sh\n')
assert b'/tmp/mt6797-wifi-phase-b-1/quiescence' in qscript and BOOTX.encode() in qscript
def _q(faults, boot=BOOTX, after=BOOTX):
    return (b'__QUIESCENCE_BEGIN__\nboot=' + boot.encode() + b'\nfaults=' + faults +
            b'\n__QUIESCENCE_END__\nboot_after=' + after.encode() + b'\n')
def _ok(raw):
    return (b'', {'exit_status': 0, 'reason': None, 'stdin_complete': True,
                  'stdout_bytes': len(raw), 'stderr_bytes': 0})
def _res(raw, err=None, process=None, boot=BOOTX):
    if err is None and process is None:
        err, process = _ok(raw)
    return C2['quiescence_result'](raw, err, process, boot)
clean = _res(_q(b''))
assert clean['quiesced'] and clean['boot_match'] and clean['transport_ok'] and clean['faults'] == ''
faulted = _res(_q(b'4242:wpa-supplicant,51:wifi-sshd'))
assert not faulted['quiesced'] and faulted['faults'] == '4242:wpa-supplicant,51:wifi-sshd'
assert not _res(_q(b'', after='0000ffff-0000-0000-0000-000000000000'))['quiesced']
assert not _res(b'__QUIESCENCE_BEGIN__\n__QUIESCENCE_END__\nboot_after=' + BOOTX.encode() + b'\n')['quiesced']
# A clean record but a failed read-only transport (stderr, bad byte count) is NOT
# authoritative quiescence.
raw = _q(b'')
assert not C2['quiescence_result'](raw, b'oops', {'exit_status': 0, 'reason': None, 'stdin_complete': True, 'stdout_bytes': len(raw), 'stderr_bytes': 3}, BOOTX)['quiesced']
assert not C2['quiescence_result'](raw, b'', {'exit_status': 0, 'reason': None, 'stdin_complete': True, 'stdout_bytes': len(raw) - 1, 'stderr_bytes': 0}, BOOTX)['quiesced']
print('c2-session: PASS (boot-bound quiescence: clean quiesced; fault/boot-mismatch/missing/bad-transport not quiesced)')
