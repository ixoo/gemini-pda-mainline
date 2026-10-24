# Lifecycle boot 1: one full lifetime, then no re-arm request

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

## Evidence

`artifacts/wifi-throughput-lifecycle-1/` (sealed session, per-cycle
evidence under `session-lifecycle-1/lifecycle-c1/`), install receipt under
`artifacts/device-install-evidence/mt6797-wifi-tx-lifecycle-image-deployment-1/`,
[scalars](results/lifecycle-runtime-scalars.json).
