# Persistent Wi-Fi capture constraints

The existing same-version Gemian pmsg storage is a possible backing store, but
the old process-context witness helper is not a suitable direct writer for all
required Wi-Fi observations. This assessment selects no new memory range,
changes no kernel code and admits no physical write or recovery action.

The [source receipt](results/persistent-capture-sources.json) pins five complete
public Git objects at the selected Gemian revision and the retained build
configuration. The earlier [pmsg witness](../2026-08-28-a72-pmsg-witness/DESIGN.md)
and its [runtime result](../2026-08-28-a72-pmsg-witness/results/runtime-attempt-1-complete-pass-20260829.txt)
supply same-version retention evidence for their exact candidate, not a
replayable Wi-Fi artifact or cross-version mainline storage contract.

## Lock context

The old `pstore_write_pmsg_kernel()` takes `pmsg_lock`, a mutex, before calling
the backend. It is intended for fixed process-context sites. In the selected
power provider, `disable_subsys()` holds `mtk_clk_lock` across both the initial
state check and `sys->ops->disable()`. The pinned header defines that lock as
`spin_lock_irqsave`. Therefore a direct call to the old mutex-taking helper
from those status-read sites is invalid. Moving the physical read outside the
lock or repeating it later would change the operation being observed.

A deferred worker could copy an ordinary RAM record into pmsg later, but it
would leave the interval before that worker runs unprotected against reset or
a stalled cycle. Such a design cannot silently claim persistent in-progress
capture. A separate atomic-context-safe writer or an explicitly weaker capture
contract is needed; no such writer is implemented here.

## Capacity and write semantics

The retained configuration requests a 64-KiB pmsg zone. The persistent-ring
header contains three 32-bit fields; with no ECC allocation, usable payload is
65,524 bytes. The historical recovered pmsg file had exactly that size, but
this does not establish a future candidate's platform parameters or available
space. Candidate and recovery must verify the same resolved layout, ECC and
ownership before selecting it. The broader reserved area's size is not the
pmsg payload budget.

`ramoops_pstore_write_buf()` returns zero for a present pmsg zone after calling
`persistent_ram_write()`. The latter silently keeps only the tail of an
oversized write, overwrites old ring content as later writes wrap, and returns
the original requested count. Neither return proves retention of a complete
record sequence. The earlier witness actually lost its initial record; its
accepted suffix rule cannot be imported into a joined Wi-Fi lifetime trace.

The ring writer updates size/start metadata before copying payload bytes and
then updates header ECC. An interrupted write can therefore leave metadata
covering incomplete payload. A serialization lock alone would not establish
record commit ordering or power-loss durability. The future format needs
independently recognizable complete records, cycle identity, ordering and
integrity checks, and refusal on malformed, missing or overwritten required
records. It must reserve room for a failure/overflow terminal before admitting
normal records and stop recording before wrap; these limits are not provided
by the existing backend.

The [focused reproduction](test-persistent-ring.py) compiles the actual ring
writer with injected storage helpers. It confirms oversized-write truncation,
subsequent overwrite, the original return counts and metadata publication
before the first payload copy. The host compile uses GNU C11 and
`-Wall -Wextra -Werror -Wno-sign-compare`; the exception preserves the original
signed/unsigned comparison. This is an ordering/format test, not a physical
persistence, memory-barrier or concurrent-writer test.

## Next implementation boundary

Keep the existing reserved-memory layout as the first design option. Before
adding a writer, account for every producer and enumerate the bounded record
inventory for one complete native cycle, including DMA mapping/programming,
positive idle before unmap, firmware-stop reads and coherent common OFF.
Polling observations must preserve the original read count and short-circuit
order. No guessed transfer count or silently discarded overflow can establish
the complete cycle. If the resulting inventory cannot fit the verified zone,
resolve that conflict before choosing another layout or reducing evidence.

Then bind the exact capture budget to the separately reviewed watchdog owner
and recovery reader. The controller's four-second wait and the historical
12-second recovery window do not supply this contract. No observer, controller,
new runtime writer, kernel image or device action is introduced by this review.

## Source-derived record inventory

The [sizing receipt](results/capture-sizing.json) pins six complete source files
and reuses the existing sanitized retained-image inspection. It separates
firmware payload chunks from actual DMA transactions and from polling reads.

For the selected MT6797 divided loader, sections 0 and 1 use HIF download;
sections 2 onward take the conditional EMI-copy path. The retained image's
first two sections contain 5,840 and 8,992 bytes. At the source's 2,048-byte
`CMD_PKT_SIZE_FOR_IMAGE`, these produce three and five payload chunks:
`2048, 2048, 1744` and `2048, 2048, 2048, 2048, 800`. The other sections,
331,296 and 65,392 bytes, must not be charged as HIF payload chunks.

This gives eight payload submissions if the selected load completes, not eight
DMA transfers for the whole cycle. Section-configuration commands, subsequent
initialization commands, events and shutdown are additional. `nicTxInitCmd()`
passes through `HAL_WRITE_TX_PORT` to WTDR1, but the AHB writer takes DMA only
when its runtime `use_dma`, `fgDmaEnable` and callback checks also pass. Neither
the submission count nor the helper's unconditional success return proves a
mapping, completion or firmware execution. Common WMT patches are a separate
BTIF transfer path and must not be mixed into WLAN AHB counts.

The native EN idle loop can call its polling helper 100,001 times before the
count escape. Even one byte per read would exceed the nominal pmsg payload
capacity. The INTFLAG loop is time-based, so its read count is not supplied by
the source's five-second comparison. Capture each loop as an entry plus a
summary of existing reads: read count, last raw value, whether a read occurred,
and the exact exit reason. Preserve the original calls and branch ordering.
A loop that stalls before its summary remains an incomplete phase; its entry
must never be accepted as positive idle. Counter overflow must also invalidate
the summary rather than wrap into a small count.

The required record families are now:

| Family | Required content and joining rule |
| --- | --- |
| Cycle and initializer | Candidate/boot identity, single cycle identity, component entry/result, selected HIF and firmware identities; no arithmetic aggregate as readiness. |
| DMA acquisition | Transaction identity, device identity, RX/TX direction, requested and rounded byte counts, full DMA API address and selected mapping branch. |
| DMA programming | Same transaction, actual low SRC/DST and LEN/CON store arguments, existing ADDR2 read values and store arguments, and start/interrupt-control arguments. No extra readback. |
| DMA completion/release | INTFLAG and EN loop summaries, ACK/stop operation arguments, exact timeout/escape/reset branch, and unmap entry/completion joined to a prior positive idle result. |
| Firmware and EMI | Section/configuration outcomes, conditional EMI extent/protection/copy outcomes, stop-command outcome and actual WCIR-read completion/value with exit branch. No payload or calibration bytes. |
| Shared OFF | Actual provider dispatch, shortcut state pair, protection/control arguments, existing polling summaries and the terminal pair of clear power bits; retain short-circuit read validity. |
| Isolation and terminal | Unexpected consumer, transmit/mode/reset/boost activity; completion, failure or overflow; no successful terminal with missing required records. |

This inventory selects loop summaries rather than per-poll logging while
retaining every DMA transaction. It does not yet choose encoded record sizes,
a maximum transaction count or a new memory layout. The full-cycle transfer
count remains unbounded by the inspected sources; the writer must enforce a
finite admitted capacity and refuse overflow. The eight-chunk calculation
makes a compact capture plausible but does not prove that one complete cycle
fits. The next step is an explicit byte layout and capacity calculation for
these fields, followed by the atomic-context writer and recovery contract.
