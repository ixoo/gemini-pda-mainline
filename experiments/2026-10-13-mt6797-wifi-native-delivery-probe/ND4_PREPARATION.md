# ND4 — reviewed metadata successor preparation

Kernel input `258c88b1dff36b04e2dc9546c8e14d8d021aa86e`, native profile
`mt6797-a53-wifi-native-delivery-diag`. Exact approved proposal0187 SHA256
`dd6a6d3dea6d1c78296710c1d443436e4d0f4dee68d17ffd382ad97217188da5`.
See [source review and ND3 chronology](ND4_SOURCE_REVIEW.md).

Selection audit passed: only the explicit native series gains0187; all18 other
explicit profile series and the manifest/configuration remain byte-identical.
The four historical global-series consumers inherit the canonical append under
the coordinator's explicit admission. They are not selected for this build and
are not new valid foundations. Frozen ND3/C35 inputs/runtime are unchanged.

The ordinary managed Buildbox-1 build was submitted from a clean pushed checkout,
32jobs, experiment selector unset, with no competing heavy job and free managed
locks. The build and managed package validation passed; the validated package
was fetched under ignored `artifacts/buildbox/258c88b1.../` in the clean build
checkout. No candidate receipt, deployment identity, installation or runtime
outcome is inferred from this build. This record contains no placeholder digest
or fabricated receipt.

## Validated build identities and tests

- Job `258c88b1dff36b04e2dc9546c8e14d8d021aa86e-mt6797-a53-wifi-native-delivery-diag-m0`,
  completed `2026-10-13T22:00:20Z`, 682 selected patches in canonical order.
- Package inventory
  `178cf67da473b49e9a665fa503395e27f8538d06e5f5d9b2ddaa88ba0d026f2a`.
- Image.gz `4d7120b9b3305fc60d8b931f40ae139482f5af48baad68388d1f49aef2ae853b`;
  decompressed15960072 bytes, effective size16580608 bytes.
- Resolved configuration
  `33a50989755c6e226e3a4f388177d35956d407702f4e08120e737f28d6b2bf43`, same as ND3.
- Patchset `6d5377b7fb208530c42e67121e108e0e6c099c4350e5290847aa6f7989c809cf`.
- Actual built mac.c
  `47dbe9567a216aef6ae2703ee13204c49eb9594c1015c64f369e45598dd4c751`;
  hif.c `07763b3ba8f48ae71c2a629dcbe558c06a59b675d1fb7f57615ed148286e3769`;
  hif.h `e7f6415f630390b7b8317fc535b339b8708705630587888676a5f2ba40775618`;
  data-rx.h `02179812099659607a99e0d092c58c031960375f64d502a566274c413106134a`.

These four files match the exact reviewed/replayed source. Focused actual-HIF,
old/new decoder equivalence and extracted phase/gate/sample/report tests passed
against the actual built source under ASan/UBSan. Existing native-loop and
native-diag budget/flags tests passed there too; original strict classifier
compatibility fixtures passed. Synthetic tests do not prove live RX shape,
firmware behavior, crypto or concurrency. The build had only the inherited
patch whitespace and unrelated unused CPU-hotplug inventory warnings. No DT or
configuration change; DT schema tests were not rerun. No hardware test.

## Composition and binding sequence

[build-native-candidate-4.py](build-native-candidate-4.py) reuses the frozen
ND3/ND2 composition gates and private C32 parent. It pins the real new
commit/package/Image.gz identities above, reuses the same board DT and64-member RAM
root with its existing native release gate, and preserves the same native config
and boot command line. The custodian privately composes and returns the real
receipt; no additional assembly approval is needed within this reviewed task.

The actual ND4 compositor namespace/CLI was checked against the validated
package: commit/profile/release/inventory/Image pins match; inherited parent,
config, container and RAM-root gate bodies remain unchanged. Private C32
composition has not been run by the worker. The real receipt is pending from
the custodian.

Only that real receipt will supply the candidate, full-partition and runtime
pins. ND4 will use fresh `native-delivery/session-nd4` and `capture-nd4` paths and
a separate `runtime-nd4` identity copy. Those paths are planned, not claimed or
created by this document. Actual-module preparation/installer/capture/session
wiring tests must pass before custodian private preflight. A full-host dry run
must refuse a missing real deployment summary; no synthetic deployment is used.
ND3 runtime/receipt/script files remain byte-identical.

The last independently verified predecessor is ND3 full boot2
`7b61241a89c9d8472885c93d654ecda6f63a188f154b2a7bfc69dd5caaf9dc06`, returned
Gemian boot `701e7d15-50bc-43e2-b94e-3134bbc71de0`. These are historical facts,
not live installation admission. Before any guarded write the sole custodian
must freshly verify Gemian, live GPT/root/power and full predecessor, regenerate
the actual installer, then require full readback and clean shutdown. Owner
physical boot2 selection remains mandatory. Workers have no device access.

## Hypothesis and unique observations

ND4 measures two missing ND3 observations, without guessing a repair:

1. Which existing HIF protocol-refusal gate fails after the closed-state deauth:
   advertised selected length or already-staged header mismatch? Values already
   read identify the gate, not why firmware/transport produced them.
2. Which phases and descriptor classes are consumed, how many packets actually
   reach/call the ordinary-native decoder, and what is its first eligibility
   rejection? The one guarded descriptor sample can expose observed channel,
   header/group values without logging any payload, address, IV, PN or key.

Pending/active/drain/closed phase histograms must not be conflated; gate sums are
actual calls, while blocked means decoder not invoked. Pre-dispatch handling
is the remaining class count, not a decoder rejection. Eligible is not queued
delivery or authentication; the sample describes one call, not all packets.
Missing fields/samples are recorded as absent, not negative packet evidence.

## Unchanged protocol and decision branches

The [one-lifetime native protocol](NATIVE_DELIVERY_PROBE.md), join leaf, helper,
strict classifier, prospective sample/drain/radio/lifetime ceilings, admission,
plaintext withhold, zero crypto bypass flags, credit/poison/cleanup and single
reviewed recovery budgets remain unchanged. READY still requires DHCP, a live
matching listener and the existing window/ACTIVE contract. No forced marker,
new read/write, retry, unchanged ND3 boot or guard relaxation is admitted.

- HIF length/header failure: preserve exact phase, reason and valid/absent
  numeric fields plus ledger/terminal chronology; stop through existing poison
  and no-copy paths. Propose only an evidence-grounded follow-up, never a guessed
  live correction.
- Zero decoder calls: use phase/class/blocked counts to distinguish sample
  accounting from hook invocation; do not infer protection from byte lengths or
  absence of a DHCP reply on wire from no delivered lease.
- Calls with first-gate rejections: name only the first evaluated failure and
  compare the bounded sample where applicable; do not claim all gates failed or
  relax the predicate to deliver rejected frames.
- Eligible delivery but no authenticated challenge: retain the partial result;
  no crypto/usable station/support verdict.
- Existing diagnostic PASS: still requires the exact healthy owned cycle,
  eligible delivery with flags clear and fresh boot/mode-bound Wi-Fi exchange.
  It does not complete lifecycle/reuse/rekey/replay/IRQ/DMA/sustained clean-profile
  acceptance. Full maintained-driver goal remains incomplete.
- Identity/preservation/quiescence/seal/regression failure: stop, preserve unique
  evidence and defer any recovery whose unchanged reviewed gates are unmet.

Only the laptop custodian performs installation, capture/session and recovery.
Raw retained captures and private RAM-root material stay private; sanitized
metadata and attributable negative results are publishable under project gates.
