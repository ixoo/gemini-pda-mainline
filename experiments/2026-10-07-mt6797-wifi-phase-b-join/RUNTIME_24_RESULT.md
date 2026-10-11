# Runtime 24 result: negative, the directed Action class in its keyed descriptor variant refused after the pairwise key

Boot: mainline `a7f9d699-8f4a-40a0-9240-e177c35410bd` on candidate 23 (compile 28,
package `4d9372a7…`, boot2 `1b07a2bb…`), session tools at f6baf160, launched by the
custodian after deployment 23 (predecessor candidate 22 `419797dd…`, stock boot
`89d49b95…`). Evidence: the custodian's sanitized uploads (join diagnostic records,
log, supplicant-log, session, native-request and Wi-Fi SSH results, body fields);
kernel log sealed complete (155081 bytes, 2032 records, SHA-256 `f6ebff7b…`);
supplicant log complete (24202 bytes, SHA-256 `3c4e1468…`), no process left. No raw
log, address, body or identifier is published.

## Observed

- Phase A and the scan as before; the authentication and association exchange
  (status 0) completed and was acknowledged; the supplicant reported handshake
  completion (its own state; the host's handshake-path and C2 verdicts stay
  false); three clear broadcast Action frames of the runtime 21
  class discarded (0168 observed, counts 1 to 3); one protected group-addressed data
  frame of the runtime 17 class with WLAN index 2 discarded before the group key
  (0169 observed on hardware: 94 wire bytes, frame control 0x4208, match 0x08,
  BSSID field 1, security mode 0, status 0xc004).
- Proposal 0170 observed: the pairwise key command submitted (sequence 25), its
  one-page credit returned 12.0 ms later, message 4 sent 1.1 ms after that (pid 4,
  2 pages, in flight), the first add-key-done recorded, then `key credit returned:
  pairwise` 1.4 ms after the key-done with message 4 still in flight; message 4's
  TX done (status 0) followed. The credit's attribution to the command is by order;
  the add-key-done event is attributed by window only.
- Then one packet refused at the frame gate: 136 bytes in all (72 wire bytes at
  offset 64, groups 1 to 3), type word 0xee01, descriptor bytes 02 28 18 04 01 40
  04 e0 (unicast-to-me match, channel 40, native untranslated 24-byte header,
  BSSID field 1, WLAN index 1, TID 0, security mode 4, status 0xe004), frame
  control 0x00d0 (an unprotected Action frame, Retry clear), receiver this station
  and transmitter the target by the summary's explicit comparisons. Fail-stop:
  stopped with status -71, branch 7. The supplicant's group key command then
  arrived and was refused (-71) with the lifetime stopped; no group command was
  submitted.
- Host: the join phase completed framed and terminal (`join_terminal` 1, the
  supplicant exited 0 after CONNECTED and DISCONNECTED once each, PTK and GTK
  installation lines present); no data phase, DHCP, ping or listener ran; the Wi-Fi
  SSH check saw no readiness marker within its budget (92 s) and attempted nothing.
  Verdicts: bounded join, handshake and data false; C2 false; C3 false; not
  malformed; refusal and terminal failure recorded; `key_credits_returned`
  `['pairwise']`, `group_action_frame_discards` 3, `group_data_discard_records`
  1, `action_frame_discards` 0. These host verdicts stand as computed; the late
  helper run that exhausted its budget is attached separately and does not alter
  them.
- Not firmware evidence: the supplicant's CONNECTED, PTK and GTK lines are its own
  state, not key installation.

## Diagnosis (source, not hardware proof)

The refused packet is of runtime 18's directed clear Action class
(`action-frame.h`: 136 bytes, type word 0xee01, unicast-to-me match, BSSID field 1,
WLAN index 1, frame control 0x00d0, receiver this station, transmitter the target;
the same source-defined class, since no body or sequence was retained in either
run) with two descriptor fields changed: byte 9 is 0x40 and the status word 0xe004, where
runtime 18, before any key, carried 0 and 0xe000. In the pinned public RXD layout
byte 9's upper nibble is the security mode (4 is CCMP) and bit 2 of the status
word is `RX_STATUS_FLAG_CIPHER_MISMATCH`; the ICV-error flag is bit 4 and is clear.
Inference, not measured: once the pairwise key is installed under WLAN entry 1 the
descriptor reports that entry's cipher context, and an unprotected frame received
on it is flagged as a cipher mismatch. The decoder pinned byte 9 to 0 and the
status to 0xe000, so the frame fell through to the general gate. The category,
body, BSSID and sequence were not retained and nothing is claimed about them; the
frame is not delivered in either variant.

## Not observed and not claimed

Nothing about the firmware's key handling, add-key-done semantics or replay
behaviour follows from this run; no network function, no replay protection, no
operational claim. The pinned vendor driver's management path drops only ICV
errors before dispatching by category; no further vendor behaviour is claimed.

## Recovery

One native recovery was requested after the evidence was sealed; the collector
confirmed a changed-identity stock boot `40295547-4194-4840-8553-b45a085d1338` on
its second attempt after 15.4 s, with the regression check true. One request only.
The installed boot2 remains candidate 23 (`1b07a2bb…`).

## Decision

Proposal 0171: the directed Action class decoder admits the keyed descriptor
variant (exactly byte 9 0x40 and status 0xe004) only when the join worker passes
that the pairwise key is installed, and keeps admitting runtime 18's unkeyed
variant (exactly 0 and 0xe000) at every stage it already did; the keyed variant
before the key and every mixed pair are refused. The frame stays a discard, never
a delivery, within the same eight-per-lifetime budget; every other condition,
budget and window is unchanged. Compile 29 follows the custodian's review; a
candidate and one boot follow after that. No repeat of candidate 23.
