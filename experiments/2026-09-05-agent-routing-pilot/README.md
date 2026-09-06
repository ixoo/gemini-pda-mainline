# Experiment: agent routing and workflow pilot 01

## Record

| Field | Value |
| --- | --- |
| ID | `2026-09-05-agent-routing-pilot-01` |
| Status | running |
| Subsystem | Project coordination and Codex routing settings |
| Device variant | None; offline work only |
| Date(s) | 2026-09-05 onward |
| Investigator(s) | Integration owner and assigned work-item owners/reviewers |
| Tracking issue | None |

## Question or hypothesis

Can the frozen routing baseline improve throughput while preserving review
quality, scope containment and safety when measured across ten consecutive
eligible accepted offline items? This first cohort establishes a baseline; it
does not claim that its routes are cheaper or better than an unmeasured
alternative.

## Frozen inputs and eligibility

- Baseline repository commit: `63919a7ca33d1a0f5f6b5eaef9f33c58e79ec808`.
- Runtime used to validate the project settings: Codex desktop `0.153.4`.
  Standalone CLI `0.144.1` is incompatible with this agent configuration.
- Effective route and active-cohort pointer:
  [`project/workflow-improvement.json`](../../project/workflow-improvement.json).
- Policy and definitions:
  [`project/WORKFLOW_IMPROVEMENT.md`](../../project/WORKFLOW_IMPROVEMENT.md).

An eligible item is a bounded offline execution, implementation, reasoning or
integration handoff with a work contract, frozen parent, named owner and
reviewer, explicit acceptance checks, and no device action. It becomes a ledger
item only after integration review accepts it. A reworked handoff stays one
item. Abandoned attempts, standalone builds, device sessions, exploratory
consultations and work completed before this cohort are excluded. Accepted and
excluded candidates share one contiguous considered-work sequence and globally
unique identity, so selection cannot silently favor successful work.

First-review acceptance means the first complete review-ready handoff meets its
predeclared acceptance checks without an implementation correction. Requests
for clarification or evidence already required by the contract count as a
miss; optional polish and integrator-only composition do not.

## Safety assessment

This experiment records sanitized coordination metadata. It performs no build,
network publication, device access or hardware action and grants none. It must
not store prompts, credentials, private evidence, personal paths or device
identifiers. Model or concurrency settings never expand operational authority.

## Procedure

1. Freeze each eligible work item using `project/WORK_ITEM.md` and record the
   actual owner and review route.
2. Append every considered candidate to
   [`results/ledger.json`](results/ledger.json). Accepted entries also receive a
   consecutive accepted-item sequence, observed timing, and measured credits or
   an explicit unavailable source.
3. Run `scripts/validate-workflow-improvement.py` and the repository gate.
4. Review provisionally after item five and formally after item ten, or earlier
   on a trigger defined by the policy. Record the checkpoint in this ledger.
5. Decide `retain`, `change-one-variable` or `rollback`. A settings experiment
   predeclares its hypothesis, observation boundary and rollback condition and
   applies only to future work.
6. Close this cohort after exactly ten eligible accepted items, preserve its
   exact record here, and create a numbered successor with a rolling ten-item
   comparison window.

Comparable analysis groups work type, risk class, acceptance contract and
review tier. Report median elapsed and review/rework minutes, first-review
acceptance as a fraction, and escalation counts by reason. Compare credits only
when every item in the cohort segment uses the same observed source and unit.

## Observations

No eligible accepted item has been recorded yet. Creation of this loop is
explicitly excluded because its eligibility and timing contract did not exist
before the work began. Existing routing remains the baseline; no optimization
decision has been made.

## Analysis

Pending sufficient comparable evidence. A five-item checkpoint may conclude
that the cohort is too small or heterogeneous, and `no-change` is a valid
result. Safety, publication, provenance and scope-containment failures trigger
immediate review regardless of sample size.

## Conclusion

Inconclusive while the cohort is collecting. The existing routing remains in
effect for new work.

## Follow-up

At cohort close, link the next numbered cohort and update only the effective
decision and active pointer in `project/workflow-improvement.json`. Exact
chronology, counts, exclusions and measurements remain in this experiment.
