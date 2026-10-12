# Runtime 32 preparation: the runtime 31 protocol on candidate 31 (proposal 0179)

Status: compile 36 validated at the built input 7fa36c01 (package `521e1ce3…`, Image.gz
`ded2f6db…`); `build-candidate.py` pins it for candidate 31. The custodian composes
candidate 31 privately with the existing parent, helper and supplicant; the RAM root,
board DT and kernel configuration are expected byte-identical to candidate 30
(`449832a3…`, `25ab60f4…`, `975f8703…`). The identity bindings (adapter pins, predecessor,
runtime/capture/session/deployment numbers) are completed when the custodian's
`candidate-31.json` receipt arrives; this document fixes the hypothesis, the
observation-required gate and the branches in advance, as invited, so only the receipt
remains. No device step has run.

## What differs from runtime 31

Kernel, proposal 0179 only, after 0178 in canonical order (built driver files `mac.c`
`2d7e5a33…`, `data-rx.h` `6330bac2…`; reviewed, no comment split). 0179 is a metadata-only
observation: the receive decoder reports the GROUP_VLD mask it already computes, and the
data phase keeps per delivered class the count of frames with group 1 (the received PN
group) present or absent and a per-class bitmap of the mask values 0..15 seen, printed
once at the data phase end, with the first data RX record carrying the mask. No PN bytes,
payload or addresses are read or stored; nothing reaches the crypto path; no delivery,
drop, radio, transmit or timing behaviour changes.

Everything else is runtime 31's exactly: the same admitted radio effects, the same ping
and SSH budgets, the same data-phase budget and teardown margin, the same single native
recovery, the same credential and address handling, the same decoders' gates. The only
new evidence is the group-1 observation.

## Hypothesis and what the run can and cannot establish

Hypothesis (availability only): the delivered unicast and group data classes carry some
GROUP_VLD mask set; whether group 1 (the PN group) is among the bits set on those
delivered frames is presently unknown, and runtime 32 records it. The run establishes only
whether group 1 is available on the sampled delivered classes. It does not establish who
enforces replay, does not prove firmware enforcement or its absence, and makes no
operational, reliability or replay-protection claim; `wifi_operational` stays false. A
present group-1 PN would still prove neither the key, TID, key incarnation, authenticity
nor ordering, and the pinned mac80211 path reads the PN from the in-frame CCMP header,
which the driver's `RX_FLAG_IV_STRIPPED` delivery removes — so nothing in this run changes
the crypto path.

## Observation-required gate

A valid runtime 32 C3 measurement requires the `data group1` observation line to be
present and consistent as the classifier defines consistency: a single line, placed after
the data phase end record and before the first cleanup submission or the terminal;
`present + absent` equal to the end record's delivered unicast and group counts; the
per-class mask bitmap limited to the admitted values 8..15 (group 4 mandatory), zero iff
the class total is zero, with an odd-index bit iff group 1 was present and an even-index
bit iff group 1 was absent. A missing, duplicated or inconsistent line is malformed and
the measurement does not count; the lifecycle verdicts (C2/C3, bounded join, healthy
cleanup) are decided exactly as in runtime 31 and are independent of this observation.

## Branches, each ending the lifetime once

1. Healthy lifetime with the observation present and consistent: group 1 observed as
   present or absent on each delivered class, recorded with the mask set; the first fully
   measured C3 lifetime that also answers the availability question. The network terms
   (lease, ping, SSH) are reported apart, as in runtime 31, and decide nothing here.
2. A healthy lifetime but a malformed or absent observation line: the lifecycle verdicts
   stand; the availability question is unanswered and the observation is retried only with
   a decision-changing change, never by repeating the identical boot.
3. A refusal, disconnect, footer or any named fault as in runtime 31's branches: recorded
   by its fields, fail-stop, seal, the reviewed native recovery once; the availability
   question is unanswered.

No branch repeats a boot without a decision-changing change. Nothing is reconnected or
rekeyed. Replay enforcement in firmware remains unknown and unclaimed.

## Bindings (pending candidate 31 receipt)

Completed from `results/candidate-31.json` when it arrives: `build-candidate.py` already
pins `COMMIT 7fa36c01`, `PACKAGE 521e1ce3…`; `install-passive.py`, `capture-private.py`,
`passive-host.py`, `passive-session.py` and `prepare-runtime.py` will bind runtime 32,
capture 32, session 32 and deployment 31 with the installed candidate 30 (`e758bf36…`) as
the predecessor; `join-once.sh` and `laptop-wifi-ssh.py` unchanged. Fixtures follow the
bindings. Nothing will be installed or booted by this preparation.
