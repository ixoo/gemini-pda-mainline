# Runtime 17: message 1 delivered and message 2 sent, then a protected group-addressed data frame refused before message 3

Status: C2 negative on candidate 16 (compile 21, proposals 0153 to 0159), the
diagnostic boot: the driver delivered message 1 (tag 15, before the
activation) and sent message 2 with its credit, and then refused the next
received packet at the frame gate, a 110-byte native data RXD now fully named
by the extended summary, and fail-stopped before message 3; no key was offered
or refused. This is a different packet from runtime 16's software frame, which
did not recur; the software frame's subtype remains unmeasured. The channel-40
no-IR flag was clear during the join for the first time. The session, log
seal, A53 regression and reviewed native recovery passed.

## Identity

- Candidate 16, receipt `1aaf85ea…`, installed as [deployment 16](results/deployment-16.json)
  (full padded boot2 `c773902c…`), compile 21 input `4983499e`, package `f429ebe9…`.
- Mainline boot `cc846a32-e380-492f-a5e7-4e2caa88a352`, release
  `7.1.3-gemini-a53-wifi-phase-b-compile`; capture 17 and session 17 each ran
  exactly once from the frozen `c41ab7b8` laptop wrappers.
- Return: changed-boot Gemian `fbf740cb-2f97-456b-8222-9e67979d0c9a`, confirmed
  independently over the Gemian LAN. Complete sealed kernel log 153324 bytes,
  SHA-256 `2fc70231…`; preservation manifest `5dc6cfb7…`; complete private
  supplicant log 19488 bytes, SHA-256 `02625dd4…` (export complete, boot
  matched, zero supplicant processes). No raw log, command, identifier or
  credential left the laptop.

## Observations

- Capture 17 (Phase A): WMT common init 285/285, calibration, prerequisites ready.
- Driver sequence (sanitized records): grant channel 40; authentication TX
  pid 1, done, RX status 0; association TX pid 2, done, RX status 0; `eapol
  delivered: translated=1 frame=99 activated=0 vector=0 bss=15`; activation
  sequence 24 state 3; `eapol sent: pid=3 pages=2 bytes=135`, TX done pid 3
  status 0; then `frame refused: bytes=110 type=0x4000 allowed=0x1400
  hdr=08281804000004c0 groups=0x0 at=16 g4fc=0x10000 g4seq=0x10000 g4ta=0
  translated=0 first=0x6208 sec=0 to=0 from=1`; `stopped: status=-71 first=0
  submitted=0x801 debt=0 cleanup=0 branch=7`. No key command, no key refusal
  record (none was offered).
- Supplicant fixed phrases (counts only): one nl80211 scan result set,
  `Associated with` 2, `RX message 1` 1, `Sending EAPOL-Key 2/4` 1, message 3,
  message 4, `Installing PTK`, `Installing GTK`, key negotiation completed and
  connected all 0, disconnected 1.
- Tool fields: `supplicant_exit=0`, `connect_exit=0`, `join_terminal=1`,
  `scan_exit=0`; `channel40_ir_during_join=1` with `channel40_ir_ticks=1`;
  after exit `channel40_ir_after_beacon=0`, one line, `no_IR`;
  `c2_session_pass=false`. The classifier's `malformed_stage_record` reflects
  the absent healthy lifecycle after the fail-stop, not a malformed received
  frame.

## Diagnosis

### The refused packet, as measured

Type word `0x4000`: a data RXD (packet type 2) with no optional group, header
at offset 16. Descriptor bytes 4 to 11 `08 28 18 04 00 00 04 c0`, read against
the public gen3 layout (`nic_rx.h`): match flags `0x08`, the broadcast-frame
bit set and the unicast-to-me bit clear; channel 40; header length 24, not
translated, no padding; payload format 0 with BSSID field 1 (the value the
active station's frames carry); WLAN index 0 (the group index this driver
declared); TID 0 and security mode 0 (no cipher applied by the hardware);
status `0xc004`, the two high bits every admitted packet of this lifetime has
carried plus bit 2, `RX_STATUS_FLAG_CIPHER_MISMATCH`, with every error and
malformed-frame flag clear. Frame control `0x6208`: data, subtype 0, FromDS,
More Data, Protected; the transmitter is the target (`from=1`) and the
receiver is not this station (`to=0`). The receiver address itself and the
body were not recorded, so the frame is not identified beyond this: a
protected, group-flagged, non-QoS data frame from the AP that the hardware
could not decrypt, with 94 wire bytes whose content is unknown.

### Why it ended the join

The frame gate admits only the EAPOL decoder's clear frames and the
management decoder's permitted subtypes; a protected data frame matches
neither and the design fail-stops on any other shape. The AP's ordinary
group-addressed traffic, encrypted with a group key this station does not
hold until message 3 delivers it, can arrive at any moment after the
association; in runtime 16 it did not arrive before message 3, in runtime 17
it did. The join can therefore end at this gate at random before the
handshake completes.

### The other measurements

The runtime-16 software frame did not recur; its subtype, peer and flags
remain unmeasured, and no admission for it is proposed. The channel-40 flag
was 1 during the join (one tick) and `no IR` after the supplicant's exit, as
the source-based explanation of runtime 16 predicted; both states are now
measured once. The message-3 phrase counted 0 under either prefix because no
message 3 was processed.

## Decision

Proposal 0160 discards, without delivery or interpretation, exactly the
measured class while the station is active and before a group key command
has returned its credit: the public data RXD layout with the measured
descriptor fields (group match bit without unicast-to-me, native 24-byte
header, payload format 0 with BSSID field 1, WLAN index 0, security mode 0,
status exactly `0xc004`), a non-QoS data frame control with FromDS and
Protected set and ToDS, More Fragments, Power Management and Order clear, a
group receiver address, the target as transmitter, fragment 0 and a whole
header. The first eight are recorded by their descriptor and header fields,
at most sixty-four are accepted per join, and anything else, including the
same frame after the group key or any unicast protected frame, reaches the
refusal as before. No protected frame is delivered, no body is read, no key,
replay or cipher state is touched. A new compile and candidate follow the
review.
