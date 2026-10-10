# Runtime 19: the Action frame discarded, the pairwise key command submitted, then an unsolicited add-key-done event refused

Status: C2 negative on candidate 18 (compile 23, proposals 0153 to 0161): the
driver delivered both EAPOL frames, sent messages 2 and 4, discarded the
target's directed clear Action frame once as proposal 0161 intended, and
submitted the pairwise key command, whose page credit returned; the control
event dispatcher then refused an unsolicited 16-byte event with id `0x24` and
the join fail-stopped before the key credit was recorded, before the group
key command, and before any removal or healthy teardown. No key is proven
installed and nothing is operational. The session, log seal, A53 regression
and reviewed native recovery passed.

## Identity

- Candidate 18, receipt `b0d577ba…`, installed as [deployment 18](results/deployment-18.json)
  (full padded boot2 `dfdf6bcb…`), compile 23 input `f5477df6`, package `4f07d571…`.
- Mainline boot `29a8c52d-fbef-4e7f-afd2-28dc3ff40efd`, release
  `7.1.3-gemini-a53-wifi-phase-b-compile`; capture 19 and session 19 each ran
  exactly once from the frozen `3235f639` laptop wrappers.
- Return: the reviewed native recovery was requested once; the request
  process ended at its outer 14 s timeout (exit 255, request stage only) and
  the reviewed return collector confirmed the changed Gemian boot after four
  bounded identity reads (45.3 s), with no alternate or retried action;
  Gemian `e66144f8-d4b6-42db-a8b2-f1302adc740d` (3.18.41+) confirmed
  independently over the LAN. The final deferred-start record's
  `recovery_confirmed` is authoritative; the request-stage record's false is
  the request stage only. Complete sealed kernel log 154215 bytes (2028
  records), SHA-256 `12016be7…`; pre-recovery preservation manifest
  `5ab4556e…`; complete private supplicant log 24060 bytes, SHA-256
  `f3b82a76…` (export complete, boot matched, zero supplicant processes). No
  raw log, command, identifier or credential left the laptop.

## Observations

- Capture 19 (Phase A): WMT common init 285/285, calibration, prerequisites ready.
- Driver sequence (31 sanitized records): grant channel 40; peer ready
  sequence 23; authentication and association each TX, credit, done, RX
  status 0; `eapol delivered: translated=1 frame=99 activated=0 vector=0
  bss=15`; activation sequence 24 state 3; `eapol sent: pid=3 pages=2
  bytes=135`, credit, TX done; `eapol delivered: translated=1 frame=155
  activated=1 vector=0 bss=1`; `eapol sent: pid=4 pages=2 bytes=113`, credit,
  TX done; `action frame discarded: bytes=72 fc=0xd0 match=0x02 wlan=1 bss=1
  sec=0 status=0xe000 count=1`; `key command: pairwise submitted
  sequence=25`; `credit: pages=1 remaining=0`; `control event refused:
  status=-71 bytes=16 type=0xe000 id=0x24 seq=0`; `stopped: status=-71
  first=0 submitted=0x801 debt=0 cleanup=0 branch=6`; `key command refused:
  pairwise status=-71 running=0 active=1 configured=1 first=-71`; `key
  command refused: group status=-95 running=0 active=1 configured=1
  first=-71`. No `key credit returned`, no group command, no removal, no
  group-data discard, no healthy cleanup.
- Supplicant fixed phrases (counts only): one nl80211 scan result set,
  `Associated with` 2, messages 1 to 4 one each, `Installing PTK` 1,
  `Installing GTK` 1, key negotiation completed 1, connected 1, disconnected 1.
- Tool fields: `supplicant_exit=0`, `connect_exit=0`, `join_terminal=1`,
  `scan_exit=0`, `channel40_ir_during_join=1` (1 tick), after exit `no_IR`;
  `c2_session_pass=false`. The classifier's `malformed_stage_record` reflects
  the aborted lifecycle, not a malformed event.

## Diagnosis

### The refused event, as measured and as the pinned source defines it

Measured: a control event (type word `0xe000`) of 16 bytes, id `0x24`,
sequence 0, arriving after the pairwise key command's page credit. Its 8-byte
payload was not recorded. In the pinned public gen3 source, id `0x24` is
`EVENT_ID_ADD_PKEY_DONE`, marked unsolicited (`nic_cmd_event.h`), with
payload `EVENT_ADD_KEY_DONE_INFO` of `ucBSSIndex`, `ucReserved` and
`aucStaAddr[6]`: 8 bytes, so 16 with the event header, and a sequence of 0
for an unsolicited event; both agree with the measurement. The pinned receive
path (`nic_rx.c`) looks the station up by that BSS index and address and marks
its TX key ready ("add key done for port control"). The event is therefore
consistent with the source-defined completion of a pairwise key add; whether
it refers to this station's BSS and the target, and so to the command this
driver submitted, is unverified because the payload was not examined.
The generic page credit before it shows the TC4 ledger returned the command's
page; it attributes nothing about the key to the firmware.

### Why it ended the join

The control event dispatcher admits ids `0x27`, `0x07`, `0x10`, `0x0c` and
`0x11` only; `0x24` reached its refusal and the design fail-stops on any
other event (branch 6). The pairwise `set_key` was waiting on the ledger for
its credit record when the worker stopped and returned the worker's
`-EPROTO`; the group install then met the stopped lifetime (`-EOPNOTSUPP`),
as in runtime 18. No key payload beyond the submitted pairwise command was
built or sent.

### The other measurements

Proposal 0161 worked as designed: one Action frame discarded and recorded,
the handshake continued to the key command. The group-data discard of 0160
was again not exercised. The channel-40 flag was clear during the join.

## Decision

Proposal 0162 admits that event exactly once: 16 bytes, type `0xe000`, id
`0x24`, sequence 0, after a pairwise key command was submitted, while the
station is active and the BSS configured, during the handshake hold in which
the reserved deauthentication is queued, and before the deauthentication is
in flight or done, before any cleanup stage and before the pairwise key's
removal, with BSS index 0 and the target's address compared and never
logged, the reserved byte unconstrained and unread; it records `key done:
pairwise bss=0 peer=1` and changes nothing the hold, the teardown, the key
slots or the credit ledger depend on, transmitting nothing. Any other event
of that id stays refused and named. The classifier admits the record once
after the pairwise command and the activation and before the
deauthentication's transmission, refuses an orphan record without a command,
and requires exactly one valid record, next to both key commands and their
credits, for `driver_handshake_path_pass`: the next boot measures the
event's ownership; the command's page credit alone is not treated as proof.
A new compile and candidate follow the review.
