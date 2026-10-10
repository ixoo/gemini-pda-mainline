# Runtime 20: the handshake complete, one owned add-key-done event recorded, a second one refused after the group key command

Status: C2 negative on candidate 19 (compile 24, proposals 0153 to 0162): the
driver delivered both EAPOL frames, sent messages 2 and 4, discarded the
target's directed clear Action frame once, submitted the pairwise key command,
received its page credit, admitted the firmware's add-key-done event once for
this BSS and the target (the first time that ownership was verified), recorded
the pairwise key credit, and submitted the group key command; after that
command's page credit the dispatcher refused a second unsolicited 16-byte
event with id `0x24` and the join fail-stopped before the group key credit,
the removals and the healthy teardown. The session, log seal, A53 regression
and reviewed native recovery passed. No key is proven installed and nothing
is operational.

## Identity

- Candidate 19, receipt `92b60a90…`, installed as [deployment 19](results/deployment-19.json)
  (full padded boot2 `5d9aa34b…`), compile 24 input `4be81db8`, package `295e881b…`.
- Mainline boot `d5bd48d0-111e-43a6-9d17-b279bdf5a1d4`, release
  `7.1.3-gemini-a53-wifi-phase-b-compile`; capture 20 and session 20 each ran
  exactly once from the frozen `db1c1673` laptop wrappers.
- Return: the reviewed native recovery was requested once; the request
  process ended at its outer 14 s timeout (exit 255, request stage only) and
  the reviewed return collector confirmed the changed Gemian boot after two
  bounded identity reads (15.3 s), with no alternate or retried action;
  Gemian `cf68b54a-7a3d-4949-8e1e-db1784cdc7df` (3.18.41+) confirmed
  independently over the LAN. The final deferred-start record's
  `recovery_confirmed` is authoritative; the request-stage record's false is
  the request stage only. Complete sealed kernel log 154749 bytes (2031
  records), SHA-256 `d5832c90…`; pre-recovery preservation manifest
  `0085b86b…`; complete private supplicant log 24086 bytes, SHA-256
  `bda88650…` (export complete, boot matched, zero supplicant processes). No
  raw log, command, credential or private peer or network identifier left
  the laptop; the sanitized boot IDs, digests and metadata in this record
  went to Buildbox.

## Observations

- Capture 20 (Phase A): WMT common init 285/285, calibration (one
  acknowledgment frame, 382 reply bytes), prerequisites in order, ready for scan.
- Driver sequence (34 sanitized records): grant channel 40; peer ready
  sequence 23; authentication and association each TX, credit, done, RX
  status 0; `eapol delivered: translated=1 frame=99 activated=0 vector=0
  bss=15`; activation sequence 24 state 3; `eapol sent: pid=3 pages=2
  bytes=135`, credit, TX done; `eapol delivered: translated=1 frame=155
  activated=1 vector=0 bss=1`; `eapol sent: pid=4 pages=2 bytes=113`, credit,
  TX done; `action frame discarded: bytes=72 fc=0xd0 match=0x02 wlan=1 bss=1
  sec=0 status=0xe000 count=1`; `key command: pairwise submitted
  sequence=25`; `credit: pages=1 remaining=0`; `key done: pairwise bss=0
  peer=1`; `key credit returned: pairwise`; `key command: group submitted
  sequence=26`; `credit: pages=1 remaining=0`; `control event refused:
  status=-71 bytes=16 type=0xe000 id=0x24 seq=0`; `stopped: status=-71
  first=0 submitted=0x801 debt=0 cleanup=0 branch=6`; `key command refused:
  group status=-71 running=0 active=1 configured=1 first=-71`. No group key
  credit record, no removal, no group-data discard, no healthy cleanup.
- Supplicant fixed phrases (counts only): one nl80211 scan result set,
  `Associated with` 2, messages 1 to 4 one each, `Installing PTK` 1,
  `Installing GTK` 1, key negotiation completed 1, connected 1, disconnected 1.
- Tool fields: `supplicant_exit=0`, `connect_exit=0`, `join_terminal=1`,
  `channel40_ir_during_join=1` (2 ticks: the channel-40 no-IR flag was
  cleared while the join ran), `channel40_ir_after_beacon=0` (after the
  disconnect the IR permission was absent again, the no-IR flag restored);
  `c2_session_pass=false`. The classifier's `firmware_pairwise_key_done`
  (now `firmware_key_done_first_window`) is false only because the key
  lifetime aborted; the record itself is present, once, in its window.

## Diagnosis

### What the first event proved and what the second does not

The admitted event carried BSS index 0 and the target's address, compared by
proposal 0162 and never logged: the firmware's add-key-done notification is
addressed to this station's BSS and peer, so the runtime-19 question of
ownership is answered for the first event. It arrived after the pairwise
command's page credit and before the pairwise key credit record, as the
pinned receive path's ordering suggests.

The second event, 16 bytes, id `0x24`, sequence 0, arrived after the group
key command's page credit; its payload was not recorded, so its BSS index and
address are unknown. In the pinned public gen3 source the payload
(`EVENT_ADD_KEY_DONE_INFO`) carries only the BSS index, a reserved byte and
the station address: no key type, key index or command sequence. Both of this
driver's key commands name the target as peer, so even a recorded payload
could not tell a group-key completion from a repeated pairwise notification.
The source's receive path marks the station's TX key ready on every such
event and says nothing about a group key; it neither predicts nor excludes a
second event. The second event is therefore consistent with the firmware
acknowledging the group key add for the same station, and equally with a
delayed repeat of the first; neither reading is claimed.

### Why it ended the join

Proposal 0162 admits one event of this id per lifetime; the second reached
the refusal and the design fail-stops on any other event (branch 6). The
group `set_key` was waiting on the ledger for its credit record and returned
the worker's `-EPROTO`. No key payload beyond the two submitted commands was
built or sent; the deauthentication and the removals were never submitted.

### The other measurements

Proposals 0158, 0160 and 0161 behaved as designed; the group-data discard of
0160 was again not exercised. The channel-40 no-IR flag was clear during the
join and restored after the disconnect.

## Decision

Proposal 0163 (an incomplete checkpoint at the owner's request; see below)
admits at most two owned events of this id per lifetime and attributes them
by window only: the first after the pairwise command was submitted and
before the group one, recorded as `key done: first after=pairwise bss=0
peer=1`; the second after the group command was submitted, recorded as `key
done: second after=group bss=0 peer=1`. Whether the second is the group key's
completion or a delayed repeat of the first is stated as undecidable and is
not claimed: a repeat arriving between the group submission and that key's
own event is indistinguishable from it and is admitted as the second; a
second event before the group submission, a third event, and any event
outside the lifetime window are refused with the index, the peer flags, the
sequence and the submission and record state named, never an address. Every
lifetime guard of 0162 applies to both windows. The classifier requires the
first-window record for the handshake-path pass, reports the second-window
record without requiring it, and does not call either a proven per-key
installation. The ownership fixture covers the first and second windows, a
second event before the group command, a third event, the wrong BSS index,
peer, sequence and length, and the queued-deauthentication hold with each
teardown guard.

The owner has paused the one-event-per-boot cycle: this proposal and the
runtime-20 evidence are preserved as a review checkpoint, no compile,
candidate or installation follows, and the next step is a bounded Gemian
reference capture of one complete connect, handshake, traffic and disconnect
lifecycle at the firmware boundary, so that the remaining behaviors can be
implemented coherently and replayed offline before the next mainline boot.
