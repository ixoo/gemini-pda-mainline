# Key removal: handler effects and the remaining retirement boundary

Hardware-free source audit, 2026-10-18 UTC. C10 was installed and shut down
cleanly and is [awaiting owner physical selection](CCMP10_PREPARATION.md).
No device read, control write, candidate change or re-arm was performed for this audit. Full
Wi-Fi acceptance remains incomplete.

## Actual command and inspected scope

The [validated C10 driver source](results/ccmp10-build-validation.json)
submits separate pairwise and group removals, then station
removal, channel return and BSS deactivation. Key-state 2 means submitted;
returned TC4 pages retire command-buffer debt. The public
[CMD_802_11_KEY layout](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/connectivity/wlan/gen3/include/nic_cmd_event.h#L375-L389)
places AddRemove at payload byte 0, KeyType at 2, peer at 4, key ID at 12 and
WLAN index at 14. C10's encoder uses AddRemove 0 and KeyType 1 for pairwise,
0 for group. It has not changed from C9.

A bounded RE-VM review re-anchored the retained matching-firmware command
entry, AddRemove decision and removal arm through its return: 11, 2 and 30
instructions. All 43 core instruction records matched the retained listing;
there were no gaps or shapes outside the frozen decoder's accounting in these
ranges. The command-table identity was checked independently. The existing
64-vector decoder preflight remained passing. Raw code, addresses and private
analysis records are not published here.

## What removal establishes

| Current input | Visible effect in the inspected removal arm | What this does not establish |
| --- | --- | --- |
| Pairwise removal, KeyType 1 | A peer-address call, followed by a conditional flag clear through its returned pointer; a separate path handles a missing pointer. | The pointer's full role, hardware-key invalidation, queued plaintext retirement or an attributable completion fence. |
| Group removal, KeyType 0 | After optional diagnostic work, bypasses that conditional operation and reaches the common return. No slot-specific erase or queue fence is visible in this arm. | A whole-firmware no-op or impossible GTK retirement. Other command processing and later station/BSS teardown remain possible retirement mechanisms. |

The group arm does not consume key ID/WLAN index to select a retirement
operation within the inspected body. Its return and command credit therefore
cannot be used as proof that the specific GTK slot and its queued frames are
safe to reuse. The pairwise flag may contribute to eligibility changes; a
flag clear alone is not the missing queue/key-incarnation contract. This audit
does not require literal key-material zeroing as the only possible retirement
mechanism, nor claim that it is absent everywhere in firmware.

This narrows the next action: trace actual station/BSS teardown and the shared
queued-RX lifetime, rather than wait longer for removal credits or interpret
ADD_PKEY_DONE as a deletion acknowledgement.

## Transitive cleanup boundaries

Only the two command entries actually used by host cleanup were selected:
[REMOVE_STA_RECORD](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/connectivity/wlan/gen3/include/nic_cmd_event.h#L1028-L1033)
and [BSS_ACTIVATE_CTRL](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/connectivity/wlan/gen3/include/nic_cmd_event.h#L899-L907).
Their first bounded windows supplied 85 and 39 instructions. The BSS window ended before the valid BSS-0 branch;
that first window was argument-validation evidence, not a retirement test.
A separately specified valid-branch continuation supplied 80 instructions.

The actual one-station removal path delegates through further calls. One
explicit direct helper was inspected through its return: 25 instructions,
five ordered calls and 59 trailing undecoded halfwords. Its complete visible
body delegates work; names or return values do not identify a key/queue fence.
The BSS continuation records the active byte and passes context/active state
to further work, but is incomplete. Other shapes outside the frozen decoder's
accounting remain labeled. No recursive call/slot scan or live query followed.

The concrete unresolved boundary is now the transitive teardown work and its
ordering against firmware/HIF queued frames. Prove that contract before key-slot
reuse; do not manufacture it with a host generation label, PN reset, elapsed
time, empty software queue or successful traffic. A future source-supported
barrier must also meet the pinned mac80211 teardown ordering.

## One bounded direct-callee round

A subsequent, separately specified review inspected the five direct station
callees and the BSS context/active helper, with at most 256 bytes per target.
The six windows supplied 64, 84, 29, 85, 65 and 19 instructions. Some bodies
return within the window; others are incomplete or delegate further. Unvalidated
shapes remain labeled. The original 43 instruction anchors reproduced again.

The byte cap was narrowed to a complete instruction-prefix boundary where
needed, never expanded. The pinned decoder's big-endian 16/32-bit width rule
and 836 synthetic boundary cases supported that calculation; the decoder's
outside-restriction guard remained unchanged. Width alignment does not validate
instruction semantics, classify a list or prove branch/function completeness.

Visible station work includes per-context resets, list unlink/count operations
and further calls. The list has not been linked to the shared host RX queue;
it must not be labeled an RX flush or a key-incarnation fence by its shape or
entry count. Successful traffic would not resolve that attribution either.

A later check examined five fixed data references already present in these
bodies, each capped at 256 bytes. The list-processing function's own diagnostic
places it in a TX disconnect path; a receive-component reference belongs to a
separate context-reset helper. These labels add context, not proof of every
list's contents or a shared-RX fence. TX cleanup must not be substituted for
queued-RX retirement. No new decoding, scan or device command was involved.

The complete 19-instruction BSS helper reaches two indirect table targets,
passing context-derived indices, the active byte and address pointers. Those
target values remain unresolved, so behavior cannot be attributed from
this helper. A bounded check of the retained container's section headers found
no section directly covering those table locations. That does not exclude
aliasing or initialization by encrypted or other code; no decryption,
image-wide search, live read or recursive follow-on was performed.

This leaves a concrete source-observation need: resolve those exact BSS
implementations and the queued-frame ownership/order before asserting producer
quiescence. Any later observation needs separate admission and fresh identity;
it must not interrupt or replace the pending C10 comparison. A separate
10-entry evidence bundle was sealed and independently verified for this round.

## Current protections remain

Seven C10 key/cleanup/station/re-arm function bodies are byte-identical to C9:
withdrawal, key disable, set_key, station state, cleanup step, join worker and
re-arm helper. C10 still excludes stable-CCMP from re-arm and keeps the initial
PTK/no-reuse and fatal-poison gates. Its stage-3 `slots=retired` log remains an
inherited host-protocol label, not new firmware evidence. Keep that distinction
when recording C10's eventual cleanup result; key retirement must stay separate.

The original 27-entry and later 10-entry private evidence bundles were each
independently verified against their sealed manifests; RE processes were checked
quiescent. This audit changed no C10
artifact or source, adds no hardware-support claim and does not replace its
pending single comparison or authorize a subsequent candidate.
