# Design: MT6797 Wi-Fi native-crypto-delivery diagnostic (proposal 0181, default-off)

| Field | Value |
| --- | --- |
| ID | `2026-10-13-mt6797-wifi-native-delivery-probe` |
| Status | ND4 completed negative: 238 actual native decoder calls, zero eligibility/delivery; regulatory branch9 cancellation after disable submission, no CLOSED or HIF refusal. Preservation/seals/regression and exactly one reviewed recovery passed; changed-boot Gemian independently confirmed. See [ND4_RESULT](ND4_RESULT.md); ND3's different HIF failure remains unresolved. No firmware-mode acceptance, crypto or maintained-driver claim. Historical inputs/results remain immutable. |
| Base | Proposal 0180 ([compile 37](../2026-10-07-mt6797-wifi-phase-b-join/COMPILE_37.md)), kernel `5d6323e1` / `b33ba5a2` |
| Date | 2026-10-13 |
| Device action | ND1, ND2 and ND3 each ran once; no unchanged-artifact retry. Laptop coordinator is sole device custodian; implementation/build author has no device access. Current source reassessment uses retained sanitized ND3 evidence only. |

## Question

The reviewed ND4 metadata successor ran once; see [ND4 result](ND4_RESULT.md)
and its historical [preparation](ND4_PREPARATION.md). No unchanged retry.
The reviewed ND5 native-beacon successor is built and awaiting private
composition, not installed or runtime-tested; see [ND5 preparation](ND5_PREPARATION.md).

Does a firmware mode deliver intact protected native MPDUs the host can authenticate through
standard mac80211 — the route-4 precondition for maintained RX crypto? This is the runtime
hypothesis under test, not a precondition.

## Design

See [NATIVE_DELIVERY_PROBE.md](NATIVE_DELIVERY_PROBE.md) for the admitted bounded hybrid scope,
the source-grounded SET_MONITOR command, the strict `mt6797_data_rx_native` decoder contract
(HDR_TRAN-off native gate, 4/1/2/3 group walk, MSDU0 and legacy/MPDU safety gates, CCMP-shaped
eligibility, conservative bad-FCS filter, IV/MIC preserved), the credit-reconciled arm, the
count-all/reject-before-caps budget with the wall enforced on an empty stream, the hard-poison
ambiguity contract, and the honest positive/negative limit (valid traffic does not prove
hostile-replay rejection). The driver change is proposal 0181 under `patches/proposals/`.

## Composition and runtime

The admitted default-off diagnostic is composed into its own build and runtime
identity (candidate 32 / runtime 33 untouched); see [COMPOSITION.md](COMPOSITION.md).
The build profile `mt6797-a53-wifi-native-delivery-diag` (`kernel/manifest.json`
+ `configs/gemini-a53-wifi-native-delivery-diag.fragment`) builds the diagnostic
into the station-join kernel and force-arms the read-only `mac.native_delivery_diag=1`
boot parameter, preserving `clk_ignore_unused` and PSCI. `prepare-native-delivery.py`
is the offline preparation adapter (receipt-driven, no fabricated hashes, no
device action). Buildbox emits a validated kernel **package**; the laptop
compositor (reusing candidate-32's) produces the boot2 image and receipt. The
runtime is a single native diagnostic lifetime (one-cycle join, Wi-Fi SSH gated
on a post-ACTIVE marker, native classifier). ND1/ND2 compositor and runtime
receipts remain pinned and immutable. A repaired successor needs source review,
clean pushed inputs, a validated package and fresh candidate/runtime bindings;
the custodian supplies the real receipt using the private parent/RAM root.

## Checks

The source-reviewed deadline successor is built and privately composed, with
fresh receipt/runtime/installer bindings in [ND3 preparation](ND3_PREPARATION.md).
No ND3 deployment or device result is implied; ND3 precedes the separately
compiled maintained-BSS-absence correction in the device queue.

`tests/run-native-diag-test.py`, `tests/run-native-rx-test.py` and `tests/run-native-loop-test.py` (ASan/UBSan) pass against the
applied tree; `scripts/validate-manifest-series`, the invariant test and `scripts/check-repository`
pass; pinned `checkpatch.pl` on 0181 shows only the standing archive-proposal exceptions. No
kernel build, device, radio or crypto step is part of authoring 0181.
