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
