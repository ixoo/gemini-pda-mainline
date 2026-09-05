# Next bounded eMMC session card — not yet admitted

Coordinator source review: [completed](COORDINATOR_REPAIR_REVIEW.md). Queue selection: **none**. Owner physical
selection, present stable power and readable console: **unconfirmed**. No identity
connection is requested by this card. Sole custody stays with the A53 test task.

Retained installed candidate: raw `a25fe4cb907f4f3da2bf9f36fcf38b3fff7d8ba84adc37562fdcff2f1a422daf`,
padded `a423ad63fbb97d0f3fc4726d3957e05d3951480996b754d839a89d80a1232821`.
Candidate/deployment/prerequisite pins are in [ADMISSION_TEMPLATE.json](ADMISSION_TEMPLATE.json).
The template's null/false fields deliberately refuse execution. A private fresh
UUID draft also exists with new source pins, selection/power false and custody
handoff digest unfinalized; old drafts and consumed observations remain unchanged.

Hypothesis: this exact kernel/DT/configuration can read the complete 16 MiB
live-GPT boot2 once, retaining same-boot A53 serviceability and a complete
independent controller log. This adds storage evidence; it is not a baseline
repeat. No rebuild or reinstall is proposed.

After source review and retained deployment verification, the coordinator prepares
the admission UUID and custody record before asking the owner to select boot2.
Selection and present-power fields are finalized only after actual confirmation;
the prepared template does not assert those facts. The owner is asked to
physically select the retained boot2 candidate, keep external power connected,
report readable screen text promptly and leave the device untouched. Unexpected
heat, errors or loss of the expected console stop the session for review.

On the actual reply, use the reviewed [same-process runner](LIVE_WINDOW_HANDOFF.md).
Local USB route/address readiness must precede the one-shot identity connection;
absence identifies no OS. Identity must authenticate the expected new mainline
boot with sufficient logger lifetime. Old Gemian power and owner availability
cannot replace those observations.

After successful identity, explicitly request one pre/read/post collection.
Read limit: exactly 16 MiB, input only, inner 20 seconds, transport 40 seconds;
pre/post transports each 45 seconds. Then separately admit log seal/export,
30 seconds. Host timing reserves 164 seconds initially and rechecks before every
phase, keeping the collection and seal inside the original 600-second lifetime.
The read budget has no retry and is not renewed by changing admission UUID.

A matching hash with serviceability and complete error-free log supports the
bounded read claim. Wrong hash or controller error rejects it; missing identity,
transport timeout or incomplete log is inconclusive. A handled failed read still
allows separately admitted preservation if preflight is attributable and time
remains. No postflight follows a failed read. Unexpected interruption does not
permit guessed identity, replay or automatic recovery.

After preservation, stop for native recovery review. Final acceptance also needs
owner-confirmed changed-ID known-good recovery. No keyboard, radio or other queued
test is combined with this session, and no result automatically selects one.
