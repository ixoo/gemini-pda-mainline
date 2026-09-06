# Parallel work item and handoff

Use one instance in the owning experiment or tracking issue. This is a work
contract, not a new approval requirement or an alternative roadmap.

- **Outcome:** one externally assessable capability, evidence decision or
  independently reviewable upstream topic.
- **Owner and reviewer:** one implementation owner; one integration reviewer.
  Unassigned means nobody is working on it.
- **Scope:** exact files/subsystem; shared interfaces and their owners.
- **Model route:** selected model and effort, reason for the tier, and any
  explicit override of project defaults. Normally Luna Medium execution, Luna
  High bounded implementation, Sol Medium reasoning/review, Astra Medium for
  a named hard uncertainty. Record the review tier separately when different.
- **Stop/escalation:** completion boundary and stop conditions; after two failed
  repairs or a contradiction/unclear acceptance/scope change, hand back evidence,
  attempts, the unresolved question and next discriminating check.
- **Parent:** repository commit, explicit profile/series and relevant frozen
  input identities. Link the candidate record when applicable.
- **Dependencies:** precise facts/interfaces required; distinguish offline,
  build, hardware, upstream-feedback and rights dependencies.
- **Worktree:** small repository checkout and topic branch; no Linux source tree.
- **Validation:** smallest meaningful host/kernel/schema checks; expected
  observations, rejection cases and evidence locations.
- **Hardware:** none, or one separately admitted protocol with exact candidate,
  finite action budget, attributable result and recovery. Name the custodian.
- **Upstream:** target subsystem/tree, authorship/certification status, public
  review link when available and local-patch removal condition.
- **Owner-away work:** what can finish without physical selection; the bounded
  handoff that frees this worker for another offline item.
- **Device readiness:** planned/preparing/conditional/ready separately from
  deployment state; link an experiment-owned [session packet](DEVICE_SESSION.md)
  and its [queue entry](experiment-queue.json). State exact result predicates,
  invalidation conditions and all required owner interactions.
- **Handoff:** exact commit, changed paths, tests actually run, known failures,
  artifact references and what evidence permits integration.
- **State:** ready, active, waiting-build, waiting-device, waiting-upstream,
  blocked, review-ready or complete. State the external dependency when blocked.
- **Efficiency pilot:** for the next ten accepted offline items, record
  first-review acceptance, escalation, elapsed time, review/rework time and
  measured credits (or unavailable). Do not estimate credits from model names.

One worker hands shared manifest/series changes to the integrator instead of
racing another worker's edit. The integrator verifies canonical order and
unchanged inputs for unrelated active profiles. A completed offline item does
not select a device boot or promote a hardware-support claim.
