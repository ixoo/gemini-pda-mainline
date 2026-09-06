# Work item: choose and record MT6797 infracfg upstream ordering

- **Outcome:** freeze the smallest technically coherent upstream topic and make
  its remaining external blockers explicit.
- **Owner and reviewer:** implementation owner `infracfg_ordering_record`;
  integration reviewer `/root` with the completed independent Sol Medium
  technical review from `infracfg_final_review` as an input.
- **Scope:** this experiment's ordering/readiness records,
  `project/upstream-topics.json`, the active workflow ledger/summary, and the
  live-ledger independence repair in `scripts/test-workflow-improvement.py`.
  The six integrated patches, manifest, profile, canonical series, roadmap,
  kernel source and device are read-only.
- **Model route:** Luna High bounded implementation because the edit joins an
  upstream-ref refresh, evidence record and cross-file readiness state; Sol
  Medium integration review.
- **Stop/escalation:** stop without kernel-topic edits if current upstream contains the
  common-probe conversion, any selected source differs in a topic-relevant way,
  the six-patch payload changes, or acceptance requires authorship, public
  contact, a kernel build or device access. Escalate any contradictory source
  evidence with the exact ref/path and next comparison. Integration review
  exposed that the workflow refusal fixtures inherited the now-nonempty live
  ledger, so this contract admits the narrow fixture-isolation repair and no
  validator-policy change.
- **Parent:** project commit
  `eb32d1cab482bec7ce21b8a16f94eed70fa4b9db`; upstream source parent
  `4d7d9486c04d917265f64c55bd23b2cc4fe7749c`; profile
  `mt6797-infracfg-revised-kunit`; series
  `patches/series-mt6797-infracfg-revised-kunit`; current six mail hashes and
  retained generation evidence remain frozen.
- **Dependencies:** official mainline, clock `clk-next` and MediaTek `for-next`
  refs; exact selected-file comparison; existing build/KUnit/schema/provider
  evidence. Public ordering feedback and truthful author/DCO certification
  remain external.
- **Worktree:** this repository checkout only; no Linux tree or build directory.
- **Validation:** parse changed JSON, verify links, run the manifest-series
  invariant, topic/revised fixtures affected by the record, repository
  publication gate and both staged whitespace checks. Confirm patch/profile
  bytes are unchanged.
- **Hardware:** none.
- **Upstream:** choose topic-first locally because the conversion is absent from
  current inspected trees. Coordinate that choice with clock/MediaTek
  maintainers and the conversion author before submission. Remove local patches
  only after accepted equivalents enter the selected upstream baseline and
  regression evidence passes. Authorship/certification remains unresolved.
- **Owner-away work:** the record, checks and review can finish offline. No
  physical selection is needed.
- **Device readiness:** not applicable; no candidate or deployment state changes.
- **Handoff:** parent commit `eb32d1cab482bec7ce21b8a16f94eed70fa4b9db`;
  scoped working-tree delta is uncommitted by instruction. Changed paths are
  this work item, `results/upstream-ordering-refresh-20260906.json`,
  `revised-topic/SUBMISSION_READINESS.md`, `project/upstream-topics.json`, and
  `scripts/test-workflow-improvement.py` (fixture starts from the bootstrap
  entry with empty checkpoints/decisions; validator policy is unchanged).
  The refresh records refs observed at `2026-09-06T01:29:52Z`, all eleven
  footprint statuses, and the topic-first local ordering. JSON parsing,
  revised-topic generation/partial-tree fixtures, workflow validator and all
  15 workflow refusal fixtures, manifest-series validation, repository
  publication gate, and whitespace checks passed (the Linux-only provenance
  fixture was skipped on macOS and remains mandatory in CI). The
  six patch files, profile fragment,
  `kernel/manifest.json`, and both series files retain their pre-edit SHA-256
  values. Remaining blockers are current-tree outgoing replay/checkpatch/
  get_maintainer immediately before send, actual author/DCO/Assisted-by
  decisions, and upstream ordering coordination.
- **State:** complete and integration-accepted at `2026-09-06T01:43:13Z`;
  submission remains conditional on the external blockers above. The
  live-ledger fixture repair changed no validator policy, kernel payload or
  technical decision.
- **Efficiency loop:** if accepted, record one offline documentation/integration
  item in the active ledger with observed timestamps and unavailable credits;
  the earlier read-only consultation is excluded as review-only.
