# Retained firmware station removal and activation reply

## Result

The retained image implements distinct station-removal cleanup and an optional
station-update reply. Removal's return leads to command-object recycling. The
update reply has the public activation-event ID, sequence, length and station/BSS
fields, then reaches an unresolved output callback. This narrows the
[station-reuse requirement](RECEIVE.md): neither local command completion nor
the decoded removal return establishes that old RX and BA events have drained.
Activation output ordering is now a specific missing contract.

This is static evidence from the same retained image used by the
[command-dispatch audit](../2026-09-05-mt6797-wifi-contract/FIRMWARE_COMMAND_DISPATCH.md),
not proof that these paths executed on Gemini. The
[receipt](results/firmware-station-lifetime.json) pins the image identity,
private methods and public host inputs. No firmware bytes, private addresses,
strings, disassembly or station identities are published.

## Removal and command recycling

The previously decoded 81-entry table contains separate mapped targets for
commands `0x13` and `0x14`. The selected removal graph exhausts after 91
instructions. Its packet-pointer, eight-byte header and action/station/BSS
accesses agree with the public command header and `CMD_REMOVE_STA_RECORD_T`.

Action zero selects one station. Its lookup admits indices below 27 and returns
null otherwise; this does not make the caller a safe malformed-input handler.
The group path walks 27 entries, selects active entries with a matching BSS,
and excludes the supplied station index. This agrees with the host's choice of
BSS versus BSS-except-station action based on whether that index is in range.
Neither path supplies a new station incarnation on the wire.

Both paths use a common five-helper cleanup chain. Inspected descendants include
an eight-entry state walk and removal of entries from five linked queues.
The callers clear station state and invoke another cleanup helper. Some effects
pass through unresolved callbacks. These are positive cleanup observations,
not proof of complete RX quiescence or callback completion.

Removal returns zero. The common dispatcher then invokes a routine that clears
the incoming object's packet pointer, links the object into a pool and increments
its count. When requested, it first passes the buffer handle through another
helper with unresolved underlying callbacks. The object-recycling stores do not
encode an activation or removal reply. A response or ordering guarantee inside
an unresolved callee is not excluded; the return/recycling path itself is not
the missing host-visible fence.

## Activation response and ownership

The update handler checks payload byte 51, matching the public `ucNeedResp`
field. At the inspected response tail, a nonzero value passes the incoming
object, station pointer and original command sequence to a separate helper.
It reuses the packet buffer and directly writes length 16, packet type `0xe000`,
event ID `0x0c`, the command sequence, and the station/BSS indices. It also passes
a six-byte source/destination/length tuple to an unmapped copy-shaped helper for
the peer-address portion. The arguments and direct stores agree with the public
`EVENT_ACTIVATE_STA_REC_T`; that copy implementation remains unproved here.

The response sets the incoming object's output selector to one and reaches an
indirect callback with that selector and the buffer handle. Its table lies
outside the retained plaintext mapping. After the success/assertion path, the
code recycles the command object without releasing the transferred buffer.
The update handler returns one on this path, making the common dispatcher skip
its ordinary recycling call. This establishes distinct buffer-ownership paths;
it does not prove host delivery or ordering relative to other data/event queues.

Before treating activation as a station-reuse boundary, establish that callback's
acceptance/delivery semantics and whether older station RX/BA work can appear
after the reply. Matching sequence and peer fields correlate a reply with the
host request; they do not identify every later unsolicited event's incarnation.
The existing host-generation limitation remains. No new ACK, delay, `RX_FLUSH`
format or driver activation is inferred.

## Response-pool backpressure

The completed update-body walk exposes an early resource check. After station
lookup and before the handler's station-clear/copy mutations, a requested reply
requires a nonzero free-object count in a pool also identified by the recycling
routine. A zero count returns a distinct resource status. The common dispatcher
recognizes that status and skips its ordinary command-object recycling call.
The no-reply path bypasses this check.

This establishes an early resource-failure path that retains command ownership
at the dispatcher boundary. The count check alone does not prove an atomic
reservation. A missing activation reply therefore cannot be treated as evidence
that this handler applied the station update.

A caller follow-up now identifies a retry mechanism. The inspected input path
appends a resource-refused command to a pending list and increments its count.
A separate drain callback removes the list's first object, clears its links,
decrements the count and invokes the same dispatcher. If the resource status
recurs, it restores that object at the front, restores the count, calls a
scheduling helper and returns. Other statuses continue the drain loop. This is
command retry, not a new host reply or station incarnation.

The initialization sequence passes that drain callback to an initializer for
the same scheduling object used by both callers. The initializer stores the
callback and clears the object's links; the scheduling helper computes a
deadline and links an inactive object into its own pending list. Both
callers supply the same delay argument. The underlying time and alarm callbacks
remain unresolved, so this does not establish runtime wakeup, a measured retry
interval, eventual resource availability or teardown/cancellation safety.
The separate old-RX/BA drainage requirement remains unresolved.

## Method and limits

The existing RE-VM Ghidra project and NDS32 instruction/data mapping premises
were reused. Direct-flow walks skip callees and assume return; selected
immediate-derived callees were inspected separately. The initial update-body
walk hit its 384-node cap; a separate 18-instruction response-tail walk covered
its reply branch. A follow-up from the original entry with a 1,024-node cap now
exhausts at 488 instructions and 39 call sites, without invalid instructions or
unresolved non-call transfers. This completes the selected direct-flow graph,
not the effects of all callees: additional indirect and unmapped callbacks
remain unresolved. Other selected walks exhausted their queues under the same
callee-return assumption. Immediate-pair searches found two dispatcher references
and one drain-callback reference; these are search candidates, not a complete
caller inventory. Decoding confirmed the selected joins. Full-entry walks of
the input and drain routines cover 93 and 47 instructions respectively; the
scheduling helper and initializer cover 119 and 26. All four direct-flow queues
exhaust without invalid or unresolved non-call transfers. A bounded linear
initialization window corroborates callback registration and list setup; it
is not a complete initialization-flow proof.

Private scripts, logs and listings remain retained with the original evidence.
Public host inputs are pinned to Planet commit
`c5b0be85017ad0c599725e8273842efdbecdd88a`. No emulation, firmware execution,
device/radio access, kernel change or hardware test occurred. Repository
publication checks apply; no kernel build is needed.
