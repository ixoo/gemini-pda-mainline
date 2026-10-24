# Flow-control boot: holding the mac80211 queue is slower; a teardown race surfaced

Result record, 2026-10-24. One boot on the `mt6797-a53-wifi-flow-control`
profile: the station tree of station-3 plus proposal 0235 (stop mac80211's
queue while the eight-frame data queue is full instead of freeing the ninth
frame unsent). Build input `c48412ae`, boot `5449eb4d…`, candidate
`4b544a48…`, boot2 `8d52e5c3…`, admitted by the host watcher at 5.9 s
uptime. Same laptop, AP and TCP protocol as the series.

## Measured

| Direction | flow-control | station-3 | vendor |
|---|---:|---:|---:|
| TX, host received | **0.922 Mbit/s** (chunks 1.22, 1.08, 0.93, 1.10, 1.10) | 1.225 | 14.59 |
| RX, host sent | **8.10 Mbit/s** (device chunks 16.5, 13.1, 15.0, 11.0, 10.9) | 10.01 | 31.54 |
| CPU idle TX / RX | 87.7 % / 79.7 % | 87.7 % / 76.9 % | — |

Completion gaps (2,988 completions, 2 failed): median 0.70 ms, 75th
percentile 7.1 ms, 2,163 below 6 ms, 782 in 6–12 ms, 10 in 12–25 ms, 32
above 25 ms. Per second of the TX phase, 58–112 completions against
103–129 on station-3, and 300–450 ms of stalls above 25 ms against
140–200 ms: the 8 ms per-frame cadence inside bursts is unchanged, the
bursts are shorter and the stalls between them longer. Both directions
lost about a fifth to a quarter, beyond the 3 % spread between station-2
and station-3. One run; the chunks declined through the run and the run
was not repeated.

**Decision.** Proposal 0235 did not do what it was written for and is
retired from every measurement series rather than carried; the
flow-control profile is retired with it, and 0236 (pipelining) is rebased
onto the station tree. Why holding is worse than dropping is not
established by this run; a retry would need the stop/wake events recorded.

## Teardown: an absence notice before a credit

The data phase ended by the leaf's standard disconnect at 20.9 s, the
host acknowledgment was accepted, PM abort and the reserved
deauthentication completed as on station-3. Cleanup stage 2 was then
submitted and, 0.6 ms later and before that command's credit, a 12-byte
`EVENT_ID_BSS_ABSENCE_PRESENCE` notice arrived. The measurement tree's
absence gate admits a notice only with no page debt, nothing in flight and
cleanup stage 3, so it refused the notice with `-EPROTO`; the lifetime
fail-stopped (`join stopped: status=-71 … cleanup=3 branch=6`) with the
removal credit still owed, and the disable ran without it (`status=-71`).
Station-3 received the same notice *after* the stage-2 credit and admitted
it. The refusal logs the header only, so the body of the refused notice is
unknown.

Proposal 0243, until now in the lifecycle series only, already turns a
notice outside the admission window into a counted state change; it joins
every measurement series. Proposal 0247 removes the one refusal 0243 left
(a notice whose body is not the owned BSS's absence or presence is counted
and its four body bytes logged) and logs the body of any 12-byte event the
dispatcher still refuses, so the next refusal is diagnosable.

Session host accepted export; complete log sealed (20,455 records); native
return to changed-boot Gemian `54cfeeb8-c0d8-4b0d-a016-d8d74844de1b` in
15.3 s. The classifier's per-PID trace stays invalid after 0246 (counters
intact).

## Evidence

`artifacts/wifi-throughput-flow-control-1/` (sealed session), install
receipt under
`artifacts/device-install-evidence/mt6797-wifi-tx-flow-control-deployment-1/`,
[scalars](results/tx-flow-control-runtime-scalars.json).
