# Pipelining boot: TX ×2.6; the notice gate holds; RX lower on this run

Result record, 2026-10-24. One boot on the `mt6797-a53-wifi-pipelining`
profile: the station tree plus 0236 (submit every admissible data frame in
one worker pass, up to the in-flight depth of four, with the declared TC1
budget raised from 16 to 52 pages), 0243 and 0247 (absence and presence
notices never end the lifetime). Build input `88f5edaf`, boot `1cd23f95…`,
candidate `2ddfa924…`, boot2 `ec96eb96…`, admitted by the host watcher at
7.5 s uptime. Same laptop, AP and TCP protocol as the series.

## Measured

| Direction | pipelining | station-3 | vendor |
|---|---:|---:|---:|
| TX, host received | **3.198 Mbit/s** (chunks 3.91, 4.03, 3.89, 3.98, 3.92) | 1.225 | 14.59 |
| RX, host sent | **7.63 Mbit/s** (device chunks 12.2, 13.5, 14.2, 13.5, 13.3) | 10.01 | 31.54 |
| CPU idle TX / RX | 85.8 % / 77.6 % | 87.7 % / 76.9 % | — |

Completion gaps (4,081 completions, 8 failed): median **0.61 ms**, 75th
percentile 2.4 ms, 90th 7.8 ms; 3,204 below 6 ms, 836 in 6–12 ms, 15 in
12–25 ms, 25 above 25 ms. The TX phase now completes 230–350 frames per
second against 103–129 on station-3, with the 8 ms status-read cadence
gone from the median: the one-frame-per-pass round of status reads was the
per-frame host cost the series pointed at. TX is 2.6 times station-3 and
the five chunks agree within 4 %.

RX moved the other way, 10.01 → 7.63 Mbit/s. Across the series RX (host
sent) has ranged 8.0–10.0 and the device-side chunks 10.9–18.2, so one run
cannot attribute this; a plausible mechanism is that the worker now
submits several TCP acknowledgments per pass before its receive loop. Not
established; the next RX-direction measurement should look at the receive
loop's share of each pass.

**Decision.** 0236 is retained.

## Teardown with 0243 and 0247

The data phase (21.2 s, 4,076 queued, 4,068 done, 8 failed, 25,190 credits
returned) ended by the leaf's standard disconnect; host acknowledgment
accepted. PM abort `status=0`, reserved deauthentication delivered, the
BSS absence notice (`bss=0 absent=0`) arrived after the stage-2 credit
this time and was admitted, cleanup stage 3 with credits returned and
4,080 slots retired (0 pending, 0 unowned, 32 wraps), disable `status=0`,
one loss report from the cleanup source. No refusal, no fail-stop, so
0247's counted-notice and body-dump paths were not exercised. Complete log
sealed (27,026 records); native return to changed-boot Gemian
`f0e12505-a599-410e-9319-a5e2f9f69bb5` in 15.4 s.

## Evidence

`artifacts/wifi-throughput-pipelining-1/` (sealed session), install
receipt under
`artifacts/device-install-evidence/mt6797-wifi-tx-pipelining-deployment-1/`,
[scalars](results/tx-pipelining-runtime-scalars.json).
