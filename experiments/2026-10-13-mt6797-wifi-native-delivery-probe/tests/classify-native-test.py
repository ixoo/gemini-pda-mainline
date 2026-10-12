#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Exercise the native one-lifetime verdict over synthetic kernel records."""
import runpy
from pathlib import Path

C = runpy.run_path(str(Path(__file__).resolve().parent.parent / 'classify-native.py'))
classify = C['classify']


def kmsg(states, native_last, bypass='0', fault=False):
    out = []
    for i, s in enumerate(states):
        nat = native_last if i == len(states) - 1 else 0
        out.append(('6,1,1,-;mt6797-consys: one-shot WLAN native-diag: state=%d act=1 '
                    'total=40 native=%d bytes=4096' % (s, nat)).encode())
    if native_last:
        out.append(('6,2,2,-;mt6797-consys: one-shot WLAN native-diag RX: first '
                    'mpdu_bytes=120 crypto_bypass_flags=0x%s' % bypass).encode())
    if fault:
        out.append(b'6,3,3,-;mt6797-consys: one-shot WLAN join stopped: branch=5 ret=-71')
    return b'\n'.join(out)


def ssh(ok=True):
    return {'cycles': [{'ssh_exit': 0 if ok else 255, 'boot_match': ok,
                        'ready_seen': ok, 'ack_written': ok}]}


# Positive: IDLE->ENABLE_PENDING->ACTIVE->DISABLE_PENDING->CLOSED, native frame,
# bypass flags clear, no fault, SSH pass.
good = classify(kmsg([0, 1, 2, 3, 4], 5, '0'), ssh(True))
assert good['native_delivery_pass'], good
assert good['reached_active'] and good['closed_clean'] and good['native_delivered'] == 5
assert good['bypass_flags_clear'] and good['ssh_pass'] and not good['fault']

# Never reached ACTIVE.
assert not classify(kmsg([0, 1, 4], 0, '0'), ssh(True))['native_delivery_pass']
# Crypto-bypass flags NOT clear (FW-decrypted/stripped) -> not native crypto.
nf = classify(kmsg([0, 1, 2, 3, 4], 5, '1'), ssh(True))
assert not nf['native_delivery_pass'] and nf['first_rx_bypass_flags'] == 1
# No protected-native frame delivered.
assert not classify(kmsg([0, 1, 2, 3, 4], 0, '0'), ssh(True))['native_delivery_pass']
# A named fault makes it unhealthy.
assert not classify(kmsg([0, 1, 2, 3, 4], 5, '0', fault=True), ssh(True))['native_delivery_pass']
# SSH challenge did not complete -> inconclusive, not positive.
assert not classify(kmsg([0, 1, 2, 3, 4], 5, '0'), ssh(False))['native_delivery_pass']
# Did not close cleanly (stuck ACTIVE).
assert not classify(kmsg([0, 1, 2], 5, '0'), ssh(True))['native_delivery_pass']
# No SSH receipt at all.
assert not classify(kmsg([0, 1, 2, 3, 4], 5, '0'), None)['native_delivery_pass']

print('classify-native: PASS (positive requires ACTIVE+CLOSED, native frame, bypass flags clear, '
      'no fault, fresh post-ACTIVE SSH; translated counters unused)')
