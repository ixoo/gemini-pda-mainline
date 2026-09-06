# Workflow and settings improvement loop

This record turns the routing pilot into an event-driven improvement loop. It
optimizes delivery without making task count, model usage or low review time a
substitute for correctness, safety, upstream quality or hardware evidence.
The active-cohort and effective-decision pointer is
[`workflow-improvement.json`](workflow-improvement.json); exact counts,
chronology and measurements live in the linked experiment ledger. The work
contract is [`WORK_ITEM.md`](WORK_ITEM.md).

## Measure one accepted offline item

An integration reviewer assigns one ordered considered-work sequence whenever a
candidate handoff is accepted or excluded. This prevents a separate success-only
list from hiding failed or ineligible candidates. Abandoned attempts, device
sessions, builds and review-only consultations are not accepted offline items;
record their exclusion when they were considered for the cohort. A reworked
handoff is one accepted item, not one item per attempt. For accepted work record:

- the frozen parent, work type and risk class;
- implementation and review role, model and effort actually used;
- first-review acceptance, rework cycles and escalation outcome;
- ordered start, review-ready and acceptance timestamps, plus elapsed and
  review/rework minutes from observed timestamps or timers; and
- measured credits with their source and unit, or `null` with `unavailable` as
  the source and no unit. Never infer credits from model names, duration or
  token estimates.

The experiment ledger contains sanitized coordination metadata only. Exact
technical evidence remains in the owning experiment or handoff. Do not include prompts,
private evidence, credentials, personal paths or device identifiers.

Each accepted entry has `considered_sequence`, `accepted_sequence`, a globally
unique `candidate_id`, `offline_eligible: true`, work/risk/acceptance-contract
identities, full parent commit, actual owner/review routes and a `result`.
The result records UTC start/review-ready/acceptance times, timing source,
finite durations, review outcome, any immediate failure class, credits and the
accepted-evidence path. An escalation additionally links a packet containing
evidence, attempted repairs, the unresolved question and next discriminating
check. An excluded entry uses the same considered sequence and identity with a
reason, note and evidence path, but no accepted sequence.

## Review signals

The integration owner records a checkpoint and reviews the comparable cohort
when any of these occurs:

1. five more accepted items have accumulated since the last checkpoint;
2. two consecutive comparable items miss first-review acceptance;
3. two comparable items escalate for the same reason; or
4. a safety, publication, provenance or scope-containment failure occurs.

The first ten accepted offline items form the initial pilot. After item ten,
record the item-ten checkpoint, close that cohort, create a numbered successor,
retain a rolling ten-item comparison window and continue five-item checkpoints.
An early signal permits review, not an automatic settings change.

A checkpoint records both sequence boundaries, trigger items, the comparable
items actually analyzed, conclusion and an experiment-owned evidence path.
Nothing after either boundary may justify that checkpoint.

Compare like work: work type, risk class, acceptance checks and review tier must
be sufficiently similar. State when a cohort is too small or heterogeneous.
Use medians for elapsed and review/rework time, report first-review acceptance
as a fraction, and report escalation counts by reason. Credits are compared only
when the same measurement source and unit cover every item in the cohort.

## Change one setting safely

A settings experiment needs at least five comparable accepted items unless it
corrects a demonstrated safety or compatibility defect. Record the evidence,
one changed variable, expected effect, affected future work types, observation
window, change-parent commit, complete before/after settings snapshots and
rollback condition in the ledger before editing `.codex/config.toml` or
`.codex/agents/`. Evidence items must share the declared work type, risk class,
acceptance-contract identity and review route.

Settings changes:

- never alter active or paused tasks retroactively;
- never expand device, build, publication or authorship authority;
- preserve the two-worker staffing norm; it is project policy and not a
  changeable runtime setting in this loop. A proposed staffing-policy change
  needs its own review. The three-thread runtime ceiling may be a measured
  one-variable settings experiment. Codex counts spawned agent threads and
  excludes the primary thread, while the staffing norm counts active
  implementation or research work items;
- retain higher review or specialist routing where risk requires it, even if a
  cheaper route appears faster; and
- require the repository gate and a compatible desktop-runtime configuration
  check before adoption.

The concurrency interpretation follows the official
[Codex subagent configuration](https://learn.chatgpt.com/docs/agent-configuration/subagents),
not an inference from observed scheduling.

At the declared observation boundary, mark the decision `adopted`, `reverted`
or `inconclusive`. Revert when its predeclared condition is met. Inconclusive
results do not justify keeping a new default merely because it is already set.
Only new work contracts use an adopted route.

## Integration cadence

The integration reviewer appends the considered item to the active experiment, runs
`scripts/validate-workflow-improvement.py`, evaluates trigger conditions and
records a checkpoint when due. A checkpoint may conclude `no-change`; this is a
valid result and prevents repeated ad hoc tuning from the same evidence.

Weekly roadmap review may summarize the latest checkpoint, but the loop does
not require a scheduler and does not resume paused work. Settings proposals do
not select a roadmap item, start a worker, submit a build or admit hardware.
