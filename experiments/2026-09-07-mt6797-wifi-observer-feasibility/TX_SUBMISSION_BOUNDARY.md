# Firmware payload identity at the transmit boundary

The [request/firmware join](REQUEST_FIRMWARE.md) identifies the native ON worker
and the mapped image. Its boundary hashes cannot identify the later transmit
copy. The next byte witness must attach to the actual transport buffer and its
transfer identity. Adding only another loader-side digest would preserve this
gap.

## Source and executable counterexamples

The existing [source receipt](results/capture-sizing.json) pins the complete
Gemian `nic_tx.c`, `hal.h`, `hif_tx.h` and `ahb.c` files at
`59e00a9144d782e148332009a835b99c43382467`. The first three are verified before
the [focused test](test-tx-submission-boundary.py) extracts and compiles the actual
`nicTxInitCmd()` and AHB-selected `HAL_PORT_WR`/`HAL_WRITE_TX_PORT` definitions.
Adapter layout, memory-copy fault injection and the port writer are host shims.
The mask and alignment constants are checked against the pinned header.

The four cases pass with AddressSanitizer and UndefinedBehaviorSanitizer:

| Case | Executed result | Consequence for observation |
| --- | --- | --- |
| Ordinary 2056-byte command | Native staging copies the command into the adapter's coalescing buffer and supplies that buffer to the port writer | The loader allocation is not the final supplied pointer |
| Port writer returns false | `nicTxInitCmd()` still returns success | Worker/image/native-command success cannot substitute for a port/transfer result |
| Injected corruption immediately after staging | Port receives an altered payload byte while the original command stays byte-identical | A digest of the original allocation or command can miss a changed transmit copy |
| Synthetic 39-byte command | Port receives 40 bytes, including the pre-existing byte at offset 39 | A digest over alignment padding is not a digest of only the logical command |

The macro clears one dword after the aligned supplied extent when capacity
permits; it does not initialize the intervening alignment byte or the rest of
the coalescing buffer. The 39-byte case exercises the generic staging boundary,
not one of the selected firmware's eight payload chunks. All eight selected
chunk lengths plus their eight-byte headers are already word aligned.
The corruption is deliberately injected in the memory-copy shim, not evidence
that native concurrency or corruption occurs on the PDA.

The separately checksum-verified native `ahb.c:1046–1298` expands the aligned
size to the runtime block size, then uses that count for DMA mapping or the
PIO word loop. Thus a 2056-byte logical command with block size 512 has a
2560-byte bus extent. The staging macro initializes only four of the additional
504 bytes. The test executes neither this expansion nor DMA/PIO; this conclusion
is source analysis, consistent with the existing
[ordinary-section contract](../2026-09-05-mt6797-wifi-contract/ORDINARY_SECTION.md).
The original upstream-oriented PIO helper already supplies deterministic zero
padding. Do not change native padding merely to make observer hashes agree.

## Selected implementation boundary

Use three distinct extents: firmware payload, logical command and bus transfer.
The eight selected chunks total 14832 payload bytes, but neither command headers
nor block padding belong in that payload digest. A future producer must bind
each actual chunk's image/section/offset to the command and coalescing buffer,
then observe the selected payload span before DMA ownership transfer or PIO
reads. It must reject a missing, repeated, cross-task or mismatched join and
require the existing transfer's attributable completion. A false early port
return cannot acquire a successful transfer witness through the caller's
unconditional success.

For DMA, inspect payload bytes before `dma_map_single(..., DMA_TO_DEVICE)`;
do not add CPU reads of a device-owned mapping. A pre-map digest still requires
a stable-buffer ownership contract until completion. For PIO, a pre-loop digest
alone still does not prove every value subsequently written. These are explicit
implementation requirements, not properties established by this fixture.
The current decoder must continue to refuse a submitted-byte claim until that
producer, lifetime contract and typed transfer join exist. Full-cycle control,
resource isolation and device admission remain separate.

## Reproduction and scope

Place the three source files named above in an ignored private directory and run
`python3 experiments/2026-09-07-mt6797-wifi-observer-feasibility/test-tx-submission-boundary.py DIRECTORY`.
The test checks complete-file source pins, compiles with strict host warnings
and both sanitizers, then runs four cases. Temporary compiled files are removed.
No vendor source is included in the test or published as an additional copy.

This is an executable boundary audit, not an observer implementation, full
native translation-unit build, firmware execution result or device test. It
changes no kernel patch, profile, boot candidate or hardware action.
