#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Finite monitor-assisted stable-PTK verdict; not maintained Wi-Fi support.

Reuse the original diagnostic's exact sequence, budgets and fail-closed grammar.
CCMP accepted/queued Ethernet is SEPARATE from native ciphertext (required zero),
core delivery and hardware replay proof. Positive also requires the fresh real-
lease/boot/mode-bound Wi-Fi SSH receipt from the reviewed ACTIVE-only helper and
verified preserved/regressed/recovered session. No crypto/epoch proof fabricated.
"""

import re
import runpy
from pathlib import Path

_DIAG = re.compile(rb'one-shot WLAN native-diag: state=(\d+) act=(\d+) total=(\d+) '
                   rb'native=(\d+) bytes=(\d+)$')
_RX = re.compile(rb'one-shot WLAN ccmp-stable RX: first ethernet_bytes=(\d+) '
                 rb'flags=0x([0-9a-f]+)$')
_END = re.compile(rb'one-shot WLAN ccmp-stable end: queued=(\d+) no_reuse=1$')
_CLEANUP = re.compile(rb'one-shot WLAN join cleanup: stage=3 credits=returned '
                      rb'slots=retired deauth=[01]$')
# Any line that carries a native-diag / first-RX prefix but fails its exact
# grammar is malformed and rejected, never silently ignored.
_PREFIX = re.compile(rb'one-shot WLAN (?:native-diag|ccmp-stable (?:RX:|end:))')
_FAULT = re.compile(rb'one-shot WLAN (?:join (?:stopped:|rearm refused:|rearm wrap:)|'
                    rb'native-diag no-radio latch)')
_BOOT = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
# The exact owned one-cycle (state, act) transition sequence.
_SEQUENCE = [(1, 1), (2, 0), (3, 2), (4, 0)]
RX_MAX, NATIVE_MAX, BYTES_MAX = 512, 64, 1024 * 1024  # 0181 sample ceilings
HIF_RX_MAX_PACKET = 2352  # MT6797_HIF_RX_MAX_PACKET
CCMP_FLAGS = 0x40200512  # pinned7.1.3 8023/decrypted/IV/MIC/driverPN/no-signal
C2 = runpy.run_path(str(Path(__file__).resolve().parent.parent /
                       '2026-10-07-mt6797-wifi-phase-b-join/c2-session.py'))
RELEASE = '7.1.3-gemini-a53-wifi-ccmp-stable-monitor'


def protocol_result(leaf, leaf_err, leaf_process, exported, export_err, export_process, boot):
    """Validate the EXISTING one-cycle leaf and nested framed export; no new effect.

    Reuse C3's actual token parser/export validator, not its two-cycle conjunction.
    That validator's complete flag expects cycles1+2 and is not our one-cycle gate.
    Its metadata is cycles->{filename:bytes}, not flat DHCP/ping fields.
    """
    fields = C2['two_lifetime_fields'](leaf)
    cycle = fields['cycles'].get(1)
    valid_boot = isinstance(boot, str) and bool(_BOOT.fullmatch(boot))
    result = {'verified_boot': boot, 'leaf_cycle': cycle, 'leaf_fields': fields,
              'leaf_transport_complete': False, 'leaf_boot_match': False,
              'cycle_export': None, 'cycle_export_complete': False, 'protocol_pass': False}
    if not valid_boot:
        return result
    required = {'exit_status', 'reason', 'stdin_complete', 'stdout_bytes', 'stderr_bytes'}
    if not isinstance(leaf_process, dict) or not isinstance(export_process, dict) or \
            not required <= leaf_process.keys() or not required <= export_process.keys():
        return result
    process = leaf_process or {}
    result['leaf_transport_complete'] = bool(
        not leaf_err and process.get('exit_status') == 0 and process.get('reason') is None and
        process.get('stdin_complete') is True and process.get('stdout_bytes') == len(leaf) and
        process.get('stderr_bytes') == 0)
    result['leaf_boot_match'] = bool(
        leaf.startswith(('boot_before=' + boot + '\nkernel=' + RELEASE + '\n').encode()) and
        leaf.endswith(('__IW_PASSIVE_END__\nboot_after=' + boot + '\n').encode()))
    export = C2['cycles_export_result'](exported, export_err, export_process, boot)
    result['cycle_export'] = export
    # Strict, fixed existing c1 file frames: exact order/names, every declared
    # byte copied, no missing/duplicate/foreign-cycle/trailing or partial frame.
    # The inherited validator checks boot/transport/caps but only counts headers.
    pos = len(('__CYCLES_BEGIN__\nboot=' + boot + '\n').encode())
    frames_ok = export['boot_match'] and export['transport_ok'] and not export['truncated']
    sizes = export['cycles'].get(1, {})
    frames_ok = frames_ok and set(export['cycles']) == {1} and set(sizes) == set(C2['CYCLE_FILES'])
    for name in C2['CYCLE_FILES']:
        if not frames_ok:
            break
        header = re.match(rb'__FILE__ path=' + re.escape(
            (C2['CYCLE_DIR'] + '/c1/' + name).encode()) + rb' bytes=(\d+)\n', exported[pos:])
        if header is None or int(header[1]) != sizes[name] or \
                (sizes[name] <= 0 and name != 'dropbear.log'):
            frames_ok = False
            break
        pos += header.end() + sizes[name]
        frames_ok = exported[pos:pos + 9] == b'\n__END__\n'
        pos += 9
    result['cycle_export_complete'] = bool(frames_ok and exported[pos:] ==
        ('__CYCLES_END__\nboot_after=' + boot + '\n').encode())
    prefix = cycle.get('dhcp_prefix') if cycle else None
    data_ok = bool(cycle and cycle.get('dhcp_exit') == '0' and
        all(cycle.get(k) == 1 for k in ('dhcp_bound', 'lease_written', 'dropbear_digest_ok',
                                      'wifi_sshd_started', 'wifi_sshd_ready')) and
        isinstance(prefix, str) and re.fullmatch(r'\d{1,2}', prefix) and 1 <= int(prefix) <= 32 and
        cycle.get('ping_transmitted') == cycle.get('ping_received') == 3 and
        cycle.get('host_ack') is True)
    result['protocol_pass'] = bool(result['leaf_transport_complete'] and result['leaf_boot_match'] and
        result['cycle_export_complete'] and fields['framed'] and set(fields['cycles']) == {1} and
        fields.get('cycles_completed') == fields.get('terminals_observed') == 1 and
        fields.get('rearms_observed') == fields.get('overall_rc') == 0 and
        fields.get('connect_exit') == fields.get('supplicant_exit') and
        fields.get('supplicant_exit') in (0, 143) and data_ok and
        leaf.count(b'__JOIN_BEGIN__\n') == leaf.count(b'__JOIN_END__\n') == 1 and
        b'data_checks_failed=1' not in leaf)
    return result


def read_protocol(root, boot):
    """Read the actual retained phase directories, before deciding a full pass."""
    import json
    root = Path(root)
    try:
        return protocol_result(
            (root / 'passive-scan/stdout.txt').read_bytes(),
            (root / 'passive-scan/stderr.txt').read_bytes(),
            json.loads((root / 'passive-scan/process.json').read_bytes()),
            (root / 'cycles-evidence.raw').read_bytes(),
            (root / 'cycles-export/stderr.txt').read_bytes(),
            json.loads((root / 'cycles-export/process.json').read_bytes()), boot)
    except (OSError, ValueError, KeyError, TypeError):
        return {'verified_boot': boot, 'leaf_cycle': None, 'protocol_pass': False,
                'reason': 'missing, malformed or incomplete preserved leaf/export evidence'}


def classify(kmsg, ssh_receipt, verified_boot, protocol=None):
    """kmsg: sanitized kernel log bytes. ssh_receipt: the host's parsed
    wifi-ssh-receipt.json dict (or None). verified_boot: the sealed mainline boot
    id this run was verified under. Returns the provisional CCMP verdict dict."""
    lines = kmsg.splitlines()
    diag = [m for line in lines if (m := _DIAG.search(line))]
    rx = [m for line in lines if (m := _RX.search(line))]
    end = [m for line in lines if (m := _END.search(line))]
    malformed = sum(1 for line in lines if _PREFIX.search(line) and
                     not _DIAG.search(line) and not _RX.search(line) and not _END.search(line))
    seq = [(int(m[1]), int(m[2])) for m in diag]
    counts = [(int(m[3]), int(m[4]), int(m[5])) for m in diag]  # (total, native, bytes)
    native_last = counts[-1][1] if counts else None
    queued = int(end[0][1]) if len(end) == 1 else None
    # Original sample ceilings; CCMP64 is separately reported, native stays0.
    def bounded(c):
        t, n, b = c
        return n == 0 and 0 <= t <= RX_MAX and b <= BYTES_MAX
    monotone = all(counts[i][j] >= counts[i - 1][j]
                   for i in range(1, len(counts)) for j in range(3))
    counts_ok = bool(counts) and all(bounded(c) for c in counts) and monotone
    # Exactly one first CCMP queue record, with precise pinned core flags.
    rx_ok = (len(rx) == 1 and int(rx[0][2], 16) == CCMP_FLAGS and
             14 < int(rx[0][1]) <= HIF_RX_MAX_PACKET)
    queued_ok = bool(queued is not None and counts and 1 <= queued <= NATIVE_MAX and
                     queued <= counts[-1][0])
    result = {
        'sequence': seq,
        'sequence_ok': seq == _SEQUENCE,
        'counts_ok': counts_ok,
        'native_ciphertext_queued': native_last,
        'ccmp_ethernet_queued': queued,
        'queued_count_ok': queued_ok,
        'first_rx_ethernet_bytes': (int(rx[0][1]) if len(rx) == 1 else None),
        'first_rx_flags': (int(rx[0][2], 16) if len(rx) == 1 else None),
        'standard_decap_flags': rx_ok,
        'healthy_cleanup': sum(bool(_CLEANUP.search(line)) for line in lines) == 1,
        'hardware_replay_proven': False,
        'key_deletion_proven': False,
        'maintained_wifi_support': False,
        'fault': any(_FAULT.search(line) for line in lines),
        'malformed_records': malformed,
    }
    # Queue evidence requires the exact healthy engine and separate cleanup.
    # Neither footer proves key deletion, integrity enforcement or core delivery.
    result['eligible_ccmp_queue'] = bool(result['sequence_ok'] and result['counts_ok'] and
                                        not result['fault'] and malformed == 0 and
                                        queued_ok and rx_ok and result['healthy_cleanup'])
    # Fresh real-lease, boot/mode-bound WLAN exchange from the reviewed helper.
    valid_boot = isinstance(verified_boot, str) and bool(_BOOT.match(verified_boot))
    cycles = ssh_receipt.get('cycles') if isinstance(ssh_receipt, dict) else None
    one_cycle = isinstance(cycles, list) and len(cycles) == 1
    cycle = cycles[0] if one_cycle else None
    receipt_boot = ssh_receipt.get('boot_id') if isinstance(ssh_receipt, dict) else None
    result['authenticated'] = bool(
        valid_boot and one_cycle and receipt_boot == verified_boot and
         isinstance(cycle, dict) and cycle.get('cycle') == 1 and
        cycle.get('ssh_exit') == 0 and cycle.get('boot_match') is True and
        cycle.get('ready_seen') is True and cycle.get('ack_written') is True and
         # Device-written post-ACTIVE marker, not a host mode assertion.
        cycle.get('marker_after_active') is True and
         cycle.get('marker_mode') == 'ccmp-stable-monitor' and
        cycle.get('marker_boot') == verified_boot)
    # Provisional positive only; not sustained operation or completed support.
    result['provisional_ccmp_compatibility_pass'] = bool(
        result['eligible_ccmp_queue'] and result['authenticated'] and
        isinstance(protocol, dict) and protocol.get('verified_boot') == verified_boot and
        protocol.get('protocol_pass') is True)
    result['normal_dhcp_ping_protocol'] = protocol
    return result


if __name__ == '__main__':  # pragma: no cover
    import json
    import sys
    kmsg = open(sys.argv[1], 'rb').read() if len(sys.argv) > 1 else b''
    receipt = json.loads(open(sys.argv[2]).read()) if len(sys.argv) > 2 else None
    verified = sys.argv[3] if len(sys.argv) > 3 else None
    protocol = read_protocol(sys.argv[4], verified) if len(sys.argv) > 4 else None
    print(json.dumps(classify(kmsg, receipt, verified, protocol), indent=2))
