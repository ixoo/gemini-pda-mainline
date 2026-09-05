# Current eMMC readiness handoff

This is a local-record review after worker commit `eb38185e`, not a physical
selection request or a live device observation. Sole device custody remains with
the A53 baseline and queued device tests task.

## Remaining gate

An offline runtime-boundary review gate is OPEN. The coordinator found that
the old disabled-only fixture fails against the enabled source delta. The repair now adds explicit admission revalidation, a process-local live
timing boundary and a same-process runner, with focused synthetic tests.
Coordinator review of [LIVE_WINDOW_HANDOFF.md](LIVE_WINDOW_HANDOFF.md) and
current source identities remains required before execution readiness.
The original three-file enablement delta, included in this repair, enables `execution_gate.py` and updates its
hash in `source-pins.json` and [SESSION_PACKET.json](SESSION_PACKET.json).
That previously reviewed source enablement does not itself admit a session.
Historical disabled-preparation descriptions remain historical; the exact local
packet and its runtime admission are separate states.

The outstanding offline admission step is to finalize and hash the fresh custody
and execution admission using actual new-session facts, then revalidate it against
unchanged candidate, source and prerequisite bytes. It cannot be completed now:
physical selection and stable power are still false in the prepared draft.
Custody exclusivity and no concurrent device operations are true. The validator
currently refuses with `custody/selection/power unconfirmed` as intended. Readable
console, authenticated new boot identity and sufficient remaining logger lifetime
are also required before dispatch; these cannot be fabricated offline.

Before this repair, the bounded local recheck passed packet source closure and draft source identity,
retained candidate/deployment validation and the explicit `reviewed-supplemental`
prerequisite. The original strict baseline remains incomplete. The global read
attempt is absent, and the prepared next session has no identity claim. Earlier
failed identity attempts remain consumed and immutable. The repair changes source bytes, so the earlier draft is now additionally invalid
on source identity and must not be executed or silently repinned. This review
created no claim, sent no device packets, and made no interface-state observation.

## Retained installed candidate

The queue currently has `selected_item: null`. The retained installed candidate
and verified deployment below are available for a subsequently admitted session;
this record does not select a queue item:

- Raw candidate SHA-256: `a25fe4cb907f4f3da2bf9f36fcf38b3fff7d8ba84adc37562fdcff2f1a422daf`.
- Padded candidate SHA-256: `a423ad63fbb97d0f3fc4726d3957e05d3951480996b754d839a89d80a1232821`.
- Candidate manifest SHA-256: `54b07f0c70e77fd1e34fde4fc1c929980f0d8c3410f0a97ce3f15ffec1a66179`.
- Deployment receipt SHA-256: `5aed5d6554922835ad6e50091056f9145b2fc1b07d40507353c38202e4b50543`.

These are retained artifact/deployment facts, not a claim about the device's
current OS. No rebuild or reinstall is needed for the proposed measurement.
Previously recorded Gemian power evidence is historical and cannot establish
present power continuity. USB absence cannot establish either Gemian or mainline;
Gemian LAN and mainline USB are distinct authenticated transports as described in
[TRANSPORT_REFERENCE.md](TRANSPORT_REFERENCE.md).

## Next attributable physical test

When the coordinator and owner resume the already prepared session, the owner
physically selects the same installed boot2 candidate, reports readable console
and continued power, and leaves it untouched. This handoff does not issue that
request. No current admission in this handoff has actual new-session owner facts.

The hypothesis is that this exact kernel/DT/configuration can complete one
bounded read of live-GPT boot2 while retaining same-boot A53 serviceability and
an independent complete controller log. The new evidence is an exactly counted
16 MiB input-only read and hash with before/after guards and sealed log, not
another baseline observation or marker-only derivative.

On an actual timely owner reply, inspect the local USB address/interface/direct
route before claiming the separately authorized one-shot identity check. If
absent, do not connect or spend that check; do not infer an OS. A passing check
must authenticate the new mainline boot and guard, with boot age below 400
seconds. Its ten-second budget has no retry. Finalize the admission only with
actual facts and enough time for pre/read/post (maximum 130 seconds), separate
log seal/export (30 seconds), and elapsed coordination inside the original
600-second logger lifetime.

The measurement is one read of boot2 bytes 0 through 16777215, with a 20-second
inner deadline and 40-second transport limit; pre/post each have 45 seconds.
There is no write, mount, benchmark, extra read or combined keyboard/radio test.
Failed preflight prevents the read; failed/incomplete read prevents postflight.

A matching hash, passing serviceability and complete error-free controller log
support only the bounded read claim and separate recovery review. Wrong hash or
attributable controller error rejects it; timeout, missing identity or incomplete
log is inconclusive. Preserve all evidence without retry. Native recovery remains
separately admitted after preservation review; final acceptance additionally
requires owner-confirmed changed-ID known-good recovery. No automatic reboot or
promotion of another queued test follows any result.

The operational sequence is owned by [FRESH_SESSION.md](FRESH_SESSION.md),
[SESSION_PACKET.json](SESSION_PACKET.json) and the completion runtime. Ordered
subsequent work remains in the [roadmap](../../../docs/ROADMAP.md).

The revised same-process runner is required for live timing; follow its reviewed
interface rather than invoking the old collectors directly. The [session card](SESSION_CARD.md) contains only pending facts; it is not
admitted until the open review gate above is closed.
