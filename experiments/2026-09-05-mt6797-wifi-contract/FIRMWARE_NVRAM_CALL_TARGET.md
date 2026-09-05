# Bounded resolution of the call carrying the NVRAM reference

On one statically selected path, the computed call carrying the NVRAM reference
has a target derived from instruction immediates inside the retained plaintext
code mapping. No memory load or runtime function-pointer table is required to
resolve that target on this path. Computed call encoding alone was therefore
not evidence of unresolved table dispatch. The target's purpose and the
incoming entry to the caller remain unidentified.

## Local provenance method and assumptions

This slice reused the private project and entry/reference candidates from
[the predecessor trace](FIRMWARE_NVRAM_PATH.md). It did not repeat the broad
firmware scans, change anchors or inspect another firmware image. The call is
the previously identified first call following the reference pair.

An initial straight-line inspection stopped at a control transfer without
claiming target resolution. A bounded graph search then selected one path
from the candidate entry to the same call, following direct edges and
fallthrough without entering callees. The search was capped at 256 discovered
addresses. The selected path contains 21 instructions through the call and
one conditional edge. Its branch choice is assumed, not a proven condition
or runtime observation. No earlier call was encountered on this path.

Local Ghidra p-code propagation starts with unknown register values and tracks
copies, constants, integer operations and extensions with output-width
truncation. Unsupported results remain unknown. Instruction-local temporary
state is discarded between instructions; a prior call would invalidate tracked
state conservatively. The implementation can classify reads from the retained
plaintext mapping under the provisional little-endian data assumption, but
this path evaluated **zero** such loads. The selected CALLIND operand resolves
from immediates, so this result does not depend on those data-load semantics.
The private target is saved in the existing project rather than printed.

This is a narrow conditional-path derivation, not a generic validator,
emulator, complete data-flow analysis or proof that another path computes the
same target. The existing assumption that execution can enter the candidate
caller remains open.

## Bounded target-prefix check and remaining meaning

The target lies in plaintext section 2 and is two-byte aligned. At that
candidate address, seven instructions decode through the first control
transfer, which is not computed. The first instruction reads and writes the
stack pointer. This supports a callable-code candidate, but does not establish
a unique function boundary, complete ABI, all paths or return behavior.
No further callee traversal was performed.

The useful change is that the caller's local target value is now available
for later semantic work; reconstructing an unknown table or incoming register
is unnecessary for this selected path. The missing premises are the target's
actual contract and an attributable incoming transfer to the caller. Passing
the NVRAM-associated address still does not establish diagnostics, command
`0x48` handling, record application, or EFUSE/default precedence. These
uncertainties do not block independent host implementation.

## Retention and validation

The small existing private guest project, scripts and bounded logs are retained
under the previous restrictive managed-root policy. Its identity/retention
record now includes the target derivation and the initial straight-line
refusal. The private program stores the target candidate for reuse. No source
hash was recomputed, no firmware or database was exported, and no private
bytes, addresses, disassembly or calibration values are published. The RE
shell was closed. There was no device, radio, decryption, emulation or kernel
build action. This document records static analysis only; source record policy
and hardware admission remain unchanged.
