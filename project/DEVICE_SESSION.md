# Device session packet

Copy this template into the owning experiment. Fill every applicable field
before marking its queue entry ready. This describes one bounded experiment;
[the roadmap](../docs/ROADMAP.md#owner-away-progress) owns scheduling and
[the queue](experiment-queue.json) links to readiness records. No commands are
executed by the queue itself.

## Identity and ownership

- Queue ID, experiment record, implementation owner, reviewer and device custodian:
- Preparation state: planned / preparing / conditional / ready / blocked / stale.
- Device state: unselected / selected / waiting-owner-boot / running / complete.
- Frozen repository revision and exact source, patch/config/profile identities:
- Immutable package, candidate, DT, initramfs and runner/validator records:
- Current custody/handoff reference; unknown device state must be checked live:

## Question and dependencies

- One falsifiable hypothesis and its useful upstream/capability outcome:
- Intentional change from the named baseline and unchanged relevant inputs:
- Required result predicates, exact supporting records and unresolved conditions:
- What can finish offline while each runtime dependency is unavailable:
- Pass / failure / inconclusive observations and the next decision each permits:
- What invalidates readiness, including input changes and consumed budgets:

## Offline completion

- Input/profile audit, focused host/kernel/schema checks and rejecting fixtures:
- Buildbox/package/container checks and reproducible candidate composition:
- Exact observation-shell and deployment refusal checks; actual limits of fixtures:
- Capture, classification, interrupted-run refusal and recovery tools validated:
- Expected artifacts retained and reconstruction/retention needs reviewed:
- Reviewer confirms dependencies and all applicable gates; missing values are not passes:

## Session contract

- Exact validated candidate selected by the experiment, not newest file by time:
- Finite boot/read/write/sample/load/time budget, including failure consumption:
- Allowed effects, excluded effects, stop conditions and safe interruption point:
- Live identity/GPT/root/mount/power/recovery checks required before deployment:
- Existing installer, full-readback receipt and clean-shutdown procedure:
- Per-boot identity and pristine-state checks required before any observation:
- Compatible tests, order, interference audit and combined budget if sharing a boot:
- Which dependent tests stop after a failed or inconclusive observation:
- Evidence capture/classifier invocation; private and sanitized output locations:
- Recovery path and exactly where owner action is required again:

## Owner session card

Write a short, plain-language card with the next physical action, expected
screen/USB behavior, estimated interaction time if known, required key presses
or cable changes, and what to do if the expected behavior does not appear.
Distinguish preparation, installation and physical boot selection. Each required
physical cycle remains explicit; do not promise the entire queue will run after
one selection unless the reviewed session contract proves that.

## Result handoff

Link the immutable deployment receipt, boot identity, per-test classification,
consumed budgets, recovery evidence and sanitized result. State whether each
conditional successor is now eligible, still conditional, stale or blocked.
Preserve negative results; do not overwrite a consumed record or silently retry.
