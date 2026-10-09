# Seventh Phase B runtime: the cleanup's protocol error is measured

Boot identity: mainline `3cfe1f68-5525-4652-83e9-a83a7fdb781b` from candidate
6 (boot2 `e6b7dd4e…`, receipt `e4fbd0e2…`, compile-11 package `86b0a208…`,
input `d88d6e22`), laptop session source `f408f15e`, returned to a changed-ID
Gemian boot `8599964c-c0d6-4a63-9081-5747400b45c9` through the reviewed native
recovery. Sanitized records: [results/runtime-7.json](results/runtime-7.json)
and the laptop's combined, unchanged
[results/runtime-7-session-result.json](results/runtime-7-session-result.json).
The sealed log is 152619 bytes, 2016 records, SHA-256 `8dea8341…`, manifest
`7dea44fd…`. Raw evidence and the AP identity stay private.

## Observations (measured)

- Initialization 285/285, calibration ack, PA rails off; one passive scan
  passed; the owner's BSS matched; the connect request was acknowledged.
- The management exchange repeated runtime 6 exactly: authentication frame
  sent and acknowledged, response status 0, mac80211 `authenticated`;
  association request sent and acknowledged, response status 45, mac80211
  `denied association (code=45)`; cleanup submissions 0, 1 and 2 each returned
  one page; nine pages in total.
- The 0146 diagnostics answered the runtime-6 question. The footer reads
  `status=-71 first=0 submitted=0x801 debt=0 cleanup=3 branch=6`, and the
  line before it is `control event refused: status=-71 bytes=12 type=0xe000
  id=0x11 seq=0`. No idle-gate refusal and no credit overflow was logged. The
  protocol error came from the control-event parser, on a 12-byte unsolicited
  event with identifier 0x11, received about one millisecond after the
  BSS-off cleanup submission's page was returned. The event body was not
  logged, so its values are unmeasured.
- The original classifier reported `malformed_stage_record=true` because the
  new diagnostic line was an unknown record kind; its JSON is preserved as
  returned. Regression and recovery passed.

## Identification (publicly pinned source, not a device measurement)

In the gen3 headers the project pins by URL and digest
(`nic_cmd_event.h` at the pinned revision), event 0x11 is
`EVENT_ID_BSS_ABSENCE_PRESENCE`, marked unsolicited. Its structure, from
`que_mgt.h` at the same revision (SHA-256 `f970b0f9…`, fetched for this
record), is the eight-byte event header followed by `ucBssIndex`,
`ucIsAbsent`, `ucBssFreeQuota` and one reserved byte: twelve bytes, matching
the observed length. The vendor driver's handler records the absent flag and
quota on its BSS record and otherwise takes no action. Receiving it right
after the channel privilege was aborted and the BSS deactivated is consistent
with a BSS going absent; which body values the device sent is unmeasured.

## Correction (proposal 0147)

The control-event parser admits exactly this event under a strict contract:
twelve bytes, sequence 0, BSS index 0 (the owned slot), a boolean absent
flag, only while the host-owned teardown has submitted the BSS-off command and
nothing is owed, in flight or queued, and at most twice per lifetime. It logs
the body as metadata (`bss absence: bss= absent= quota= reserved=`). The
quota is never treated as TC4 credit or as proof of drain or quiescence; the
original idle guards, budgets and retirement are unchanged, and any other
shape, sequence, slot, body value or lifecycle position is still refused.
[tests/join-peer-test.c](tests/join-peer-test.c) drives the production parser
with synthetic source-defined cases: two admitted events during the teardown,
the budget, and refusals for a solicited sequence, a foreign slot, a
non-boolean flag, a wrong length, a position before the BSS-off submission, an
owed page, a frame in flight and a completed cleanup. The live parser
validates the real body on the next boot.

The join classifier now recognizes the diagnostic record grammar with exact
bounded fields, so a refusal or an admitted indication is neither a stage
record nor malformed, while any unknown kind or a known prefix with the wrong
grammar remains malformed; health is still decided by the stage grammar.
[tests/host-test.py](tests/host-test.py) covers both.

## Next

Candidate 7 pairs a compile-12 kernel (0147) with the candidate-4 RAM root and
helper, after the owner's review of the patch. The boot's decision-changing
observation is the final cleanup line (`cleanup: stage=3 credits=returned
slots=retired deauth=0`) with the admitted indication's logged body, or a new
specific refusal. A healthy cleanup then opens the next development stage
toward complete Wi-Fi: the protected association, key exchange and data path
under their own bounded protocols.
