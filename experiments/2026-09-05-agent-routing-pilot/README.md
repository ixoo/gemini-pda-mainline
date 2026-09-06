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

The contiguous ledger now contains thirteen considered candidates: nine eligible
accepted offline items, one cohort-bootstrap exclusion, one device-session
exclusion and two pre-dispatch tooling-contract exclusions. All nine accepted
items missed first-review acceptance. The first two
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

Item seven compiled the pure MT6797 reserved-resource layout bridge. Its first
review found a selector-range incompatibility with the predecessor EMI ABI,
an unavailable freshness claim, incomplete refusal-output poisoning and a
missing start-after-end fixture. Two bounded repair passes closed those issues;
the exact 13-patch Buildbox build then replayed, compiled and linked the real
AArch64 object and validated/fetched the package. It selected no permission or
runtime caller and did not escalate. Credits remain unavailable.

Item eight compiled the one-attempt MT6797 EMI service gate. The first complete
handoff review found refusal fixtures that could hide an unexpected callback
and a verifier network access outside the frozen offline scope. Two bounded
repairs replaced that path with live callback/storage snapshots, completed the
state, alias, generation and inventory coverage, and documented the caller-held
serialization, context-lifetime and partial-overlap preconditions. The exact
fourteen-patch Buildbox build compiled and linked the AArch64 object with no
runtime caller or effect path. This pre-publication scope-containment finding
triggers the checkpoint below; it did not enter the accepted implementation.
Credits remain unavailable.

Item nine performed a bounded public-primary-source sweep for effective MT6797
AP/CONSYS/WLAN EMI routing and overlapping-region arbitration. Three
predeclared attempts used ten requests and retained metadata for two immutable
MT8192 TF-A files, but found neither an exact MT6797 routing chain nor a
compatible winner rule. The accepted verdict keeps AP, CONSYS, WLAN,
arbitration, active-region applicability and policy selection unresolved. Its
first review found that whole-record digests masked the semantic mutation
guards and that the new verifier lacked its SPDX identifier. One repair made
the 33 refusals meaningful, added a positive generic-CONSYS control and proved
that WLAN promotion fails for its missing transaction attribution. No source
body, private evidence, device action, VM or build entered the item. Credits
remain unavailable.

The proposed deterministic read-only firmware traversal tool is considered
sequence ten but is not an accepted offline item. Two pre-dispatch contract
repairs closed its fixed branch caps, read-only capability direction and
arrival-independent joins, but still left an impractical worst-case retained
state bound and incomplete canonical success/refusal protocol. Its declared
two-repair stop activated before implementation, private analysis, VM access or
device access; the exact escalation remains in its work contract.

A fresh sparse-state tooling candidate then bounded retained cells and froze
the outer success/refusal protocol. Two contract repairs still left a mixed
acyclic/source-cycle propagation case that could ignore an admitted predecessor,
plus one missing refusal code and an ambiguous terminal map kind. Its own stop
therefore activated before implementation. This second exclusion confirms that
the line was becoming a larger analysis framework; offline progress pivots to
an independent roadmap item rather than weakening the attribution method.

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

## Post-item-seven compile-review checkpoint

Checkpoint `pilot-01-post-item-seven-compile-review-misses` closes accepted
sequence 7 and considered sequence 9. The EMI ABI, remap-fields and
resource-layout compile items share the explicit prospective review group
`mt6797-kernel-compile-helper-v1`: all are cross-file Luna High implementations
with Sol Medium review, deterministic synthetic patches, strict host fixtures,
canonical-series integration, exact Buildbox compilation and object/linkage
evidence. All three missed first-review acceptance and none escalated.

The three-item group has median elapsed time 30.1279534333 minutes and median
review/rework time 21.56612915 minutes. First-review acceptance is 0/3; credits
are unavailable throughout. The conclusion remains `too-small`: three items do
not meet the five-comparable-item threshold for a settings experiment, and the
misses arose from distinct contract, provenance and interface defects. No
settings change is justified.

## Post-item-eight scope-containment checkpoint

Checkpoint `pilot-01-post-item-eight-scope-containment` closes accepted
sequence 8 and considered sequence 12. It is triggered immediately by the
offline-scope violation found in item eight's first complete review. The issue
was confined to the verifier, removed before integration, and independently
rechecked; no device, private-evidence or published runtime boundary was
crossed.

The EMI ABI, remap-fields, resource-layout and service-gate items form the
four-item `mt6797-kernel-compile-helper-v1` comparison group. Their median
elapsed time is 34.5556433833 minutes and median review/rework time is
23.4864866834 minutes. First-review acceptance is 0/4; none escalated, and
credits are unavailable throughout.

The conclusion remains `too-small`. Four comparable items do not meet the
five-item threshold for a settings experiment. The scope miss supports keeping
the explicit offline constraint and review gate, both of which caught it; it
does not yet identify a model, effort or concurrency setting that should
change. The baseline route is retained.

## Post-item-nine reasoning-review checkpoint

Checkpoint `pilot-01-post-item-nine-reasoning-review-misses` closes accepted
sequence 9 and considered sequence 13. Items six and nine are consecutive in
the `hard-reasoning-verdict-receipt-v1` comparison sequence and both missed
first-review acceptance, so the policy requires another early review. Including
item five, the three-item group shares hard-uncertainty reasoning, Astra Medium
ownership, Sol Medium review, independently frozen source/attempt records,
conservative multi-verdict receipts and offline semantic refusal checks.

The group has median elapsed time 20.55 minutes and median review/rework time
9.6 minutes. First-review acceptance is 0/3. Items five and six escalated for
different verifier-boundary and missing-tooling reasons; item nine completed
one bounded verifier repair without escalation. Credits are unavailable for all
three.

The conclusion remains `too-small`. Three related investigations do not meet
the five-comparable-item threshold for a settings experiment, and their review
misses have different immediate causes. The evidence supports keeping the
semantic-review gate; it does not justify changing model, effort or concurrency
settings. The baseline route remains in effect.

Creation of this loop remains excluded because its eligibility and timing
contract did not exist before work began. The passive CONSYS ownership snapshot
also remains excluded as a device session. The stopped tooling contract is an
abandoned pre-dispatch candidate, as is its independently scoped sparse
successor. None changes the accepted count.

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
