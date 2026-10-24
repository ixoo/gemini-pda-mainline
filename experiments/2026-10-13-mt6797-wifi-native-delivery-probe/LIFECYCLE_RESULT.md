# Lifecycle boots 1 to 10: each boot takes the second lifetime one stage further

Result record, 2026-10-24. One boot on the `mt6797-a53-wifi-lifecycle`
profile (pipelining tree plus 0240 re-arm, 0241 loss reason, 0243) under
the two-cycle host harness: each cycle is a scan, join, DHCP, three pings,
the five-chunk TCP protocol in both directions, host acknowledgment and the
standard disconnect; the leaf then waits for the driver's re-arm record
before selecting the network again. Build input `88f5edaf`, boot
`8dac7669…`, candidate `519581a8…`, boot2 `10978b3c…`, admitted at 6.4 s
uptime.

Runs before 2026-10-24 booted an inherited `board.dtb` that no build produced; proposal 0261 reproduces it from source and the [equivalence boot](DEVICE_TREE_PROVENANCE.md#equivalence-boot-passed-2026-10-24) confirmed the series' results stand on it.

## Cycle 1: pass

| Direction | cycle 1 | pipelining | vendor |
|---|---:|---:|---:|
| TX, host received | 3.108 Mbit/s (chunks 3.93–4.22) | 3.198 | 14.59 |
| RX, host sent | 6.60 Mbit/s (device chunks 15.5–17.5) | 7.63 | 31.54 |
| CPU idle TX / RX | 84.8 % / 76.3 % | 85.8 % / 77.6 % | — |

3,743 completions, 2 failed, median gap 0.44 ms; data phase 24.5 s by the
leaf's disconnect; PM abort, deauthentication delivered, stage 3 with
credits returned and slots retired, both key removals, disable `status=0`,
loss report `source=cleanup reason=0 class=host` (0241's first record),
then mac80211's `Connection to AP lost`. Quiescence proven for the cycle.

## Cycle 2: never started

After the station teardown the driver logged nothing for the remaining
eleven minutes: no `join rearm`, no `rearm refused`, no `rearm wrap`, no
fail-stop. The leaf's re-arm wait ran to its wall (`cycle=1 rearm=absent`),
the harness recorded `cycles_started=2 cycles_passed=1`, the classifier's
first failing gate is `rearms` (0 observed, no fault), and the session
sealed the complete log (24,998 records) and returned the device to
changed-boot Gemian `af877fc7-8235-4b32-b57e-08e6360c9c15`.

**Cause, from the built tree.** The re-arm pass is queued from two
places. Proposal 0240 unlocked the worker's rendezvous site for the stable
epoch, but no worker pass runs after a retired terminal. The other
requester, the mac80211 station-removal callback, still required the
stable epoch to be off and the old two-lifetime cap, so it never queued
the pass. Proposal 0248 drops both gates there and requires the healthy
stage-3 cleanup to be done already (so a teardown arriving first cannot
log a false refusal; the worker's site keeps that order). Everything else
in this boot, including 0243's and 0241's new records, behaved as
specified. Next boot: the same harness on the lifecycle tree plus 0248.

## Lifecycle boot 2 (0248): same outcome, and the real cause

Build input `d67f3fd7`, boot `7b768cda…`, boot2 `76adce93…`, admitted at
8.0 s. Cycle 1 passed again (TX 2.922 Mbit/s, chunks 3.61–3.98; RX
6.75 Mbit/s, device chunks 16.8–17.5; 3,733 completions, 5 failed, median
gap 0.48 ms; teardown complete), then the same silence: no re-arm, no
refusal, no fault; `cycles_started=2 cycles_passed=1`; sealed (24,950
records); returned to changed-boot Gemian
`c5c2c830-6bc4-48b1-8841-aa81f53c2383`.

Both logs order the end of the lifetime the same way: the supplicant's
local deauthentication, the data-phase end, PM abort, the stage-3
terminal, then mac80211's two key removals about 11 ms later, then the
connection-loss notice. The key-removal callback waits for the healthy
cleanup, logs, and cancels the join worker synchronously before the key
is freed. The terminal had just queued the re-arm pass with a 20 ms
delay, so the cancel discarded it while its pending flag stayed set, and
the station-removal site that 0248 unlocked then saw a request already
pending and queued nothing. 0248 removed a real gate but was not
sufficient. Proposal 0249 re-queues the pass after that cancel when a
re-arm is still pending and the lifetime is neither closed nor poisoned;
the pass keeps its rendezvous, quiescence and wrap rules. Next boot:
lifecycle-3 with 0249.

## Lifecycle boot 3 (0248 + 0249): the re-arm fires; the second scan refuses a notice

Build input `88fd578a`, boot `6ec6eedd…`, boot2 `2bd8396d…`, admitted at
8.8 s. Cycle 1 passed (TX 3.156 Mbit/s, chunks 3.95–4.28; RX 6.33 Mbit/s,
device chunks 15.8–17.1; teardown complete). This time the driver logged
`join rearm: lifetime=1 token=2 sta_seq=21 sequence=35` 0.2 ms after
mac80211's connection-loss notice, the leaf saw it (`cycle=1
rearm=present`, `enable_network=OK`), and cycle 2 selected the network.

The second scan was admitted 4 s later and refused 28 ms after that: the
firmware answered it with the same 12-byte BSS absence/presence notice
(id 0x11, sequence 0) that the join path now counts, but the scan's event
consumer knows only the done header, the debug event and the sleepy
notification, so it logged `unknown event … id=0x11` and retired the scan
with `status=-71`; the channel request that followed was refused for
lack of a scan (`config=-95`) and the lifetime stopped there
(`cycle=2 data_phase=fault_or_timeout`). The first lifetime's scan never
meets this notice because it runs before any BSS exists. Harness:
`cycles_started=2 cycles_passed=1 rearms_observed=1`; sealed (27,578
records); returned to changed-boot Gemian
`cd90a4fb-d0d6-464d-b635-cb75b0f61aca`.

Proposal 0250 admits the notice in the scan consumer (logged once with
its four body bytes, then ignored); every other unknown event stays a
fault. Next boot: lifecycle-4 with 0250.

## Lifecycle boot 4 (0248–0250): the second lifetime joins; a late key removal closes it

Build input `2fea15db`, boot `09ce9685…`, boot2 `e65967a1…`. Cycle 1
passed (TX 2.59, RX 5.59 Mbit/s). The re-arm fired, the second scan logged
the BSS notice twice (`body=00010200` while scanning, `00000000` after the
done header) and completed, the channel grant, authentication, association
and station activation (`lifetime=2`) all succeeded, and beacons were
delivered. The handshake then never completed: both EAPOL candidates were
refused, the PM connection step reported `attempted=0 … dtim_status=-61`,
and mac80211 gave up (`failed to move station … to desired state`).

The cause is in the 300 µs around the re-arm. mac80211 removes the two
keys one after the other, each removal cancels the join worker, and the
re-arm pass had been queued by the terminal and re-queued after the first
removal (0249). It ran 90 µs after the first removal and 170 µs *before*
the second, which then waited for a cleanup the epoch reset had already
cleared, timed out (`ccmp-stable disable … status=-110`) and withdrew the
new lifetime's receive path, so no EAPOL frame could be admitted.

Proposal 0251 counts mac80211's key removals per epoch and defers the
re-arm pass, request kept pending, until both have been seen; the second
removal re-queues it. Everything the second lifetime did reach, from the
scan through activation, now behaves as the first. Harness:
`cycles_started=2 cycles_passed=1 rearms_observed=1`; sealed (26,198
records); returned to changed-boot Gemian
`3f113be8-5bf7-457a-a6eb-29637d099d00`. Next boot: lifecycle-5 with 0251.

## Lifecycle boot 5 (0251): the re-arm is refused as a wrap on a cyclic PID

Build input `b7558043`, boot `cf5a925e…`, boot2 `33e1f785…`. Cycle 1
passed (TX 2.482 Mbit/s, chunks 3.11–3.34; RX 5.62 Mbit/s, device chunks
11.0–12.3; teardown complete, both key removals seen), and the re-arm
pass then refused: `join rearm wrap: token=1 sta_seq=20 sequence=35
next_pid=82`, which poisons the lifetime. The leaf saw the fault
(`cycle=1 terminal=fault_or_timeout`), the classifier's first failure is
that record (`no_fault` gate), sealed (25,715 records), returned to
changed-boot Gemian `9b35a4fa-ef15-4ac0-a276-298a887a6f2f`.

The join PID counter is synced from the data PID pool, which cycles
through its range during every data phase and restarts with the epoch,
so its value at the terminal is wherever the last data frame left it:
10 and 15 on boots 3 and 4, which passed the readiness check's
`next_pid > 63` clause by luck, and 82 here. Proposal 0252 drops that
clause; the wrap rule keeps the channel token, the station sequence and
the command sequence, the boot-scoped identities it was written for.
Next boot: lifecycle-6 with 0252.

## Lifecycle boot 6 (0252): the first lifetime stops on an expired data slot

Build input `2d80832a`, boot `fad2ec53…`, boot2 `96bf3ce7…`. This boot ran
on the weakest link of the series (TX 2.395 Mbit/s, chunks 2.9–3.2; eleven
failed frames). Twelve seconds into the data phase, during the second
receive chunk, the worker's deadline check found a data slot whose TX
status had not arrived within its 750 ms deadline and stopped the
lifetime (`join stopped: status=-110 … branch=1`, credit observation
`site=2`, 8 frames unaccounted, one slot pending). The leaf then saw no
host acknowledgment (`cycle=1 host_ack=absent`), the harness recorded
`cycles_started=1 cycles_passed=0`, sealed (15,347 records), returned to
changed-boot Gemian `e55151bd-490f-44f8-bbfe-26ffb2937f65`. The re-arm
gates fixed by 0248–0252 were never reached; nothing is known about them
from this boot.

Every earlier boot of the series had zero unaccounted frames, so the
expiry is new, and it is a lost frame rather than a protocol fault.
Proposal 0253 retires an expired slot before the deadline check: the
frame is reported to mac80211 unacknowledged, counted as failed and with
the consecutive failures that end the data phase, and a late status for
its PID stays counted as unowned. Next boot: lifecycle-7 with 0253.

## Lifecycle boot 7 (0253): two lifetimes on the device; the host's 5 s admission guard

Build input `e22d9838`, boot `3280ef7c…`, boot2 `10a1b156…`. Lifetime 1
passed (TX 2.47 Mbit/s, RX 5.71 Mbit/s, teardown complete, both key
removals), the re-arm fired, and the second lifetime ran end to end on
the device: scan with the BSS notice logged and ignored, channel grant,
authentication, association, activation as lifetime 2, DTIM latched,
power management credited, the four-way handshake, both keys installed,
the data phase (the leaf's DHCP bound, listener ready, three pings
answered), its end by disconnect, the stage-3 cleanup with credits
returned, both key removals, and a further re-arm afterwards, which the
driver allows since 0240 removed the two-lifetime cap. The supplicant
counted two complete handshakes and two connected events in one boot.
Sealed (26,356 records); returned to changed-boot Gemian
`ca90fb06-5313-4e55-9b75-e7d4b65d97c5`.

What did not happen is the host's cycle-2 measurement. The per-cycle
exchange script requires the exchange to begin within 5 s of that
lifetime's PM credit clock, the stream-admission rule inherited from the
stable-monitor protocol; cycle 1 met it (ready seen 4.4 s after the
clock), cycle 2 did not (the host saw the leaf's ready marker 11.8 s after
its wait began), so the script exited before any traffic, the leaf's
acknowledgment wait ran out and the lifetime ended by disconnect without
throughput. The classifier also still expects exactly one re-arm. Both
are harness contracts, not driver behaviour: the next run widens the
admission bound for the second cycle and accepts the trailing re-arm.
The driver side of the plan's second-lifetime item is demonstrated.

## Lifecycle boot 8: two lifetimes measured; the device logger's 2 MiB cap

Same image as boot 7 (build `e22d9838`, boot2 `10a1b156…`), boot
`a3691ccf…`, with two harness changes: the second cycle's exchange may
begin up to 30 s after its PM credit clock, and the classifier accepts the
trailing re-arm. Both cycles passed on the host and the device:

| Cycle | TX, host received | RX, host sent | CPU idle TX / RX |
|---|---:|---:|---|
| 1 | 2.456 Mbit/s (chunks 3.18–3.27) | 5.59 Mbit/s (device chunks 10.5–12.2) | 84.6 % / 78.7 % |
| 2 | 1.681 Mbit/s (chunks 2.73, 3.13, 3.16, 3.25, 3.24) | 3.91 Mbit/s (device chunks 10.0–12.9) | 79.3 % / 74.7 % |

Both acknowledgments were written and both standard disconnects
accepted; the leaf reported `cycles_completed=2 rearms_observed=2`, the
supplicant two complete handshakes and two connected events, and the
device log shows activation as lifetime 1 and lifetime 2 with the re-arm
between them. The second re-arm the leaf counted follows lifetime 2's
stage-3 cleanup and key removals, so that teardown completed too.

The sealed log is incomplete: the device-side RAM logger stops at its
2 MiB byte limit, reached at 64.5 s uptime inside lifetime 2's data phase
(two lifetimes write about two per-frame records for some seven thousand
frames). The session therefore classified as returned with an incomplete
log and the classifier, which passes the re-arm, lifetime, scan, fault and
receipt gates on the partial log, cannot see lifetime 2's data-phase end,
terminal and key removals. Returned to changed-boot Gemian
`d2f7adf3-339e-49af-878d-fc741bdad1cd`.

**Where this leaves the second-lifetime item.** Demonstrated on the
device and measured by the host; not yet sealed as one complete log. The
confirming boot needs either a larger logger limit for lifecycle runs or
the two per-frame records demoted for them, then the same image once
more. Cycle 2's lower throughput (first chunk 2.73, then 3.1–3.25) is
noted, not interpreted, until a complete log can be read.

## Lifecycle boot 9: two lifetimes in one complete sealed log; second-lifetime item closed

Same image again (build `e22d9838`, boot2 `10a1b156…`, no reinstall), boot
`b4be0086…`, firmware ready at 10.9 s uptime. One harness change: the
lifecycle runs measure two chunks per direction instead of five, so two
lifetimes' per-frame records fit under the device logger's 2 MiB limit.
Both cycles passed on the host and the device, and this time the log is
whole:

| Cycle | TX, host received | RX, host sent | CPU idle TX / RX |
|---|---:|---:|---|
| 1 | 2.864 Mbit/s (chunks 3.33, 3.20) | 7.11 Mbit/s (device chunks 11.98, 12.52) | 86.8 % / 79.2 % |
| 2 | 2.482 Mbit/s (chunks 3.26, 3.28) | 5.54 Mbit/s (device chunks 10.75, 11.18) | 81.9 % / 76.5 % |

The sealed log is complete: 1,412,427 bytes, 8,697 records, sealed on the
host's stop signal at 54.0 s with the logger reporting a pass, and the
session classified as a RAM-service regression pass with the complete log
through the seal. On that log the classifier passes all nine gates
(re-arms, lifetimes, data phases, terminals, keys removed and re-added,
second-cycle PN seeding, scans, no fault, receipt): `lifecycle_pass` and
`two_lifetime_pass` are both true, with no first failure.

What the device did, from the log:

- **Lifetime 1.** Keys done at 15.1 s uptime; data phase 12.95 s with
  1,553 data frames queued, 1,552 done and 1 failed; slot ledger 1,557
  allocations and 1,557 completions (12 PID wraps, none unowned); standard
  disconnect, three-stage cleanup with the deauthentication transmitted,
  all credits returned and slots retired; both keys removed; re-arm
  record `lifetime=1 token=2` at 28.15 s.
- **Re-arm to lifetime 2.** Scan admitted, two passive BSS notices logged
  as informational by 0250 and one BSS absence outside teardown counted
  (not acted on); fresh keys done at 32.1 s, 4.0 s after the re-arm.
- **Lifetime 2.** Data phase 19.17 s with 1,667 frames queued, 1,667 done
  and none failed; ledger 1,671/1,671 (13 wraps); standard disconnect,
  the same complete cleanup with deauthentication transmitted, both keys
  removed; second re-arm record `lifetime=2 token=2` at 51.42 s.
- No data slot expired (0253's path was not needed), no fault record, no
  refused event.

Host side: both acknowledgments written and both standard disconnects
accepted; the second cycle's exchange began 7.7 s after its credit clock
(within the 30 s bound). Returned to changed-boot Gemian
`c73da941-e073-4de7-9edb-4ca8df2122c9` in two attempts.

**Second-lifetime item: closed.** One boot ran two complete WPA2-PSK
station lifetimes with the driver's own re-arm between them, each with
scan, join, keys, DHCP, pings, measured TCP traffic in both directions,
standard disconnect, three-stage cleanup and key removal, in one complete
sealed log that the classifier passes. Cycle 2's per-chunk TX rate equals
cycle 1's (3.26–3.28 against 3.20–3.33 Mbit/s); its lower aggregate is
inter-chunk time, and boot 8's first-chunk ramp did not recur. Cycle 2's
device-side RX chunks are about 1 Mbit/s lower than cycle 1's; noted, not
interpreted. Reconnection after an access-point loss, rather than after
the host's standard disconnect, is the next lifecycle question and
remains untested.

## What two lifetimes establish, and what they do not

Two lifetimes ran on the device with fresh keys, in one complete sealed log
(boot 9). The re-arm barrier that admitted the second is host-side: the
stage-3 cleanup, the whole slot ledger retired and both key removals
credited. It is not a firmware guarantee. The firmware's key-done event
carries no generation, and a returned page credit does not bound event
delivery (measured: the event arrives 1–5 ms after the credit), so a stale
untagged key event could satisfy a new install window; the PN epochs bound
the damage to a failed lifetime rather than a plaintext leak, and nothing
here claims replay or attribution safety. Reconnection after access-point
loss, longer operation and power management remain untested; boot 10 adds
that an idle connection was lost after six minutes.

## Lifecycle boot 10: the host harness refused three cycles; an idle connection was lost at 367 s

New image: build `d838628f` adds proposal 0254 (an idle scan re-opens the
scan cycle instead of fail-stopping the lifetime), boot2 `87d7b532…`
(predecessor `10a1b156…`), boot `5805513e…`. Planned: three
supplicant-driven lifetimes with one chunk per direction. Nothing was
measured: the host helper exited with status 2 before any Wi-Fi exchange.
The retained phase-b parser that the helper chain runs through admits one
or two cycles and refuses three; that exit bypassed the helper's failure
receipt, the session host then had no quiescence result and refused export,
and the device was returned by the reviewed preservation path (quiescence
proved, complete log sealed, changed-boot Gemian
`605bbbd1-7efb-4f95-b329-aba26c1a08f5`). Harness result, not a driver
result; the harness now hands that parser its admitted value while the plan
binds the real count, and a parser exit leaves a receipt. The
third-lifetime question is unanswered and queued behind the RX
re-baseline and the rate boot.

What the device did while it waited: cycle 1 scanned, joined (activation
lifetime 1 at 14.9 s), completed the handshake, DHCP and pings (7 data
frames queued, 7 done), then sat connected with no host traffic. At
382.7 s uptime, 366.7 s into the data phase, the firmware reported a
connection loss (`source=monitor reason=4 class=air`), the first time the
owned loss path has fired on the device. The driver ended the data phase
with reason connection-loss, ran the three-stage cleanup with the
deauthentication transmitted, saw both keys removed and re-armed
(`lifetime=1 token=2`). The leaf had already stopped (its acknowledgment
window closed at the terminal), so no scan followed and 0254's path was not
exercised. Two readings remain open and this boot does not separate them:
an access-point inactivity disassociation of a station that sent nothing
for six minutes (4 is the 802.11 inactivity reason code, if the firmware
passes it through), or a firmware keep-alive that is not running. The
600-second P2E-D2 gate passed with a probe every ten seconds, so the
connection holds under light traffic; idle, it does not. Recorded as an
open item for general operation. The loss path itself, data end, cleanup
and re-arm, behaved as the loss test expects.

**Finding: connected but idle, the link is lost after about six minutes;
under light periodic traffic it holds for 600 s.** The frame-count
discriminator was applied to this log: between the last host frame at
21.6 s and the loss at 382.7 s the driver recorded no transmit completion
(slot ledger 11 allocations, 11 completions, none unowned), and the
driver's transmit admission passes only control-port EAPOL and LLC/SNAP
data, so mac80211's null-data keep-alive cannot reach the air. The
firmware's own keep-alive frames report no host completion, so the zero
count does not show whether they were sent; the loss came 361 s after the
last host frame, a multiple of the firmware's 30-second keep-alive period,
which fits a keep-alive that runs and fails to hold the association rather
than one that never ran. Either way the host must keep the link alive
itself, with a periodic frame the gate admits or a keep-alive shape admitted
deliberately; that is a separate variable, queued after the rate boot.

## Evidence

`artifacts/wifi-throughput-lifecycle-1/` to `…-lifecycle-10/` (sealed
sessions, per-cycle evidence under `session-lifecycle-1/lifecycle-c1/`),
install receipts under
`artifacts/device-install-evidence/mt6797-wifi-tx-lifecycle-image-deployment-1/`
`…/mt6797-wifi-tx-lifecycle2-deployment-1/`,
`…/mt6797-wifi-tx-lifecycle3-deployment-1/`,
`…/mt6797-wifi-tx-lifecycle4-deployment-1/`,
`…/mt6797-wifi-tx-lifecycle5-deployment-1/`,
`…/mt6797-wifi-tx-lifecycle6-deployment-1/`,
`…/mt6797-wifi-tx-lifecycle7-deployment-1/` and
`…/mt6797-wifi-tx-lifecycle10-deployment-1/`,
[scalars](results/lifecycle-runtime-scalars.json).
