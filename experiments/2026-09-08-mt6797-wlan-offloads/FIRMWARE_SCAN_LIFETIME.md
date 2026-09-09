# Retained firmware scan cancellation and completion

## Result

The retained image supplies mapped handlers for V2 scan request `0x03` and
cancel `0x1b`, plus a concrete scan-done `0x0d` constructor. Cancellation and
that constructor are separate control-flow paths. Do not implement cancellation
by waiting unconditionally for a scan-done event, or treat a scan-done event as
a cancellation acknowledgement or a cross-request drain fence.

This 2026-09-09 follow-up uses the existing RE-VM firmware model and the
[host scan contract](SCAN.md). The [receipt](results/firmware-scan-lifetime.json)
pins the firmware identity, private analysis scripts and listings. No firmware
was executed and no device, radio, key or calibration state was accessed.
Raw instructions, addresses and firmware remain private.

## Request and cancellation identity

The 81-entry dispatch table contains one match for each selected command.
The V2 wrapper branches on payload byte 7. The branch selected by the public
host's zero-initialized reserved byte decodes the request sequence and BSS from
payload bytes 0 and 1. Its core stores that sequence into the shared request
state. The cancellation handler compares its own payload byte 0 with that
same state byte. This is a concrete sequence join, not an assumption based on
the command names. The header's outer sequence is a different field.

On a matching sequence, the cancel handler selects a state-dependent helper
or queued-request removal according to another state word. It also reads the
extended-channel byte. A mismatch is not a proven effect-free rejection:
the mismatch branch contains additional state-dependent work. The inspected
handler does not compare a BSS field in the cancel payload; the public payload
has none.

In the mode-zero, ordinary-state cancellation path, the helper selects idle
instead of the separately labelled scan-done state. The idle state's queue
helper returns null when its list is empty; the state machine then returns
without traversing its scan-done constructor. Nonempty queues can start further
work. Other modes have different stop paths and are not collapsed into this
ordinary case.

This identifies a path that bypasses the explicit constructor, not a
firmware-wide absence of events: the cancellation path includes callbacks and
other callees whose complete effects remain unresolved. Their success,
scheduling and resource-release behavior are not established by a zero handler
return. A reliable cancellation boundary is therefore still missing.

## The normal scan-done record

The diagnostic state-name table identifies state 7 as scan-done. Its selected
branch requests a 24-byte event object. With a non-null object it constructs:

| Field | Observed construction |
| --- | --- |
| Header length/type | 24 bytes / `0xe000` |
| Event ID / outer sequence | `0x0d` / zero |
| Payload sequence | Current scan-context sequence; the mode-zero context resolves to the same byte written by the request core and checked by cancellation |
| Payload current state | 7 |
| Other payload values | Completed-channel count, sparse-channel information, version byte, counter and PNO indication, matching the public completion layout |

The explicit outer zero confirms that the generic pending-command sequence
matcher is unsuitable for this event. The payload has no separate aborted
status or BSS identity. A constructor call therefore cannot tell the host that
its cancellation request was accepted, nor authenticate a reused scan sequence.

The branch selects the same output wrapper used by the prior station/key
analysis, with selector zero. After that call it still updates internal mode
and timing state and runs additional helpers. A null allocation takes a
different continuation without constructing this event. Neither the allocation
path nor the output call proves reliable delivery, when the host can receive
the event, or that older results and callbacks have drained.

## Validation and next boundary

The initial 1,024-node state-machine walk was incomplete and is retained as
such. A bounded repeat from the original entry exhausts at 1,649 nodes with
106 call sites; all ten completed selected walks have no invalid instruction
or unresolved non-call computed transfer. Calls remain skipped under an
assumed return. Exhausted direct graphs are not a proof of every callee,
feasible runtime path, hardware effect or concurrent ordering.

The host adapter requirements remain: one truthful terminal completion,
validated payload identity before state mutation, and a separate firmware
stop/reuse decision. Next attribute the cancellation cleanup callbacks and
output scheduling to a supported stop/drain rule; neither the normal scan-done
record nor the generic command result supplies one here. This evidence adds no
delay, retry, firmware write, driver activation or device candidate.
