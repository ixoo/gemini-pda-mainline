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

## Evidence

`artifacts/wifi-throughput-rxbase-1/` (sealed session), install receipt
`artifacts/device-install-evidence/mt6797-wifi-tx-rxbase-deployment-1/`
(result skipped-already-matching), [scalars](results/rx-rebaseline-runtime-scalars.json).
