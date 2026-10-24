# Current: station-3 completed its teardown; flow-control next

[Station result](TX_STATION_RESULT.md): station-3 (0245, 0246, 8 MiB ring)
repeated the throughput (TX 1.225 Mbit/s, RX 10.01 Mbit/s, median gap
1.16 ms) and completed the whole close: standard disconnect, host
acknowledgment accepted, PM abort, deauthentication delivered, cleanup
stages, key removals, slots retired, native return to changed-boot Gemian
`4ad62c4b-e0a1-4575-b9ac-23d85ab3c30d`. The single build arm is the
foundation for the measurement boots that follow.

Next boot: flow-control (station tree + its series), then pipelining,
autorate, lifecycle. Key reuse, rekey and reconnect remain disabled until
the lifecycle boot.

# Historical: single arm measured neutral; station-3 next with 0245 and 0246

[Station result](TX_STATION_RESULT.md): the consolidated single build arm
matches or beats the tree it came from (TX 1.192 Mbit/s, RX 9.85 Mbit/s,
median completion gap 1.11 ms). Station-1 never reached Wi-Fi (leaf read a
removed parameter, fixed by 0239). Station-2 ended early on two host-chosen
limits: the 1 MiB kernel ring wrapped past the leaf's data-window marker
(single-arm profiles now boot with an 8 MiB ring; 0246 demotes the two
per-frame slot lines) and the 4,096-pass lifetime quota ended the lifetime
before any teardown command (0245 removes it). Device returned to
changed-boot Gemian `135292c1-d711-46a4-855f-2ed92b3ff6c7`. No retry.

Next boot: station-3 (station profile + 0245 + 0246 + 8 MiB ring), expected
to repeat the throughput and complete the teardown with the host
acknowledgment accepted; then flow-control, pipelining, autorate, lifecycle.
Key reuse, rekey and reconnect remain disabled until the lifecycle boot.

# Historical: quiet-console measured; single-arm station candidate next

[Quiet-console result](TX_QUIET_CONSOLE_RESULT.md): with the driver unchanged
and only the serial console quieted, the median gap between TX completions
fell from 8.2 ms to 1.05 ms and the 12–25 ms population almost vanished;
TX 1.044 Mbit/s (+19 %), RX 8.02 Mbit/s. The remaining TX limit is the data
queue freeing the ninth frame unsent (proposal 0235 next). The run exposed a
teardown defect: a receive record framed for the other monitor state right
after the data-end monitor-control disable fail-stopped the lifetime before
any teardown command; proposal 0238 drops such records after data end.
The session host refused export (quiescence query exit 63); a separate
reviewed preservation sealed the complete log and returned the device to
changed-boot Gemian `d2d47ea1-90df-4845-9e8c-8ac1b1dff2b0`. No retry.

Next boots, one variable each, all on the retained kernel release string:
`mt6797-a53-wifi-station` (0234 single build arm + 0237 proven monitor
control + 0238; expected: same throughput as quiet-console, teardown
completes), then `mt6797-a53-wifi-flow-control` (+0235), then
`mt6797-a53-wifi-pipelining` (+0236). Key reuse, rekey and reconnect remain
disabled. Earlier handoffs below are historical and consumed.

# Historical: progress-aware yield installed; physical boot2 pending

[Depth-four result](TX_DEPTH_RESULT.md): TX 0.506 Mbit/s, RX 7.061 Mbit/s,
idle 84.3% / 77.3%, peak four owners, whole-ledger cleanup and status-0
transmitted deauth. Reviewed return independently confirmed changed-boot Gemian.
Consumed, no retry. Its measured TX gap clusters are approximately 4.2/31.8 ms.

[Yield comparison](TX_YIELD_COMPARISON.md): patch 0233 resets the no-progress
guard on successful frame submission or matched completion retirement. After
32 no-progress immediate iterations, pending work requests 1 ms; genuinely idle
work retains 20 ms. Existing HZ=250 means a one-jiffy nominal 4 ms short yield.
Depth four, fixed-rate descriptor, ledger, PID attribution, deadlines,
admission, management and key ownership remain unchanged. Actual-source
fixtures, ASAN/UBSAN, strict checkpatch and repository checks pass.

Validated build `1a4f291e` has byte-identical configuration to depth four.
Full boot2 `8014a0dd67c5cf5641ef4134fa5412bba971a4c93c095d48c60f02a95051ccae`
was written/synced/flushed and fully read back with matching SHA-256. Gemian
clean shutdown confirmed unreachable. Both offline constructors pass using
the genuine receipt; candidate and sealed host hashes verified at this
physical-handoff stage. No yield measurement has run; one attempt unconsumed.

Runtime `artifacts/wifi-throughput-yield-1`. After owner boot2 selection,
root launches `artifacts/wifi-tx-yield-work/hosts/throughput-run.py` with that
runtime and `--execute` exactly once, using Python 3.13. Live identity precedes
firmware start; five 1 s/1 MiB chunks per direction, prompt standard disconnect,
seal/export and reviewed return. Compute first-class gap histograms with
`summarize-throughput-completion-gaps.py` using the matching within-chunk filter.
Falsifiable TX target 2.5–3 Mbit/s; report partial/unmet result honestly.

Root retains device custody and final records; harness and analysis delegated.
No retry, rate change, DMA, rekey or protected re-arm. Reconnect closed,
safeguards dormant. Rate adaptation remains a separate following pass.

# Historical handoff: baseline 2 measured; bounded TX pump comparison

[Baseline 2 result](THROUGHPUT_BASELINE_2_RESULT.md): TX five chunks,
0.205740 Mbit/s, 87.525% aggregate idle, 959 completions/four nonzero.
RX unmeasured: inherited regular-file limit; offline streaming counter and
preflight fix pass. Prompt standard disconnect, whole-ledger stage 3 and
status-0 reserved deauth passed. Sealed evidence and independent changed-boot
Gemian confirmed. Baselines 1/2 and P2E-D1/D2 consumed, no repeat.

[Pump comparison](TX_PUMP_COMPARISON.md): patch 0231 adds bounded immediate
scheduling for pending work, idle/guard backoff 20 ms, at most 32 consecutive
immediate iterations. No depth, ledger, PID, deadline or admission change.
Default off except the new measurement profile. Validated Buildbox build
23745fe9 differs in config only by pump=y; RAM/DT unchanged. Final protocol:
five 1 s/1 MiB-cap chunks per direction, 100 ms gaps, nc data and SSH control;
2 MiB logger unchanged. Thirteen host fixtures and four retained-BusyBox
loopback cases pass. Exact candidate/readback and real receipt checks must
precede the one physical pump boot. DMA deferred; reconnect closed.

# Historical handoff: invalid baseline recorded; corrected run prepared offline

[Baseline 1](THROUGHPUT_BASELINE_RESULT.md) is invalid (SSH idle policy); no
rate claim. The independent first connection-loss teardown did not retire its
ledger. The [offline audit](LOSS_PATH_TEARDOWN_AUDIT.md) reproduces a driver
waiter candidate against actual installed source; firmware dropping group
removal is unproved because the host stopped before its credit bound expired.

[Corrected baseline 2](THROUGHPUT_BASELINE_2_PREDECLARATION.md): five 10 s/1 MiB
chunks per direction, chunk progress plus independent SSH keepalives, direction
CPU/netdev snapshots, prompt single EOS/quiescence-guarded standard disconnect,
honest whole-ledger/delivery verdict, seal and reviewed return. Ten measurement
fixtures and the actual-source waiter fixture pass; actual capture/session
constructors and installed-image input validation pass offline. One new boot
authorized by the owner's correction, no rebuild/image change; physical boot2
selection remains required. No retry of baseline 1 or either P2E run.
Reconnect closed, safeguards dormant; TX DMA still held on its contract.

# Historical handoff: PIO baseline consumed; returned to Gemian

[Baseline result](THROUGHPUT_BASELINE_RESULT.md): one unchanged-image boot,
join/DHCP/three pings/authentication passed. TX was interrupted by the retained
SSH server's 30-second idle policy: 842312 received bytes in 31.067 s,
invalid stalled transfer; no rate claim; RX and CPU idle unavailable. Missing EOS withheld the
standard disconnect. Later connection-loss teardown transmitted reserved
deauth status 0 but stopped on group-removal credit debt (-110); no whole-ledger
stage 3. Evidence sealed and independently rehashed; reviewed return and
independent changed-boot Gemian confirmation passed. No retry, build or image
change. The boot allowance is consumed; no further device action queued.
Reconnect remains closed, safeguards dormant. TX DMA remains refused on the
[unresolved transfer contract](DMA_TRANSFER_CONTRACT.md). Earlier handoffs below
are history, not an active test queue.

# Historical handoff: PIO baseline prepared; physical boot2 selection pending

[Predeclared throughput baseline](THROUGHPUT_BASELINE_PREDECLARATION.md): one
fresh boot, unchanged installed `3da69187` / boot2 `5f63e2d32fc0...`; join,
DHCP/three pings/SSH, device TX then RX up to 60 s each, software CPU/netdev
boundary counters, one EOS-guarded standard disconnect, whole-ledger stage 3,
sealed export/regression and reviewed return. Offline fixtures/constructors pass;
full installed-partition checksum verified read-only. No image change or build.
Prepared runtime: `artifacts/wifi-throughput-baseline-1`. One attempt only.

Reconnect is closed as a limitation, not a pending task. Do not reopen without
owner decision; 0229/0230 stay dormant. [DMA transfer contract](DMA_TRANSFER_CONTRACT.md)
requires refusal on unresolved bit-32 routing, ownership and error quiescence;
TX DMA implementation and comparison boot are held. RX DMA remains separate.
The baseline consumes the standing allowance only when executed; no baseline
result is claimed before the physical boot. P2E-D1/D2 remain consumed.
Earlier handoffs below are history, not an active test queue.

# Current handoff: probe pass closed; single-lifetime fallback and DMA/throughput next

[Probe-path result and authorized fallback](OBSERVABLE_RECONNECT_DECISION.md):
actual source rejects protected QoS-null in the native encoder; the sole internal
reserved owner blocks later data/deauth and reports completion as deauth. New
mechanisms would be required, so the one-pass timebox is closed. No admission
change, rebuild, install or boot. Retain the single-lifetime baseline; 0229/0230
stay dormant. No further reconnect design or WMT lifecycle work is pending.
The next Wi-Fi project is DMA/throughput under the roadmap. The one-boot
allowance remains unconsumed; P2E-D1/D2 remain consumed. Earlier handoffs are
history, not an active test queue.

# Current handoff: negative credit boundary; provider re-probe unavailable

[Offline boundary audit results](FIRMWARE_RESTART_BOUNDARY.md): released pages
precede key events by 5.059/1.079 ms; no credit/drain retirement proof exists.
No firmware stop/off counterpart is implemented. MAC `.stop` is host-only and
"firmware stopped" is a retained-state log. Provider re-probe was evaluated
first and refuses the retained `bound` owner; the built-in provider has no
remove lifecycle and suppresses bind attributes. NIC cycling keeps firmware
running and is not a boundary. New WMT stop/off work needs an explicit owner
decision and has not started. No available boundary today, no restart run
predeclared, no command, rebuild or boot. Reuse/rekey/re-arm stay refused;
0229/0230 remain dormant. The one-boot allowance remains unconsumed.
Earlier checkpoints below are historical.

# Current handoff: dormant host prerequisites; firmware decision pending

[Two offline tracks](TWO_LIFETIME_OFFLINE_TRACKS.md): 0229/0230 add unconsumed,
default-off host fence and PN-epoch helpers. Actual-source fixtures pass; no
admission or descriptor-provenance capability is added. The owner is producing
the four-handler event/credit, timer-cancellation and queue-flush evidence table.
Until it resolves, re-arm stays refused. No commands, build, installation or
boot; the one-boot allowance remains unconsumed. P2E-D1/D2 remain consumed.
Earlier checkpoints below remain history, not an active physical handoff.

# Current handoff: two-lifetime offline gate held before build

[Incomplete offline admission](TWO_LIFETIME_PREDECLARATION.md): actual-source
fixtures reproduce untagged key-event and old-descriptor attribution gaps if
protected reuse is enabled without a producer-retirement boundary. No production
re-arm, kernel build, candidate, installation or device action occurred. The
installed kernel remains `3da69187`; any eventual candidate needs a rebuild with
0228. No boot allowance is consumed and no physical selection is pending.
Reconnect remains open. P2E-D1/D2 remain consumed; do not repeat them.

# Current handoff: P2E-D2 complete; no further P2E boot

[Recorded result and offline follow-up](SESSION_0202_PLAN.md#p2e-d2-consumed--600-second-gate-pass-delivery-transmitted-cleanup-pass):
gate600s PASS, delivery status 0 TRANSMITTED, guarded disconnect refused by the
host interval, cleanup stage 3 whole ledger PASS. D1 and D2 are consumed; never
repeat either. Installed kernel/image are unchanged. The next device item is
an owner decision. [Second-lifetime prerequisites](SECOND_LIFETIME_PREREQUISITES.md)
remain offline. Earlier handoffs below are history, not a pending boot queue.

## Current: owner paused all work — status checkpoint

All implementation, builds and device work are paused at the owner’s request.
No device action or physical boot handoff is pending. Earlier handoffs below
are historical and consumed; do not execute them as current instructions.
P2E-1 stopped on host orchestration before Wi-Fi was reached. Its evidence is
preserved and the reviewed return independently confirmed changed-boot Gemian
`0d88c2d5-b21e-47fe-bf39-c95e896f724a`.

The fail-closed launcher correction is committed and Linux-validated; no further
attempt has run. Ten-minute received-traffic acceptance and same-boot reconnect
remain unproven. Key reuse, rekey and protected reconnect remain disabled.
Unrelated restored research is excluded from this status checkpoint.

---

## Latest: P2E-1 consumed — host launch failure, return confirmed

[One result row and analysis](SESSION_0202_PLAN.md#p2e-1-consumed--outer-launch-failure-and-late-start-refusal)
and [scalars](results/p2e-runtime-scalars.json) record the admitted attempt.
The added identity reader failed locally on a missing output directory; the
outer shell continued instead of failing closed. Bootstrap completed under the
capture's independent identity checks, but the leaf refused its existing
whole-second start limit before scan or any protected lifetime. SSH was never
reached. This is a host result, not evidence against the driver or a P2E pass.

All 61 seal entries, 1,978 contiguous log records, host quiescence and regression
verified before the original reviewed return. A separate authenticated check
confirmed changed-boot Gemian. No manual abort, retry or second recovery ran.

`laptop-run-ccmp-p2e.py` now replaces the ad hoc launch: create the identity
output first, fail closed on any acquisition/identity error, pass only the
fresh boot ID to the helper before bootstrap, and invoke the original failure
session once if capture refuses. It retains the original whole-second <=50
guard and every transport/data deadline. Local launcher tests and an actual
offline constructor fixture pass. Clean pushed input `c37baf06` passed all ten
launcher tests on Linux with no skips, including the actual retained collector
and a local child. The full Linux repository check passed. The constructor used
a historical receipt as an offline fixture only; it establishes no live readiness.
See the [launcher validation record](results/p2e-launcher-validation.json).
No new device attempt or physical handoff is admitted by this checkpoint.

---

## Earlier: P2E host-only preparation — before device admission

The owner authorized the separate [P2E evidence successor](SESSION_0202_PLAN.md#p2e-host-evidence-successor--preparation-admitted-execution-held).
Its reader retains all 602 planned arrival timestamps plus one excess-arrival
sentinel, and its refused-disconnect record includes the already acquired
PM-relative offset and unchanged bounds. The consumed P2 source and evidence
remain intact. P2E uses fresh `capture-ccmp-p2e` and `session-ccmp-p2e` paths,
the unchanged P2 image/leaf/classifier, and the existing custody and recovery
contracts. No new kernel, installation or device run is admitted.

[Validation](results/p2e-host-validation.json) on clean pushed input `e59f9370`
passed all 31 client tests on Linux with no skips, including real pipes beyond
244 arrivals, all 602 planned timestamps, fragmentation, excess arrivals,
partial timeout retention, PTY custody and eight actual generated guard-boundary
subcases. The original reader's 244-entry defect reproduces independently.
Routing/custody fixtures select the exact new helper, keep both 900-second log
decoders and preserve refusal on unknown local/remote owners. Repository checks
passed locally and on the clean Linux checkout.

This is host preparation, not a hardware pass or a live handoff. No kernel or
image was rebuilt, no installation or device operation ran, and no P2E runtime
receipt exists. A later execution needs its own admission, current device
identity, guarded installation/readback of the unchanged P2 image, real receipt
preparation and owner physical boot selection. Do not reuse an earlier boot
selection or start a P2E session while execution is paused.

Key reuse, rekey and protected reconnect remain disabled pending the separate
firmware queued-RX/key-retirement barrier. The ten-minute gate is still unproven.

---

## Latest: P2 consumed — host-limited duration; healthy cleanup and return

See the [single result row/analysis](SESSION_0202_PLAN.md) and
[scalars](results/p2-runtime-scalars.json). P2 authenticated SSH and retained
602 valid raw chunks over a 601-second remote schedule, but its host receiver
kept only 244 timestamp entries. The required >=600-second host receive span
and continuity are unproven. All initial/59 periodic pings passed; no device
duration failure was measured. The later helper abort refused at its interval
guard, exit 49; the exact rejected offset was not retained.

The unchanged leaf wall ended data at 718.184 seconds. Whole-ledger stage 3,
zero debt and deauth ACK passed separately; all 75 seal entries and 4,992
contiguous log records independently verified. The original reviewed return
and separate authenticated changed-boot Gemian check passed. No device work
or retry remains pending for this consumed run.

Next, follow the owner's separate private collection task before another
Wi-Fi lifecycle test. Keep its static admission, candidate, boot and evidence
separate. A later P2 successor needs the real-runner timestamp cap corrected
and tested beyond 244 chunks; it is not implemented by this result checkpoint.
Key reuse, rekey and same-boot reconnect remain disabled; ten-minute acceptance
and maintained Wi-Fi remain incomplete.

---

## Latest: P2 installed — new physical boot2 handoff pending

P2 source `1bbcaad8` passed the relevant Linux actual-source helper, leaf,
verdict, loader/binding and installer checks, including the final cold-start
boundary. The reviewed installer verified the predecessor, wrote boot2,
required matching full-partition readback and confirmed clean shutdown.
Complete actual offline host preparation passed with the scoped 900-second
log contract. No P2 capture or session has run; earlier boot selections are
consumed.

The [P2 predeclaration](SESSION_0202_PLAN.md) requires >=600 seconds of received
authenticated SSH, 59 periodic probes and standard disconnect requested at
PM +604..608 seconds. The validated kernel is unchanged; only the USB script
and bounded observer differ from P1D's RAM root. Verify those live hashes,
kernel notes, a fresh boot UUID, uptime and active logger before the one
capture/session. The leaf refuses starts after whole-second uptime 50 and
reserves >=130 seconds for quiescence/export/sealing. A late start is a host
admission result; do not silently retry it.

A new owner-operated physical boot2 selection with USB connected is pending.
After P2 testing and preservation/return, proceed with the separately requested
private collection task before the next Wi-Fi lifecycle test. Its design and
admission remain separate. Key reuse, rekey and reconnect remain disabled;
full maintained-Wi-Fi acceptance remains incomplete.

---

## Latest: P1D passed — ten-minute host-envelope preparation next

P1D's [row/analysis](SESSION_0202_PLAN.md) and
[scalars](results/p1d-runtime-scalars.json) record the full admitted gate:
121.136 seconds received SSH, all initial/periodic pings, 167 completed PID
reuses, prompt standard disconnect and whole-ledger stage 3 with deauth ACK.
The post-client snapshot took 0.602 seconds. All 75 seal entries and 3,283
contiguous records independently verified. The original harness and a separate
authenticated check confirmed changed-boot Gemian after one reviewed return.
No P1D device operation remains pending.

Next is >=600 seconds of received SSH and standard disconnect. Audit in the
existing session plan identifies necessary host limits, including the USB
server's 360-second hard connection cap and the boot-started logger's
600-second deadline/exact verifier. Prepare those coherently before a new
image/boot. Reuse the validated kernel: measured driver counts project below
its current caps; no driver deadline or cap change is justified. There is no
ten-minute candidate or physical handoff yet. Key reuse, rekey, same-boot
reconnect, supported ordinary crypto and minimal board acceptance remain open.

---

## Latest: P1D prepared — new physical boot2 handoff pending

P1H's [row and analysis](SESSION_0202_PLAN.md) and
[scalars](results/p1h-runtime-scalars.json) are committed at `c1a100cb`.
The >=120-second received SSH gate passed; its prompt-disconnect gate failed
on a half-second host snapshot timeout. It later reached clean whole-ledger
teardown at the admitted leaf wall, with 167 completed ordinary PID reuses.

P1D host input `2da1f41b` corrects only that software snapshot envelope and
bounded terminal-wait USB progress. All 22 helper tests and actual leaf/gate
fixtures passed on clean Linux; syntax, ShellCheck, retained-source/binding
and repository checks passed. The kernel/package/profile and boot artifacts
are unchanged. The reviewed guard verified the matching full partition,
skipped writing, preserved a separate deployment seal and confirmed clean
shutdown. Complete actual offline host preparation passed.

One new owner-operated physical boot2 selection with USB connected is now
pending. No P1D device session has run; earlier selections are consumed.
Require a fresh UUID and the exact P1 kernel-notes identity before the one
capture and one session. This run still requires >=120 seconds of received
SSH and a prompt standard disconnect under the unchanged time/ownership
gates. Only after that gate passes proceed toward 600 seconds. Key reuse,
rekey and reconnect remain disabled; full usable-Wi-Fi acceptance is incomplete.

---

## Latest: P1H consumed — SSH duration passed; host control gate failed

See the [single row](SESSION_0202_PLAN.md) and
[scalars](results/p1h-runtime-scalars.json). SSH exited 0 with 243 chunks
received across 121.090 seconds; initial 3/3 and periodic 11/11 pings passed.
The next first failure was the source-pinned 0.5-second post-client USB
snapshot. Without a verified open-window snapshot the helper correctly sent
no disconnect. The full planned session remains FAIL.

The original host refused recovery while a child remained live. After the
admitted leaf wall, independent read-only observations confirmed quiescence.
Eventual supplicant teardown ended data at 298.704 seconds with deauth ACK,
whole-ledger stage 3, no debt and 167 completed ordinary PID reuses. All 90 seal
entries/3,283 contiguous records verified before one reviewed recovery. A
separate authenticated check confirmed changed-boot Gemian. No retry ran.

Next: correct only the host snapshot envelope and bounded terminal-wait USB
progress, retaining all driver/firmware/control-time gates. Validate the actual
host paths, then prepare a separate fresh boot handoff. The 120-second stream
is demonstrated; prompt standard disconnect remains the failed gate. No
600-second or same-boot reconnect claim is established.

---

## Latest: P1H ready; waiting for a new physical boot2 selection

The P1 result is committed at `24f9ba08`. The corrected host envelope and
its exact pins are pushed at `15d4cf5e`, with separate P1H deployment evidence
at `5cfb7b24`. The Linux actual-leaf/progress and binding checks, syntax,
ShellCheck, local retained-source/config fixtures and repository checks passed.
No kernel changed or rebuilt: boot artifacts and full boot2 checksum are
byte-identical to the installed P1 image. The guard verified that match,
skipped writing and confirmed clean shutdown; offline host preparation passed.

One new owner-operated boot2 selection with USB connected to the custodian
is pending. P1's earlier reply is consumed. There has been no P1H device test.
Require a fresh UUID, exact kernel-notes identity, one capture and one session.
The test still requires >=120 seconds of received SSH traffic, completed PID
reuse and standard disconnect. Stop at any earlier first failure, preserve it
and retain independent duration/network/cleanup verdicts. No private firmware
mechanism or offset-avoidance rule is inferred.

---

## Latest: P1 consumed; host maximum-duration defect

P1's [single table row](SESSION_0202_PLAN.md) and
[scalars](results/p1-runtime-scalars.json) supersede earlier pending handoffs.
It authenticated and received 116 ticks across 57.563 seconds, then the
server's retained `-M 60` limit closed SSH. The 120-second gate failed.
Standard early disconnect reached whole-ledger stage 3 with reserved PID 127
acknowledged at PM +64.189 s. Ordinary PID reuse was measured: 32 completed
reuses, all 158 allocations completed. Six periodic probes passed through
PM +60 s; the other five were not reached. No HIF refusal or monitor-loss event.

The original seal/recovery gate correctly refused a nonzero supplicant count.
After bounded read-only classification, a preservation-only continuation
revalidated child quiescence and all evidence before one reviewed recovery.
All 89 seal entries and 2,740 contiguous records verified. An independent
check confirmed changed-boot Gemian. There is no pending device operation.

Next: correct the host listener maximum-duration limit and USB progress
envelope on the unchanged installed P1 image, with focused actual-leaf tests,
then make a new explicit physical boot2 handoff for a separate 120-second run.
Do not count P1 as a duration pass or retry it silently. The exact +63-second
comparison remains unexecuted; offset correlations establish no timing rule.
Key reuse, rekey, reconnect and ten-minute acceptance remain unproven/disabled.

---

# Wi-Fi resume checkpoint — INCOMPLETE

**P1 installed and prepared; waiting for a new physical boot2 selection.**
Kernel input `71c4b4a8`, bindings `2ec08e59`, final host test `7dc1d496`.
[Current handoff](SESSION_0202_PLAN.md#p1-handoff-ready--physical-boot2-selection-pending).
All Linux source/host checks, twenty client cases including real PTY, the single
kernel build, package/composition validation, guarded installation/full readback,
clean shutdown and fresh host preparation pass. Full boot2 checksum
`f19d4e27bd24fc38b091c8847440c051f83e92da3972865125ae4c0a0589e998`;
[actual receipt](results/ccmp-stable-monitor-candidate-p1.json).
No P1 capture/session or result exists. Require a fresh mainline boot UUID and
exact 84-byte kernel notes
`b0213c37e6080b8b334f73842ca3162390cdfeecb29d8eb93bd41d2c2bf9b160`
before the one admitted run. Do not reuse the consumed I50 physical reply.
The P1 hypothesis is sustained initial-key traffic with completed ordinary-PID
reuse and standard disconnect: 243 absolute half-second chunks schedule 121 s,
requiring at least 120 s of live client receipt span, eleven periodic probes,
verified remote/local quiescence and whole-ledger/ACK cleanup. First failures,
including an early host abort, remain separate; no shorter-duration pass or
wire-generation/key-retirement inference. Full Wi-Fi acceptance is unfinished.

**I50 consumed once: duration/network/acknowledged cleanup PASS; SSH NOT REACHED.**
Boot `e8a4c5ca-1fda-42ad-a0f7-1b68e99c08f7`, kernel `00f351eb`, bindings
`eca5e7dd`, handoff `6908713d`. [One row and analysis](SESSION_0202_PLAN.md#i50-consumed--acknowledged-idle-tail-teardown-ssh-not-reached),
[one scalars file](results/i50-runtime-scalars.json). Data budget 50.005 s,
initial 3/3 and periodic 4/4 replies, release credit and whole-ledger stage 3
pass. Reserved deauth ACK followed a measured 10.099-second data-completion
idle gap; this weakens idle-only causation without identifying a mechanism.
The host helper refused the I50 namespace before client/TCP; no SSH result or
host ACK exists. The exact child-CLI guard is reproduced offline. The immutable
full-session verdict remains false. All 62 seals, 2,134 contiguous records,
eight available cycle frames, quiescence/regression and reviewed return verify.
Independent Gemian `0ad152bc-0456-4298-82d2-eb50d09ada81`. No pending physical
action or unchanged I50 retry. The narrow host admission correction and its
seven actual-main cases pass from clean pushed inputs on Linux.
[Connected-lifetime/PID/accounting/monitoring source](SESSION_0202_PLAN.md#connected-source-prepared--build-input-validation-pending)
has passed clean Linux source fixtures and the required kernel build.
[The real P1 package/candidate and host protocol](SESSION_0202_PLAN.md#p1-built-and-composed--complete-host-validation-before-deployment)
are composed and now pass clean Linux host checks, guarded deployment/full
readback/shutdown and fresh preparation, as recorded in the current handoff
at the top. No physical P1 selection has been consumed yet. Key reuse/rekey/reconnect remain
disabled and full Wi-Fi acceptance remains incomplete.

**S1 consumed once: controlled core disconnect and 20-second SSH stream PASS.**
Unchanged GTK8 image, boot `cff2c4f8-466d-406b-a7ad-d9f1e8bfee1e`; host inputs
`2a197328`, handoff `f12da769`. [One row and analysis](SESSION_0202_PLAN.md#s1-consumed--ssh-stream-and-standard-disconnect-pass),
[one scalars file](results/s1-runtime-scalars.json). DHCP, initial 3/3 and
post-release periodic 5/5 pings pass. Fresh authenticated SSH produced five
chunks spanning 20.450 seconds across the +6.252 s channel-release credit;
client exit 0, no stderr. Standard disconnect accepted near PM +55.6 s ended
data with reason `disconnect`, elapsed 55.502 s. This planned stop is not a
full 60-second duration pass. PM abort, acknowledged deauth and all remaining
cleanup commands completed; whole-ledger stage 3, zero debt, local disables 0.
No HIF refusal, capacity stop or 0x13 event. Owned-beacon admissions were stale;
no continuous-beacon claim. All 75 seals / 2,202 contiguous records, one-cycle
export, remote/local/device quiescence, regression and one reviewed return
verify. Independently confirmed Gemian `9dac50f6-816c-4c08-981d-79535cb56f69`.
No physical action or S1 retry is pending. No S1 kernel build/change occurred.

The I50 preparation/handoff and S1 successor plans below are consumed history;
use the current I50 result at the top. The connected-lifetime source archives are prepared but unbuilt; longer-window
admission still needs the source and host gates above.

**GTK8 consumed once: finite capability, post-release protected traffic,
60-second duration and whole-ledger host cleanup PASS.** Boot
`a996ec5e-fc20-49d3-a160-2ed321e3e156`, kernel `8792a406`, bindings `49ff0b1c`,
handoff `b9555ddf`.
[One row and analysis](SESSION_0202_PLAN.md#gtk8-consumed--protected-traffic-beyond-the-join-privilege),
[one scalars file](results/gtk8-runtime-scalars.json).

The 9,000 ms join privilege was submitted for release at PM +6.275 s and
credited at +6.300 s (25.016 ms, no deadline extension). All five periodic
probes replied beyond that credit and the original reported grant horizon;
owned successful data completions continued through PM +50.296 s. The window
ended by budget at 60,009 ms. DHCP, three initial pings and SSH exit 0 in
1.397 s passed. SSH authenticated **before** release and closed; no maintained
post-release authenticated stream is claimed. Checked PTK/GTK 42/231, GTK ARP
handoffs 106, withheld 0. No HIF refusal, capacity stop, pre-budget AP loss or
0x13 event. Standard scan acceptance remains open.

PM abort credited first; reserved deauth PID 40 still missed 750 ms and later
returned status 5 during removals. No ACK or invented refund. The ledger
returned whole at station removal; cleanup skipped a second channel abort and
credited BSS-off at floor zero. Host stage 3, zero debt, local key disables
status 0. This is host cleanup success, not acknowledged deauth or independent
firmware key/queued-RX retirement. Owned-beacon admissions were 21 total/20
since PM, last age 58.114 s; do not infer continuous beacon delivery or RF loss.

All 71 seals and 2,186 contiguous records, complete one-cycle export,
helper/device quiescence, regression and one reviewed return verify.
Independently confirmed Gemian `4f0120ad-fa64-462a-82d3-c2c3f9b0a30e`.
Two read-only identity invocations preceded the one capture/session: the first
used the SSH helper incorrectly and exited nonzero; the corrected stdin
invocation verified identity. No radio/session retry. No live device process
is pending for GTK8, which is consumed; S1 is also consumed as recorded above.

The S1 preparation/handoff above is historical and consumed; use the current
S1 result at the top for the next source decision.

Prior GTK7 result follows as history; its successor below is now consumed.

**GTK7 consumed once: capability and 60-second low-traffic duration PASS;
whole-ledger cleanup stage 3 reached, deauthentication still unacknowledged.**
Boot `138674d4-2aff-4ff5-ad75-a0670d432b36`, source `8aed6b61`, tooling
`cd1a81ef`, handoff `1cfeb81e`.
[One row and analysis](SESSION_0202_PLAN.md#gtk7-consumed--whole-ledger-cleanup-with-late-deauthentication),
[one scalars file](results/gtk7-runtime-scalars.json).

Data ended by budget at 60,011 ms. DHCP, initial three replies, SSH exit 0 in
1.618 s and all five periodic numeric-router probes passed. Checked PTK/GTK
41/238; GTK ARP handoffs 107, withheld 0; no named HIF refusal or 0x13 event.
Every owned TX completion and cleanup command timestamp is exported relative
to the 0x16 credit. No continuous SSH-traffic claim is made. Standard scan
acceptance remains open; the passive-scan classifier reports no standard BSS.

PM abort credited **before** reserved deauth. PID 41 still missed 750 ms and
was retired with one page debt, without ACK/refund. Removals proceeded under
the existing 100 ms bounds. The ledger returned whole during station removal;
late retired completion status 5 followed. Channel abort/BSS-off credited at
floor zero; healthy stage 3, `deauth=0`, both local disables status 0. This is
whole-ledger cleanup with an unacknowledged frame, not a bounded-debt terminal
or timely deauth success. PM-abort-first did not cure the missing completion;
periodic traffic also changed, so unique causal attribution is unavailable.

Owned-beacon admissions at data end: total 21, since PM 20, last age 58.162 s.
Do not claim continuous beacon delivery or infer RF loss from this counter;
phase-1 type-7 total 110 is not an owned-beacon count. All five periodic pings
replied, so the predeclared fixed-offset host-TX failure trigger did not occur.

All 71 seals, 2,185 contiguous kmsg records, complete one-cycle export,
helper/device quiescence and A53 regression verify. One reviewed return and
independent Gemian identity confirm `78b701cf-cb65-4283-bc32-dbe7dadb5497`.
GTK7 has no live device process or retry pending and is consumed; the new
GTK8 physical handoff is recorded above.
A default-off [connected-channel comparison](SESSION_0202_PLAN.md#after-gtk7--bounded-connected-channel-ownership-comparison)
is prepared under 0217: a nine-second join grant released during the unchanged
60-second window, original command/frame/tail limits, periodic traffic and
GTK7 teardown. Local and Linux actual-source/option-off/HIF fixtures and the required
Buildbox build pass at `8792a406`; [GTK8 package/host bindings](SESSION_0202_PLAN.md#gtk8-validated-package--host-binding-validation-pending)
are prepared from the validated package. Five host fixtures and the
strict post-release verdict pass locally and on Linux. Guarded installation
and offline host preparation now pass; physical GTK8 selection is pending
as recorded above. No GTK8 hardware observation is claimed. Two/ten minutes of authenticated SSH traffic and same-boot reusable
lifetimes remain unproved.

Keep 0x16 before keys, counter-only 0210/fatal event refusal, connection-monitor
flag, no nullfunc, existing frame/command deadlines and resource caps. No PID
or key reuse, rekey or reconnect. Keep publications on `main`; preserve public
measurements and exclude firmware-RE explanations/private source identities.

Earlier GTK6 command-path credit with one retained page and its whole-ledger
stop remain recorded in the [prior analysis](SESSION_0202_PLAN.md#gtk6-consumed--command-path-credit-with-a-retained-page)
and [scalars](results/gtk6-runtime-scalars.json). Do not repeat it unchanged.

GTK1's prior ERANGE is classified and its [0205 correction](../../patches/proposals/0205-wifi-mt6797-retain-the-validated-channel-grant-horizon.patch)
is proved to permit the requested data budget in GTK2. GTK1 had both keys
submitted/credited before refusal and lacked healthy cleanup; it did not test
GTK/network/SSH. Earlier intermittent SSH silence remains unclassified. D3 and
GTK2 both resolved an initially absent neighbor without proving how.

The [reviewer reassessment](SESSION_0202_PLAN.md#reviewer-reassessment-before-further-implementation-or-any-build)
corrects the all-`0xc200` premise: C11's 32 eligible groups required `0xc000`.
Expanded 2,718 actual-source cases and eleven paired-helper cases pass locally
and on Linux from clean pushed input `f45b7645`. The owner adopted group-first
preparation. The independent 60-second window and permanent standard client
stderr/netstat retention passed locally and on Linux at `5b92d39a`.
The strict initial-GTK context/checker is implemented under the
[predeclared source contract](MAC80211_GROUP_RX_CONTRACT.md#predeclared-initial-gtk-preparation).
Its actual-source fixtures pass locally and on Linux from clean pushed input
`4bde0dbf`, including canonical overlay compatibility and seven standard-client
cases. See the source contract for scope and deliberate checkpatch exclusions.
No hardware GTK acceptance or SSH-cause proof is claimed. Preserve strict
PN/integrity/ownership requirements.
0202 remains separate and unbuilt. The owner resumed regular builds/tests;
0203/0204/0205 ran as GTK2 and the admitted capacity successor is built. Keep one scalars
file and one table row per future run; no per-run result documents. No -48
adjustment, longer transaction deadlines, rekey, reuse or reconnect.

Prior framing result: [D2](SSH_D2_RESULT.md) consumed once on unchanged C10.
Port 0 advertised 94, staged descriptor 142; complete advertised PIO transfer
then equality refusal/poison/no-copy. Fault at ENABLE_PENDING, branch 4/-71,
23.238 ms after data-phase log, not a timeout. DHCP/pings/SSH and all local
queries were not reached. Healthy cleanup failed; one page debt retained.
Seal/quiescence/A53 regression and changed-boot Gemian independently verified.
C10 remains installed but consumed; no physical selection is pending.

The [bounded RX contract review](D2_RX_CONTRACT_REVIEW.md) verifies exact C10
source, TX-only arm quiescence and retained pre-arm WHISR 0x2. Public gen3 mapping
suggests an RX indication; this is not a FIFO/producer fence. New enable-time
+48 differs from historical close-time -48. The actual-source regression now
covers 94/142 on both ports, valid 94 and I/O faults; local ASan/UBSan passed.
No host framing correction is proved. The [follow-up source review/proposal](RX_FORMAT_OWNERSHIP_SUCCESSOR.md)
selects one fixed-format ownership comparison: initialize before scan-ready,
retain the format for the firmware instance, keep data-window/crypto gates.
Exact C10 EAPOL headers passed 48 existing cases on Linux with ASan/UBSan.
The [0202 prototype](FIXED_RX_FORMAT_PREPARATION.md) is implemented and passes
1482 ASan/UBSan cases plus RX/option-off comparisons locally and on Linux.
The separate approved 0203 window patch passes actual-source boundary/parity
checks. Final strict patch review has only the intentional missing DCO sign-off.
The old A/B plan is superseded: no further ARP-pair boot. Initial GTK plus the
independent window is next; no kernel build or execution is admitted.

The [three-run C10 baseline](CCMP10_BASELINE.md) remains SSH 2/3, all its finite
transport/network/host-cleanup windows passed. [D1](SSH_D1_RESULT.md) passed
without reproducing failure. Exact earlier TCP/KEX/auth failure stage remains
unknown; D2 does not classify it. [C11](CCMP11_RESULT.md) did not enable GTK.

Keep equality, complete transfer, poison/no-copy; no -48 adjustment, longer
transport deadline, speculative register or unrelated callback RE. GTK delivery
remains disabled on tested images; the default-off prototype is unbuilt. Rekey,
reuse and reconnect stay disabled. Staged 60 s / 2 min / 10 min and full
Wi-Fi acceptance remain incomplete. The pause record below is historical.

Historical pause boundary. The owner explicitly resumed implementation on
2026-10-17; see the [completion successor](CCMP_COMPLETION_SUCCESSOR.md) for
the new source/evidence review and candidate gates. The frozen C5 result and
old launch commands below remain consumed, not repeatable instructions.

**Owner stopped work after the single CCMP5 test and reviewed return. This
checkpoint authorizes nothing beyond preserving the record.** No driver work,
tests/builds, analysis execution, candidate selection or device action resumes
automatically. No unchanged C5 retry. No next candidate or fix is decided.

## Read these records, not the old launch commands

1. [CCMP5 result](CCMP5_RESULT.md): earlier -110/branch1 timeout, one checked
   Ethernet queue, no DHCP lease/SSH/full pass, no observed HIF refusal. Exact
   frozen kernel/profile/package/receipt/tool/deployment/boot identities and
   evidence seals are there; the deployment's full checksum is custodian-verified
   supplemental metadata, not a copied deployment record or new live inspection.
2. [CCMP5 preparation](CCMP5_PREPARATION.md): package/composition/receipt pins
   and tooling bindings; historical instructions are consumed, not a new run.
3. [0195 controlled comparison](RUNTIME_NO_POST_PROPOSAL.md): exact source,
   patch/body, two MAC entry points, preserved boot-reader post metadata and
   boot-drain invariants, focused actual-source tests and causal limits.
4. [C4 result](CCMP4_RESULT.md) and [C3 result](CCMP3_RESULT.md): finite WPA2/
   DHCP/one-ping progress, no SSH ACK/full pass, later post-CLOSED gap48. C4's
   staged0x4000 is an untrusted hint, not a certified packet/producer identity.

Latest executed tooling is `0f70e74bcd0d1fcafa4b47f8e94996e04cedc65a`; immutable
kernel input is `ea1fc0056738453a6e0d76cbea1d82db7ebbea48`; source85d1d621.
This documentation checkpoint does not require another kernel build. Candidate,
receipts, completed tools and prior evidence remain unchanged.

## Preserved state and boundaries

- Last confirmed current OS: Gemian3.18.41+/aarch64, changed boot
  `d09f829e-2a7e-4b5f-a240-b718c63f26ff`. Boot2 retains full C5
  `776cccbe841af9e36ccf981f19ec30456c61b819c6fa3d113dcd59c59533b812`.
- One capture/session, one reviewed return, helper/device children quiescent,
  full log preserved and63-entry seal verified by the custodian. See result for
  exact hashes and independent-verification scope. No pending retry is owed.
- Previously proposed bounded analysis remains **UNEXECUTED / HOLD**; it is not
  an approved next action. No new output or producer mechanism is established.
- Maintained Wi-Fi is incomplete: normal-mode per-frame PN/integrity/replay,
  key-epoch retirement/GTK/rekey/reuse, transport/resource/lifetime reliability
  and clean-profile ten-minute acceptance are unresolved. See the existing
  [support matrix](../../docs/HARDWARE_SUPPORT.md) and
  [roadmap](../../docs/ROADMAP.md); this checkpoint does not promote support.

## Next decision, only after an explicit owner resume

First review the **recorded earlier timeout and the read-sequence comparison**:
what stopped branch1 before the C3/C4 comparison point, which required evidence
is actually present, and which explanations remain unproved. Absence of a later
refusal cannot discriminate a repair when the trial terminates earlier. That
decision is not an instruction to boot, build, scan, add observers, relax RX or
retry C5. Resolve scope and review a concrete next proposal before new effects.

Keep one custodian for any eventually admitted device work; retained identities
are not fresh live checks. All safety/boot2/evidence/finite-budget/one-return
rules remain mandatory. Until the owner resumes: **HOLD**.
