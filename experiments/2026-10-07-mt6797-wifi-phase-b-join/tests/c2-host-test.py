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
import signal
import subprocess
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
        if label == 'quiescence':
            qraw = (b'__QUIESCENCE_BEGIN__\nboot=' + BOOT.encode() +
                    b'\nfaults=\n__QUIESCENCE_END__\nboot_after=' + BOOT.encode() + b'\n')
            return qraw, b'', {'exit_status': 0, 'reason': None, 'stdin_complete': True, 'stdout_bytes': len(qraw), 'stderr_bytes': 0}
        if label == 'cycles-export':
            # A well-framed two-cycle export (both cycles' lease and host-ack
            # present): transport/boot/framing intact and not truncated, so the
            # recovery gate must not refuse it.
            out = ['__CYCLES_BEGIN__', 'boot=%s' % BOOT]
            for n in (1, 2):
                for f in ('lease', 'host-ack'):
                    body = b'data-' + f.encode()
                    out.append('__FILE__ path=/tmp/mt6797-wifi-phase-b-1/c%d/%s bytes=%d' % (n, f, len(body)))
                    out.append(body.decode())
                    out.append('__END__')
            out += ['__CYCLES_END__', 'boot_after=%s' % BOOT]
            craw = ('\n'.join(out) + '\n').encode()
            return craw, b'', {'exit_status': 0, 'reason': None, 'stdin_complete': True, 'stdout_bytes': len(craw), 'stderr_bytes': 0}
        return b'', b'', {'exit_status': 0, 'reason': None, 'stdout_bytes': 0, 'stderr_bytes': 0}
    globals_ = {'invoke': invoke, 'BUDGETS': {'passive-scan': (30, 262144)}}
    execute = type('E', (), {'__globals__': globals_})()
    return {'execute': execute, 'claim': {'phase_budgets': {'passive-scan': {'seconds': 30}}}}


with tempfile.TemporaryDirectory(prefix='mt6797-c2-host-') as directory:
    work = Path(directory)
    private = work / 'private'
    (private / 'artifacts/credentials').mkdir(parents=True)
    root = work / 'runtime/wifi-phase-b/session-33'
    root.mkdir(parents=True)
    (work / 'runtime/wifi-phase-b/capture-33').mkdir()
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
        # The active path runs the inherited scan-tuning prepare over the real bound
        # script (prefix plus the revised join-once.sh, above 16384 bytes): its
        # source guard is re-pointed to the 32768-byte cap; at the historic value
        # the same chain refuses, so the guard itself is still exercised.
        assert host.SCAN.SOURCE_LIMIT == 32768 and 16384 < bound.stat().st_size <= 32768
        chained = host.prepare_with_c2(None)
        assert chained['claim']['phase_budgets']['passive-scan']['seconds'] == (330 if psk else 30)
        host.SCAN.SOURCE_LIMIT = 16384
        try:
            host.prepare_with_c2(None)
        except Exception as error:  # the inherited require's refusal
            assert 'scan script source changed' in str(error), error
        else:
            raise AssertionError('the inherited source guard did not refuse at 16384')
        host.SCAN.SOURCE_LIMIT = 32768
        calls.clear()
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
        assert calls == ['passive-scan', 'supplicant-log', 'quiescence', 'cycles-export', 'log-export', 'log-export'], calls
        assert written == [root / 'supplicant-log-result.json', root / 'quiescence-result.json',
                           root / 'cycles-evidence.raw', root / 'cycles-evidence-result.json'], written
        exported = json.loads(written[0].read_bytes())
        assert exported['complete'] and exported['bytes'] == len(LOG) and 'CTRL-EVENT' not in written[0].read_text()
        assert prepared['execute'].__globals__['BUDGETS']['supplicant-log'][0] == 20
        assert prepared['claim']['phase_budgets']['supplicant-log']['seconds'] == 20
        assert prepared['execute'].__globals__['BUDGETS']['cycles-export'][0] == 20
        assert prepared['claim']['phase_budgets']['cycles-export']['seconds'] == 20
        # The quiescence read is indexed by the real invoke as BUDGETS[label]; an
        # unregistered phase would KeyError and refuse every run, so its narrow
        # budget must be registered (this is the caller/stub-mismatch guard).
        assert prepared['execute'].__globals__['BUDGETS']['quiescence'] == (20, 4096)
        assert prepared['claim']['phase_budgets']['quiescence'] == {
            'connections': 1, 'seconds': 20, 'stdout_bytes': 4096, 'stderr_bytes': 16384}
        # The scan-tuning prepare is replaced by a stub to check the outer hooks.
        host.SCAN.prepare = lambda candidate: {**prepared, 'claim': {
            **prepared['claim'], 'passive_scan_script_sha256': 'deadbeef'}}
        outer = host.prepare_with_c2(None)
        assert outer['execute'].__globals__['BUDGETS']['passive-scan'] == (330, 262144)
        assert outer['claim']['phase_budgets']['passive-scan']['seconds'] == 330
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
        # Runtime 21: the C3 result binds the laptop's Wi-Fi SSH receipt to the
        # session result's established `mainline_boot` field (the real retained
        # shape, not boot_id); missing, foreign or malformed receipts fail.
        (root / 'passive-scan-userspace.json').write_text(json.dumps({'transport_complete': True, 'standard_scan_succeeded': True}))
        (root / 'supplicant-log-result.json').write_text(json.dumps({'complete': True, 'bytes': len(LOG), 'phrases': None}))
        (root / 'deferred-start-result.json').write_text(json.dumps({
            'classification': 'x', 'deferred_start_records': {}, 'mainline_boot': BOOT, 'phase': 'done',
            'preservation': {'log_complete': True}, 'recovery_confirmed': True, 'recovery_requested': True,
            'regression_pass': True, 'return': {}, 'returned_gemian_boot': 'ffffffff-0123-0123-0123-0123456789ab'}))
        join = {'driver_handshake_path_pass': True, 'driver_data_path_pass': True, 'session_verified': True}
        c2 = host.c2_result(join, True)
        lifetimes = {'two_lifetime_pass': True}
        receipt_path = work / 'wifi-ssh-receipt.json'
        # Runtime 33: the aggregate laptop-wifi-ssh receipt (per-cycle, boot-bound, all_pass).
        agg = {'boot_id': BOOT, 'cycles_expected': 2, 'all_pass': True,
               'cycles': [{'cycle': 1, 'boot_match': True, 'ack_written': True, 'closed': False},
                          {'cycle': 2, 'boot_match': True, 'ack_written': True, 'closed': False}]}
        host.WIFI_SSH_RECEIPT = receipt_path
        receipt_path.write_text(json.dumps(agg))
        c3 = host.c3_result(join, c2, lifetimes)
        assert c3['wifi_ssh_boot_bound'] is True and c3['wifi_ssh'] == agg, c3
        # The single-count supplicant body here does not satisfy the doubled handshake, so C3
        # fails; the full two-lifetime composition is exercised in c2-session-test.
        assert c3['c3_session_pass'] is False
        # A foreign boot does not bind; a non-all_pass or non-aggregate/malformed/missing
        # receipt fails and is recorded as absent where applicable.
        receipt_path.write_text(json.dumps({**agg, 'boot_id': 'ffffffff-0123-0123-0123-0123456789ab'}))
        assert host.c3_result(join, c2, lifetimes)['wifi_ssh_boot_bound'] is False
        receipt_path.write_text(json.dumps({**agg, 'all_pass': False}))
        assert host.c3_result(join, c2, lifetimes)['c3_session_pass'] is False
        receipt_path.write_text(json.dumps({'ready_seen': True, 'boot_id': BOOT}))  # old single-cycle shape, no cycles
        assert host.c3_result(join, c2, lifetimes)['wifi_ssh'] is None
        receipt_path.write_text('not json')
        assert host.c3_result(join, c2, lifetimes)['wifi_ssh'] is None and host.c3_result(join, c2, lifetimes)['c3_session_pass'] is False
        receipt_path.unlink()
        assert host.c3_result(join, c2, lifetimes)['wifi_ssh'] is None
        receipt_path.write_text(json.dumps(agg))
        (root / 'deferred-start-result.json').write_text(json.dumps({'regression_pass': True, 'boot_id': BOOT}))
        assert host.c3_result(join, c2, lifetimes)['wifi_ssh_boot_bound'] is False, 'boot_id alone is not the established mainline_boot'
        host.WIFI_SSH_RECEIPT = None
        assert 'rc = 0 if ready' not in (HERE / 'passive-host.py').read_text()
    # Runtime 33: the owned Wi-Fi helper. First the argv / enabled / no-retry wiring with a
    # non-joining fake, then the REAL process-group kill against a fixture whose leader exits
    # while a child ignores SIGTERM (the exact bug a fake could not exercise).
    class HelperCollector:
        def __init__(self):
            self.written = []

        def write_new(self, path, data):
            self.written.append(path)

    class FakeProc:
        pid = 424242

    spawned = []

    def fake_spawn(argv, **kw):
        spawned.append((argv, kw))
        return FakeProc()

    H = host.WifiHelper(root / 'keys', BOOT, root / 'r.json', spawn=fake_spawn)
    assert H.enabled()
    H.start()
    assert H.record['started'] and H.pgid == FakeProc.pid and len(spawned) == 1
    argv, kw = spawned[0]
    assert argv[1].endswith('laptop-wifi-ssh.py') and BOOT in argv
    assert '--cycles' in argv and '--receipt' in argv and kw.get('start_new_session') is True
    H.start()  # idempotent: no second spawn (no blind retry)
    assert len(spawned) == 1
    for bad in (host.WifiHelper(None, BOOT, root / 'r.json'),
                host.WifiHelper(root / 'keys', None, root / 'r.json'),
                host.WifiHelper(root / 'keys', BOOT, None)):
        assert not bad.enabled()
        bad.start()
        assert bad.record['started'] is False and bad.record['safe'] is True  # nothing owned, nothing to seal-block

    # A fixture whose child genuinely ignores SIGTERM/SIGINT and lingers in the group. The
    # child signals a ready file only AFTER installing the trap, and the leader exits only
    # after seeing it, so the later group SIGTERM is guaranteed to hit an already-trapped
    # child (no race) — making SIGKILL deterministically required.
    ready = work / 'child-ready'
    ignore_term = work / 'ignore-term.sh'
    ignore_term.write_text("#!/bin/sh\ntrap '' TERM INT\n: > '%s'\nwhile : ; do sleep 0.2 ; done\n" % ready)
    ignore_term.chmod(0o755)

    def real_spawn(argv, **kw):
        cmd = 'sh %s & while [ ! -f %s ] ; do sleep 0.02 ; done ; exit 0' % (ignore_term, ready)
        return subprocess.Popen(['sh', '-c', cmd], **kw)

    coll = HelperCollector()
    real = host.WifiHelper(root / 'keys', BOOT, root / 'r_real.json', spawn=real_spawn,
                           join_timeout=3, grace=1.0, poll_interval=0.1)
    try:
        real.start()
        assert real.record['started']
        real.join_and_record({'collector': coll})
        assert real.record['exit'] == 0, real.record            # the leader was reaped
        assert real.record['group_quiescent'] is True, real.record
        assert real.record['safe'] is True, real.record
        # SIGTERM alone did not quiesce the group (the child ignored it); SIGKILL was needed.
        assert int(signal.SIGTERM) in real.record['signals'] and int(signal.SIGKILL) in real.record['signals']
        assert coll.written == [host.ROOT / 'wifi-ssh-helper.json']
    finally:
        try:
            os.killpg(real.pgid, signal.SIGKILL)
        except OSError:
            pass

    # A still-running, TERM-ignoring LEADER: proc.wait times out, SIGTERM is ignored, SIGKILL
    # is required, and the killed leader must be reaped so the group probe can confirm quiescence
    # (a zombie leader would otherwise keep killpg(PGID,0) succeeding forever).
    leader = work / 'ignore-leader.sh'
    leader.write_text("#!/bin/sh\ntrap '' TERM INT\nwhile : ; do sleep 0.2 ; done\n")
    leader.chmod(0o755)

    def leader_spawn(argv, **kw):
        return subprocess.Popen(['sh', str(leader)], **kw)

    coll2 = HelperCollector()
    lead = host.WifiHelper(root / 'keys', BOOT, root / 'r_lead.json', spawn=leader_spawn,
                           join_timeout=1, grace=1.0, poll_interval=0.1)
    try:
        lead.start()
        lead.join_and_record({'collector': coll2})
        assert lead.record['timed_out'] is True, lead.record            # the leader outran join_timeout
        assert int(signal.SIGKILL) in lead.record['signals'], lead.record  # TERM ignored, KILL needed
        assert lead.record['exit'] is not None, lead.record             # the killed leader was reaped (no zombie)
        assert lead.record['group_quiescent'] is True and lead.record['safe'] is True, lead.record
    finally:
        try:
            os.killpg(lead.pgid, signal.SIGKILL)
        except OSError:
            pass

    # The export/seal transition is refused while an owned helper group is not quiescent.
    host.HELPER.record['owned'] = True
    host.HELPER.record['safe'] = False
    prep = host.c2_prepare(None)
    inv = prep['execute'].__globals__['invoke']
    try:
        inv({'collector': HelperCollector()}, 'log-export', b'')
    except RuntimeError as error:
        assert 'not confirmed quiescent' in str(error)
    else:
        raise AssertionError('export/seal was not refused for an unsafe helper group')
    host.HELPER.record['owned'] = False
    host.HELPER.record['safe'] = True

print('c2-host: PASS (C2 selection, supplicant-log phase once before the seal, budgets, private claim, phase-complete exit substitution, verdict)')
