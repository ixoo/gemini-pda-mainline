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
helper and downstream uses of those globals remain uninspected. The selected
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

The next useful firmware question is the one helper selected by feature bit 8
and the consumers of the three reserved-byte globals, with the exact record and
firmware identity retained. That can narrow compatibility without a radio test.
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
