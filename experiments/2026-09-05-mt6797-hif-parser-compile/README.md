# Private HIF and MTKE parser compile proposal

This packet proposes one compile-only profile containing the
[private HIF core](../2026-09-05-mt6797-wifi-hif-core/README.md) and the original
structural MTKE parser integrated at `1badfaa6`. It adds no caller, probe,
firmware acquisition, power ownership, normal command, EMI operation or START.
The HIF and parser remain separate APIs in the same private directory.

## Exact proposed integration

[proposal.json](proposal.json) lists the profile, pinned kernel source, complete
five-entry proposed series ordering, managed paths and required symbols.
Append the existing HIF core patch unchanged after the historical library
scaffold, then append [the parser patch](0002-wifi-mediatek-add-mtke-parser.patch).
The parser patch adds three source files and changes only the private directory's
Makefile and Kconfig. It selects CRC32 and compiles mtke.o and crc-kernel.o.
The kernel adapter calls `crc32_le(~0U, data, size) ^ ~0U`; the pinned kernel API
does not complement either end itself. CRC32 selects BITREVERSE and may choose
architecture optimizations. No private CRC implementation is added.

Use the proposed [fragment](config.fragment) with allnoconfig. NET, NETDEVICES,
WLAN and WLAN_VENDOR_MEDIATEK must all resolve enabled to reach the private menu.
ARM64, COMPILE_TEST, MT6797_HIF_CORE and CRC32 must resolve enabled. Keep modules,
LTO and dead-code elimination disabled for attributable emitted-object checks.
The historical library scaffold stays in the series but its symbol is disabled
in this new profile. Its old profile and completed build receipt remain intact.

The coordinator alone may edit canonical series, manifest and shared configs.
Appending two patches changes every profile using the shared provider series:
all require an invariant audit, and the managed provider source marker must be
refreshed once under serialized Buildbox control. Reuse the existing source path;
do not preserve it by making a second kernel tree. Existing immutable packages
remain attributable to their old source marker. A fresh out-of-tree build path
separates this profile's outputs. Exact revision, patchset/config/source hashes
must be computed from the eventual clean selected commit before submission;
this proposal does not invent an admitted build revision.

## Source and offline checks

[inputs.json](inputs.json) records original and packaged parser hashes, unchanged
HIF/protocol inputs and reviewed CRC/menu dependency hashes. Parser algorithm
and header bytes are unchanged; the two C file SPDX comments use kernel line
comment syntax. Host fixture copies remain pinned. No vendor source or firmware
bytes are included.

The generator constructs two tiny text commits, emits only the parser delta,
and checks exact replay. Run `python3 experiments/2026-09-05-mt6797-hif-parser-compile/scripts/verify.py`
from the repository root to reproduce it and run the synthetic differential and
exact-allocation sanitizer suites. [validation.json](validation.json) preserves
the results and full strict checkpatch output without exclusions. Its two
fixed-width-type checks refer to the original header's host-only typedefs, which
are excluded by __KERNEL__; retain them as explicit review findings. Missing DCO
and generic MAINTAINERS findings also remain. No certifying identity is invented;
this is not an upstream-ready submission.

The previous HIF packet tests the actual core with host scalar/time substitutions.
These parser suites use host zlib and do not compile or execute crc-kernel.c.
Kernel CRC compilation/linkage is an explicit outstanding gate, not inferred
from host success. No Buildbox or device operation is performed by these tools.

## Emitted-object acceptance

On the eventually admitted clean revision, use only the explicit Buildbox kernel
entry point. Require successful build and normal validated package retrieval,
then inspect the same backend job's objects read-only; the export package does
not contain all object files or vmlinux.

For every required object in proposal.json, require ELF64 little-endian AArch64,
nonzero FUNC definitions for every listed global function, matching source
hashes, and the corresponding .cmd proving kernel compilation with __KERNEL__.
Require both actual HIF scalar callbacks as local nonzero functions. Inspect
their ordered 32-bit command/FIFO loads and stores; barriers are ordering
observations, not a hardware completion guarantee.

Require mtke.o's unresolved mtke_crc32 reference and crc-kernel.o's unresolved
crc32_le reference, with the latter's initial/final complement in disassembly.
Require the private built-in.a to contain hif.o, mtke.o and crc-kernel.o, the CRC
library object to be built, and all seven public functions plus crc32_le to have
matching definitions in linked vmlinux and System.map. Missing, optimized-away,
stale or wrong-architecture objects fail this gate even if an Image exists.
Record the resolved .config, exact job/source markers and source hashes beside
these observations. Reject any host-test substitution define in kernel commands.

Scope the no-initcall/no-export/no-registration inspection to these three private
objects and source files; unrelated kernel exports are not failures. No DT node
or initramfs caller is provided. Build success establishes compilability and
linkage only. Runtime ownership and loader integration need separate review;
normal commands remain separate until a real post-START owner exists.
