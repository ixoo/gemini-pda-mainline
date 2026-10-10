# Runtime 18: the four-way handshake completed in the supplicant, keys offered, then a directed clear Action frame refused before any key command

Status: C2 negative on candidate 17 (compile 22, proposals 0153 to 0160): the
driver delivered both EAPOL frames (tags 15 then 1), sent messages 2 and 4
with their credits, the supplicant processed messages 1 and 3, sent 2 and 4,
completed its key negotiation, reported connected and offered both keys; the
frame gate then refused the next received packet, which the extended summary
named as an unprotected Action frame from the target to this station, and
the join fail-stopped before either key command reached the firmware. The
group-data discard of proposal 0160 was not exercised: no group frame arrived
before the stop. The channel-40 flag was clear during the join. The session,
log seal, A53 regression and reviewed native recovery passed. Four handshake
messages are demonstrated on the air; the keys are not installed in the
firmware and nothing is operational.

## Identity

- Candidate 17, receipt `cf5958f2…`, installed as [deployment 17](results/deployment-17.json)
  (full padded boot2 `5135b2f8…`), compile 22 input `6a3b000d`, package `096b50b5…`.
- Mainline boot `cfaef005-d3da-4987-b083-dac03d9f2edf`, release
  `7.1.3-gemini-a53-wifi-phase-b-compile`; capture 18 and session 18 each ran
  exactly once from the frozen `f50b98e0` laptop wrappers (executables as at
  `f4010c87`).
- Return: changed-boot Gemian `9ad08944-1958-4b15-a91a-c6bbbbdce2e3`, confirmed
  independently over the Gemian LAN. Complete sealed kernel log 153762 bytes,
  SHA-256 `68bdd064…`; preservation manifest `19534f4d…`; complete private
  supplicant log 24060 bytes, SHA-256 `196f9ad4…` (export complete, boot
  matched, zero supplicant processes). No raw log, command, identifier or
  credential left the laptop.

## Observations

- Capture 18 (Phase A): WMT common init 285/285, calibration, prerequisites ready.
- Driver sequence (27 sanitized records): grant channel 40; authentication TX
  pid 1, done, RX status 0; association TX pid 2, done, RX status 0; `eapol
  delivered: translated=1 frame=99 activated=0 vector=0 bss=15`; activation
  sequence 24 state 3; `eapol sent: pid=3 pages=2 bytes=135`, credit, TX done;
  `eapol delivered: translated=1 frame=155 activated=1 vector=0 bss=1`; `eapol
  sent: pid=4 pages=2 bytes=113`, credit, TX done; then `frame refused:
  bytes=136 type=0xee01 allowed=0x1400 hdr=02281804010000e0 groups=0x7 at=64
  g4fc=0x10000 g4seq=0x10000 g4ta=0 translated=0 first=0xd0 sec=0 to=1
  from=1`; `stopped: status=-71 first=0 submitted=0x801 debt=0 cleanup=0
  branch=7`; `key command refused: pairwise status=-71 running=0 active=1
  configured=1 first=-71`; `key command refused: group status=-95 running=0
  active=1 configured=1 first=-71`. No key command, credit or removal; no
  group-data discard record.
- Supplicant fixed phrases (counts only): one nl80211 scan result set,
  `Associated with` 2, messages 1, 2, 3 and 4 one each, `Installing PTK` 1,
  `Installing GTK` 1, key negotiation completed 1, connected 1, disconnected 1.
- Tool fields: `supplicant_exit=0`, `connect_exit=0`, `join_terminal=1`,
  `scan_exit=0`, `channel40_ir_during_join=1` (1 tick), after exit `no_IR`;
  `c2_session_pass=false`. The classifier's `malformed_stage_record` reflects
  the absent healthy lifecycle after the fail-stop, not a malformed frame.

## Diagnosis

### The refused packet, as measured

Type word `0xee01`: the vendor's software-defined frame type (the layout its
receive path hands to management processing), groups 1, 2 and 3, so the
header starts at offset 64; 136 bytes in all, 72 on the wire. Descriptor
bytes 4 to 11 `02 28 18 04 01 00 00 e0`: match flags `0x02`, the
unicast-to-me bit only (no HT control, multicast or broadcast); channel 40;
header length 24, untranslated, no padding; payload format 0 with BSSID
field 1; WLAN index 1 (this station's own index); TID 0 and security mode 0;
status `0xe000`. Frame control `0x00d0`: management type, subtype 13
(Action), no flag set, unprotected; the receiver is this station (`to=1`)
and the transmitter is the target (`from=1`). The 48-byte body, including
the category and action fields, and the sequence were not recorded; no
category is claimed. Runtime 16's refused 136-byte software frame had the
same type word and length and was never named; it is consistent with the
same class, which is an inference.

### Why it ended the join

The management gate permits only disassociation and deauthentication after
the association (mask `0x1400`); an Action frame matches no decoder and the
design fail-stops on any other shape. The AP sends it shortly after message
4 (runtimes 16 and 18); in runtime 17 the group-data refusal came first.

### The key refusals, from the source

The pairwise install passed `set_key`'s admission (the join was running, the
station active, the BSS configured) and waited on the TC4 ledger
(`mt6797_mac_join_wait_management` or `mt6797_mac_join_wait_credit`) for the
in-flight reply's credit; those waits return `mac->first_error` as soon as the
worker records one, and the worker's fail-stop on the Action frame set it to
`-EPROTO` (-71); the record shows `running=0` because the worker had already
stopped. No key payload was built or sent. The group install arrived after
that and met `set_key`'s first admission check with the lifetime stopped
(`!join_running`, `first_error` set, `closing` and `join_retired` set), which
returns `-EOPNOTSUPP` (-95): the generic refusal outside the admitted state,
caused by the same stop, not inherited from the pairwise error. Both keys
were offered by the supplicant and neither reached the firmware; no credit
or removal exists.

## Decision

Proposal 0161 discards exactly the measured class while the station is
active: the software-frame type word with groups 1 to 3, the descriptor bytes
exactly as measured (unicast-to-me only; 24-byte untranslated unpadded
header; format 0 with BSSID field 1; WLAN index 1; byte 9 zero; status
`0xe000`), frame control `0x00d0` with only the Retry bit free, receiver this
station, transmitter and BSSID the target, fragment 0, at least the category
byte present and never read. Each discard is recorded, at most eight per
join; the ninth and every other shape, including protected or Action No Ack
frames, other subtypes, group or other receivers and other peers, are refused
and named as before. No frame is delivered, no body is read, no RF submission
results (the hardware acknowledges on its own), no credit, lifecycle or key
handling changes. The group-data discard of 0160 stays as reviewed and
unexercised. A new compile and candidate follow the review.
