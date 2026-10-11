# Runtime 27 result: negative; observed data completions and a lease, then a refusal consistent with the 0168 class after its eight recorded discards

Boot: mainline `e2aa21a4-807b-4e4b-aeeb-0e2f89111e0e` on candidate 26 (compile 31,
package `bc0f928e…`, input c7ba623f, boot2 `e322e068…`), session tools at bd62d989,
launched once by the custodian after deployment 26 (predecessor candidate 25
`b38d25a9…`, stock boot `010ae842…`). Evidence: the custodian's eleven sanitized
uploads; kernel log sealed complete (159218 bytes, 2053 records, SHA-256 `bf9e0798…`);
supplicant log complete (26554 bytes, SHA-256 `5a7875f6…`). No raw capture, packet
content, address, credential or image is published.

## Observed

- Initialization passed; the association exchange and the supplicant's handshake
  phrases (its state); both key commands credited and both add-key-done windows
  recorded (attribution by window only); `data phase: budget_ms=6168
  teardown_margin_ms=5000 inside_grant=1`.
- 0173 observed: four keyed beacons skipped and recorded (the matcher's source-defined
  conditions held for them; their unmeasured fields are observed only through the
  matcher). 0168 observed eight times across the lifetime (counts 1 to 8 between
  59371455 and 60470359 µs, eight in 1.10 s, in bursts).
- 0172 observed, each term apart: `data TX: first pid=5 pages=3 bytes=342` at
  59826341 µs; `TX done: pid=5 status=0` at 59829521 µs (+3180 µs after the submission; a completion with
  status 0, not an acknowledgement or a delivery claim); the first unicast protected
  data frame delivered to mac80211 at 59830915 µs; `data credit: pages=3 debt=0
  count=1` at 59854260 µs (+27919 µs after the submission, +24739 µs after the TX done; the first frame's pages
  returned). Then `data credit: pages=3 debt=0 count=2` at 59878283 µs and `TX done:
  pid=6 status=0` at 59879448 µs; `data credit: pages=1 debt=0 count=3` at 60518270 µs
  and `TX done: pid=7 status=0` at 60519505 µs. End counters: rx_unicast 3, tx_queued 4,
  tx_done 3, tx_failed 0, tx_credits 7 (cumulative). The fourth queued frame has no
  recorded completion before the stop; that is not a timeout claim.
- Host (session fields): `udhcpc` exit 0, lease written, bound, prefix length 24; the
  retained Dropbear's digest matched, the listener started and became ready; `ping`
  sent 3, received 0. The laptop helper saw the readiness marker after 4.6 s and made
  its one SSH exchange: exit 255, 0 bytes, boot match false, elapsed 14.6 s, bound to
  this boot. A lease is genuine network evidence; no full networking, operational or
  replay-protection claim follows, and the ping and SSH outcomes are negative.
- Stop: after the eighth 0168 discard, at 60542442 µs one packet of that class's
  descriptor shape was refused at the frame gate (708 bytes, type word 0xee01,
  descriptor 08 28 18 3c ff 00 00 e0, groups 1 to 3, header at 64, first
  frame-control byte 0xd0, security mode 0, receiver not this station, transmitter
  not the target). The refusal diagnostic carries no full frame control, receiver or
  fragment field, so the ninth-frame reading rests on the descriptor shape and the
  gate's order in the source (the class decoder is evaluated and then the count
  compared with 8), not on those fields. Fail-stop at 60545017 µs: status -71, branch
  7, TC4 debt 0. The data phase ended on the supplicant's disconnect (elapsed
  1704 ms).
- Verdicts as computed: bounded join, handshake and data false; C2 false; C3 false;
  not malformed; refusal and terminal failure recorded; `unique_tx_acknowledgements`
  false. That last term is a classifier attribution defect, not a hardware
  observation: the rule counted the three data completions (PIDs 5 to 7) against the
  management and security submissions only. It is corrected in this commit and the
  original verdict is not rewritten.

## Diagnosis (source-supported inference, not hardware proof)

Observation: eight frames of the 0168 class in 1.10 s, in bursts, then a refusal whose
metadata (descriptor shape, first frame-control byte, security mode, receiver and
transmitter comparisons) is consistent with that class after the count of eight; the
full frame control, receiver and fragment of the refused frame were not measured.
Inference from the source: the gate evaluates the class decoder and then the count
against 8, so a ninth frame of the class is refused at that point, which matches the
footer (branch 7, status -71, TC4 debt 0). The eight-per-join cap, chosen when
one such frame had been observed (runtime 21), is therefore the source-supported
reading of this stop; whether the class would keep arriving over a longer data phase
is not measured. The data completions and the lease are observations of the same
lifetime, not a claim about the data path beyond them.

## Recovery

One native recovery was requested after the evidence was sealed and confirmed with
the regression check true; a changed-identity stock boot
`57c5ae6e-57d1-41ff-8f15-5d1251bd7203` was independently verified live. One request
only. The installed boot2 remains candidate 26 (`e322e068…`).

## Decision

Proposal 0174 keeps the 0168 decoder exactly as it is, counts that class without a
cap of its own, records the first eight as before and the total before the stage-3
record; the lifetime's existing receive budget (`MT6797_JOIN_MAX_PACKETS`, 32768
packets, unchanged) bounds it, as it bounds the clear and keyed beacons; nothing is
delivered or interpreted and no submission follows. The concrete need is the observed
eight in 1.10 s against a data phase whose budget is seconds; no rate beyond that
observation is claimed. The directed Action class keeps its own eight. The classifier binds data
completions to the recorded first data submission and the driver's serialized PID
allocation (the first data PID is the last pre-phase PID plus one, its pages follow
from its bytes, completions follow in consecutive PIDs after that record, each once,
the deauthentication takes the PID after the dequeued frames, never more than
tx_queued), reports status 0, non-zero and late completions apart, and reconciles the
end record's tx_done and tx_failed with the recorded completions whether or not any
exist; absent first submission, PID jumps, reversed order, duplicate, pre-phase and
unknown-status completions are malformed. A completion is neither an acknowledgement
nor a delivery. One bounded next test: the runtime 27
protocol on a candidate carrying 0174, nothing else changed. No repeat of candidate
26; no replay-protection or operational claim.
