# Design: MT6797 Wi-Fi native-crypto-delivery diagnostic (proposal 0181, default-off)

| Field | Value |
| --- | --- |
| ID | `2026-10-13-mt6797-wifi-native-delivery-probe` |
| Status | ND1 (d104654d) was built, installed under the reviewed boot2 guard and RUN ONCE: NEGATIVE before native delivery, caused by a HOST defect (the SET_MONITOR CID 0xFC was omitted from the command validator `mt6797_join_prepare_command`, so the enable was refused locally, EINVAL) -- the firmware capability is UNOBSERVED. See [ND1_RESULT](ND1_RESULT.md). Fix: proposal 0181 now adds the config-gated 0xFC validator case (+ a validator-path test); a rebuild yields the ND2 candidate. Recovery is UNCONFIRMED (return collector did not reach known-good Gemian). |
| Base | Proposal 0180 ([compile 37](../2026-10-07-mt6797-wifi-phase-b-join/COMPILE_37.md)), kernel `5d6323e1` / `b33ba5a2` |
| Date | 2026-10-13 |
| Device action | ND1 was installed and run once (host-defect negative; see [ND1_RESULT](ND1_RESULT.md)); recovery unconfirmed. Root is sole device custodian; no worker device access. The 0181 validator fix and tests are offline; ND2 build/compose/install is root-driven. |

## Question

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
on a post-ACTIVE marker, native classifier). The executable compositor, capture/
session and classifier are still being completed; build and device remain held
until root reviews the source and profile.

## Checks

`tests/run-native-diag-test.py`, `tests/run-native-rx-test.py` and `tests/run-native-loop-test.py` (ASan/UBSan) pass against the
applied tree; `scripts/validate-manifest-series`, the invariant test and `scripts/check-repository`
pass; pinned `checkpatch.pl` on 0181 shows only the standing archive-proposal exceptions. No
kernel build, device, radio or crypto step is part of authoring 0181.
