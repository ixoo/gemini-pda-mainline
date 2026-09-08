# Retained firmware command dispatch and NVRAM fields

Follow-up, 2026-09-08. The original NVRAM-text caller is now joined to
**command `0x43`, RSSI path compensation**, through a decoded firmware dispatch
table. **Command `0x48`, complete NVRAM settings, has a separate handler**.
That handler reads a small selection of record fields, including three bytes
the selected host structure calls reserved. This advances static firmware/host
attribution; it does not prove execution, calibration acceptance or radio safety.

## From the diagnostic caller to dispatch

The [diagnostic interpretation](FIRMWARE_DIAGNOSTIC_CALLEE.md) is preserved.
The original caller reads a pointer at offset 8 of its incoming object, skips
an eight-byte header, copies two payload bytes to globals and conditionally
reports their shifted values. Its complete selected direct-flow walk has 44
instructions and two calls; the second diagnostic call remains indirect.

A four-byte-aligned search of the retained plaintext data section found one
little-endian pointer to that caller and no big-endian match. Neighboring
words suggested an ID/function table. An immediate-pair search for references
into that table's neighborhood supplied a candidate lookup anchor. These
searches alone are heuristics; the following decoded consumer establishes the
layout used for the two selected entries.

The inspected prefix obtains the packet pointer from incoming-object offset 8
and loads the command byte at packet offset 4, matching the public normal
command header. The lookup compares that byte with entry offset 0, loads a
function pointer at offset 4, advances by eight bytes and stops after 81
entries. It calls a matching pointer with the original incoming object, subject
to a global-state/command-allowlist check. One state permits the general match;
this is not an unconditional dispatch claim or a runtime state observation.

Entry indices 50 and 51 associate IDs `0x43` and `0x48` with the original
caller and a distinct target respectively. The public host header independently
names `0x43` as path compensation and defines its payload as two signed bytes
for 2.4 and 5 GHz. It names `0x48` as NVRAM settings and embeds the complete
512-byte structure. These separate joins supersede the earlier assumption that
a text reference containing NVRAM might itself identify the full-record handler.

The table-consumer walk starts at the address-construction anchor and exhausts
after 117 instructions; it is not a claimed complete containing-function
boundary. A separate 30-instruction linear prefix reaches that anchor and
includes a preceding return and candidate prologue. The retained receipt
records caps, counts and method hashes. Calls are not traversed, and following
their fallthrough assumes return.

## Full-record handler: observed field access

The separately inspected `0x48` target exhausts its selected direct-flow graph
after 31 instructions, with one call and one terminal instruction. The pointer
and header relationship above places its reads at these payload offsets:

| Record offset | Width | Decoded effect | Selected host declaration |
| --- | ---: | --- | --- |
| 263 | 1 byte | Copy to a fixed global byte | `ucRxDiversity` |
| 268 | 2 bytes | Test bit 8; pass 0 when set, 1 otherwise, to an immediate-derived helper | `u2FeatureReserved` |
| 272 | 1 byte | Copy to a fixed global byte and gate the following two copies | Within `aucTailReserved` |
| 270 | 1 byte | Copy to a separate global if the gate is nonzero; clear that global otherwise | `aucPreTailReserved` |
| 271 | 1 byte | Copy to another global if the gate is nonzero; clear that global otherwise | First byte of `aucTailReserved` |

These are static access/effect facts, not decoded RF meanings. The nested
helper and selected downstream use are examined in the follow-up below. The selected
handler contains no visible whole-record copy, checksum/version check or
record-applied acknowledgement. An earlier validation layer is not excluded,
and absence of a check here is not a firmware-wide absence claim. The zero
return is an internal handler result, not evidence of a host-visible reply.

## Implementation consequence

Keep the original record intact. Do not zero, regenerate or repurpose its
reserved bytes merely because the host header leaves them unnamed: this image
reads some of them. Do not interpret successful command submission as application
of every calibration field. The host also sends separate parameter commands,
and this full-record handler demonstrably has a narrower selected-field role.
No change to the existing opaque 512-byte submission helper is required.

The follow-up below narrows those dependencies without a radio test. Remaining
questions include the arithmetic caller and the other reserved-byte consumers.
The actual installed/executing image, record provenance, complete calibration
and regulatory behavior remain separate requirements. Shared HIF power/stop
ownership is unchanged; no active driver or firmware operation is admitted.

## Evidence and validation

The [receipt](results/firmware-command-dispatch.json) pins the existing firmware
identity, six private analysis scripts and two public host headers from Planet
commit `c5b0be85017ad0c599725e8273842efdbecdd88a`. The existing RE-VM Ghidra
project was reused. Instruction decoding uses the prior NDS32 mapping premise;
the pointer table provides additional support for little-endian data but does
not independently prove every ABI or mapping assumption.

All bounded runs completed and the relevant instructions/p-code were reviewed.
No calibration values, firmware strings/bytes, private addresses or disassembly
are published. Private results remain under the project's existing retention
and cleanup policy. Repository checks apply; no kernel build, emulation, device
access, firmware loading, calibration write or radio test was performed.

## Follow-up: feature-dependent writes and a reserved-byte consumer

The feature-bit helper's selected direct-flow graph exhausts after 37
instructions, with one indirect call. Both branches perform two 32-bit stores
to fixed addresses outside the mapped plaintext sections. One branch uses a
fixed pair of values; the other changes the first value and derives the second
by subtracting the logically right-shifted, zero-extended 2.4 GHz compensation
byte from a constant. That byte is the global written by command `0x43`.
The derived branch applies when record offset 268 bit 8 is clear.

The common tail reads the second destination and passes that value, the Boolean
argument and the compensation byte to an unresolved indirect callback. There
is no comparison establishing a successful readback in this graph. The
addresses' peripheral meaning and callback effects remain unproved; these
stores are static decoded effects, not observed hardware writes.

This establishes a cross-command data dependency: on the derived branch,
`0x48` uses the compensation state present when it runs. The pinned public
`wlanLoadManufactureData` source conditionally submits `0x43` when the RSSI
compensation-valid field is nonzero, then later copies and submits all 512
bytes with `0x48`. Both requests set the no-response form. This is host
submission order, not proof of firmware execution/completion order, successful
submission, or the initial compensation value when the first request is omitted.
An implementation must preserve the original conditional preparation sequence;
the full-record request alone is not a demonstrated replacement.

A separate bounded search found candidate consumers of the globals loaded
from reserved record bytes. Following one address-construction anchor to its
return establishes that the offset-270 global is loaded as an unsigned byte,
used in a signed comparison against a constant minus the incoming accumulator,
and either added to that accumulator with signed-byte narrowing or replaced
by the constant. The 13-instruction selected graph has no calls. It begins
inside a containing function: neither its incoming accumulator's meaning nor
the conditions selecting this path have been established. This is positive
evidence of arithmetic use, not a decoded power unit, valid range or safe
replacement value.

The candidate search inspected up to 12 instructions after each matching
upper-address immediate at two-byte offsets in plaintext section 2. Its 19
matching windows include overlaps, stores and unrelated low-immediate matches;
they are not 19 proven consumers. The offset-271 and offset-272 consumers and
other candidate paths remain unresolved. This search cannot establish absence
of indirect or differently constructed references.

The [follow-up receipt](results/firmware-nvram-feature.json) pins the three
private scripts, bounds and additional public source identity. All selected
instructions and p-code were reviewed in the RE VM; private listings remain
retained there. No firmware bytes, private addresses, calibration values or
strings are published. No kernel code changed and no device access, emulation,
firmware load, calibration operation or radio test was performed.
