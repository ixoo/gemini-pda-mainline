# Runtime 15: association accepted, message 1 delivered, message 2 sent, the next EAPOL-shaped packet refused at its BSSID tag

Status: C2 negative on candidate 14 (compile 19, proposals 0153 to 0157): the
first handshake measurement on this hardware delivered message 1 and sent
message 2; the driver then refused the next received packet, a clear
translated EAPOL-shaped data packet from the AP, at its gate because its RXD
BSSID tag was 1, a value never measured before, and fail-stopped. Whether
that packet was message 3 is inferred from its position and visible shape,
not validated: no EAPOL body, message information, length or MIC of it was
examined, and the supplicant's log counts no received message 3. No key
command was submitted; the session, log seal, A53 regression and reviewed
native recovery passed.

## Identity

- Candidate 14, receipt `889b101f…`, installed as [deployment 14](results/deployment-14.json)
  (full padded boot2 `911e3d67…`).
- Mainline boot `27d0ac28-a85c-4377-a9b6-bb2d0f40f214`, release
  `7.1.3-gemini-a53-wifi-phase-b-compile`; capture 15 and session 15 each ran
  exactly once from the frozen `da5a776a` laptop wrappers with the custodian's
  fresh PSK-bound script.
- Return: changed-boot Gemian `b3805d07-c6c1-45df-b3be-e8a59507caff`, confirmed
  independently over the Gemian LAN. Complete sealed kernel log 153275 bytes,
  SHA-256 `dd618ea0…`; preservation manifest `abacf476…`; complete private
  supplicant log 19509 bytes, SHA-256 `d380fb1b…` (export complete, boot
  matched, zero supplicant processes). No raw log, command, identifier or
  credential left the laptop.

## Observations

- Capture 15 (Phase A): WMT common init 285/285, calibration ACK 1, task-4
  reply 382 bytes, PA rails off, prerequisites ready.
- Driver sequence (sanitized records): authentication TX pid 1, done, RX
  subtype 11 status 0; association TX pid 2, done, RX subtype 1 status 0;
  `eapol delivered: translated=1 frame=99 activated=0 vector=0 bss=15`
  (message 1); activation sequence 24 state 3; `eapol sent: pid=3 pages=2
  bytes=135` (message 2), credit 2 returned, TX done pid 3 status 0; then
  `frame refused: bytes=203 type=0x51af allowed=0x1400
  hdr=0228ce04010000c0 groups=0x8 at=34 g4fc=0x208 g4seq=0x10 g4ta=1
  translated=1 first=0x888e`; `stopped: status=-71 first=0 submitted=0x801
  debt=0 cleanup=0 branch=7`. No key command, no removal; fail-stop obeyed.
- Supplicant fixed phrases (private log, counts only): `Associated with` 2,
  `RX message 1 of 4-Way Handshake` 1, `Sending EAPOL-Key 2/4` 1, `RX
  message 3` 0, `Sending EAPOL-Key 4/4` 0, key negotiation completed 0,
  connected 0, disconnected 1; `nl80211: Received scan results` 1, `New scan
  results available` 2, `Scan completed` 1, `Scan requested` 1,
  `CTRL-EVENT-SCAN-RESULTS` 0.
- Tool fields: `supplicant_exit=0`, `connect_exit=0`, `join_terminal=1`,
  `channel40_ir_after_beacon=0`, `scan_exit=1`; `c2_session_pass=false`.
  The classifier's `malformed_stage_record` reflects the absent healthy
  deauthentication and cleanup after the fail-stop, not the refused frame's
  shape.

## Diagnosis

The refused packet's recorded summary is a complete data-type RXD (203
bytes, packet type 2, group 4 present, header offset bit set, translated
14-byte header, MSDU payload format 0, channel 40, WLAN index 1, status
`0xc000`) whose group-4 frame control is `0x0208` (data, From-DS) with the
AP as transmitter and whose first Ethernet word is `0x888e`: the clear
translated EAPOL shape of message 1 in every visible field except RXD byte
7, `0x04`, whose bits 2 to 7 carry BSSID tag 1 where message 1 carried 15.
Its position after message 2's acknowledgement is consistent with message 3;
nothing beyond the Ethernet type was examined, so that reading is an
inference. Proposal 0152's decoder admitted tags 0 and 15 only
(`eapol-rx.h`), and the admission bound 15 to the interval before the BSS
command's credit completion and 0 to afterwards; the tag is therefore the
one proven refusal, and it says nothing about whether the decoder's
remaining framing gates (header, LLC/SNAP, EAPOL-Key version, type, length)
would have admitted the body. In the pinned gen3 source the field is
`ucBssid` bits 2 to 7 of RXD DW1 (`nic_rx.h`, `RX_STATUS_BSSID_MASK`),
filled by the firmware and consumed by no driver code; the own-MAC index the
vendor assigns to its first BSS is 0 (`cnm.c`), so the value is not a
declared index, and no primary source defines its values; none is claimed.
Three measurements exist: 15 before the station activation (runtimes 12 and
15) and 1 after it (runtime 15). Tag 0 was never measured.

## Decision

Proposal 0158 binds the admission to the measured values only: tag 15 until
the BSS command's credit completion is recorded, tag 1 while the station is
active (`join_sta_active`); the decoder admits exactly those two values and
any other is refused and named as before, and the decoder's remaining
framing gates verify the after-activation packet on the next boot. No other
driver change. The tool
side: the one-scan gate counts the nl80211 driver's debug line instead of a
control-interface event that never reaches the log, the four handshake
messages are counted from the supplicant's debug lines, and the channel-40
flag records its query status, line count and flag words so a 0 names its
reason. Runtime 16 on a new candidate follows the review; this result is the
first handshake measurement and it is negative: two of the four messages
are demonstrated, the third is not.
