# Recovery takeover design

## Public contract

`mtk_wdt_recovery_takeover()` accepts a bound MediaTek watchdog device, exactly
15000 ms, and a result object. It is available only when the driver is built in
and the default-off takeover configuration is selected. The runtime variant
gate accepts only `mediatek,mt6797-wdt`.

The result reports whether ownership began, a nonzero one-shot identity, and
the mode/length words observed around the write. A repeat returns
`-EALREADY` with the original identity and performs no write.

## Hardware order

Under one owner lock:

1. read the current mode;
2. allocate a nonzero identity;
3. publish irreversible ownership before the first write;
4. program the exact 15-second length;
5. preserve unrelated mode bits while clearing IRQ/dual mode and setting
   enable/auto-start;
6. reload once; and
7. read back the length and recovery-mode mask.

A readback mismatch returns `-EIO` but retains ownership because a write was
already attempted. There is no release or cancellation API.

## Competing operations

The same lock serializes ordinary ping, timeout, start, stop, and pretimeout
operations. Once recovery is owned, each returns `-EBUSY` before MMIO. Restart
remains available because an explicit system restart is not a keepalive and
cannot strand the device beyond the bounded recovery policy.

## Hardware-free tests

The internal operation takes injected register reads, writes, and identity
allocation. Five cases cover exact success/write order, invalid inputs and
zero identity, repeat refusal, length-readback failure, and mode-readback
failure. The fake transport has no MMIO, sleep, timer, platform device, or
watchdog-core registration.

QEMU proves this software boundary only. It does not establish the physical
MT6797 timeout or reset behavior; that proof belongs to the eventual complete
CPU8 candidate with retained last-stage evidence.
