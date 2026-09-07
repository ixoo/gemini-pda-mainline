# Work item: Gemini sensor current-upstream architecture

- **Outcome:** Produce an independently reviewable current-public-source
  disposition for local disabled BMI160 patch 0052 and the known BMI160/STK3310
  sensor identities: select the smallest truthful upstream topic with a consumer
  and validation story, or record an exact stop.
- **Owner and reviewer:** `gemini_reasoner` / Sol Medium owns the source audit;
  Project Planning integrates; Astra Medium reviews electrical identity,
  interrupt, rail and safe-probe boundaries.
- **Scope:** This experiment directory only. Read patch 0052 and the frozen July
  sensor README, STK3310 reuse audit and HAL axis contract; inspect current
  official Linux IIO/input bindings/drivers, MT6797/Gemini DTS and bounded public
  history. Do not inspect private captures or vendor sources and do not edit
  patches/shared files.
- **Model route:** Sol Medium for current-tree identity/interface reasoning;
  Astra Medium review because the unresolved physical address, rail, interrupt
  and orientation contract is a hardware-ownership uncertainty.
- **Stop/escalation:** Stop after classifying patch 0052, BMI160 and STK3310
  driver/binding identity, board dependencies and validation story. Do not
  implement. Escalate if names/addresses conflict or if any proposal requires an
  unproved rail, interrupt, register transaction or orientation transform.
- **Parent:** repository commit
  `c8344011557b2369e8d15187a5969103108a2c18`; patch 0052 SHA-256
  `d55ebcf56b8a573b98b97419ec35ba110bffba65e7f6ff594578818aad89e3d4`;
  July README/reuse/axis SHA-256 values
  `f046614df6455f4a233fb9d01ba91537114add4f0c6802a9e5f35ba2e197fe41`,
  `ec035dca7befd4779b07d495ed66686c0ba5ac152a0ebb590a0327eaac2e091f`,
  and `aa525f7a4e2f1e583dc356354c571fd8195f1097931ca9260db1f9a7352c926d`.
  Record exact current public revisions and file identities.
- **Dependencies:** Public source/network access only. No build, device,
  private vendor material, retained binary or upstream feedback.
- **Worktree:** Shared checkout; ownership is limited to
  `experiments/2026-09-07-gemini-sensors-upstream-architecture/`. Other agents
  work concurrently; do not revert or overwrite their edits.
- **Validation:** Strict JSON; frozen/current hashes; local links; whitespace;
  canonical local position; source-backed compatible/register/IRQ/supply and
  mount-matrix claims. Distinguish disabled description from runtime support.
- **Hardware:** None. No Gemini/private access, I2C transaction, sensor rail,
  interrupt, sampling or device-session admission.
- **Upstream:** Identify IIO/Devicetree/DTS routes, truthful authorship/DCO
  boundary, dependency order and local-patch removal condition.
- **Owner-away work:** Entire item is offline. An accepted stop does not enable
  either sensor or establish scale, axes, orientation or wake behavior.
- **Device readiness:** Not applicable; no queue/candidate change.
- **Handoff:** Create `README.md` and `results/source-review.json` with exact
  sources, patch/identity dispositions, dependency map, validation, limits,
  recommendation and `review_ready_utc`.
- **State:** complete; review-ready at `2026-09-07T20:49:17Z` and accepted
  on first review at `2026-09-07T20:52:42Z`.
- **Efficiency loop:** If accepted, Project Planning appends one measured offline
  item to pilot 04; credits remain unavailable unless actually measured.
