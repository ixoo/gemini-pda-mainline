# Retained ROM patch order and wire addresses

The [read-only RE-VM analysis](results/rom-patch-order.json) verifies the two
retained files and stripped AArch64 loader against their selected entries in
the earlier corpus manifest. It decodes metadata using reviewed loader
instructions, joins the kernel ioctl/array selection and source header layout,
and checks the source-defined fragment arithmetic. No loader or vendor API was
executed; no new VM file or hardware action was created. These are retained-file
facts, not proof of the currently installed Gemian file identities or patch
applicability on a new mainline power lifetime.

| Download sequence | Retained file | Firmware address wire bytes | Body bytes after 28-byte header | 1000-byte fragments / final bytes |
| --- | --- | --- | --- | --- |
| 1 | `ROMv3_patch_1_1_hdr.bin` | `00 00 0a f0` | 46444 | 47 / 444 |
| 2 | `ROMv3_patch_1_0_hdr.bin` | `00 00 09 00` | 210876 | 211 / 876 |

The source WMT header comprises 16 date bytes, four platform bytes, two hardware
version bytes, two software version bytes and four patch-version bytes. The
selected loader seeks to offset 22, reads the version bytes separately, then
reads the four-byte patch-info word at offset 24. The high nibble of its first
byte supplies patch count, and the low nibble supplies download sequence. It
clears that first byte when forming the four address bytes passed to the patch
info ioctl. Both retained files describe a two-patch group; their sequence
values are one and two. Their little-endian address values are `0xf00a0000` and
`0x00090000`. These are firmware command fields, not AP physical/MMIO addresses
or independently admitted memory ranges.

The matching kernel ioctl checks the one-based sequence against patch count
and stores each descriptor at sequence minus one. The control getter returns
that ordered descriptor, and the SoC patch downloader copies its address bytes
into the second patch-address command before fragment transfer. Thus lexical
filename order would reverse the selected order. A future constructor must use
validated metadata rather than filename suffix or filesystem enumeration.

The retained Gemian log's successful summaries are 47/444 then 211/876, matching
this ordered pair's source-based arithmetic. That corroborates the association;
it does not substitute for installed-file hashes, checked hardware/ROM-version
selection, address applicability or proof that every earlier script succeeded.
The reviewed loader does not consistently reject short reads; a new parser must
require complete bounded input instead of inheriting that policy. Four synthetic
metadata refusals cover absent/empty body, unselected count and invalid sequence.

All 258 fragment command/event exchanges and the two address exchanges per patch
need finite transport budgets. Each completed patch is followed by reset in the
selected source. The current 11-byte query's fixed TX/16-byte RX path cannot
simply be widened to transmit 1005-byte patch commands: review FIFO progress,
full-STP acknowledgements/checksums, reset epochs and every failure lifetime.
Firmware remains private with unresolved redistribution rights. First-query
liveness and the remaining [common-init contracts](COMMON_INIT_REVIEW.md) still
precede any effect-bearing patch-transfer candidate.

The [strict constructor](ROM_PATCH_CONSTRUCTOR.md) now validates the selected
metadata and builds every fragment without mutating firmware input. Synthetic
sanitizer tests and native retained-file checks in the RE VM passed; installed
attribution, hardware applicability and transfer admission remain unproved.

The same constructor now includes the complete selected address/fragment/reset
order, with exact pinned-source vector comparison and 264 synthetic full-STP
state exchanges. See [the construction boundary](ROM_PATCH_CONSTRUCTOR.md#complete-selected-patch-command-order).

The later [installed-pair review](ROM_APPLICABILITY.md) establishes exact
installed hashes for both retained files on one checked Gemian boot. It also
identifies unchecked ROM returns and an inconsistent register-read event
length, so checked mainline applicability remains open. Earlier statements
above describe the retained-file-only checkpoint.
