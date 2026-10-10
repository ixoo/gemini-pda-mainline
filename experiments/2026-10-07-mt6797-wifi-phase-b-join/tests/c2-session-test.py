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
