# Design: MT6797 Wi-Fi native-crypto-delivery diagnostic (proposal 0181, default-off)

Latest executed result: [D2](SSH_D2_RESULT.md) (2026-10-18 UTC) hit a port-0
94/142 header-length refusal during mask ENABLE_PENDING on unchanged C10.
DHCP/pings/SSH and the intended local queries were not reached. Healthy cleanup
failed; poison/debt were retained. Evidence and reviewed return to changed-boot
Gemian were independently verified. No retry, length adjustment or timer change.

The [three-run C10 baseline](CCMP10_BASELINE.md) passed all finite transport/
network/host-cleanup windows, SSH 2/3; [D1](SSH_D1_RESULT.md) then passed without
classifying the earlier SSH failure. D2 is a separate transport result, not an
SSH measurement. The [RX contract review](D2_RX_CONTRACT_REVIEW.md) covers this
new +48 direction, existing pre-arm status and updated actual-source fixtures.
No successor candidate is admitted. GTK delivery, rekey, reuse and reconnect
stay disabled; ordinary integrity/key retirement and sustained acceptance remain.

| Field | Value |
| --- | --- |
| ID | `2026-10-13-mt6797-wifi-native-delivery-probe` |
| Status | Inconclusive ordinary-crypto availability: ND6 queued18 native beacons and captured translated reported-index1 Group4 metadata, ordinary native0. After CLOSED a header-length HIF refusal stopped the join; no healthy cleanup-stage3 claim. Preservation/seals/quiescence/regression and exactly one reviewed recovery passed. See [ND6_RESULT](ND6_RESULT.md); historical [ND5_RESULT](ND5_RESULT.md) remains immutable. No authenticated ordinary native exchange, firmware-policy or maintained-driver support claim. |
| Base | Proposal 0180 ([compile 37](../2026-10-07-mt6797-wifi-phase-b-join/COMPILE_37.md)), kernel `5d6323e1` / `b33ba5a2` |
| Date | 2026-10-13 |
| Device action | ND1 through ND6 each ran once; no unchanged-artifact retry. ND6 recovered to independently verified changed-boot Gemian. Laptop coordinator is sole device custodian; implementation/build author has no device access. |

## Question

The reviewed ND4 metadata successor ran once; see [ND4 result](ND4_RESULT.md)
and its historical [preparation](ND4_PREPARATION.md). No unchanged retry.
The reviewed ND5 native-beacon successor ran once; see [ND5 result](ND5_RESULT.md)
and historical [preparation](ND5_PREPARATION.md). No identical retry.

ND6 selects reviewed metadata-only proposal 0189 at kernel input `6e29f38a`;
validated build and actual-source paired tests passed, configuration unchanged.
The [compositor](build-native-candidate-6.py) produced the
[real receipt](results/native-delivery-candidate-6.json), imported byte-exact as
[runtime identity](runtime-nd6/results/candidate.json). Fresh
[prepare](prepare-native-delivery-6.py), [installer](install-native-6.py),
[capture](laptop-capture-native-6.py), [host](passive-host-native-6.py) and
[session](laptop-session-native-6.py) bindings preserve the frozen protocol;
[actual binding tests](tests/nd6-wiring-test.py) pass offline. ROOT completed
guarded installation and one runtime cycle; see [ND6 result](ND6_RESULT.md).
Historical returned Gemian is not proof of current device identity.

ND6's sole retargeted sample observes the first actual ACTIVE/admitted ordinary
class2 translated rejection reporting programmed index1. Group4 availability
permits bounded descriptor FC/TA equality only; absent fields stay absent, and
Ethernet destination bytes are never FC. Two reported-index split counters do
not prove ownership, authentication or producer truth. This measurement must
guide representation/producer work, not admit rejected frames or claim support.
Eight terminal lines, one sample and all decoder/crypto/budget/control behavior
are unchanged; full maintained-driver acceptance remains incomplete.

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
