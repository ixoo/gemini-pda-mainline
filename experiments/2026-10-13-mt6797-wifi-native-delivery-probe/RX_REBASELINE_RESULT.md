# RX re-baseline: the receive level since pipelining is reproducible, not link variance

Result record, 2026-10-24. One boot on the installed lifecycle image (build
`d838628f`: the pipelining tree with 0240–0254; boot2 `87d7b532…`, the
installer found it already matching and wrote nothing), the five-chunk TCP
protocol in both directions, one lifetime, nothing else changed. Boot
`95fc360b…`, candidate `51607367…`. Question: did pipelining cost receive
throughput (10.01 → 7.63 → 7.11 → 5.54 Mbit/s across boots), or does the
link vary?

## Measured

| Direction | Host-side aggregate | Device-side chunk rates | Host-side chunk rates | CPU idle |
|---|---:|---|---|---|
| RX (5 × 1 MiB, host → device) | **6.99 Mbit/s** | 11.81, 11.98, 11.98, 10.49, 11.49 (mean 11.6) | 16.6, 24.5, 23.1, 19.8, 23.3 (socket writes, not a link rate) | 78.5 % |
| TX (5 × 1 s, device → host) | **2.76 Mbit/s** | — | 3.45, 3.30, 3.16, 3.17, 3.49 (host received, mean 3.31) | 86.1 % |

The host-side aggregate divides the five chunks' bytes by the whole
exchange including the inter-chunk gaps and host setup (6.0 s for 5 MiB
received at 11.6 Mbit/s device-side), so the device-side chunk rate is the
cleaner receive figure. Data phase 21.5 s, 3,936 data frames queued, 3,935
done, 1 failed; standard disconnect accepted, teardown complete, log
complete (1.66 MB). Returned to changed-boot Gemian
`c9fa4427-c705-4ad2-8426-1b26d205b0e9`.

## Against the earlier runs

| Run | Tree | RX host aggregate | RX device chunks | TX chunks |
|---|---|---:|---|---|
| station-2 / station-3 | single arm, no pipelining | 9.85 / 10.01 | 16.1–18.2 | 1.45 |
| pipelining | + 0236 | 7.63 | 12.2–14.2 | 3.89–4.03 |
| lifecycle boot 9, cycle 1 | + 0240–0253 (two chunks) | 7.11 | 12.0, 12.5 | 3.20, 3.33 |
| lifecycle boot 9, cycle 2 | same, second lifetime | 5.54 | 10.75, 11.18 | 3.26, 3.28 |
| **rx-rebaseline** | + 0254, five chunks | **6.99** | **10.5–12.0** | **3.16–3.49** |

## What it answers

The receive level since pipelining is 7.0–7.6 Mbit/s host-side and
10.5–14 Mbit/s device-side on four boots, against 9.9–10.0 and 16–18
before it; it did not land near 10. The link is therefore not varying at
the level that would explain the drop: pipelining (0236, every admissible
data frame per worker pass) cost about 30 % of receive throughput,
reproducibly. Cycle 2 of boot 9 (5.54) sits about 20 % under that band on
one run and stays unexplained. Transmit on the lifecycle tree is also
below the pipelining boot (3.2–3.5 against 3.9–4.0 per chunk, 2.76 against
3.20 aggregate) on three boots now; that gap is noted, not attributed.

The RX cost has a candidate mechanism already on file: the pipelining pass
submits every admissible frame before it reads the receive port, delaying
receive service while the host is also transmitting (TCP acknowledgments
for the RX stream are host transmissions). The experiment that tests it,
bounding submissions per pass when the receive port has pending frames, is
one variable and is queued after the rate boot.

## RX-fix boot (0256, retired): the order inside the pass is not the mechanism

One boot with proposal 0256 (build `aabfc63f`, boot2 `0663f1a9…` over
`f02087dc…`, boot `398a2d44…`): when the previous pass's receive loop had
delivered frames, the pass drained the receive port before it submitted;
depth, page budget, credit model and admission unchanged. Same protocol,
one lifetime.

| Direction | Host-side aggregate | Device-side chunk rates | Host-side chunk rates | CPU idle |
|---|---:|---|---|---|
| RX | **7.23 Mbit/s** (re-baseline 6.99) | 11.81, 11.98, 11.34, 11.49, 12.71 (mean 11.9; re-baseline 11.6) | 18.4, 22.6, 19.8, 20.1, 25.9 | 78.5 % |
| TX | **2.75 Mbit/s** (re-baseline 2.76) | — | 3.37, 3.29, 3.35, 3.27, 3.38 (mean 3.33; re-baseline 3.31) | 86.2 % |

The reorder engaged on 1,586 passes and moved neither direction outside
noise: receive did not recover and transmit did not fall. Data phase
21.0 s, 3,584 frames queued, 3,581 done, 3 failed; disconnect accepted,
teardown complete, log complete. Returned to changed-boot Gemian
`04d5197a-9d8f-46b3-beab-d08c52cda99e`. Proposal 0256 is retired.

**What the sealed logs add.** In the receive window the device transmits
only TCP acknowledgments, about 340–410 completions per second against a
pass cadence of one every 0.5–0.7 ms (median completion gap), so there is
rarely more than one frame to submit per pass: 0236's submission loop
cannot engage in this direction, and its TC1 budget (16 → 52 pages) is a
host-side ledger that already admitted four acknowledgment-sized frames
before the change and sends nothing to the firmware. The other two patches
of the pipelining boot, 0243 and 0247, add bounded logging on the receive
event path, nothing per frame. Device netdev counters show every segment
received once in every run (3,681–3,686 receive packets for 5 MiB), so
the loss is not dropped frames; the acknowledgment count rose with the
pipelining tree (2,381 → 2,497–2,790 transmit packets in the receive
window). The per-chunk device receive rate fell from 16–18 to 11–12
Mbit/s, about 0.3 ms more per received frame, and the mechanism is not
identified by these runs. A capped submission count per pass, the second
variant proposed, cannot engage for the same reason the reorder did not;
a repeat of the vendor control after this boot measured 45.1 Mbit/s
transmit and 38.5 Mbit/s receive on the same link (RSSI −54 dBm;
[scalars](results/vendor-control-2.json)), above the 2026-10-23 control,
so the link has not degraded and the mainline receive level is not
link-limited; the receive path itself has no per-frame records, so the
next step that can discriminate is receive-path instrumentation (frames per pass, read
time per frame, pass cadence) on the same image, or a boot of the
pre-pipelining station tree with only 0236 added, to re-establish which
boot moved the receive rate.

## Evidence

`artifacts/wifi-throughput-rxbase-1/` and `…-rxfix-1/` (sealed sessions), install receipts
`artifacts/device-install-evidence/mt6797-wifi-tx-rxbase-deployment-1/`
(result skipped-already-matching) and `…-rxfix-deployment-1/`, [scalars](results/rx-rebaseline-runtime-scalars.json).
