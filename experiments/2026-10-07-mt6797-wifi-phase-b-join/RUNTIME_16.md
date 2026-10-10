# Runtime 16: both EAPOL frames delivered and both replies sent, then a software frame refused before any key command

Status: C2 negative on candidate 15 (compile 20, proposals 0153 to 0158): the
driver delivered the AP's message 1 (tag 15, before the activation) and the
next EAPOL-shaped packet (tag 1, active), sent messages 2 and 4 with their
credits, and then refused the next received packet at the frame gate, a
136-byte software-defined frame about which the refusal summary could say
nothing, and fail-stopped. The supplicant completed its handshake and offered
both keys; no key command reached the firmware. The session, log seal, A53
regression and reviewed native recovery passed. Two of the four handshake
messages are demonstrated on the air in each direction; the keys are not.

## Identity

- Candidate 15, receipt `a99fc4f9…`, installed as [deployment 15](results/deployment-15.json)
  (full padded boot2 `eb43ddef…`), compile 20 input `67a37ca1`, package `ee32128d…`.
- Mainline boot `622c43de-c6fb-4a5d-948e-797b7f03e3db`, release
  `7.1.3-gemini-a53-wifi-phase-b-compile`; capture 16 and session 16 each ran
  exactly once from the frozen `e094ff6f` laptop wrappers.
- Return: changed-boot Gemian `485cca7c-1a75-456d-bf1e-2898c63ca0ed`, confirmed
  independently over the Gemian LAN. Complete sealed kernel log 154043 bytes,
  SHA-256 `aa306cb1…`; preservation manifest `4867365c…`; complete private
  supplicant log 24272 bytes, SHA-256 `f723a847…` (export complete, boot
  matched, zero supplicant processes). No raw log, command, identifier or
  credential left the laptop.

## Observations

- Capture 16 (Phase A): WMT common init 285/285, calibration ACK 1, task-4
  reply 382 bytes, PA rails off, prerequisites ready.
- Driver sequence (sanitized records): authentication TX pid 1, done, RX
  status 0; association TX pid 2, done, RX status 0; `eapol delivered:
  translated=1 frame=99 activated=0 vector=0 bss=15`; activation sequence 24
  state 3; `eapol sent: pid=3 pages=2 bytes=135`, credit, TX done pid 3
  status 0; `eapol delivered: translated=1 frame=155 activated=1 vector=0
  bss=1`; `eapol sent: pid=4 pages=2 bytes=113`, credit, TX done pid 4
  status 0; then `frame refused: bytes=136 type=0xee01 allowed=0x1400
  hdr=0000000000000000 groups=0x0 at=0 g4fc=0x10000 g4seq=0x10000 g4ta=0
  translated=0 first=0x10000`; `stopped: status=-71 first=0 submitted=0x801
  debt=0 cleanup=0 branch=7`. No key command, no removal.
- Supplicant fixed phrases (private log, counts only): `nl80211: Received scan
  results` 1; `Associated with` 2; `WPA: RX message 1 of 4-Way Handshake` 1;
  `WPA: Sending EAPOL-Key 2/4` 1; `RSN: RX message 3 of 4-Way Handshake` 1
  (the `WPA:`-prefixed variant 0, see below); `WPA: Sending EAPOL-Key 4/4` 1;
  `WPA: Installing PTK` 1; `WPA: Installing GTK` 1; `WPA: Key negotiation
  completed` 1; `CTRL-EVENT-CONNECTED` 1; `CTRL-EVENT-DISCONNECTED` 1.
- Tool fields: `supplicant_exit=0`, `connect_exit=0`, `join_terminal=1`,
  `channel40_ir_after_beacon=0` with `channel40_query_exit=0`,
  `channel40_lines=1`, `channel40_words=no_IR`; `scan_exit=0`;
  `c2_session_pass=false`. The classifier's `malformed_stage_record` reflects
  the absent healthy deauthentication and cleanup after the fail-stop, not a
  malformed received frame.

## Diagnosis

### The refused packet

Type word `0xee01` is, in the pinned gen3 source, a software-defined packet
(`RX_PKT_TYPE_SW_DEFINED`, bits 13 to 15 = 7) whose low nibble marks it as a
frame (`RXM_RXD_PKT_TYPE_SW_FRAME`, `nic_rx.h`), the kind the pinned receive
path hands to its management processing (`nic_rx.c`, `nicRxProcessMgmtPacket`);
bits 9 to 12 declare groups 1, 2 and 3, so the hardware descriptor occupies
64 of the 136 bytes and the wire frame 72. That is exactly the layout the
driver's own management decoder reads for the authentication and association
responses, and the decoder refused this one: not an allowed subtype
(disassociation and deauthentication were permitted, mask `0x1400`), or not
addressed from the AP to this station, or with header flags outside the
admission. Which of these applied is unmeasured: the refusal summary
interpreted only data-type RXDs (packet type 2), so every field of this
record is zero or the unknown sentinel. The frame control, subtype, peer
match, header flags and security mode are therefore unknown, and no
identification of the frame is claimed.

### Key-command timing

The refusal followed message 4's TX done immediately and the join fail-stopped
on it; the supplicant installs the pairwise key after it has handed message 4
to the driver, so by the time its `set_key` could reach the driver the join
had already stopped. The driver's `set_key` refuses silently outside the
admitted state, so no record says whether a key was offered and refused or
never offered. The supplicant's log shows the keys were offered (`Installing
PTK`, `Installing GTK`, each once).

### The message-3 marker

`rsn_supp/wpa.c` logs message 3 with the `WPA:` prefix in
`wpa_supplicant_process_3_of_4_wpa` (line 2477, the WPA path) and with the
`RSN:` prefix in `wpa_supplicant_process_3_of_4` (line 2546, the WPA2 path
this network takes). The runtime-15 phrase used the `WPA:` prefix and counted
0 although message 3 was processed; the owner's prefix-aware count is 1.
Message 4 was never counted as message 3.

### The channel-40 flag

The query after the supplicant's exit reported exactly one channel-40 line
carrying `no IR`, while the association had just succeeded on that channel.
In `net/wireless/sme.c`, `disconnect_work` calls `regulatory_hint_disconnect`
once every interface is idle after a disconnection; in `net/wireless/reg.c`
that function, for a wiphy without `REGULATORY_COUNTRY_IE_IGNORE` (this
driver sets no regulatory flags), calls `restore_regulatory_settings`, which
clears the beacon hints and restores the world regulatory domain, in which
channel 40 is no-IR. The driver's deauthentication ends the connection, the
supplicant exits, and the flag queried afterwards is the restored one. The
runtime-15 and runtime-16 zeros are this timing, not a radio or driver
condition; the Phase C1 scripts queried the flag before any connection.

## Decision

- Driver, diagnostic only (proposal 0159): the refusal summary interprets
  software frames as it interprets data RXDs and adds the descriptor's
  security mode and the receiver-is-this-station and transmitter-is-the-target
  flags; a refused key command is named with its status and state flags. No
  receive admission or effect changes: the next boot measures the refused
  frame's control, peer match and header flags, and an exact policy for it is
  decided from that measurement, not from its type and length.
- Tooling: the message-3 phrase drops its prefix; `Installing PTK` and
  `Installing GTK` are counted; the channel-40 state is sampled every tick of
  the wait and the during-join observation is the gate, with the after-exit
  state recorded next to it.
