# Native source observation feasibility — 2026-09-08

## Decision

Compiled observation at existing native reads is a distinct possible mechanism,
but is not yet an admitted experiment. Function entry/return tracing would be
insufficient even if available. The selected public source exposes useful
values inside DMA and shutdown loops, together with paths that can report
success without the required observation. No observer was implemented and no
hardware was accessed in this assessment.

This narrows the next action: select a reproducible candidate source and
configuration, then design capture at the actual accesses below. A new candidate
requires its own runtime baseline; it need not reproduce the unknown original
source revision of the installed Gemian image. Do not
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

## Gemian build selection follow-up

The [source comparison receipt](results/native-build-selection-sources.json)
pins twelve individually retrieved files from
`gemian/gemini-linux-kernel-3.18@59e00a9144d782e148332009a835b99c43382467`.
All six observation-site files above are byte-identical to the Planet inputs.
This source already has a [Buildbox compile setup](../../docs/BUILDBOX.md#gemian-observer-compile-review-lane)
with a pinned compiler and retained configuration. Its earlier A72 hook
reconciliation does not attribute this Wi-Fi implementation to the installed
binary, and its A72 observer patches are not selected for this work.

The retained configuration was rehashed against its published digest. Together
with the retrieved makefiles and headers, it establishes the following source
selections, subject to checking the actual complete compiler invocation:

- `CONFIG_MTK_COMBO_CHIP="CONSYS_6797"` and `CONFIG_MTK_COMBO_WIFI=y` select
  built-in gen3 and its `ahb.o`, `ahb_pdma.o`, and `sdio_bus_driver.o` objects.
  The gen3 makefile adds `_HIF_SDIO` only to the other chip branch.
- `hif.h` sets `CONF_MTK_AHB_DMA=1` and `CONF_HIF_DMA_INT=0`; `ahb.c` leaves
  `MTK_DMA_BUF_MEMCPY_SUP` commented out. These select polling and DMA API
  mapping in the inspected source unless another input overrides the symbols.
  Runtime `use_dma`, `fgDmaEnable`, and callback availability still determine
  whether a particular transfer takes DMA. The address fields are `ULONG`;
  their effective width and any register-write narrowing need compiled review.
- `CONFIG_OF=y`, disabled `CONFIG_MTK_CLKMGR`, and the platform header's
  `CONSYS_PWR_ON_OFF_API_AVAILABLE=1` select the common CCF power wrapper.
  Other consumers and actual provider dispatch remain runtime observations.

The exact power-provider source additionally defines `TOPAXI_PROTECT_LOCK`.
Its selected protection helper at lines 400–458 has a count-limited wait followed
by diagnostics and `BUG()` on timeout. That is a fault terminal, not an ordinary
successful return or a recoverable timeout. Its successful polling exit can
supply the existing protection-status observation without adding a read.

At lines 2098–2104, `sys_get_state_op` reads both status registers but reports
ON only when both bits are set. With `CHECK_PWR_ST=1`, `disable_subsys` at
2345–2349 skips the physical OFF sequence whenever this result is false.
Consequently, one set bit and one clear bit can take the same shortcut as both
bits clear. Record the raw pair and the shortcut separately; neither the false
state result nor successful disable return proves coherent OFF. This differs
from the terminating OFF loop, whose OR condition requires both bits clear.

This closes the source-file compatibility question for the reusable Gemian
build setup. The next implementation prerequisite is a concrete one-cycle
capture/recovery design and compiled verification of the selected paths, not
another search for the unknown original kernel revision. A new instrumented
image still needs its own baseline and admission before any radio operation.
