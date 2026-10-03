# Experiment: MT6797 Wi-Fi implementation audit

## Record

| Field | Value |
| --- | --- |
| ID | `2026-10-03-mt6797-wifi-audit` |
| Status | `completed` (offline review; no build or device action) |
| Subsystem | MT6797 CONSYS, WMT and Wi-Fi |
| Device variant | Project Gemini (Gemian image identifies 4G UK 6M15BS/X600) |
| Date(s) | 2026-10-03 |
| Investigator(s) | Claude (owner-requested audit) |
| Tracking issue | [#25](https://github.com/ixoo/gemini-pda-mainline/issues/25), [#34](https://github.com/ixoo/gemini-pda-mainline/issues/34) |

## Question

Why does the mainline Wi-Fi path complete scans without receiving any frame,
and what should the next work be? This review covers the Wi-Fi proposals
0035–0085, their isolated profiles, the experiments from
[2026-09-25](../2026-09-25-mt6797-consys-status/README.md) to the
[unfinished event-mask checkpoint](../2026-10-02-mt6797-scan-event-sample/README.md),
the [Wi-Fi contract](../../docs/hardware/mt6797-wifi.md) and issue #34. It is
read-only analysis. It changes no profile, candidate or patch.

## What the mainline path does today

Each step below is observed in at least one exact-candidate boot; the
[Wi-Fi contract](../../docs/hardware/mt6797-wifi.md) links every receipt.

1. Passive CONSYS owner, reservation, VCN18/VCN28/VCN33-Wi-Fi handles,
   CONMCU reset and modern CONN domain binding.
2. CONN power-on, delayed chip ID `0x0279`, CONMCU reset release.
3. Region-19 WMT memory setup (policy, remap, 343 KiB clear), region-18 EMI
   policy, copy of both WLAN EMI sections with readback.
4. VCN33-Wi-Fi enabled in software mode at 3.3 V, HIF function 1 enabled,
   two ordinary sections downloaded, START, ready WCIR `0x00300279`.
5. Capability query, bounded debug-event drain, sleepy notice, private board
   record, base-power/domain/regulatory sets, TC4 credit reconciliation.
6. mac80211 wiphy, station netdev up, broadcast filter, BSS activation and one
   passive scan per boot on 2.4 GHz or channel 40, with matching completion
   and returned credit.

What has never happened: a received management frame, a BSS result,
association or traffic. In the [counter scan](../2026-10-02-mt6797-passive-scan-count/README.md)
the firmware's own management-processing counter was zero, so the frames are
not reaching firmware processing at all. This is not a host delivery problem.

## Findings

### 1. The whole WMT common initialization is missing (primary)

In the vendor stack, Wi-Fi never starts on a bare CONSYS. WMT power-on runs
first, over the BTIF/STP link to the CONSYS MCU, and only then does the WLAN
driver probe and download its own firmware through the HIF.

- Pinned [`opfunc_pwr_on`](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/common/common_main/core/wmt_core.c#L1026-L1090)
  performs hardware power-on and then `wmt_core_stp_init`, which calls the
  chip `sw_init`.
- Pinned [`mtk_wcn_soc_sw_init`](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/common/common_main/core/wmt_ic_soc.c#L975-L1250)
  then, in order: configures STP over BTIF, raises the MCU clock (for IC
  `0x0279`), downloads every ROM patch followed by a WMT reset, applies Wi-Fi
  and LTE coexistence settings, switches the BT and Wi-Fi PA LDOs on, sends
  `WMT_CORE_START_RF_CALIBRATION_CMD` (`01 14 01 00 01`) and waits for its
  event, switches the PA LDOs back, initializes coexistence, sets crystal
  trimming, the oscillator type when co-clock is enabled, and the FM strap.
- Pinned [`wmt_func_wifi_on`](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/common/common_main/core/wmt_func.c#L694-L727)
  only calls the WLAN probe for SOC chips. So RF calibration and the ROM
  patch belong to the WMT common power-on and precede every Wi-Fi start.
- Gemian requests `WMT_SOC.cfg` and both `ROMv3_patch_*` files at boot
  ([connectivity record](../2026-07-12-connectivity-wmt-recovery/README.md)).
  WMT status reports patch `20180307`.

The mainline candidates have no BTIF driver, no STP framing and no WMT
command path. The region-19 "WMT setup" in proposal 0048 prepares memory only.
No mainline boot has downloaded a ROM patch, run RF calibration or applied
coexistence and crystal settings. A firmware that runs, answers commands,
walks its scan state machine and still processes zero frames is what an
uncalibrated or unconfigured RF path would look like.

This is an inference from source order and the observed symptom, not a proof.
It is the largest unexamined difference between mainline and Gemian, and it
sits upstream of every receive gate sampled so far.

### 2. Rail differences around calibration (secondary)

Vendor calibration runs with both VCN33-BT and VCN33-Wi-Fi enabled
([`mtk_wcn_consys_hw_bt_paldo_ctrl` and `..._wifi_paldo_ctrl`](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/common/common_main/mt6797/mtk_wcn_consys_hw.c#L897-L975),
`CONSYS_BT_WIFI_SHARE_V33` is 0). Proposal 0041 requires VCN33-BT to be off
and never enables it. Gemian showed both VCN33 rails in use with carrier
([rail counts](../2026-09-26-gemian-wifi-reference/results/rail-clock-counts-v8-1.json)).
This matters once calibration is attempted; it is not by itself a reason for
zero reception.

### 3. The receive-sampling series has stopped paying off

Seven consecutive boots, from the [5 GHz scan](../2026-10-02-mt6797-passive-scan-5g/README.md)
to the [pool sample](../2026-10-02-mt6797-scan-pool-sample/README.md), each
read one or two firmware RAM words further back along the firmware's receive
path. Every result was "prerequisite present, zero frames": channel state
correct, mode 5, pool full, all statistics zero. Each boot costs a full
candidate, deployment, owner selection and recovery cycle. Proposal 0085 would
move one more step back to cached event masks. Even a positive answer there
would not say why no frame arrives, and the RF setup in finding 1 is
upstream of all of it.

### 4. There is no positive passive-scan reference

The [Gemian reference](../2026-10-02-gemian-passive-scan-reference/README.md)
returned BSS results, but the pinned vendor AIS code turns an empty-SSID scan
into an active scan, and Gemian was associated at the time. "Gemian receives
during a passive scan" has never been shown. This does not explain a zero
firmware counter on a channel with a live access point, but it means the
mainline passive-only design has no like-for-like control.

### 5. Issue #34 has not recurred

The CPU7 null-pool panic happened once, in the first START boot before the
region-19 WMT setup existed. Every START boot since
[WMT-before-start](../2026-09-29-mt6797-wmt-before-start/README.md), more
than twenty runtime receipts in the experiments above, completed without it,
and proposal 0051 stays in the profiles to name the workqueue if it returns.
The root cause is still unknown. Keep #34 open as a watch item rather than a
P0 gate, and close it once a teardown path (unbind with cancelled delayed
work) is exercised without a fault.

### 6. Everything is still one-shot diagnostics

Each profile stacks a single-use sysfs trigger and a retired lifetime on top
of the previous one; 44 `series-a53-wifi-*` profiles exist. That was the
right way to reach START safely. It does not form a driver yet: there is no
interrupt path, no packet DMA, no unbind or restart, and no reuse of
lifetimes. Consolidation should wait until reception works, but it is the
main body of work after that.

## Next steps

In order. Steps 1–2 need no mainline boot.

1. **Map the vendor power-on sequence against mainline.** One table, one row
   per step of `opfunc_pwr_on`, the consys hardware power-on and
   `mtk_wcn_soc_sw_init`, with columns for what mainline does today, the
   transport each step needs, and the files it needs. Include the BTIF
   register and DMA contract from the pinned vendor BTIF driver. Mark which
   steps plausibly affect Wi-Fi reception: ROM patch, RF calibration, PA LDOs,
   coexistence, crystal trim.
2. **Confirm the sequence ran on this device in Gemian.** Read-only: check the
   retained Gemian boot logs or the existing instrumented v8 kernel for the
   WMT patch-download and calibration results. If the instrumented kernel is
   reused, one bounded function trace of the `sw_init` steps is enough.
3. **First mainline boot: BTIF/STP liveness.** A small isolated profile that,
   after CONN power-on and CONMCU reset release and before the Wi-Fi HIF,
   drives BTIF by PIO and sends one harmless WMT query (the STP option query
   in `init_table_1_2`). Decision: an event comes back (link alive) or not
   (fix the transport before anything else). Check whether upstream
   `btmtkuart` STP framing and the `btmtk` WMT helpers can be reused.
4. **After transport liveness: common initialization, then scan.** Review and
   add the selected default/full-mode negotiation, enabled DLM script, ordered
   ROM patch download and WMT resets, selected conditional settings, PA-LDO/RF
   calibration (with VCN33-BT enabled as in the vendor order) and coexistence,
   then the existing Wi-Fi START and one passive channel-40 scan. Decision: a nonzero firmware
   management count or a BSS means reception is unblocked; still zero means
   compare the remaining vendor steps one at a time. The
   [source follow-up](STARTUP_FOLLOWUP.md) finds crystal trimming disabled and
   Gemian co-clock disabled; do not add those unselected branches. These boots
   are decision milestones, not a promise of completion in two attempts.
5. **After reception works:** association through mac80211 host MLME, then
   bounded traffic over PIO, then packet DMA and interrupts, then teardown and
   restart, then fold the diagnostics into one driver.

Park the [event-mask checkpoint](../2026-10-02-mt6797-scan-event-sample/README.md)
(proposal 0085) unfinished. Revisit it only if step 4 still shows zero frames
and the remaining vendor differences are exhausted.

## Limitations

This review used the repository, its receipts and pinned public vendor
source. It did not inspect private captures, retained firmware in the RE VM
or the device. Finding 1 is a source-order inference that steps 2–4 must test.
ROM patches and `WMT_SOC.cfg` are retained privately; their use in private
tests follows the existing firmware boundary and redistribution remains
separate.

## Startup follow-up

The [partial startup mapping](STARTUP_FOLLOWUP.md) adds retained Gemian patch
and coexistence observations, identifies the initial STP mandatory mode and
enabled DLM branch, and corrects the crystal-trim assumption: that branch is
disabled in both selected source files. BTIF PIO and complete failure handling
remain to be reviewed before a candidate.

The [query integration](../2026-10-03-mt6797-wmt-default-query/README.md) now
records implementation and a successful fetched compile package. It does not
admit a device test or establish transport, calibration or Wi-Fi reception.


The [common-initialization review](COMMON_INIT_REVIEW.md) narrows the selected
LTE/efuse/merged-interface branches and qualifies the calibration inference:
the vendor helper skips opcode-0x14 event-content comparison. It also records
ignored DLM/MCU-clock errors and overwritten PA-control outcomes. These remain
explicit design inputs for a checked, finite common-init owner after query
liveness; no new hardware action or candidate follows from the review.

## Default transport runtime follow-up

[Runtime 2](../2026-10-03-mt6797-wmt-default-query/results/runtime-2.json) now proves
one mainline default WMT query/event round trip with retained clocks, complete
preservation, passing regression and confirmed Gemian return. Earlier no-device
statements above describe the audit date/checkpoints. Continue step 4 by preparing
the checked mandatory set-options/full-mode boundary and its command owner;
ROM patch, calibration and reception remain unproved.
