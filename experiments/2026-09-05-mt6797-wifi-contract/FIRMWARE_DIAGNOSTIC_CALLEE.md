# NVRAM reference reaches a diagnostic formatter

Follow-up, 2026-09-08. The previously resolved
[computed-call target](FIRMWARE_NVRAM_CALL_TARGET.md) now has a supported
**diagnostic-formatting interpretation**. The NVRAM-associated address is
passed as a format argument into a bounded string-formatting routine. This
reference is not evidence that the called routine applies a calibration record.
The caller may still participate in calibration work, but its incoming entry
and surrounding semantics remain unidentified.

## Two bounded inspections

The existing private Ghidra project and exact firmware identity were reused
in the RE VM. No source extraction, broad keyword/reference scan, decryption,
emulation or device access was repeated. The
[receipt](results/firmware-diagnostic-callee.json) records the method identities
and bounds. Candidate mappings, NDS32 instruction interpretation and provisional
ABI/data-order assumptions remain those of the earlier investigation.

The first walk starts at the retained call-target candidate, follows direct
branches and fallthrough, and skips callees. Its 256-node cap was not reached:
the queue exhausted after 96 instructions, with two call sites, one terminal
instruction, no unresolved non-call computed edge, and no invalid or
out-of-plaintext-code node. Following call fallthrough assumes return; these
counts do not establish complete runtime reachability or a unique function end.

The target saves the incoming argument registers to its stack, then arranges
four arguments for its first call: an output-buffer position, remaining capacity,
the original first argument, and a pointer into the saved argument area. The
first call's destination is again constructed from instruction immediates.
Its returned length updates a bounded cursor, with separate error/full handling.
Later code recognizes a trailing line-feed byte, inserts a carriage return when
needed, and conditionally passes the buffer and length to another call. This
supports a buffered text-output wrapper; the final output transport is unproved.

A second, separately selected walk inspects that first callee. It reached its
512-node limit with work still queued, so it is explicitly incomplete. The
inspected instructions nevertheless provide positive formatting evidence:

- the third argument is consumed as a byte string;
- a percent byte changes parser state;
- subsequent states recognize formatting flags, decimal width, a precision
  separator, length modifiers and conversion characters;
- ordinary bytes are copied subject to output capacity, and a terminating
  zero is stored on the inspected exit paths; and
- values are fetched through the fourth-argument area as conversion operands.

The combination supports a `vsnprintf`-like role without assigning a library
symbol or claiming full standard conformance. No larger traversal is needed to
classify this reference's use. The unseen paths, nested helper semantics and
output transport are not counted as verified.

## Consequence for calibration research

Treat the NVRAM text reference as a diagnostic-format argument, not as the
location of command `0x48` dispatch or proof of record acceptance, application,
EFUSE precedence or RF settings. The call does not resolve those questions.
Continuing down the formatting/output implementation would not identify the
calibration consumer. Return to the original caller's incoming dispatch or an
independently attributable command/record data path if further firmware work
is needed; do not keep extending this diagnostic callee solely because it is
reachable in the static model.

The [calibration applicability contract](CALIBRATION_APPLICABILITY.md) remains
unchanged. This finding creates no new hardware prerequisite and does not
block independent host protocol work. No driver, radio operation, calibration
write, firmware load or upstream support claim follows.

Private scripts, logs and listings are retained beside the existing project
under its restrictive directory and cleanup policy. Only independently worded
semantics, analysis counts and hashes are published. Firmware bytes, strings,
private addresses, raw disassembly and calibration values remain outside Git.
Validation consists of the two successful bounded Ghidra runs, manual review
of the relevant instruction/p-code paths and repository publication checks;
there is no kernel build or runtime test.
