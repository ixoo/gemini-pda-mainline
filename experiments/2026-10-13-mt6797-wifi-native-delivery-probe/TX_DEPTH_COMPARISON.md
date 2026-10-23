# Bounded data-depth comparison: predeclaration

Hypothesis: allowing up to four ordinary data TX owners can overlap the
status round trip that still serializes pump-1. The descriptor remains fixed
at nominal OFDM 6 Mbps; rate control and aggregation are separate later passes.
DMA remains deferred. No reconnect, key-slot reuse or rekey is enabled.

The only runtime variable relative to [pump-1](TX_PUMP_RESULT.md) is ordinary
data in-flight depth, one to four. The actual source uses TC1 for ordinary
data; TC4 management/security and reserved deauthentication stay unchanged.
The unchanged TC1 page pool may constrain effective depth below four. There
is no pool enlargement, page-debt reconciliation change, PID reuse rule change,
deadline extension, admission change or new firmware command. Each data owner
keeps its existing 750 ms deadline; exact PID completion retires only its owner.
Credit shortfall or a busy next PID waits without allocating/submitting.
Cleanup requires no outstanding owners, debt zero and whole ledgers.

## One finite run

Build from clean pushed inputs using the depth measurement profile, validate
artifact/config/source identities and use the reviewed boot2 guard and matching
full-partition readback. Clean shutdown, then physical boot2 selection by owner.
Verify fresh live identity before firmware start. One attempt, no retry.

Join, DHCP, three pings and authenticated Wi-Fi SSH; plain TCP `nc` data,
SSH control/progress/keepalive. Device TX followed by device RX, five chunks per
direction, each bounded by 1 s or 1 MiB, 100 ms gaps. Keep the 2 MiB logger,
receiver streaming counter and file-limit preflight. Capture per-chunk elapsed,
delivered bytes/rate, aggregates, CPU idle, netdev errors/drops, TX status
completion/nonzero counts, and descriptor completion attempt counts where
available. Do not equate status completion with a radio ACK/encryption proof.

Disconnect promptly through the existing EOS-derived standard window; require
honest per-run delivery and whole-ledger stage-3 results. Seal/export evidence,
reviewed return and independent changed-boot Gemian confirmation. A failed
classifier never authorizes a repeat. Preserve original automatic output.

## Decision branches

- First driver/link error, credit anomaly, identity mismatch or link loss:
  stop, preserve/export, reviewed return; no retry or widening.
- RX harness failure: RX unmeasured, report the harness condition.
- Depth four improves TX: report magnitude against pump-1 (0.290676 Mbit/s,
  86.496% idle) and RX (2.846408 Mbit/s, 82.587% idle), with per-chunk rates
  and completion/attempt counts. Distinguish configured depth from observed
  peak outstanding owners.
- Modest or unchanged TX: report the remaining serialization/airtime limit;
  do not change rate, aggregation, ledger, pool sizes or deadlines in this run.

Five short chunks are a finite comparison, not a sustained-throughput claim.
Baseline-2's 51.8 s protocol differs; pump-1 uses this same duration-bound shape
and is the primary comparison. No rate-change pass is authorized here.

## Sealed offline candidate

Validated build `957b5f3e41a9a2d4781a09ea4709d855bffa0245`, profile
`mt6797-a53-wifi-tx-depth-measurement`. See
[build and fixture scalars](results/tx-depth-build-validation.json).
The configuration delta against the actual pump package is only depth=4;
all seven relevant prepared-source exports match the reviewed files.

- Candidate manifest: `c5786bf65130093e1bf1ee84ac617fd74a1e70f356b3d0c05f20617c6e5cffc8`.
- Android boot image: `8d1a49b876890f2afd0b416dc39264dfafd45dc0af03323a7584aba014181943`.
- Full 16 MiB boot2: `574fb99045fb13261235372fb1549b8682116fc534fc13d417226eb6787726c7`.
- Live notes: 84 bytes at Image offset 12900184,
  SHA-256 `c91b6cf420ceb03653ec7f9dc50bc1b1d98b9c95b85c9cacddb8f130ad7d38ea`.

The exact RAM/DT and parent boot reproduction passed. Private successor host
bindings and installer are sealed under `artifacts/wifi-tx-depth-work/`;
the helper changes only its session label. The embedded device guard is
byte-identical to the reviewed pump installer. Offline constructors loaded
these bindings and refused at the missing genuine deployment receipt, as
required; after installation they must pass using the actual receipt.

Verification occurs at build/package, host-seal, installation and physical-boot
stage boundaries, or after a material content change. No run has happened at
this offline checkpoint. The owner must physically select boot2 after verified
installation and shutdown.

## Installation handoff

The reviewed installer wrote/synced/flushed boot2 and verified matching full
readback `574fb99045fb13261235372fb1549b8682116fc534fc13d417226eb6787726c7`.
Clean shutdown confirmed unreachable. Both capture and session offline
constructors passed against the genuine depth deployment receipt; host hashes
and candidate/receipt bindings were verified at the physical-handoff boundary.
The one measurement attempt is unconsumed. Physical boot2 selection is pending;
no throughput result is claimed for depth four yet.
