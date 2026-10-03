# WMT common startup mapping: partial source review

This follow-up advances the [audit](README.md), without a build or device action.
The [receipt](results/startup-followup.json) pins independently retrieved vendor
and Gemian-v8 source files and a retained private Gemian log. The two
`wmt_ic_soc.c` files are byte-identical. This is not a complete hardware power,
BTIF register or failure-lifetime contract; no candidate is admitted.

| Selected vendor step | Current mainline relationship | Transport / input | Remaining question |
| --- | --- | --- | --- |
| `opfunc_pwr_on`: hardware power, then STP initialization | CONSYS/rails/reset and WMT memory have individual runtime receipts; no common STP executor | AP resource owner, then BTIF | Compare complete hardware order and cleanup, not names alone |
| `wmt_core_stp_init`: open transport, configure BTIF mandatory mode, obtain chip operations, call `sw_init` | Absent | BTIF/STP default-mode exchange | Default-mode framing must precede full-mode framing |
| `sw_init` lines 1009–1045: query default STP, set options, switch host to full mode, wait 10 ms, query again | Absent | WMT query/set events through BTIF | First liveness test should stop after a matched default query; it cannot assume full-mode setup |
| Lines 1046–1050: enabled DLM power script | Absent | WMT register commands | Review exact targets and effects; do not skip this enabled branch |
| Lines 1053–1104: prepare ordered patch inputs, raise MCU clock, download each patch and reset, restore clock | Absent | BTIF/STP plus private ROM patch metadata and bytes | Validate identity, order, addresses, fragments, replies and finite failure handling |
| Lines 1120–1168: conditional efuse/voltage and LTE filter configuration | No equivalent common command sequence | WMT plus selected build/configuration | Check actual preprocessor branches; do not copy every conditional setting |
| Lines 1169–1190: BT and Wi-Fi PA rails on, calibration script, rails off | Existing WLAN-only rail handling omits this calibration lifetime | Shared regulator owner plus WMT calibration command/event | Prove rail mode/order and cleanup; vendor return overwrites are not an error-handling model |
| Lines 1192–1197: coexistence initialization | Absent | WMT and private WMT configuration | Configuration lookup is logged; exact applied fields/events remain unverified |
| Lines 1199–1201: optional crystal trimming | Disabled in both selected source files | Private board record if enabled | Not a missing executed step in this source; do not invent trim writes |
| Lines 1207–1219: oscillator command only for co-clock | Gemian logs co-clock disabled | WMT if applicable | Do not require the unselected oscillator branch |
| Lines 1226 onward: FM strap and conditional diagnostic settings | Absent | WMT/configuration | Determine reception relevance and exact selected branches before implementation |
| WLAN function-on/probe and WLAN image START | Already observed through the mainline HIF executor | Existing WLAN HIF and private WLAN firmware | Must follow successful common initialization; firmware responsiveness alone is not RF reception |

## Retained Gemian evidence

The private v8 boot log records two successful patch-download fragment summaries,
then `wmt_stp_init_coex` configuration lookup and co-clock disabled. The
[v8 build receipt](../2026-09-26-gemian-wifi-reference/results/build-v8.json)
pins Gemian commit `59e00a9144d782e148332009a835b99c43382467`; the inspected
WMT source at that revision matches the vendor source byte for byte.

Under that selected source path, a calibration-script failure returns before
coexistence initialization. Reaching coexistence therefore supports prior
completion of the vendor calibration script. The [script-helper review](COMMON_INIT_REVIEW.md)
finds that opcode `0x14` skips event-content comparison; this does not establish
a checked calibration-success status. This is a source-conditioned inference: no explicit
calibration completion event was recovered, exact compiled-function equivalence
has not been checked, and successful calibration is not measured RF performance.
The absence of an explicit log is not evidence of failure.

The older direct WLAN off/on trace kept Bluetooth on and never exercised common
power-on, so its missing `sw_init` calls cannot disprove this boot sequence.
Do not repeat that consumed trace to answer a different question.

## Next work

Review the pinned `drivers/misc/mediatek/btif/common/mtk_btif.c`, `btif_plat.c`,
`btif_dma_plat.c` and headers for PIO initialization, FIFO/status semantics,
clock/reset/IRQ ownership and DMA exclusion. Map the remaining hardware power
steps and STP mandatory framing/parser before implementing the isolated query.
Resolve enabled DLM and build-conditional scripts before any full calibrated
scan candidate. Proposal 0085 remains parked. No source review here authorizes
calibration, register writes or a boot by itself.

The [BTIF mandatory-mode review](BTIF_MANDATORY.md) now pins framing vectors
and selected FIFO/register behavior. IRQ-masked polling, aliased FIFO control,
read effects and DMA exclusion still require resolution before implementation.


The [common-initialization review](COMMON_INIT_REVIEW.md) now joins the selected
v8 configuration and inherited Makefile flags: LTE filtering is selected, while
the MT6580-only efuse voltage branch and merged PCM are not. It records DLM,
MCU-clock and PA-control error handling that a new owner must not silently reuse.
No additional command or full initialization candidate is admitted.
