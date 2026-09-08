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
structure's selected population path is examined below; it is not established
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

## Follow-up: temporary startup parameters and efuse-labelled input

The state-2 branch obtains the temporary parameter pointer with arguments
selecting allocation class 2 and size 128, stores it in the global used by the
initializer, and conditionally invokes a population wrapper. Near the end of
that branch it passes the pointer to a release-style wrapper and clears the
global. The allocation/release wrappers have complementary bitmap-pool paths
and indirect fallback paths. The selected class-2 allocation uses an indirect
fallback, so its exact storage provider remains unresolved.

The population wrapper obtains a second, 256-byte allocation, invokes a
decoder with the original parameter pointer and that second pointer, then
passes the second pointer to the release wrapper. A null allocation takes a
separate diagnostic/error path. This is a local temporary-buffer lifetime,
not a filesystem-record restoration path. No leak-free or allocation-success
claim is made for the unresolved callbacks.

The decoder's selected 177-instruction graph replaces its second argument
before reading it. It calls another helper with the original destination,
zero and length 128, then obtains indexed values through a single indirect
callback. An initial loop reports indices 0 through 7; later calls fetch
selected indices again and use bit tests, extraction and conditional stores
to populate the temporary structure. The first helper's calling pattern is
consistent with clearing memory, but its body is outside the retained mapping;
therefore a fully zero-initialized output has not been proved.

The diagnostic label joined to the index/value loop names efuse data. Labels
joined to later extraction paths name detector slope/offset, per-band DPD and
PA-bias fields. These labels corroborate a firmware-side efuse decode path;
they do not prove physical fuse access, factory validity, units or board
applicability. The indexed callback's pointer slot is outside the retained
mapped sections, so neither its target nor its acquisition effects are known.

The selected decoder contains no explicit stores to the two RSSI-validity
bytes later consulted by the initializer. That local absence is not a proof
that those bytes are zero: the preparation helper, indirect callbacks and
other writers remain outside this claim. In particular, do not turn the
initializer's fallback constants into host-side replacement calibration.

The [startup-parameter receipt](results/firmware-startup-parameters.json) pins
five private scripts and their bounds. The wrapper, decoder and allocation/
release graphs all exhausted their queues. Selected parameter passing and
field stores were checked in p-code. The six diagnostic labels were read only
inside the RE VM and are paraphrased here; no raw strings or values are
published. No device access, emulation, kernel build, fuse read, calibration
write or radio operation occurred.
