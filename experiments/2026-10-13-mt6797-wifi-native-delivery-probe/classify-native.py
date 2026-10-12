#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Native-crypto-delivery one-lifetime verdict (proposal 0181).

Positive is decided from the native diagnostic's OWN kernel records and the fresh
post-ACTIVE Wi-Fi SSH challenge, never the translated C3 data counters:

  * the native diagnostic reached ACTIVE and then CLOSED cleanly (its state
    sequence, "one-shot WLAN native-diag: state=... native=..."), state enum
    IDLE=0 ENABLE_PENDING=1 ACTIVE=2 DISABLE_PENDING=3 CLOSED=4;
  * at least one protected-native MPDU was delivered to mac80211 with ALL the
    crypto-bypass flags CLEAR ("one-shot WLAN native-diag RX: ...
    crypto_bypass_flags=0x0"), so mac80211 ran its own AES-CCM decrypt, MIC and
    replay under the live key -- the translated/plain path was withheld;
  * the fresh Wi-Fi SSH exchange, gated on the device's post-ACTIVE boot/mode
    marker, completed (exit 0, boot match, readiness seen).

A diagnostic result is route 4's precondition met for that mode and sample, not
sustained operation or driver completion. A negative is inconclusive. Sanitized:
counts/flags/state only; no addresses, bodies or keys.
"""

import re

STATE = {0: 'IDLE', 1: 'ENABLE_PENDING', 2: 'ACTIVE', 3: 'DISABLE_PENDING', 4: 'CLOSED'}
_DIAG = re.compile(rb'one-shot WLAN native-diag: state=(\d+) act=(\d+) total=(\d+) '
                   rb'native=(\d+) bytes=(\d+)$')
_RX = re.compile(rb'one-shot WLAN native-diag RX: first mpdu_bytes=(\d+) '
                 rb'crypto_bypass_flags=0x([0-9a-f]+)$')
# A named join fault anywhere makes the lifetime unhealthy on its own.
_FAULT = re.compile(rb'one-shot WLAN (?:join (?:stopped:|rearm refused:|rearm wrap:)|'
                    rb'native-diag no-radio latch)')


def classify(kmsg, ssh_receipt):
    """kmsg: the sanitized kernel log bytes. ssh_receipt: the host's parsed
    wifi-ssh-receipt.json dict (or None). Returns the native verdict dict."""
    lines = kmsg.splitlines()
    diag = [m for line in lines if (m := _DIAG.search(line))]
    rx = [m for line in lines if (m := _RX.search(line))]
    states = [int(m[1]) for m in diag]
    native_counts = [int(m[4]) for m in diag]
    result = {
        'native_records': len(diag),
        'states': [STATE.get(s, str(s)) for s in states],
        'reached_active': 2 in states,
        'closed_clean': states[-1:] == [4] if states else False,
        'native_delivered': max(native_counts) if native_counts else 0,
        'first_rx_bypass_flags': (int(rx[0][2], 16) if rx else None),
        'bypass_flags_clear': bool(rx) and int(rx[0][2], 16) == 0,
        'fault': any(_FAULT.search(line) for line in lines),
    }
    cycle = None
    if isinstance(ssh_receipt, dict):
        cycles = ssh_receipt.get('cycles') or []
        cycle = cycles[0] if cycles else None
    result['ssh_pass'] = bool(cycle and cycle.get('ssh_exit') == 0 and
                              cycle.get('boot_match') is True and
                              cycle.get('ready_seen') is True and
                              cycle.get('ack_written') is True)
    # Positive: the native path reached ACTIVE and closed cleanly, delivered at
    # least one protected-native frame with bypass flags clear, no fault, and the
    # fresh post-ACTIVE SSH challenge completed. Translated counters are not used.
    result['native_delivery_pass'] = bool(
        result['reached_active'] and result['closed_clean'] and
        result['native_delivered'] >= 1 and result['bypass_flags_clear'] and
        not result['fault'] and result['ssh_pass'])
    return result


if __name__ == '__main__':  # pragma: no cover
    import json
    import sys
    kmsg = open(sys.argv[1], 'rb').read() if len(sys.argv) > 1 else b''
    receipt = json.loads(open(sys.argv[2]).read()) if len(sys.argv) > 2 else None
    print(json.dumps(classify(kmsg, receipt), indent=2))
