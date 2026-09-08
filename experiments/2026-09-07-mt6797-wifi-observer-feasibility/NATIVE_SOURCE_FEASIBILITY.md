# Native source observation feasibility — 2026-09-08

## Decision

Compiled observation at existing native reads is a distinct possible mechanism,
but is not yet an admitted experiment. Function entry/return tracing would be
insufficient even if available. The selected public source exposes useful
values inside DMA and shutdown loops, together with paths that can report
success without the required observation. No observer was implemented and no
hardware was accessed in this assessment.

This narrows the next action: establish an exact, rebuildable known-good source
and configuration, then design capture at the actual accesses below. Do not
repeat the closed retained binary observer or the unavailable live ftrace path.

## Reproducible source boundary

All six files were fetched individually from
`lineage-geminipda/android_kernel_planet_mt6797` at
`c5b0be85017ad0c599725e8273842efdbecdd88a`. Byte lengths and SHA-256 digests
matched the existing ledgers:

- [HIF DMA sources](../2026-09-05-mt6797-wifi-contract/results/hif-dma-sources.json):
  `ahb.c`, `ahb_pdma.c`, `wlan_lib.c`, `mtk_wcn_consys_hw.c`.
- [Initialization sources](../2026-09-05-mt6797-wifi-contract/results/init-bounds-sources.json):
  `hal.h`.
- [SPM sources](../2026-09-05-mt6797-wifi-contract/results/spm-key-order-sources.json):
  the Planet `clk-mt6797-pg.c` entry.

Line numbers below refer to these exact files. This is public-source analysis,
not attribution of the installed Gemian binary. Configuration alternatives
remain alternatives until the candidate configuration and compiled code prove
which path is active. No vendor source is copied into this repository.

## Required observations and false positives

| Required evidence | Existing source site | Capture requirement and limitation |
| --- | --- | --- |
| DMA API address joined to programming | `ahb.c` mapping/configuration paths around 911–999 and 1176–1260; `ahb_pdma.c` 232–299 | Record the full DMA API return before conversion, device, direction and length, actual SRC/DST write arguments, and ADDR2 read/write arguments. The preallocated-buffer branch is not a DMA API mapping. Write arguments prove issued programming, not register readback or endpoint translation. |
| Completion and positive idle before unmap | `ahb_pdma.c` 345–372; `ahb.c` completion and EN loops | Capture existing INTFLAG and EN read results with their transaction and loop exit reason. Stop only disables interrupts; its idle loop is inactive code. The caller's EN loop has a count escape before unmap. A stop call or successful transfer return is not positive idle. |
| Firmware stop | `wlan_lib.c` 941–1047 | Capture stop-command acceptance, actual WCIR read completion/value and the exact exit branch. Adapter-stop returns its initially successful status even when guards skip stop, fallback succeeds, or timeout/reset occurs. Require the ordinary READY-clear path for this discriminator; distinguish fallback, reset and skipped paths. |
| WCIR value validity | `hal.h` 217–238; `ahb.c` 703–720 | The non-SDIO wrapper can queue a read to the HIF thread and ignores the result of its interruptible completion wait. A caller-local value alone does not establish that this read completed. Capture the actual register access and join it to the stop request; prove the selected threading path. The AHB accessor itself returns true after its MMIO read and does not report a separate bus-error result. |
| Coherent CONSYS OFF | `mtk_wcn_consys_hw.c` 616–680; `clk-mt6797-pg.c` 574–618, 2298–2445 | The common wrapper's clock-disable call returns void. The selected CCF provider can poll bus protection and both power-status registers, but configuration can omit ACK polling and provider dispatch can skip work. Capture actual provider execution, selected branch and existing status reads, joined to this cycle. A common-layer success or clock reference release is insufficient. |

The SDIO `HAL_MCR_RD` implementation at `hal.h` 68–91 can skip a read on
`ADAPTER_FLAG_HW_ERR`; that is not the non-SDIO implementation above and must
not be used to explain AHB behavior without a build-path match.

The provider's OFF test uses short-circuit OR between the primary and secondary
power-status reads. A successful terminating evaluation reads both and sees
both CONN bits clear. Intermediate evaluations need not read the secondary
register. Instrumentation must preserve this access count and ordering rather
than adding unconditional reads. Bus protection and control writes also need
their own attributed observations; the pair of OFF bits alone does not prove
the complete coherent-OFF predicate. Some native provider loops are unbounded,
so a finite observer buffer does not make the enclosing radio operation bounded.

## Remaining admission work

A concrete candidate must identify the actual source/configuration, DMA address
width, selected mapping path, HIF-thread completion path, CCF provider and other
CONSYS consumers. It must specify one joined load/shutdown cycle, bounded
capture storage, overflow refusal, access-preserving hooks, acquisition effects,
radio-operation limits and recovery. A hook must not call a polling helper again
just to log its value. No payload, firmware or calibration capture is needed.

The successful-cycle observation would still not establish failure retention,
remove safety, or a production upstream driver. Those boundaries remain in the
[HIF architecture assessment](../2026-09-07-mt6797-hif-upstream-architecture/README.md).
This assessment changes no hardware-support claim and authorizes no build,
deployment, boot selection or radio action.
