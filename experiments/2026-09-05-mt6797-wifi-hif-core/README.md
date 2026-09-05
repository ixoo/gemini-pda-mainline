# Private MT6797 HIF execution core proposal

This original implementation connects the frozen INIT section helpers to ordered
kernel command/FIFO accesses. It has no runtime caller, platform probe or device
admission. The historical HIF compilation scaffold and its selected profile stay
unchanged; this is a separate logical patch for coordinator review.

## Contract and hypothesis

A future existing CONSYS owner must supply and retain a powered mapping covering
at least 0x1004 bytes, exclusive driver ownership, IRQ quiescence, reset exclusion
and a valid caller-owned INIT transaction. Allocation owns memory only; it does
not acquire hardware, seed credits or establish these prerequisites. The context
mutex serializes its own users only. Free is allowed after every user has stopped
and joined, and releases no provider resources.

The context owns its 2560-byte heap scratch buffer. Public calls use a nonwaiting
mutex acquisition and a caller-supplied absolute monotonic deadline, with at most
one second remaining. Ordinary sections are capped at 1 MiB. These are explicit
development policy ceilings, not measured performance or parser validity limits.
The caller retains immutable, distinct request/data/result storage and transaction
lifetime. No firmware ownership write, SMC, DT node, fake owner, EMI transfer,
START operation or broader loader is supplied.

The hypothesis is that actual core control flow preserves the frozen sequence,
credit, ACK and padding contract while stopping before another scalar action after
failure or deadline expiry. Host tests can test this; they cannot establish real
MMIO completion, hardware ownership or kernel compilation. Ordered readl/writel
cannot return recoverable bus errors here, and an absolute software deadline
cannot interrupt a stuck accessor. Injected host I/O failures test propagation,
not a kernel bus-fault recovery facility.

## Register evidence

The pinned Planet gen3 source at
`c5b0be85017ad0c599725e8273842efdbecdd88a` routes HIF register reads through
`include/hif.h` to `sdio_cr_readl` in `sdio_bus_driver.c`. Executed fields select
function 1, byte mode, fixed port and count four: logical register numbers belong
in the command, not in the physical mapping offset. The command is written at
physical offset zero and the value read at 0x1000.

| Logical register | Literal command |
| --- | --- |
| WCIR 0 | 0x10000004 |
| WHLPCR 4 | 0x10000804 |
| WRPLR 0x90 | 0x10012004 |

Only these three logical reads are exposed. The existing FIFO encoder whitelist
is unchanged. The source call-chain evidence was reviewed separately; no vendor
source is embedded in this original implementation.

## Packaging and validation

[inputs.json](inputs.json) pins the upstream commit, two parent Kbuild files,
seven unchanged styled headers and four new source files. The generator produces
[the logical patch](0001-wifi-mediatek-mt6797-private-hif-core.patch), verifies its
replay and uses disposable text fixtures rather than a Linux source checkout.
The proposed private Kconfig symbol is default-off and requires ARM64 and
COMPILE_TEST inside the wireless MediaTek menu. A future selected profile must
also enable the enclosing network/wireless menus; the existing scaffold profile
is not silently changed. Canonical series and manifest selection remain the
coordinator's responsibility.

Run `python3 experiments/2026-09-05-mt6797-wifi-hif-core/scripts/verify.py`
from the repository root. It reproduces the patch, executes the actual hif.c
with allocation/lock/clock/scalar-I/O substitutions and runs pinned strict
checkpatch without exclusions. [validation.json](validation.json) preserves
exact identities, compiler flags and complete review output.

Strict C11 plus AddressSanitizer and UndefinedBehaviorSanitizer passed three
literal register commands, six register failure positions, all 662 scalar
failure positions in a 2049-byte ordinary section, and 666 scalar deadline
boundaries. Additional cases cover expiry before the next chunk, pending ACK,
wrong ACK sequence/length/status, no credits, repeated sequence, invalid phase,
busy context, invalid inputs and the unchanged FIFO whitelist. Completed chunks
alone count as submitted; failure poisons the retained transaction, preserves
debits/history and never retries or refunds. Test source hashes are recorded.

Checkpatch has zero source findings, but retains the missing DCO error and generic
MAINTAINERS warning. This synthetic unsigned experiment archive is not ready for
upstream submission; no certifying identity or sign-off was invented. No kernel
build, backend access or device observation was performed for this packet.

## Decision and integration boundary

The host result supports review of the private implementation only. A kernel
build must be separately selected, committed and published before Buildbox use.
A runtime caller requires a real owner/probe contract and separately admitted
firmware acquisition, parser, EMI and boot sequencing. The ordinary request can
accept a validated parser section without coupling this patch to a parser ABI.
Normal commands use a separate resource contract and must not reuse INIT credit
admission. No device boot is requested by this proposal.
