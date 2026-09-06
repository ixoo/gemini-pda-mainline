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

The contiguous ledger now contains eight considered candidates: six eligible
accepted offline items, one cohort-bootstrap exclusion and one device-session
exclusion. All six accepted items missed first-review acceptance. The first two
required escalation: the integration item exposed live-ledger fixture coupling,
and the dynamic reserved-memory implementation needed corrected OF semantics,
owned declaration copies and static-path regression coverage. The next two
cross-file implementation items required bounded evidence or verifier repairs
but no escalation; exact Buildbox compilation and host checks accepted both.

Item five was a hard-uncertainty source investigation. It retained four
unresolved EMI routing/priority verdicts and blocked policy selection. Two
verifier-boundary repairs still left mutable metadata and predicate gaps, so the
required escalation added independent frozen metadata and 34 mutation-refusal
fixtures before final Sol review accepted it.

Item six was a separate hard-uncertainty retained-firmware attribution. Its
preflight matched every frozen identity but proved that none of the five
permitted immutable scripts implemented the new deterministic traversals. It
therefore stopped both branches before an attempt, preserved null unmeasured
counts and four unresolved verdicts, and escalated the exact missing read-only
tooling contract. Two chronology-only review repairs aligned the work contract
with the accepted stop receipt. Credits are unavailable for all six items. No
accepted measurement is inferred from model identity or elapsed
time.

## Post-item-six early-signal checkpoint

Checkpoint `pilot-01-post-item-six-review-misses` closes accepted sequence 6
and considered sequence 8. Items five and six are consecutive
hard-uncertainty reasoning handoffs with the same Astra Medium owner route,
Sol Medium review route, conservative multi-verdict receipt, unresolved-result
acceptance, offline verifier and mutation-refusal shape. Their work-contract
paths differ because technical identities belong to separate experiments, but
their acceptance checks are sufficiently similar for this early review. Both
are assigned the explicit review-signal group
`hard-reasoning-verdict-receipt-v1` and missed first-review acceptance. This
group affects only early review signals; the stricter exact-contract tuple still
governs settings decisions.

The two-item comparison has median elapsed time 18.3833333333 minutes and
median review/rework time 10.675 minutes. First-review acceptance is 0/2. Both
items escalated, for different reasons: item five required stronger independent
verifier freezing after repeated repair, while item six stopped before an
analysis attempt because the admitted immutable tools could not implement the
new method. Credits are unavailable for both.

The conclusion remains `too-small`. The shared miss signal warrants preserving
the precise failure classes and continuing measurement, but two technically
different investigations do not support a route or settings change. No safety,
publication, provenance or scope-containment failure was accepted.

Creation of this loop remains excluded because its eligibility and timing
contract did not exist before work began. The passive CONSYS ownership snapshot
also remains excluded as a device session; neither changes the accepted count.

## Item-five checkpoint

Checkpoint `pilot-01-item-five` closes accepted sequence 5 and considered
sequence 7. The cohort is too heterogeneous for a route change: it contains one
cross-file integration item, one hard-uncertainty implementation, two
cross-file implementations and one hard-uncertainty reasoning item. Only the
two cross-file kernel-compile implementations form a useful like-work subgroup
with the same owner and review routes and materially similar host, patch replay,
provenance and Buildbox acceptance checks.

That two-item subgroup has median elapsed time 29.64092795 minutes and median
review/rework time 20.23501580835 minutes. First-review acceptance is 0/2 and
neither item escalated. Two observations cannot distinguish route behavior from
task-specific verifier and evidence demands. Credits cannot be compared because
both measurements are unavailable. The other work types have only one item
each, so they are not used as performance comparators.

## Analysis

The required interval review concludes `too-small`. The review misses justify
continuing to measure precise acceptance defects, but do not establish that one
model, effort or concurrency setting caused them. No safety, publication,
provenance or scope-containment failure was accepted into the repository. A
settings experiment still lacks the five comparable items required by policy.

## Conclusion

No settings change. The frozen baseline remains in effect while the cohort
continues toward ten eligible accepted offline items.

## Follow-up

At cohort close, link the next numbered cohort and update only the effective
decision and active pointer in `project/workflow-improvement.json`. Exact
chronology, counts, exclusions and measurements remain in this experiment.
