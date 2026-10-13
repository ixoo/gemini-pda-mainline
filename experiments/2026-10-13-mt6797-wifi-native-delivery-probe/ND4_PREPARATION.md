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
composition was run by the custodian, not the worker. The real receipt and fresh
offline/runtime bindings are recorded below. ND4 is **not installed**.

### Real composition receipt and exact bindings

The custodian reports all frozen config/RAM/inventory/provenance/PSCI/clock/LK
gates passed, all six file hashes/sizes independently verified, and exact16MiB
zero padding verified. Only the kernel changed from installed ND3; config,
board DT and the whole64-member RAM root are byte-identical. The author verified
the supplied receipt digest, byte-exact identity copies and unchanged ND3
config/DT/RAM metadata. Private images were not copied into Git.

- [Real candidate receipt](results/native-delivery-candidate-4.json), byte-exact
  [runtime identity](runtime-nd4/results/candidate.json):
  `b7ca24a196fb416b25ce6e078770087b96d3ea240dd9928230d1e3156d7dd079`.
- Raw boot `f6eb9084c6cad5bc466359d3858df6253bb950983e82d50ffe9e9cd6cb2864c3`,
  12668928 bytes; candidate directory must be `candidate-` plus this full digest.
- Full boot2 `7ce16dc852c1d89881c3ed4e676713fde1f8af755f297cc3e9671cddf6819a0c`,
  16777216 bytes. Composition is not deployment or boot evidence.

| Tool | ND4 binding |
| --- | --- |
| [prepare-native-delivery-4.py](prepare-native-delivery-4.py) | Exact receipt pin before evidence creation; fresh `native-delivery/session-nd4`, capture left absent for its one-attempt claim |
| [install-native-4.py](install-native-4.py) | Real receipt, ND3 predecessor, actual program digest and `mt6797-wifi-native-delivery-deployment-4`; unchanged GPT/root/power/write/readback/shutdown gates |
| [laptop-capture-native-4.py](laptop-capture-native-4.py) | Exact receipt, `capture-nd4` and `session-nd4/deployment-summary.txt`, unchanged Phase-A/one-attempt gates |
| [passive-host-native-4.py](passive-host-native-4.py) | `session-nd4`/`capture-nd4`, `runtime-nd4` identity and helper receipt paths; unchanged budgets/verdict |
| [laptop-session-native-4.py](laptop-session-native-4.py) | Actual prepare/check_ram_root namespace selects ND4; mandatory supplicant/wpa_cli/private-source pins retained; installer routed to ND4 |

Tool SHA256 pins:

- Installer `a99ab4a5f1e5e17fc14538c95aedb8aa1d1100baa0b5189c54d5a7806223155b`.
- Standalone prepare `c29374e156e796d4bdc7e40ff5595004755c1d4f5d9174096d06e7d0c0137d6c`.
- Capture `f7e12c567b47e7aa502048313d0093846131f2d8007eba96ba30bf162f979922`.
- Host `e27ca1642f9921a8fceb24b4c4f48c889a05a589d754f14a9bfd9357046b2937`.
- Session `c5b6744c1d8c0f378da14d4e6b2b2ee29d1715171c7e0d27f7bd2ea0ccceb2ec`.

[Actual-module wiring tests](tests/nd4-wiring-test.py) pass for these namespaces,
receipt copies, installer/self-digest derivation, bad candidate refusal,
offline fresh-root preparation/reuse refusal and changed receipt refusal before
evidence creation. ND3 wiring regression and original classifier/helper fixtures
pass. Tests use temporary offline fixtures, create no deployment summary or
device operation, and do not validate the private candidate's full file set.
Actual private standalone/installer/session preflight remains with the custodian.
A full-host dry run must refuse missing real deployment evidence. There is no
installation, boot or native-delivery claim. ND3/C35 scripts/receipts/evidence
remain immutable; no wrapper change requires a kernel rebuild.

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
