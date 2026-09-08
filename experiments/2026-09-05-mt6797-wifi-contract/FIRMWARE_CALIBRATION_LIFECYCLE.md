# Retained firmware calibration initialization order

Follow-up, 2026-09-08. The transmit-compensation clearing stores are joined
through three immediate-derived call edges to the firmware's state-2 branch.
That branch later selects state 5, which the previously inspected dispatcher
uses for general command admission. This places the clears in a decoded
initialization sequence; it does not establish a live initialization trace,
exclusive state ownership or persistence of subsequently submitted calibration.

## Explicit writes and their caller chain

The [field analysis](FIRMWARE_COMMAND_DISPATCH.md) identified the globals loaded
from record offsets 270 and 271 as transmit-path-loss compensation. A selected
576-instruction routine contains explicit zero-byte stores to both globals.
The stores precede their respective diagnostic branches, so disabling those
diagnostics does not skip the stores. The routine also assigns the two RSSI
compensation globals from an optional pointed-to structure when its relevant
validity bytes are nonzero, and from separate constants otherwise. The
structure's producer and provenance have not been decoded; it is not established
as the host's complete 512-byte NVRAM record. None of these firmware fallback
values supplies a safe mainline calibration default.

Two successively enclosing routines call this initializer through decoded
immediate-derived targets. Their selected graphs have 86 and 55 instructions.
The nearer caller clears the selector global used by the transmit-compensation
arithmetic before invoking the initializer. The outer caller also contains a
fixed-address read/modify/write outside the plaintext mapping. Other callees
and indirect callbacks remain uninspected; their effects and return behavior
are not inferred from these counts.

Three bounded reference searches each found one adjacent-immediate candidate
for the next call edge. Local instruction decoding verifies those three
positive edges. These are not exhaustive caller searches: references through
tables, nonadjacent construction, other mappings or indirect computation are
not excluded.

## Join to the command-admission state

The final caller is in the state-handling routine. Its entry takes a requested
state, saves the previous state to a separate global and writes the requested
state to the same global word read by the command dispatcher. A value of 2
selects the long branch containing the initialization chain above. Later on
that branch, the local requested state becomes 5; the common tail compares it
with the global and loops to the state-write block when they differ.

The [earlier dispatch walk](FIRMWARE_COMMAND_DISPATCH.md#from-the-diagnostic-caller-to-dispatch)
permits general matching commands in state 5, including `0x43` and `0x48`.
Thus the explicit local transition toward general command admission follows
the compensation initialization call on this selected path. This does not prove
that unrelated callees or concurrent activity cannot change the state earlier,
that every call returns, or that a particular boot reaches state 5. A later
state-2 invocation could repeat the initialization; no invocation-count or
one-time-only property has been established.

This resolves the location of the observed clears without interpreting them
as evidence that a successfully submitted record is always erased afterward.
It also does not prove retention: firmware restart/reinitialization, command
completion and output callback effects remain lifecycle requirements. Keep
calibration preparation attached to an attributable firmware initialization,
and require evidence of application for any future bring-up claim.

## Evidence and limits

The [receipt](results/firmware-calibration-lifecycle.json) pins the retained
image, private scripts, bounds and selected walks. The first tail walk reached
its 512-node cap after following a state-loop edge; it was incomplete. A
separate entry-prefix inspection then established the state-global pointer and
candidate entry. The entry-based walk exhausted at 525 nodes under a 640-node
cap. That bounds direct control flow, not the behavior of its 90 calls.

Selected call edges, state stores and compensation stores were checked in
instruction listings and p-code. Linear windows were anchor searches and may
start within preceding instructions; they are not function-boundary proofs.
All private output remains in the existing RE VM project. No raw firmware,
private addresses, instruction listings, fallback values, calibration data or
identifiers are published. Repository checks apply; no kernel build, emulation,
device access, firmware loading or radio operation was performed.
