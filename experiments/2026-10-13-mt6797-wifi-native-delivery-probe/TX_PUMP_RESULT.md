# TX pump comparison 1: measured, consumed

The immediate-pump candidate measured TX at **0.2906759265 Mbit/s**, versus
baseline 2's **0.2057399139 Mbit/s**: **+41.2832%** aggregate. This is a modest
rise, not an order-of-magnitude change. RX measured **2.8464076555 Mbit/s**;
baseline 2 has no valid RX result, so no RX improvement claim is possible.

## Exact identity

- Run: `PIO-throughput-pump-1`; mainline boot `16d1b06e-5051-459a-9fc4-54e0841c60d2`.
- Build commit: `23745fe907c48ae0137cf5151b1117770545ce07`.
- Profile: `mt6797-a53-wifi-tx-pump-measurement`; release `7.1.3-gemini-a53-private-p2e-delivery` is shared with the baseline and is insufficient alone.
- Package manifest SHA-256: `44a071bdd43322bcc21bbf99da60ee89407e6b64523ca24d1a64828a6c36c532`.
- Candidate manifest SHA-256: `16eb08d56be896e0d607b12142aaee6e52e95a1332a7f669932fe1e529d5ac9f`.
- Boot2 full-partition candidate/readback SHA-256: `e33c85f94b1217918ffe4bb886195fa469c564a49684b4f9c3fc62234540970d`.
- Live notes: 84 bytes, SHA-256 `e875f110f15fefaba186133a7092c5476566ce3262de927d8d73db7c99622c22`; identity check reports root hashes verified before firmware start.

## Measurement and limits

Plain `nc` TCP carried bulk data, SSH only control/progress. Both directions
completed five duration-bounded chunks, each 1 s or 1 MiB cap, with 100 ms gaps.
All device chunks ended with expected timeout exit 143. RX host sends hit the
1 MiB cap on chunks 3 and 5; delivered RX uses device counts, never host-sent
bytes. The device clock resolution is 10 ms.

| Direction | Delivered bytes / aggregate elapsed | Aggregate Mbit/s | Aggregate device idle / iowait | Status completions / nonzero |
| --- | --- | --- | --- | --- |
| Device TX → host | 217976 / 5.999148333 s host span | 0.2906759265 | 86.496% / 0% | 208 / 0 |
| Host → device RX | 2230872 / 6.270 s device span | 2.8464076555 | 82.587% / 0% | 295 / 0 |

TX chunk rates in order: **0.366995, 0.378251, 0.343899, 0.320318,
0.332211 Mbit/s**; median **0.3438994788**. Baseline chunk rates were
0.202007, 0.204181, 0.193683, 0.212439, 0.221851; median 0.2041814378.
Every new TX chunk exceeds the baseline's observed range; median rises about
68.43%. This meets the predeclared modest-rise branch, below 10×. The observed
range is not a confidence interval.

RX chunk rates: **1.743335, 2.144760, 4.209236, 2.347279, 7.225663 Mbit/s**.
RX aggregate host-sent rate/count are not delivered throughput. Aggregate
spans include transitions and gaps; RX's endpoint windows and TCP buffering
also affect short chunks. Baseline 2 TX used five size-bounded chunks with
10 s timeouts and a **51.829942958 s** aggregate host span. Pump1 used 1 s
chunks. Compare per-chunk rates as well as aggregate rates; the aggregate
+41.28% is not a controlled estimate of the pump's isolated causal effect.

Netdev deltas: TX direction TX packets 246/drop 0/errors 0, RX packets
192/dropped 8/errors 0; RX direction TX packets 1959/drop 0/errors 0, RX
packets 2296/dropped 9/errors 0. Preserve the nonzero RX-drop counters.
Aggregate idle over eight CPUs cannot exclude saturation of one service CPU.

## Disconnect, ledger and return

The standard EOS-derived disconnect was accepted, exit 0. Sealed raw kmsg
records deauth completion and cleanup both `completion_valid=1 status=0
transmitted=1`; the whole-ledger cleanup is `stage=3 credits=returned
slots=retired deauth=1 delivery=transmitted`. Window and cleanup slot summaries
both have **541 allocations, 541 completions, pending=0, unowned=0, wraps=4**.
This proves the observed standard-disconnect delivery and ledger result for
this finite lifetime; it does not establish encryption/air ACK or reconnect.

The legacy classifier reports `healthy_cleanup=false` and downstream
throughput/protocol flags false; its expected cleanup shape predates the
`delivery=transmitted` suffix. Do not report these false flags as the raw
stage-3 result. Session exit 1 is retained separately from successful traffic,
raw teardown evidence and RAM-service regression/return. Do not silently rewrite
historical classifier output.

All **75** pre-recovery seal entries independently rehashed. Seal SHA-256
`e70461c35fcd3597a04127a567a1773b502e4e9ab1c9508f93498746405291ea`.
Complete kmsg: **561461 bytes**, **4284 contiguous records (0–4283)**,
SHA-256 `0768d7fb8200b79916a081bc8bb7474a602130db7b235a5bb57ec5a0f5a5ba99`.
The raw-byte `kmsg.status` SHA-256 is
`b49301557ab99b1770a21efc1044fb6453aba257f038d2a5b4c5673232b1ff11`;
the collector's separate normalized status hash must not be confused with it.
Session result records RAM-service regression pass and reviewed recovery
confirmed. Independent Gemian inspection reports `3.18.41+`, `aarch64`, changed
boot **`fad9559a-afb0-4624-a689-58b5840f0551`**.

## Bounded conclusion

The 20 ms scheduling delay is a real but minor contributor to the very low TX
rate: removing avoidable waits produced a modest rise while TX remained below
0.4 Mbit/s in every chunk. Source-based interpretation points to the fixed
6 Mbps transmit rate/airtime together with single-in-flight and completion/
credit serialization as dominant remaining limits. That interpretation is
not a direct airtime measurement or a proof of how much each limit costs.
Keep the distinction between observed improvement and source-based bottleneck
analysis explicit. DMA remains deferred; this run does not justify DMA as a
throughput fix. The consumed run is complete, without retry. The owner subsequently selected
bounded data depth as the next single-variable pass; rate changes remain separate.

## Completion counts for the depth comparison

The complete ordinary-data phase reports 537 completions, all status 0 and
advanced=1. Firmware-reported `ucTxCount`: 527 frames at 1, ten at 2, sum 547.
The parser exposes this count only when the advanced flag is set. Its source
name does not establish a retry formula; ten retries is an inference only if
the field includes the initial attempt. Preserve the count histogram as the
direct observation. Direction-specific completions above cover their shorter
measurement intervals, not the whole data phase. Reused PIDs are separate
owners and must not be deduplicated across the run.

## Fixed-rate descriptor finding

The actual built `join-tx.h` data encoder sets `d[11] = 0x80`
(fixed-rate enable) and `d[26..27] = 0x4b << 2` (bytes `2c 01`),
identified by its source as nominal OFDM 6 Mbps. Descriptor source SHA-256:
`9a440e9542ca55034514fd8f7d9b2c34e10e1ab31cb160c1ca5f248fcc1deb60`.
This records the configured rate, not an independent on-air PHY measurement.
The depth pass must leave this encoder byte-identical.

## Verification and process

Preparation hashes were sealed at the candidate/install/physical-handoff stage
boundaries, with extra verification only after material identity-binding edits.
The post-run boundary independently verified the 75-entry evidence seal and
changed-boot Gemian return. Original automatic results remain preserved;
the public classifier now accepts the exact delivery suffix for future runs.

The binding pass and device run stayed in root as instructed. Delegation did
not reduce root steps in this completed run, and corrective binding iterations
prevent a claim of fewer turns. The next depth package delegates host harness
and read-only source analysis; root retains device custody and final records.
