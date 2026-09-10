# Reject failed native DMA mappings

The unselected [patch](patches/dma-map-error/0001-wlan-reject-failed-native-DMA-mappings.patch)
adds the missing DMA API error checks to the two MT6797 AHB port operations.
It follows [startup retention](PROBE_RETENTION.md). This is an implementation
checkpoint, not a candidate or device result; DMA timeout/count-escape handling,
shared ownership and independent recovery remain unresolved.

The [receipt](results/dma-map-error-sources.json) pins the complete parent and
child `ahb.c`, the two native fixture headers and the DMA API guide from Gemian
revision `59e00a9144d782e148332009a835b99c43382467`. The guide requires checking
`dma_map_single()` with `dma_mapping_error()` before using the returned address.
Both inspected port functions omitted that check and passed the result to
`DmaConfig()` and `DmaStart()`. Their `ULONG` address fields retain the full
native return width; checking for zero or a guessed sentinel is not a substitute
for the DMA API result.

## Change and limits

Each new check occurs immediately after mapping, before the mapping witness,
DMA configuration, start, poll, stop or unmap. A failed mapping reaches one
helper that sets the existing fatal flag, aborts capture, performs the native
HIF unmask request, unlocks the HIF lock and balances the clock request when
its callback owner exists. The port returns false. No unmap is issued for a
failed mapping, and no DMA-engine register is programmed on this branch.

Command setup and the HIF mask request already precede mapping in the native
path. Their writes are not undone by an error check. The helper uses the same
unmask/unlock/clock-disable order as the successful native release; this is
software request accounting, not proof of the hardware's interrupt, FIFO,
clock or common-power state. The helper neither resets nor reinitializes the
HIF. Capture abort invalidates the cycle; it does not create a successful
mapping record for the failed attempt.

The existing fatal TX entry already returns false. Fatal RX entry now does so
as well, instead of reporting success without a transfer. Its reset and
firmware-owned entry behavior is preserved. Sequential later port requests
are refused; a caller already past the entry check, a competing reset or HIF
reinitialization is not excluded by this patch. No new concurrency or recovery
contract is inferred from the fatal flag.

Successful mappings retain their native programming and release path. The
[deadline and idle-count failures](DMA_HOOKS.md#selected-deadline-and-idle-exits)
after programming remain unchanged. In particular, this patch does not make an
unproven idle safe to unmap, or repair a native deadline's retained lock.
The archive identity is synthetic, with no DCO certification or upstream
submission claim.

## Verification

The [fixture](test-dma-map-error.py) reuses the native DMA lifetime harness and
executes both complete parent and child port bodies with the pinned native
macros and configuration type. DMA, MMIO, clocks, locks and capture helpers are
injected. Eight comparisons cover RX/TX, successful/failed API results, and
zero/a nonzero 64-bit address. This confirms that the API result, rather than
the address value, selects refusal.

All eight pass. The parent programs and unmaps the injected failed addresses;
the child returns false without configuration, start, poll, stop or unmap,
balances the modeled lock/mask/clock state and refuses subsequent RX/TX entries.
Successful mappings retain those native operation counts. Strict host
compilation, exact patch replay/reversal and strict Checkpatch pass, with
explicit unused-code fixture exceptions and the established legacy-name and
synthetic-sign-off Checkpatch exceptions. These are injected source executions,
not physical DMA observations.

`check-startup-objects.py COMMIT --dma-map-error` selects 31 patches and the
existing 19-unit native compile scope, verifies source/API pins and runs the
focused fixture. The [native compilation receipt](results/dma-map-error-object-compile.json)
records success at `b3559e46e145db184b06616e3d4e6cc7ca94c91d`. All 91 regular
package files match the remote inventory and the 90-entry checksum manifest;
its SHA-256 is `8acd6b1c89f8b474d2fec169f27558c243d5f4d5c4885946fa6f53e81a9067ee`.
The compiled AHB source matches the pinned output. Native commands retain
baseline warning suppression; empty diagnostics are not warning-clean evidence.

Full linking, DMA failure containment, consumer isolation and reviewed
controller/recovery integration remain necessary before device admission.
No device was accessed for this checkpoint.
