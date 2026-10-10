#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""The host adapter's C2 hooks, offline: a PSK-bound script selects the C2
pieces, the supplicant-log phase runs once between the join script and the
log seal with its own budget, its result lands under the private root, the
join phase budget covers the bounded loop, and the claim carries no digest of
the PSK-bound script. No device action."""
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parents[1]
BOOT = '0123abcd-0123-0123-0123-0123456789ab'
LOG = (b'nl80211: Received scan results (1 BSSes)\nwlan0: WPA: RX message 1 of 4-Way Handshake from x\nwlan0: WPA: Sending EAPOL-Key 2/4\nwlan0: RSN: RX message 3 of 4-Way Handshake from x\nwlan0: WPA: Installing PTK to the driver\nwlan0: WPA: Installing GTK to the driver\nwlan0: WPA: Sending EAPOL-Key 4/4\nwlan0: WPA: Key negotiation completed with x\n'
       b'wlan0: CTRL-EVENT-CONNECTED - x\n')
BODY = (b'__JOIN_BEGIN__\nsupplicant_nl80211__received_scan_results=1\nsupplicant_wpa__rx_message_1_of_4_way_handshake=1\nsupplicant_wpa__sending_eapol_key_2_4=1\nsupplicant_rx_message_3_of_4_way_handshake=1\nsupplicant_wpa__installing_ptk=1\nsupplicant_wpa__installing_gtk=1\nsupplicant_wpa__sending_eapol_key_4_4=1\nsupplicant_associated_with=0\n'
        b'supplicant_wpa__key_negotiation_completed=1\nsupplicant_ctrl_event_connected=1\n'
        b'supplicant_ctrl_event_disconnected=0\nsupplicant_exit=0\nsupplicant_log_bytes=' + str(len(LOG)).encode() +
        b'\nchannel40_ir_after_beacon=1\nchannel40_query_exit=0\nchannel40_lines=1\nchannel40_words=none\nchannel40_ir_during_join=1\nchannel40_ir_ticks=3\n__JOIN_END__\nconnect_exit=0\njoin_terminal=1\n')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stub_prepared(calls):
    def invoke(active, label, script, *, network_status=None):
        calls.append(label)
        if label == 'supplicant-log':
            raw = (b'__SUPPLICANT_LOG_BEGIN__\nboot_id=' + BOOT.encode() + b'\nbytes=' + str(len(LOG)).encode() +
                   b'\nsupplicant_processes=0\n' + LOG +
                   b'\n__SUPPLICANT_LOG_END__\nbytes_after=' + str(len(LOG)).encode() + b'\nboot_after=' + BOOT.encode() + b'\n')
            return raw, b'', {'exit_status': 0, 'reason': None, 'stdin_complete': True, 'stdout_bytes': len(raw), 'stderr_bytes': 0}
        return b'', b'', {'exit_status': 0, 'reason': None, 'stdout_bytes': 0, 'stderr_bytes': 0}
    globals_ = {'invoke': invoke, 'BUDGETS': {'passive-scan': (30, 262144)}}
    execute = type('E', (), {'__globals__': globals_})()
    return {'execute': execute, 'claim': {'phase_budgets': {'passive-scan': {'seconds': 30}}}}


with tempfile.TemporaryDirectory(prefix='mt6797-c2-host-') as directory:
    work = Path(directory)
    private = work / 'private'
    (private / 'artifacts/credentials').mkdir(parents=True)
    root = work / 'runtime/wifi-phase-b/session-20'
    root.mkdir(parents=True)
    (work / 'runtime/wifi-phase-b/capture-20').mkdir()
    (root / 'observation-result.json').write_text(json.dumps({'boot_id': BOOT}))
    for psk in (False, True):
        bound = work / ('bound-%d.sh' % psk)
        prefix = b'TARGET_SSID=x\n' + (b'WPA_PSK_HEX=' + b'0' * 64 + b'\nexport WPA_PSK_HEX\n' if psk else b'')
        bound.write_bytes(prefix + (HERE / 'join-once.sh').read_bytes())
        bound.chmod(0o600)
        os.environ.update(GEMINI_PRIVATE_REPO=str(private), GEMINI_RUNTIME_ROOT=str(work / 'runtime'),
                          GEMINI_JOIN_SCRIPT=str(bound))
        host = load('phase_b_host_%d' % psk, HERE / 'passive-host.py')
        assert host.C2_SCRIPT is psk and host.SCAN.PREPARE is host.c2_prepare
        calls = []
        host.WIPHY_PREPARE = lambda candidate: stub_prepared(calls)
        written = []

        class Collector:
            def write_new(self, path, data):
                written.append(path)
                path.write_bytes(data)
        prepared = host.c2_prepare(None)
        active = {'collector': Collector()}
        invoke = prepared['execute'].__globals__['invoke']
        invoke(active, 'passive-scan', b'')
        invoke(active, 'log-export', b'')
        invoke(active, 'log-export', b'')
        if not psk:
            assert calls == ['passive-scan', 'log-export', 'log-export'] and not written
            assert 'supplicant-log' not in prepared['execute'].__globals__['BUDGETS']
            continue
        assert calls == ['passive-scan', 'supplicant-log', 'log-export', 'log-export'], calls
        assert written == [root / 'supplicant-log-result.json']
        exported = json.loads(written[0].read_bytes())
        assert exported['complete'] and exported['bytes'] == len(LOG) and 'CTRL-EVENT' not in written[0].read_text()
        assert prepared['execute'].__globals__['BUDGETS']['supplicant-log'][0] == 20
        assert prepared['claim']['phase_budgets']['supplicant-log']['seconds'] == 20
        # The scan-tuning prepare is replaced by a stub to check the outer hooks.
        host.SCAN.prepare = lambda candidate: {**prepared, 'claim': {
            **prepared['claim'], 'passive_scan_script_sha256': 'deadbeef'}}
        outer = host.prepare_with_c2(None)
        assert outer['execute'].__globals__['BUDGETS']['passive-scan'] == (45, 262144)
        assert outer['claim']['phase_budgets']['passive-scan']['seconds'] == 45
        assert outer['claim']['passive_scan_script_sha256'] == 'private-psk-bound'
        assert host.select_prepare(True) is host.prepare_with_c2
        assert host.select_prepare(False) is host.c2_prepare
        # The verdict pieces read the private framed stdout and the export result.
        (root / 'passive-scan').mkdir()
        (root / 'passive-scan/stdout.txt').write_bytes(BODY)
        phase = root / 'passive-scan-userspace.json'
        # Without the join phase's process record nothing passes.
        assert host.c2_result({'driver_handshake_path_pass': True}, True)['c2_session_pass'] is False
        phase.write_text(json.dumps({'transport_complete': True, 'standard_scan_succeeded': True}))
        result = host.c2_result({'driver_handshake_path_pass': True}, True)
        assert result['c2_session_pass'] is True and result['join_phase_complete'] is True
        assert result['supplicant_log']['bytes'] == len(LOG)
        assert host.c2_result({'driver_handshake_path_pass': False}, True)['c2_session_pass'] is False
        # The inherited exit condition: only the iw demonstration is replaced,
        # by the join phase's complete process; a timed-out or truncated phase
        # still fails, and so does any other failed record.
        (root / 'deferred-start-result.json').write_text(json.dumps({
            'regression_pass': True, 'recovery_confirmed': True,
            'preservation': {'log_complete': True, 'provider_probe': {'registered': True}},
            'deferred_start_records': {'record_counts': {host.SETUP_MARKER.decode(): 1}}}))
        (root / 'kmsg.log').write_bytes(host.PREPOWER_MARKER + b'\n')
        (root / 'passive-scan-result.json').write_text(json.dumps({'passive_scan_demonstrated': False}))
        assert host.phase_b_scan_success(root) is False
        assert host.phase_b_scan_success(root, True) is True
        phase.write_text(json.dumps({'transport_complete': False, 'standard_scan_succeeded': False, 'reason': 'timeout'}))
        assert host.phase_b_scan_success(root, True) is False
        assert host.c2_result({'driver_handshake_path_pass': True}, True)['c2_session_pass'] is False
        phase.write_text(json.dumps({'transport_complete': True, 'standard_scan_succeeded': False}))
        assert host.phase_b_scan_success(root, True) is False
        phase.write_text(json.dumps({'transport_complete': True, 'standard_scan_succeeded': True}))
        (root / 'passive-scan-userspace.json').write_text(json.dumps({'transport_complete': True, 'standard_scan_succeeded': True}))
        (root / 'kmsg.log').write_bytes(b'')
        assert host.phase_b_scan_success(root, True) is False, 'other records still decide'
        (root / 'kmsg.log').write_bytes(host.PREPOWER_MARKER + b'\n')
        (root / 'supplicant-log-result.json').unlink()
        assert host.c2_result({'driver_handshake_path_pass': True}, True)['c2_session_pass'] is False
        assert 'rc = 0 if ready' not in (HERE / 'passive-host.py').read_text()
print('c2-host: PASS (C2 selection, supplicant-log phase once before the seal, budgets, private claim, phase-complete exit substitution, verdict)')
