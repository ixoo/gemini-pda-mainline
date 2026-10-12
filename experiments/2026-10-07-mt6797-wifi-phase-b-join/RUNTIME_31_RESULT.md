# Runtime 31 result: the first complete bounded C2+C3 pass — healthy join, data phase, DHCP/ping/SSH and a clean three-stage cleanup, with no refusal and no footer

Boot: mainline `fdb6a30a-4938-48b2-af07-bcde7b7a575f` on candidate 30 (compile 35,
package `bfa7516a…`, built input 8ccf249c, raw boot `7aee04b8…`, full padded boot2
`e758bf36…`), session tools at 692ccb69, consumed once by the custodian after
deployment 30 (derived reviewed installer `e2b9ad42…`, predecessor candidate 29
`27005b8f…`, guard passed, full 16 MiB readback `e758bf36…` and an independent
full-stream compare, install exit 0, clean power-off; the owner selected boot2
physically). Evidence: the custodian's thirteen sanitized uploads in the ignored private evidence
directory (mode 0700, each file 0600, every hop SHA verified); kernel log sealed complete (166574 bytes, 2101 records, SHA-256
`683f0015…`); supplicant log complete (26364 bytes, SHA-256 `4685719a…`, no per-line
timestamps, independently framed length and digest verified); logger 91125 ms; the host
wait ended on the join's terminal (join lifecycle terminal, exit 0, host phase 9.366 s,
empty keepalive, stderr 0). No raw capture, packet content, address, credential or image
is published.

## Verdict (as computed, preserved)

The first complete bounded C2+C3 pass of the series:
`c2_session_pass=true`, `c3_session_pass=true`, `bounded_join_pass=true`,
`healthy_cleanup_demonstrated=true`, `stage_and_credit_order_verified=true`,
`driver_handshake_path_pass=true`, `driver_data_path_pass=true`,
`management_exchange_demonstrated=true`, `associated_station_activation_demonstrated=true`,
`unique_tx_acknowledgements=true`. No refusal (`refusal_recorded=false`), no terminal
failure (`terminal_failure_recorded=false`, `terminal_branch=null`,
`terminal_status=null`), not malformed (`malformed_stage_record=false`).
`wifi_operational=false`. This is the first healthy lifetime of candidate 30; it is one
bounded lifetime, not an operational, reliability or replay-protection claim.

## Observed (kernel records, µs since boot; chronology from the custodian's sanitized `join-records.txt`, record SHA `bcb74332…`)

- Handshake: open-system authentication (`TX subtype=11 pid=1 status=0`, `RX subtype=11
  status=0`), association (`TX subtype=0 pid=2 status=0`, `RX subtype=1 status=0`), the
  two EAPOL deliveries (`frame=99 activated=0 bss=15`; `frame=155 activated=1 bss=1`,
  station activated at sequence 24), and both key commands credited: pairwise submitted
  sequence 25 at 85322881, `key done: first after=pairwise`, `key credit returned:
  pairwise`; group submitted sequence 26 at 85361458, `key done: second after=group`,
  `key credit returned: group`. The supplicant log carries the matching one-of/three-of
  four-way messages, `installing ptk`, `installing gtk`, `key negotiation completed`,
  `associated with` (2), one connected and one disconnected ctrl event, exit 0, 0
  residual processes.
- Data phase: opened at sequence 2035 (85372789) with `budget_ms=6176
  teardown_margin_ms=5000 inside_grant=1`; `data TX: first pid=5 pages=3 bytes=342` at
  85537460; `data RX: first group=0 tid=0 keyid=0 bytes=333 vector=0` at 85541309;
  27 consecutive TX completions, PIDs 5 to 31, all status 0, none failed, none late;
  ended at sequence 2082 (91553411) `reason=budget elapsed_ms=6180 rx_unicast=34
  rx_group=12 rx_dropped=0 tx_queued=27 tx_done=27 tx_failed=0 tx_credits=56`. The data
  phase closed on its own budget, not on any refusal.
- Beacons: four `beacon delivered` records (one clear `keyed=0`, three `keyed=1`, RCPI
  90/88); total at stage 3 `beacons delivered: total=63 keyed=61`.
- Discards, all the pre-existing management classes, none the new data classes: eight
  `group action frame discarded` (bytes 644, fc 0xd0, match 0x08, wlan 255, bss 15,
  status 0xe000; counts 1 to 8 at sequences 2009, 2037, 2038, 2054, 2076, 2078, 2079,
  2081 — one before the data phase, the rest across it) and one directed `action frame
  discarded` (bytes 72, fc 0xd0, match 0x02, wlan 1, bss 1, status 0xe000). No pre-key
  `group data discarded` (the 0164 status-0xc004 class of runtimes 17, 22 and 30 did not
  appear). **The new 0178 data LLC-mismatch class was not observed** (`data_llc_discards`
  records 0, total null) and **the 0177 after-removal cleanup class was not observed**
  (`cleanup_group_discards` records 0, total null).
- Cleanup, healthy: deauthentication `TX subtype=12 pid=32 status=0` (sequence 2083/2085);
  key removals pairwise submitted sequence 27 (91579774) and group submitted sequence 28
  (91602667), each with its credit; cleanup submissions stage 0 (91630545), stage 1
  (91658476), stage 2 (91682529); `bss absence: bss=0 absent=0 quota=0 reserved=0`
  (91706534); and the healthy `cleanup: stage=3 credits=returned slots=retired deauth=1`
  at sequence 2098 (91708956). No footer record followed; the lifetime ended on the
  healthy stage-3 cleanup.
- Host, separately: `udhcpc` exit 0, one lease bound, prefix 24; `ping` 3 sent, 3
  received; the laptop's one Wi-Fi SSH exchange exit 0, 37 bytes, boot match true,
  readiness after 4.5 s, elapsed 5.6 s, bound to `mainline_boot` `fdb6a30a…`. Each is
  reported as what it is; none is implied by another, and none is an operational or
  reliability claim.
- Supplicant disconnect: one event, reason 4, `locally_generated=1`, line 372 (the log
  has no per-line timestamps). Causality is not inferred beyond the kernel's own
  budget-and-cleanup chronology above: the kernel data phase ended on its budget and the
  cleanup completed healthy; the single local supplicant disconnect is recorded as a
  field, not read as a cause.

## Scan and Phase A (as computed, preserved)

Phase A reached ready-for-scan (common init 285/285, negotiation passed, BT H1 absent,
PA rails off after). The single admitted scan completed (`scan_completed=true`,
`standard_scan_succeeded=true`, channel 40 permitted, firmware management processing
count 15, one validated beacon reported) with the tuning and counter diagnoses
`inconclusive` as before; `passive_scan_demonstrated=false`, `rf_tuning_verified=false`,
`effective_rf_dwell_verified=false`. No new RF or tuning claim follows.

## Recovery (as computed, preserved; do not rewrite the request-stage field)

The reviewed native recovery was requested once after the seals:
`native-request-result.json` records `recovery_confirmed=false` — the request-stage
field at the moment of the request. The return collector then recorded the completed
return separately (`session-result.json`/`deferred-start-result.json`:
`recovery_confirmed=true`, return attempts 2, elapsed 15.422 s, classification
`changed-ID-Gemian`), and an independent known-good Gemian SSH confirmed the changed boot
`505bcade-6441-4729-82ee-025c341648b9`, release 3.18.41+, aarch64. The device is on
Gemian now. The request-stage `false` and the later confirmed `true` are both kept as
recorded; neither is rewritten into the other.

## What this does and does not establish

Establishes, once, on this boot: the full mainline WPA2-PSK station lifecycle on the
mt6797 — association and firmware activation, both keys submitted and credited, a bounded
data phase with 27 data TX completions with status 0 and 34 unicast plus 12 group receive
frames and zero drops, a DHCP lease, three ICMP replies and one boot-bound SSH exchange,
and a clean host-owned three-stage cleanup returning the credits and retiring the slots
with no refusal and no footer. The TX completions are status-0 completion records, not a
measured ACK or delivery proof, and the records do not split the 27 by Ethernet unicast
(DHCP may broadcast); the separately recorded management TX acknowledgements
(authentication and association, response status 0) stay as stated. The key-state fields
denote submitted-and-credited commands, not a measured hardware-install proof.

Does not establish: that 0178's data LLC-mismatch path or 0177's cleanup path was
exercised (neither triggering frame arrived this boot, so neither is demonstrated and
neither can be credited with the pass); any operational, reliability, throughput or
persistence claim beyond this one bounded lifetime; decryption of any frame (security
mode and header translation are descriptor observations); or firmware replay-protection
behavior, which remains unknown and unclaimed. No RF tuning or effective dwell is proved.

## Smallest concrete next step (hardware-free, source; no repeat boot, no speculative rebuild)

The lifetime is deliberately bounded: the driver retires the data phase on its budget and
tears down. The first justified question that does not widen generally and does not need
the device is a single, scoped dependency: **does the vendor RX metadata layout we already
decode expose a received group-key packet number (PN)?** This bears only on *host-side
replay accounting over the existing IV-stripped receive path* — the frames that path
delivers have the IV stripped, so any host replay check would need the PN surfaced in
metadata. It is **not** a precondition for native-format software CCMP, which is a separate
approach requiring intact ciphertext, the CCMP header and MIC, authentication, and its own
evidence that the hardware can deliver such frames at all. Even a present PN proves neither
enforcement nor integrity on its own: host replay accounting would still need the exact
key, TID, key incarnation, authenticity and ordering semantics, none of which a PN field
supplies. Establishing the fact is a read-only reading of the vendor receive descriptor and
header where rights allow, within the current hardware-free scope; no patch, build, boot,
RE replay, radio or calibration test is part of it, and replay enforcement in firmware
remains unknown. A repeat of this identical boot is not proposed. The result is a dependency
finding to decide the next measurable move, not a generalized push toward an operational
interface.
