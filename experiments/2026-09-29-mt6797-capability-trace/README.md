# Locate the first post-START capability-query failure

The [first capability boot](../2026-09-29-mt6797-capability-query/results/runtime-1.json)
reached firmware-ready WCIR `0x00300279`, then its sole normal command returned
`-EIO` in about 1.16 ms without a capability record. The full private log was
preserved, A53 regression passed, and the device returned to changed-boot
Gemian. The final status does not distinguish an occupied receive queue,
failed TX, unexpected WRPLR length, failed RX, or rejected event header.

Patch 0054 adds a result trace to the existing one-shot query. It records the
last completed stage, pre/post WRPLR, PIO setup/completion and byte counts. It
records only logical length, packet type, event ID and sequence if a complete
RX happened. It never logs MAC, date, reserved bytes or event payload. There
is no new transaction, MMIO access, deadline, NVRAM/radio action or packet DMA.
The patch is applied after 0053 in a separate profile and local release.

The next boot tests the hypothesis that the prior `-EIO` can be assigned to
one of those stages using the same query. A pre-existing WRPLR value stops
before TX. An incomplete TX/RX or malformed length/header stops this boot's
HIF session. A matching event advances only to capability observation; radio,
calibration and network traffic still require separate evidence and review.
No identical boot should be repeated without a decision-changing measurement.

Before physical selection, build the pushed clean profile with Buildbox, verify
the exact package and candidate against the previous board DT and private RAM
root, and use the guarded live-GPT boot2 installer from authenticated Gemian.
The owner physically selects boot2 after clean shutdown. On a new authenticated
mainline boot, preserve the complete private log and regression result, then
return through the reviewed recovery path and verify changed-boot Gemian.
A panic requires preserving evidence and following the stop conditions.

## Offline validation

The actual patched HIF core passes the focused host test under strict C11,
ASan and UBSan, including the one successful exchange, all 69 scalar access
faults, stale queue, wrong length/sequence and missing-reply deadline. The
patch applies to the pinned prepared source and `checkpatch.pl --no-signoff`
reports zero errors and warnings. The test source is in
[`tests/test-capability.c`](tests/test-capability.c). This simulation cannot
establish a device response. Build and physical result are pending.
