# Runtime 29 result: negative lifetime; the data phase ran to its budget with the network milestone repeated, the deauthentication completed and both key-removal commands credited, then a refusal at cleanup stage 0

Boot: mainline `cdcdc822-6c58-4146-8bda-72e3b1acde06` on candidate 28 (compile 33,
package `bf244275…`, built input 94e9c890, boot2 `92bf31d0…`), session tools at
bb57f446, consumed once by the custodian after deployment 28 (predecessor candidate 27
`c45503fa…`, stock boot `8e3984fd…`). Evidence: the custodian's thirteen sanitized
uploads; kernel log sealed complete (166218 bytes, 2096 records, SHA-256
`4a059343…`); supplicant log complete (24188 bytes, SHA-256 `37f8c920…`); logger
246956 ms; the host wait ended on the join's terminal (join lifecycle terminal, exit
0). No raw capture, packet content, address, credential or image is published.

## Observed (kernel records, µs since boot)

- Handshake as before; both key commands credited with their add-key-done windows;
  `data phase: budget_ms=6148 teardown_margin_ms=5000 inside_grant=1` at 241953398.
- 0176 observed: four beacons delivered and recorded, two clear before the group key
  (241751126, 241876317; RCPI 94 and 96) and two keyed after it (241974073,
  242070095); no total (it is written at stage 3, not reached), so deliveries beyond
  four are not counted. No nullfunc poll and no local disconnect occurred during the
  data phase.
- Data: `data TX: first pid=5 pages=3 bytes=342` at 243170030, `TX done: pid=5
  status=0` at 243171262 (+1232 µs), first credit at 243193972; 28 consecutive
  completions, PIDs 5 to 32, all status 0, none failed, none late. `data phase end:
  reason=budget elapsed_ms=6164 rx_unicast=34 rx_group=16 rx_dropped=0 tx_queued=28
  tx_done=28 tx_failed=0 tx_credits=57` at 248117997: the first data phase of the
  series to end by its budget.
- Host, separately: `udhcpc` exit 0, lease bound, prefix 24; the listener ready;
  `ping` 3 sent, 3 received; the laptop's one Wi-Fi SSH exchange exit 0, 37 bytes,
  boot match true, readiness after 6.7 s, elapsed 8.0 s. The milestone of runtime 28
  repeated. No Wi-Fi operational, reliability or replay-protection claim;
  `wifi_operational` stays false.
- Cleanup: the reserved deauthentication `TX: subtype=12 pid=33` at 248120268, its
  credit, `TX done: pid=33 status=0` at 248143037; `key removal: pairwise submitted
  sequence=27` and its credit; `key removal: group submitted sequence=28` and its
  credit at 248189948; `cleanup submission: stage=0` at 248191004 and its credit at
  248213950.
- Stop: `frame refused` at 248215064 (1114 µs after that credit, 25116 µs after the
  group key removal's credit): 110 bytes, type word 0x4000, descriptor bytes 08 28 18 04
  ff 00 00 c2, no RX groups, header at 16, first frame-control word 0x6208, security
  mode 0, receiver not this station, transmitter the target. Footer at 248217634:
  status -71, first 0, submitted 0x1801, debt 0, cleanup 1, branch 7. The supplicant's
  one disconnect carries reason 3 with `locally_generated=1` (its own leaving
  deauthentication at the session's end), distinct from runtime 28's reason 4.
- Verdicts as computed (preserved): bounded join false; `malformed_stage_record`
  false; refusal recorded; terminal failure recorded, branch 7; acknowledgements
  unique; handshake and data-path passes false (the lifetime fail-stopped); healthy
  cleanup false; C2 false; C3 false.

## The refused packet, decoded by the pinned vendor layout (source, not hardware proof)

Type word 0x4000: packet type 2 (`RX_PKT_TYPE_RX_DATA`, bits 13 to 15) with no
status groups (bits 9 to 12 zero), the hardware data descriptor, not the software
frame form (0xe001 plus groups) every other delivered frame of the lifetime carried.
Descriptor: match flags 0x08 (broadcast), channel 40, header length 24 untranslated,
payload format 0 with BSSID field 1, WLAN index 255 (no table entry), TID 0 and
security mode 0, status 0xc200: the two high bits every admitted packet carries and
`RX_STATUS_LLC_MIS` (bit 9), every error flag clear. Frame control 0x6208: data,
FromDS, More Data, Protected. This is the group-data class of runtimes 17 and 22
(group-data.h, proposal 0164: descriptor 08 28 18 04 02 00 04 c0, frame control
0x6208) in a descriptor variant consistent with the after-removal window: the WLAN
index names no entry and the body, still encrypted, trips the LLC check instead of the
cipher-mismatch flag. The pinned vendor data path drops a frame flagged LLC mismatch
without delivering it. The group key removal command's credit preceded the packet by
25 ms; a removal's credit proves buffer consumption only, so this packet does not
prove that the hardware retired the key. Inference, not measured: the AP's group
traffic continued while the cleanup commands ran, and the descriptor changed with the
removal window.
The existing group-data discard applies only while the station is active before the
group key, under the declared entry and status 0xc004, so the packet reached the gate
and the gate refused it as designed.

## Proposal 0177

`patches/proposals/0177-…`: the after-removal variant is named by a second decoder in
group-data.h with the keyed class's frame conditions (non-QoS data, FromDS and
Protected set, ToDS, More Fragments, Power Management and Order clear, a group receiver,
the target as transmitter, fragment 0, at least 40 bytes after the header) and the
observed descriptor (broadcast or multicast match flag only, native 24-byte header,
payload format 0 with BSSID field 1, WLAN index 255, byte 9 zero, status exactly
0xc200), each predicate gated exactly on the observed values until the next
observation; the keyed decoder is unchanged. During the cleanup, after the group key
removal command was submitted and before stage 3, that exact variant is discarded, never
delivered or interpreted, no submission follows; the first eight are recorded, the
total before the stage-3 record; the lifetime's packet budget and the cleanup's own
deadline bound it. Before the removal, or after stage 3, it is a refusal as before. No
other shape, radio, TX or time budget changes. The classifier knows the records and
their window (after the group key removal's record, before the terminal), the total,
and reports records and total apart.

## Proposed runtime 30 protocol (bounded, one test)

Candidate 29 from compile 34 (0163 to 0177) with candidate 28's RAM root, DT and
config; runtime 29's protocol otherwise unchanged. Hypothesis: the AP's group frames
during the cleanup are discarded and counted, the cleanup stages 1 to 3 are recorded
and the lifetime ends healthy (no footer); the beacon total with its keyed part and the
network terms are observed and reported apart. Branches: (1) stages 1 to 3 recorded,
no footer: the first healthy C3 lifetime; (2) a refusal of another shape during the
cleanup: recorded by its fields, the next audit; (3) a disconnect or a branch-9 footer:
read from the supplicant fields and the delivered-beacon records; (4) any other named
refusal or fault: fail-stop, seal, native recovery once. No repeat of candidate 28
without this change; no operational or replay-protection claim.
