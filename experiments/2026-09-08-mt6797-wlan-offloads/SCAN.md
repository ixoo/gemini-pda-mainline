# Scan completion and cancellation contract

## Decision

Keep scan request acceptance, host completion and firmware quiescence separate.
The selected vendor path can report a non-aborted scan after cancellation or
timeout; that notification is not evidence that the firmware finished scanning.
A future mac80211 adapter must preserve cancellation/error status and validate
event identity before changing the active scan's timer or state.

This 2026-09-09 follow-up uses five public Planet gen3 files and the pinned
upstream mac80211 header. Complete hashes and inspected ranges are in the
[source receipt](results/scan-sources.json). Four vendor files and the upstream
header match the earlier offload review; Linux glue is newly pinned. No device,
firmware, radio operation or kernel build was involved. This specifies a future
adapter, not an implemented scan engine or a renewed HIF observation.

## Wire identity and host cancellation

The selected header declares V2 request `0x03`, legacy request `0x1a` and cancel
`0x1b`. V2 includes an eight-bit payload scan sequence and BSS index. Cancel has
the payload sequence, an extended-channel byte and two reserved bytes; it has
no BSS field. The declared completion payload also has no BSS identity. The
normal event's outer command sequence is not the payload scan sequence.

`scnFsmMsgAbort()` checks both sequence and BSS against the active host request,
then submits cancel without a requested response, completion callback or timeout
callback. It generates a local `SCAN_STATUS_CANCELLED` message and enters idle,
which can immediately select a queued scan. The cancel submission return is
not checked. Removing a queued request instead generates cancellation locally
without sending a firmware cancel for that request.

Thus a local cancelled message is not a firmware stop acknowledgement. The
inspected path supplies no cancellation fence before the next request. The
eight-bit AIS sequence increments on requests; a host generation alone cannot
authenticate an old completion after wire-sequence reuse. This identifies an
unresolved ordering requirement, not a demonstrated late-event failure.

## Two completion hazards in the selected source

| Path | Direct source behavior | Consequence for the new adapter |
| --- | --- | --- |
| Firmware scan-done dispatch | `nic_rx.c:1967–1972` uses packet length to choose a version flag and calls the handler. | Validate the actual payload extent before reading any version-dependent field; a version flag is not a bounds check. |
| Scan-done handler | `scan_fsm.c:700–701` stops its timer and clears timeout history before the active-state/sequence comparison at line 734. It also updates sparse-channel state before that comparison. | Reject an unrelated completion before mutating any active-request state. With scan B active, a late event for A can otherwise suppress B's scan-module timer even when B is not completed. The separate AIS timer is a different mechanism. |
| Local done delivery | `ais_fsm.c:1911–1912` saves the sequence and frees the message without reading its `eScanStatus`. Matching SCAN/ONLINE_SCAN cases call `kalScanDone()` with success. | Carry the terminal reason through completion; the local cancellation status cannot be discarded. |
| AIS timeout | `ais_fsm.c:3401–3402` calls `kalScanDone()` with success, then requests scan abort later in the function. | Timeout is an aborted/error result. Host notification cannot stand in for firmware cancellation or resource release. |
| Linux notification | `gl_kal.c:3336–3347` does not use its status argument. Its scan-complete indication detaches the request under a lock and calls `cfg80211_scan_done(request, FALSE)` at line 1128. | Detaching the request prevents this path from completing that pointer twice, but does not make its non-aborted result truthful or prove firmware quiescence. |

These are source-level control-flow findings. They do not establish the exact
running binary, observed event order, or a firmware defect. No vendor fix is
added to the upstream patch layer.

## Standard-interface mapping

At the pinned upstream revision, `hw_scan` must honor regulatory channel
configuration. Once it accepts a request, the driver must call
`ieee80211_scan_completed()` even on failure; a negative callback return instead
rejects the request. `cancel_hw_scan` does not itself complete the request:
completion still requires that explicit call.

The adapter therefore needs one serialized terminal transition per accepted
request, joining event, cancel, timeout and removal paths. Complete cancellation,
timeout and transport failure as aborted; reject malformed or unrelated events
without cancelling the current deadline. Keep the request and its event/timer
ownership valid until that terminal transition, and join local work before
freeing it. Host completion and the right to start another firmware scan are
separate decisions when cancellation or ordering is uncertain.

Before implementing that latter decision, establish the exact firmware cancel
handler's output and ordering behavior, including late completion and sequence
reuse. Neither a no-response set command, an unrelated query, a delay nor a
locally incremented generation supplies this proof. Request encoding, permitted
channels, scan-result delivery and shared power/HIF failure lifetime remain
necessary parts of usable scanning. No standalone state-machine fixture or
radio candidate is added without those connected interfaces.

The [retained-firmware follow-up](FIRMWARE_SCAN_LIFETIME.md) now joins the
request and cancel sequence state and identifies the normal completion
constructor. An ordinary cancellation path bypasses that constructor; its
callbacks still lack a proved stop/drain rule. Waiting unconditionally for
`0x0d` is therefore not an established cancellation protocol.
