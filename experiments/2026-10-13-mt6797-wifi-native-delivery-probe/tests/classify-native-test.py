#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Exercise the native one-lifetime verdict: exact owned sequence, fresh mode-bound
authenticated exchange, and the eligible-vs-authenticated separation."""
import runpy
from pathlib import Path

C = runpy.run_path(str(Path(__file__).resolve().parent.parent / 'classify-native.py'))
classify = C['classify']
BOOT = '626e02e3-2c12-4cfa-9055-858dbd563ee6'
OTHER = '0123abcd-0123-0123-0123-0123456789ab'
SEQ = [(1, 1), (2, 0), (3, 2), (4, 0)]


def kmsg(seq=SEQ, native_last=5, bypass='0', fault=False):
    out = []
    for i, (st, act) in enumerate(seq):
        nat = native_last if i == len(seq) - 1 else 0
        out.append(('6,1,1,-;mt6797-consys: one-shot WLAN native-diag: state=%d act=%d '
                    'total=40 native=%d bytes=4096' % (st, act, nat)).encode())
    if native_last:
        out.append(('6,2,2,-;mt6797-consys: one-shot WLAN native-diag RX: first '
                    'mpdu_bytes=120 crypto_bypass_flags=0x%s' % bypass).encode())
    if fault:
        out.append(b'6,3,3,-;mt6797-consys: one-shot WLAN native-diag no-radio latch')
    return b'\n'.join(out)


def receipt(boot=BOOT, exit0=True, marker=True, mode='native-delivery',
            mboot=BOOT, cycles=1):
    c = {'ssh_exit': 0 if exit0 else 255, 'boot_match': True, 'ready_seen': True,
         'ack_written': True, 'marker_after_active': marker,
         'marker_mode': mode, 'marker_boot': mboot}
    return {'boot_id': boot, 'cycles': [c] * cycles}


# Positive: exact owned sequence, flags clear, no fault, fresh mode-bound exchange.
good = classify(kmsg(), receipt(), BOOT)
assert good['native_delivery_pass'] and good['eligible_delivery'] and good['authenticated']

# Eligible delivery holds, but authentication fails on a STALE receipt (an R33
# first-cycle receipt whose boot is not the verified sealed boot).
stale = classify(kmsg(), receipt(boot=OTHER), BOOT)
assert stale['eligible_delivery'] and not stale['authenticated'] and not stale['native_delivery_pass']

# No device-written post-ACTIVE marker, or wrong mode -> not authenticated.
assert not classify(kmsg(), receipt(marker=False), BOOT)['authenticated']
assert not classify(kmsg(), receipt(mode='observability'), BOOT)['authenticated']
assert not classify(kmsg(), receipt(mboot=OTHER), BOOT)['authenticated']  # marker bound to wrong boot

# SSH did not complete -> not authenticated.
assert not classify(kmsg(), receipt(exit0=False), BOOT)['authenticated']
# More than one cycle (a second association) -> refused.
assert not classify(kmsg(), receipt(cycles=2), BOOT)['authenticated']
# No verified boot passed -> cannot authenticate.
assert not classify(kmsg(), receipt(), None)['authenticated']

# Wrong owned sequence (a no-radio latch act=3 instead of SUBMIT_DISABLE) -> not eligible.
assert not classify(kmsg(seq=[(1, 1), (2, 0), (4, 3)]), receipt(), BOOT)['eligible_delivery']
# Never reached ACTIVE.
assert not classify(kmsg(seq=[(1, 1), (4, 0)]), receipt(), BOOT)['eligible_delivery']
# Extra/repeated cycle in the log -> not the exact one cycle.
assert not classify(kmsg(seq=SEQ + SEQ), receipt(), BOOT)['eligible_delivery']
# Bypass flags NOT clear (FW-decrypted/stripped) -> not eligible native crypto.
nf = classify(kmsg(bypass='1'), receipt(), BOOT)
assert not nf['eligible_delivery'] and nf['first_rx_bypass_flags'] == 1
# No protected-native MPDU queued -> not eligible.
assert not classify(kmsg(native_last=0), receipt(), BOOT)['eligible_delivery']
# A fault fails it.
assert not classify(kmsg(fault=True), receipt(), BOOT)['eligible_delivery']

print('classify-native: PASS (exact owned 1/2/3/4 act 1/0/2/0 cycle; eligible delivery separate from the '
      'fresh boot/mode-bound authenticated SSH exchange; stale/wrong-mode/multi-cycle refused)')
