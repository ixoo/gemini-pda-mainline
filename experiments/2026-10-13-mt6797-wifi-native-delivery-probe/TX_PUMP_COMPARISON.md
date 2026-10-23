# TX pump comparison 1 — one candidate, one measurement boot

Owner decision after [baseline 2](THROUGHPUT_BASELINE_2_RESULT.md), 2026-10-23.
DMA is deferred. The measured TX direction supplies the 0.205740 Mbit/s
(rounded 0.206), 87.525% aggregate-idle reference; RX has no baseline result.
No claim that a DMA change would fix throughput follows from that measurement.
Future DMA justification would concern CPU headroom, with its separate
[transfer-contract unknowns](DMA_TRANSFER_CONTRACT.md) still unresolved.

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
block. Existing credit/attribution/admission code is unchanged. Checkpatch has
zero errors/checks and its new-file/MAINTAINERS advisory; this remains an
internal, non-certifying experiment patch, not an upstream submission.

The measurement profile retains the installed RAM guard's release string
`7.1.3-gemini-a53-private-p2e-delivery`. The **new source commit, build notes,
configuration and full-image digest** must identify it uniquely; release alone
is never its identity. This avoids changing the established RAM admission
contract along with the scheduling experiment. This is a pump measurement,
not another P2E run. Reconnect and dormant lifetime safeguards remain closed/off.

## Before device admission

Commit/push reviewed inputs, then build from a clean checkout with
`KERNEL_PROFILE=mt6797-a53-wifi-tx-pump-measurement ./scripts/build-kernel --backend buildbox`.
Require canonical series order, exact selected config (pump y, prerequisites n),
validated package/source/compiler identity and unchanged finite driver caps.
Compose one candidate using the retained reviewed RAM members and admitted
firmware inputs, without introducing a sampler. Pin its hashes before install;
guard live-GPT boot2 and require matching full-partition readback, clean
shutdown and physical owner selection. No alternate partition or boot retry.

RX counts through `timeout nc | wc -c`, with no regular payload file or
ulimit increase. Preflight rejects a planned regular-file sink exceeding the
inherited 128 KiB limit. The fixture streams 1 MiB through the actual generated
counter under that limit. Independent SSH keepalives and chunk progress remain.

The unchanged 2 MiB logger is a finite bound: projecting baseline-2 record
volume to five faster 1 MiB chunks each way would exceed it. Byte budget versus
an explicitly authorized capture-bound change must be settled and pinned
**before device admission**. No logger or driver resource limit is silently
raised. This does not block building/testing the scheduling-only kernel.

## Single-run hypothesis, procedure and branches

Hypothesis: removing avoidable delayed-work sleeps increases TX beyond the
0.206 Mbit/s reference with unchanged single-frame ownership. Measure CPU too;
aggregate idle alone cannot exclude saturation of one service CPU.

Verify fresh live image/notes/RAM identity before the existing firmware start.
Join, DHCP, three pings, SSH; five separate known-size chunks per direction,
device TX then RX, timeout at most 10 s/chunk and progress at each boundary.
Preserve the 5 s SSH keepalive and 135 s owned-process bound. Record actual
bytes/time, completed chunks, CPU idle/iowait, netdev deltas and completion/error
counts for each direction. A known-size short completion is not a sustained
50 s result. Report any byte-budget difference from baseline explicitly.

After traffic, prove remote-group/local-endpoint quiescence, immediately make
one EOS-derived standard disconnect attempt, report delivery and whole-ledger
stage 3 separately, seal/export, regression and reviewed return. Independently
confirm changed-boot Gemian. No prolonged intentional idle period.

Identity/cold-start/admission refusal, first driver/link/credit error, harness
refusal or resource cap ends the attempt; withhold later traffic, preserve and
return through the reviewed path. Unknown ownership holds recovery. A refused
disconnect is a harness result, no second attempt. Missing whole ledger remains
a failure even if the traffic rate improves. No repeat follows a censored run.

If TX moves by an order of magnitude, the next throughput question is link rate
and aggregation. This pass adds no DMA, RX-DMA, deeper queue, rekey, key-slot
reuse, protected re-arm, firmware-lifecycle command or provider lifecycle work.
