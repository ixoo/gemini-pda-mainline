# TX pump comparison 1 — one candidate, one measurement boot

Owner decision after [baseline 2](THROUGHPUT_BASELINE_2_RESULT.md), 2026-10-23.
DMA is deferred. The measured TX direction supplies the 0.205740 Mbit/s
(rounded 0.206), 87.525% aggregate-idle reference; RX has no baseline result.
No claim that a DMA change would fix throughput follows from that measurement.
Future DMA justification would concern CPU headroom, with its separate
[transfer-contract unknowns](DMA_TRANSFER_CONTRACT.md) still unresolved.

Final owner steering: **duration-bounded first**, five chunks per direction,
**1 s or 1 MiB hard cap**, whichever ends first, **100 ms gaps**. The earlier
128 KiB size-bound preparation is superseded before installation or boot.
The 2 MiB logger and every driver resource cap remain unchanged.

## Source finding and minimal change

In the installed-source audit, data enqueue requests delay 0, but a running
join worker requeues at 20 ms while only one frame can be in flight. That
places scheduling gaps between frame selection, TX completion and credit
reconciliation. The public source also has an optional snapshot cadence;
snapshots remain off in this experiment and that existing cadence is preserved.

Patch 0231 adds `CONFIG_MT6797_CCMP_TX_PUMP`, default n. Only the new
`mt6797-a53-wifi-tx-pump-measurement` profile selects y. Its worker schedules
delay 0 for queued frames, in-flight completion ownership or pending command/
data credit; idle uses 20 ms. After **32 consecutive delay-0 iterations**, the
next iteration uses 20 ms and resets the counter. A held reserved frame can
keep the queue nonempty; the guard also bounds that case. No new internal
owner, TX depth, page/PID policy, deadline, admission or firmware command.
The prior loss-path waiter candidate is not changed in this scheduling pass.

The actual-source fixture compiles the scheduling helper with ASan/UBSan,
checks pending/idle choices and repeated guard backoffs, and verifies the rest
of the MAC source is identical outside includes, the counter and scheduling
block. The freshly built source passes the same fixture. Against the actual installed
source, HIF is byte-identical; data TX, RX, guard, credit/management waiters and
key-disable functions are identical. Reporting and compiled-off snapshot
mechanisms remain outside the active data change. Checkpatch has
zero errors/checks and its new-file/MAINTAINERS advisory; this remains an
internal, non-certifying experiment patch, not an upstream submission.

The measurement profile retains the installed RAM guard's release string
`7.1.3-gemini-a53-private-p2e-delivery`. The **new source commit, build notes,
configuration and full-image digest** must identify it uniquely; release alone
is never its identity. This avoids changing the established RAM admission
contract along with the scheduling experiment. This is a pump measurement,
not another P2E run. Reconnect and dormant lifetime safeguards remain closed/off.

## Before device admission

Reviewed inputs were committed/pushed and built from a clean checkout with
`KERNEL_PROFILE=mt6797-a53-wifi-tx-pump-measurement ./scripts/build-kernel --backend buildbox`.
Require canonical series order, exact selected config (pump y, prerequisites n),
validated package/source/compiler identity and unchanged finite driver caps.
Compose one candidate using the retained reviewed RAM members and admitted
firmware inputs, without introducing a sampler. Pin its hashes before install;
guard live-GPT boot2 and require matching full-partition readback, clean
shutdown and physical owner selection. No alternate partition or boot retry.

Build `23745fe907c48ae0137cf5151b1117770545ce07`, package manifest SHA-256
`44a071bdd43322bcc21bbf99da60ee89407e6b64523ca24d1a64828a6c36c532`,
has **only CONFIG_MT6797_CCMP_TX_PUMP=y** as a config difference from baseline.
An earlier build enabled cfg80211 debugfs through the inherited profile; it
was rejected for installation and corrected. Candidate boot2 SHA-256
`e33c85f94b1217918ffe4bb886195fa469c564a49684b4f9c3fc62234540970d`,
manifest `16eb08d56be896e0d607b12142aaee6e52e95a1332a7f669932fe1e529d5ac9f`,
84-byte live-notes SHA-256
`e875f110f15fefaba186133a7092c5476566ce3262de927d8d73db7c99622c22`.
The parent container was reproduced byte-for-byte before replacing only the
kernel/config; RAM and board tree are byte-identical. The exact
[candidate validator](validate-tx-pump-candidate.py) is read-only. Real deployment
receipt checks complete after readback and before physical boot; no synthetic
receipt is accepted as device evidence.

RX counts through `timeout nc | wc -c`, with no regular payload file or
ulimit increase. Preflight rejects a planned regular-file sink exceeding the
inherited 128 KiB limit. The fixture streams 1 MiB through the actual generated
counter under that limit. Independent SSH keepalives and chunk progress remain.

Thirteen host fixtures cover byte/duration endings, per-chunk parsing, CPU
arithmetic and RX file-limit preflight. Four offline VM-loopback cases using
the exact retained BusyBox (SHA-256
`52151e7f322f926b64049cdaa1410dc3ea6485525e0624b05813791c219ae933`)
verify TX/RX cap completion (exit 0) and one-second termination (exit 143),
including pipe-based RX counting under the unchanged 128 KiB regular-file
limit. This is utility evidence, not a device throughput result.

The 2 MiB logger is still an absolute finite bound. Duration-bounding limits
active transfer time, but does not promise that every possible fast path fits
that byte budget. A logger/resource cap censors the run; preserve and stop,
never extend a limit or repeat the boot to finish the other direction.

## Single-run hypothesis, procedure and branches

Hypothesis: removing avoidable delayed-work sleeps increases TX beyond the
0.206 Mbit/s reference with unchanged single-frame ownership. Measure CPU too;
aggregate idle alone cannot exclude saturation of one service CPU.

Verify fresh live image/notes/RAM identity before the existing firmware start.
Join, DHCP, three pings, SSH; device TX then RX, five chunks each, ending at
1 s elapsed or the 1 MiB hard cap, with 100 ms gaps. Plain `nc` uses separate
TCP data sockets in both directions. The retained RAM inventory has no iperf3;
SSH carries only control/progress/5 s keepalives, not bulk-data crypto. Its
small control work still contributes to CPU accounting. Preserve the existing
135 s owned-process bound. Record each chunk's actual elapsed time, bytes,
rate and ending reason, plus aggregate rates, CPU idle/iowait, netdev deltas
and completion/error counts. RX uses the device's received-byte count, not
host-sent bytes. A cap-ended short chunk is explicitly labelled.

**Protocol difference:** baseline-2 TX spanned 51.829942958 s of size-bounded
chunks with a 10 s timeout (all five ended at that timeout); this run uses
1 s. The comparable quantities are per-chunk
rates, not bytes or total test durations. Baseline-2's five per-chunk TX rates
were 0.202007, 0.204181, 0.193683, 0.212439 and 0.221851 Mbit/s; median
0.2041814378 Mbit/s. Report the aggregate comparison to 0.205740 Mbit/s too,
including the intentional-gap and short-run caveat.

After traffic, prove remote-group/local-endpoint quiescence, immediately make
one EOS-derived standard disconnect attempt, report delivery and whole-ledger
stage 3 separately, seal/export, regression and reviewed return. Independently
confirm changed-boot Gemian. No prolonged intentional idle period.

Identity/cold-start/admission refusal, first driver/link/credit error, harness
refusal or resource cap ends the attempt; withhold later traffic, preserve and
return through the reviewed path. Unknown ownership holds recovery. A refused
disconnect is a harness result, no second attempt. Missing whole ledger remains
a failure even if the traffic rate improves. No repeat follows a censored run.

Score the measured TX median per-chunk rate against that baseline median:

- At least 10 times higher: pump cadence was the ceiling under this protocol;
  next question is link rate, rate control and aggregation.
- Above baseline's observed chunk-rate range but below 10 times: modest rise;
  the remaining ceiling is elsewhere (depth or per-frame credit serialization).
  Report and stop; do not widen this pass.
- Within baseline's observed range (or worse): no established improvement;
  the 20 ms reschedule was not demonstrated as the limit. Re-examine the worker
  path before any further change. This single-run band is not a confidence interval.
- RX harness refusal: RX unmeasured, never a link result. Incomplete/censored TX:
  no rate-branch score. Delivery/whole-ledger verdicts remain independent.

This pass adds no DMA, RX-DMA, deeper queue, rekey, key-slot reuse, protected
re-arm, firmware-lifecycle command or provider lifecycle work.
