# Lifecycle boots 1 to 4: each boot takes the second lifetime one stage further

Result record, 2026-10-24. One boot on the `mt6797-a53-wifi-lifecycle`
profile (pipelining tree plus 0240 re-arm, 0241 loss reason, 0243) under
the two-cycle host harness: each cycle is a scan, join, DHCP, three pings,
the five-chunk TCP protocol in both directions, host acknowledgment and the
standard disconnect; the leaf then waits for the driver's re-arm record
before selecting the network again. Build input `88f5edaf`, boot
`8dac7669…`, candidate `519581a8…`, boot2 `10978b3c…`, admitted at 6.4 s
uptime.

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

## Evidence

`artifacts/wifi-throughput-lifecycle-1/` to `…-lifecycle-7/` (sealed
sessions, per-cycle evidence under `session-lifecycle-1/lifecycle-c1/`),
install receipts under
`artifacts/device-install-evidence/mt6797-wifi-tx-lifecycle-image-deployment-1/`
`…/mt6797-wifi-tx-lifecycle2-deployment-1/`,
`…/mt6797-wifi-tx-lifecycle3-deployment-1/`,
`…/mt6797-wifi-tx-lifecycle4-deployment-1/`,
`…/mt6797-wifi-tx-lifecycle5-deployment-1/`,
`…/mt6797-wifi-tx-lifecycle6-deployment-1/` and
`…/mt6797-wifi-tx-lifecycle7-deployment-1/`,
[scalars](results/lifecycle-runtime-scalars.json).
