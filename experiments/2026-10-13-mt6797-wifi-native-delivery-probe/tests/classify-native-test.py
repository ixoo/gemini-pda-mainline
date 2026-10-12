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


def kmsg(seq=SEQ, native_last=5, bypass='0', fault=False, totals=None, bytez=None,
         mpdu=120, rx=1):
    out = []
    n = len(seq)
    for i, (st, act) in enumerate(seq):
        nat = native_last if i == n - 1 else 0
        tot = (totals[i] if totals else 40)
        byt = (bytez[i] if bytez else 4096)
        out.append(('6,1,1,-;mt6797-consys: one-shot WLAN native-diag: state=%d act=%d '
                    'total=%d native=%d bytes=%d' % (st, act, tot, nat, byt)).encode())
    for _ in range(rx if native_last else 0):
        out.append(('6,2,2,-;mt6797-consys: one-shot WLAN native-diag RX: first '
                    'mpdu_bytes=%d crypto_bypass_flags=0x%s' % (mpdu, bypass)).encode())
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

# Counter ceilings: total > 512, native > total, native > 64 or bytes > 1 MiB fail.
assert not classify(kmsg(totals=[40, 40, 40, 600]), receipt(), BOOT)['counts_ok']
assert not classify(kmsg(native_last=99, totals=[40, 40, 40, 40]), receipt(), BOOT)['counts_ok']
assert not classify(kmsg(native_last=65, totals=[70, 70, 70, 70]), receipt(), BOOT)['counts_ok']
assert not classify(kmsg(bytez=[4096, 4096, 4096, 2 * 1024 * 1024]), receipt(), BOOT)['counts_ok']
# Non-monotonic counters (total decreases) fail.
assert not classify(kmsg(totals=[40, 40, 40, 10]), receipt(), BOOT)['counts_ok']
# Oversized first MPDU (> HIF max 2352) is not eligible.
assert not classify(kmsg(mpdu=4000), receipt(), BOOT)['eligible_delivery']
# A duplicate/second native RX record is malformed -> not eligible.
assert not classify(kmsg(rx=2), receipt(), BOOT)['eligible_delivery']
# A malformed native-diag line (prefix present, grammar broken) must be REJECTED,
# not silently ignored, even appended to an otherwise-positive log.
broken = kmsg() + b'\n6,9,9,-;mt6797-consys: one-shot WLAN native-diag: state=broken'
bres = classify(broken, receipt(), BOOT)
assert bres['malformed_records'] == 1 and not bres['eligible_delivery'] and not bres['native_delivery_pass']
rxbroken = kmsg() + b'\n6,9,9,-;mt6797-consys: one-shot WLAN native-diag RX: first mpdu_bytes=x'
assert classify(rxbroken, receipt(), BOOT)['malformed_records'] == 1
# A well-bounded monotone positive still passes.
assert classify(kmsg(totals=[0, 10, 40, 40], bytez=[0, 1024, 4096, 4096]), receipt(), BOOT)['native_delivery_pass']

print('classify-native: PASS (exact owned 1/2/3/4 act 1/0/2/0 cycle; eligible delivery separate from the '
      'fresh boot/mode-bound authenticated SSH exchange; stale/wrong-mode/multi-cycle refused)')
