# Work item: MT6797 audio current-upstream architecture

- **Outcome:** Produce an independently reviewable current-public-source decision
  for local patches `0045` and `0064`: identify the smallest coherent upstream
  audio topic with a real consumer/validation story, or record an exact stop.
- **Owner and reviewer:** `gemini_reasoner` / Sol Medium owns the source audit;
  Project Planning integrates; a separate reviewer accepts or rejects the
  handoff.
- **Scope:** This experiment directory only. Read the two named local patches,
  the July audio experiment, current official Linux and Devicetree sources, and
  public subsystem history. Do not edit patches, series, manifest, configuration,
  shared documentation, or project registries.
- **Model route:** Sol Medium because the task is cross-tree interface and
  dependency reasoning. Review tier is Sol Medium unless a concrete hardware
  ownership contradiction requires Astra Medium.
- **Stop/escalation:** Stop after classifying both patches, the current AFE/codec/
  machine-card/binding dependency graph, testability, and upstream target. Do not
  implement. Escalate immediately if public/current sources conflict with the
  frozen evidence in a way that changes hardware ownership or safe enablement.
- **Parent:** repository commit
  `2f6a56e058c80dac1a53381fedab748b3a0048a6`; local inputs:
  `0045` SHA-256 `a07bcf53e3c1fcddfed58ef6ec74e59b664acf8916e6c2c5bcbef027bc29128e`,
  `0064` SHA-256 `b5fc79ee89672106bcec8014f3fc973a4553671e95eae4537e99d0ce274d004d`,
  July README SHA-256
  `05ac5115903ea73105bcefe2064b0df4d32f6d0c325b89c082cf85197a07ad45`.
  Record exact current public revisions and file identities consulted.
- **Dependencies:** Public source/network access only. No build, hardware,
  private vendor source, retained binaries, or upstream feedback is required.
- **Worktree:** Shared repository checkout; ownership is limited to
  `experiments/2026-09-07-mt6797-audio-upstream-architecture/`. Other agents are
  working concurrently; do not revert or accommodate by overwriting their edits.
- **Validation:** Strict JSON parsing; exact hashes/revisions; local link and
  whitespace checks; verify each current-source claim against official public
  source. Distinguish compile/schema feasibility from runtime audio support.
- **Hardware:** None. Do not contact the Gemini, run audio, inspect private
  captures, or admit a device action.
- **Upstream:** Identify the current ASoC/Devicetree target, truthful authorship
  state, patch-removal condition, dependency order, and whether the disabled DTS
  node has an acceptable consumer/test story.
- **Owner-away work:** Entire item is offline. A bounded accepted stop frees the
  worker; it does not enable the codec, machine card, speaker, microphone, or any
  voice path.
- **Device readiness:** Not applicable; no queue or candidate change.
- **Handoff:** Create `README.md` and `results/source-review.json` with source
  identities, patch dispositions, dependency map, validation, limitations,
  recommendation, and `review_ready_utc`.
- **State:** complete; review-ready at `2026-09-07T20:12:34Z` and accepted
  after one documentation repair at `2026-09-07T20:15:58Z`.
- **Efficiency loop:** If accepted, Project Planning records this as one offline
  item in the active workflow-improvement cohort with measured timestamps and
  unavailable credits unless an actual credit source exists.
