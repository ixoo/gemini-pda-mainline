# Runtime 30 result: negative lifetime; the network milestone repeated, then a refusal inside the data phase of a translated group frame flagged LLC mismatch

Boot: mainline `a3bf87eb-7291-4406-92a8-b737221fea85` on candidate 29 (compile 34,
package `f6ef3ead…`, built input 4cf4b465, boot2 `27005b8f…`), session tools at
2bcc9fbb, consumed once by the custodian after deployment 29 (predecessor candidate 28
`92bf31d0…`, stock boot `d1c8e5cc…`). Evidence: the custodian's thirteen sanitized
uploads; kernel log sealed complete (164097 bytes, 2084 records, SHA-256
`308e3a46…`); supplicant log complete (24046 bytes, SHA-256 `b56d0135…`, no per-line
timestamps); logger 74031 ms; the host wait ended on the join's terminal (join
lifecycle terminal, exit 0). No raw capture, packet content, address, credential or
image is published.

## Observed (kernel records, µs since boot)

- Handshake as before; both key commands credited with their add-key-done windows;
  `data phase: budget_ms=6172 teardown_margin_ms=5000 inside_grant=1` at 69326885.
- Before the group key: one 0164 group-data discard (`group data discarded: bytes=94
  fc=0x4208 match=0x08 wlan=2 bss=1 sec=0 status=0xc004 count=1` at 69223134), the
  class of runtimes 17 and 22 as designed. 0176 observed: four beacons delivered (one
  clear at 69221816, RCPI 88; three keyed at 69347539, 69419597 and 69523593, RCPI
  90); no total (stage 3 not reached). 0177 not exercised: no cleanup submission, no
  key removal command, no cleanup discard record in this boot.
- Data: `data TX: first pid=5 pages=3 bytes=342` at 69467577, `TX done: pid=5
  status=0` at 69468827 (+1250 µs), first unicast protected frame delivered at
  69470175, first credit at 69499470; 27 consecutive completions, PIDs 5 to 31, all
  status 0, none failed, none late.
- Host, separately: `udhcpc` exit 0, lease bound, prefix 24; the listener ready;
  `ping` 3 sent, 3 received; the laptop's one Wi-Fi SSH exchange exit 0, 37 bytes,
  boot match true, readiness after 4.5 s, elapsed 5.7 s. The milestone of runtimes 28
  and 29 repeated a third time. No Wi-Fi operational, reliability or
  replay-protection claim; `wifi_operational` stays false.
- Stop, inside the data phase (5420.653 ms after it opened, 751 ms before its budget):
  `frame refused` at 74747538: 94 bytes, type word 0x5000, descriptor bytes 48 28 ce
  04 02 40 00 c2, status group 4 present (groups 0x8), translated header at 34, group-4
  frame control 0x6208 and sequence control 0x12c0 (fragment 0), group-4 transmitter
  the target, translation flag set, first header word 0x002e, security mode 4,
  receiver not this station, native transmitter flag not applicable to a translated
  header. Footer at 74750081: status -71, first 0, submitted 0x801, debt 0, cleanup 0,
  branch 7.
- After the footer: `data phase end: reason=disconnect elapsed_ms=6300 rx_unicast=34
  rx_group=8 rx_dropped=0 tx_queued=27 tx_done=27 tx_failed=0 tx_credits=56` at
  75627514, 877433 µs after the footer, 128 ms after the budget would have ended. The
  supplicant's one disconnect carries reason 3 with `locally_generated=1` (line 371):
  its own leaving deauthentication when the session stopped it after the terminal.
  Source: the fail-stop does not mark the data phase ended, so the station-state hook
  of that later teardown printed the end record on the already-stopped lifetime. The
  record is a consequence of the session's teardown, not a cause of the refusal and
  not an idle disconnect of runtime 28's kind.
- Verdicts as computed (preserved): bounded join false; `malformed_stage_record`
  false; refusal recorded; terminal failure recorded, branch 7, status -71; handshake
  and data-path passes false (conjunctions over an unhealthy lifetime, not a statement
  that the activation, the keys or the data exchange did not happen); healthy cleanup
  false; C2 false; C3 false.

## The refused packet, decoded by the pinned vendor layout (source, not hardware proof)

Type word 0x5000: packet type 2 (`RX_PKT_TYPE_RX_DATA`) with status group 4 present
and no RX vector. Descriptor: match flags 0x48, that is, the broadcast bit with key id
1 in bits 6 and 7 (the group key id the data phase's group frames carry); channel 40;
header byte 0xce: header translation set, 14-byte Ethernet header, 2-byte header
offset; payload format 0 with BSSID field 1; WLAN index 2 (the declared broadcast
entry); TID 0 and security mode 4 (CCMP); status 0xc200: the two high bits every
admitted packet carries and `RX_STATUS_LLC_MIS` (bit 9), every error flag clear.
Group 4: frame control 0x6208 (data, FromDS, More Data, Protected), sequence 300,
fragment 0, transmitter the target. Translated header: a group destination, type or
length word 0x002e, that is, an IEEE 802.3 length of 46 and not an EtherType: the
firmware decrypted the frame under the group key and translated its header, and the
payload carried no SNAP header the translation could map, so the LLC-mismatch flag is
set and the word after the addresses is the 802.3 length. The frame is otherwise
exactly the data receive decoder's group class (data-rx.h, 0166): that decoder requires
status 0xc000 and refused it on the status word alone, so it reached the gate.

The pinned vendor data path (`nicRxProcessDataPacket`) classifies a status word with
the LLC-mismatch flag as the error class and drops the frame without delivery
(`fgDrop = TRUE` on `HAL_RX_STATUS_IS_LLC_MIS`). Inference, not measured: a station on
the target's network sends 802.3-framed broadcasts; one arrived 5.4 s into the data
phase and ended the lifetime at the gate.

## Proposal 0178

`patches/proposals/0178-…`: the data receive class in its LLC-mismatch variant is named
by a second decoder in data-rx.h with the group form of the data receive class (type 2,
status group 4 present, header translation with the 14-byte header, payload format 0
with BSSID field 1, the declared broadcast entry, security mode 4, a broadcast or
multicast match flag with the key id bits free, the group-4 frame control of a
non-QoS FromDS protected data frame from the target with fragment 0, a group
destination and a non-group source) and status exactly 0xc200; the 0166 decoder is
unchanged. During the data phase, under the data receive gate's conditions, that exact
variant is discarded as the vendor drops it, never delivered or interpreted, no
submission follows: the first eight recorded by their descriptor fields and the
translated header's type or length word, the total before the stage-3 record; the
lifetime's packet budget and the data phase's budget bound it. The unicast form, any
other status and every other shape stay refusals as before. No radio, TX or time
budget changes. The classifier knows the records, their window (inside the data phase),
the total bound to the first min(total, 8) records, and reports records and total
apart.

## Proposed runtime 31 protocol (bounded, one test)

Candidate 30 from compile 35 (0163 to 0178) with candidate 29's RAM root, DT and
config; runtime 30's protocol otherwise unchanged. Hypothesis: 802.3-framed group
frames during the data phase are discarded and counted, the data phase ends by its
budget, the cleanup follows (the deauthentication completed, both removal commands
credited, any after-removal group frames discarded under 0177, stages 1 to 3, no
footer); the beacon, cleanup-discard and LLC-discard totals are recorded at stage 3;
the lease, ping replies and the SSH exchange are reported apart. Branches: (1) stages
1 to 3 without a footer: the first healthy C3 lifetime; (2) a refusal of another shape
inside the data phase or the cleanup: recorded by its fields, fail-stop, seal, native
recovery once, the next audit; (3) a disconnect or a branch-9 footer: read from the
supplicant fields and the beacon records; (4) any other named fault: fail-stop, seal,
native recovery once. No repeat of candidate 29 without this change; no operational or
replay-protection claim. Replay protection remains unproven and unclaimed; no RE is
needed for this change (the pinned vendor headers and source suffice).
