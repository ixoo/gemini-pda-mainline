#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Native-crypto-delivery one-lifetime verdict (proposal 0181).

Two SEPARATE conclusions, never conflated:

  ELIGIBLE DELIVERY (necessary, not sufficient): the native diagnostic ran its
  exact owned one-cycle sequence with no fault, and at least one protected-native
  MPDU was QUEUED to mac80211 with every crypto-bypass flag clear. native= counts
  eligible MPDUs handed up; it is not proof anything was authenticated.

  AUTHENTICATED PATH (the positive): a fresh Wi-Fi SSH exchange completed through
  EXCLUSIVELY native RX -- the device wrote a boot-and-mode-bound marker only
  after native ACTIVE, and the SSH exchange, gated on that marker and bound to the
  VERIFIED sealed boot, completed. A plain receipt boolean cannot establish
  freshness or mode; the caller passes the verified boot and the marker is checked
  against it.

The native state/action sequence is exactly, in order, one cycle:
  state 1 act 1 (ENABLE_PENDING via SUBMIT_ENABLE), state 2 act 0 (ACTIVE),
  state 3 act 2 (DISABLE_PENDING via SUBMIT_DISABLE), state 4 act 0 (CLOSED).
The DISABLE_PENDING->CLOSED transition requires a quiescent ledger, so a clean
close is also the command-credit retirement. Any fault (a no-radio latch, act 3,
or a named join stop) fails it. Translated C3 counters are never used. Sanitized.
"""

import re

_DIAG = re.compile(rb'one-shot WLAN native-diag: state=(\d+) act=(\d+) total=(\d+) '
                   rb'native=(\d+) bytes=(\d+)$')
_RX = re.compile(rb'one-shot WLAN native-diag RX: first mpdu_bytes=(\d+) '
                 rb'crypto_bypass_flags=0x([0-9a-f]+)$')
_FAULT = re.compile(rb'one-shot WLAN (?:join (?:stopped:|rearm refused:|rearm wrap:)|'
                    rb'native-diag no-radio latch)')
_BOOT = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
# The exact owned one-cycle (state, act) transition sequence.
_SEQUENCE = [(1, 1), (2, 0), (3, 2), (4, 0)]


def classify(kmsg, ssh_receipt, verified_boot):
    """kmsg: sanitized kernel log bytes. ssh_receipt: the host's parsed
    wifi-ssh-receipt.json dict (or None). verified_boot: the sealed mainline boot
    id this run was verified under. Returns the native verdict dict."""
    lines = kmsg.splitlines()
    diag = [m for line in lines if (m := _DIAG.search(line))]
    rx = [m for line in lines if (m := _RX.search(line))]
    seq = [(int(m[1]), int(m[2])) for m in diag]
    native_counts = [int(m[4]) for m in diag]
    result = {
        'sequence': seq,
        'sequence_ok': seq == _SEQUENCE,
        'native_delivered': max(native_counts) if native_counts else 0,
        'first_rx_bypass_flags': (int(rx[0][2], 16) if rx else None),
        'bypass_flags_clear': bool(rx) and int(rx[0][2], 16) == 0,
        'fault': any(_FAULT.search(line) for line in lines),
    }
    # Eligible delivery: the exact owned cycle, no fault, >=1 flags-clear MPDU
    # queued to mac80211. Necessary, NOT authentication.
    result['eligible_delivery'] = bool(result['sequence_ok'] and not result['fault'] and
                                       result['native_delivered'] >= 1 and
                                       result['bypass_flags_clear'])
    # Authenticated path: a fresh, mode-bound, exclusively-native Wi-Fi exchange.
    valid_boot = isinstance(verified_boot, str) and bool(_BOOT.match(verified_boot))
    cycles = ssh_receipt.get('cycles') if isinstance(ssh_receipt, dict) else None
    one_cycle = isinstance(cycles, list) and len(cycles) == 1
    cycle = cycles[0] if one_cycle else None
    receipt_boot = ssh_receipt.get('boot_id') if isinstance(ssh_receipt, dict) else None
    result['authenticated'] = bool(
        valid_boot and one_cycle and receipt_boot == verified_boot and
        isinstance(cycle, dict) and
        cycle.get('ssh_exit') == 0 and cycle.get('boot_match') is True and
        cycle.get('ready_seen') is True and cycle.get('ack_written') is True and
        # The device-written marker: after native ACTIVE, bound to this boot and
        # the native mode, so an old or wrong-mode receipt cannot satisfy it.
        cycle.get('marker_after_active') is True and
        cycle.get('marker_mode') == 'native-delivery' and
        cycle.get('marker_boot') == verified_boot)
    # Positive requires BOTH the eligible owned delivery and the authenticated
    # fresh exchange; a diagnostic result, not sustained operation or completion.
    result['native_delivery_pass'] = bool(result['eligible_delivery'] and result['authenticated'])
    return result


if __name__ == '__main__':  # pragma: no cover
    import json
    import sys
    kmsg = open(sys.argv[1], 'rb').read() if len(sys.argv) > 1 else b''
    receipt = json.loads(open(sys.argv[2]).read()) if len(sys.argv) > 2 else None
    verified = sys.argv[3] if len(sys.argv) > 3 else None
    print(json.dumps(classify(kmsg, receipt, verified), indent=2))
