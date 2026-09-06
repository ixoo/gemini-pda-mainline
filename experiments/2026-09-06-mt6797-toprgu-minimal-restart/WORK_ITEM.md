# Work item: minimal MT6797 TOPRGU restart diagnostic

- **Outcome:** Produce one reviewable Linux 7.1.3 experiment delta and named
  profile that reduce the already hardware-passed MT6797 restart behavior to
  restart-path `WDT_MODE_AUTO_START` plus restart priority 130, while leaving
  watchdog start and firmware-watchdog adoption semantics unchanged from their
  upstream behavior. This is candidate preparation, not a runtime claim.
- **Owner and reviewer:** implementation owner Hume; integration reviewer
  Curie; repository integration and any Buildbox/device action remain with the
  primary task.
- **Scope:** the implementation owner may add the experiment record and
  validator, one logically isolated patch below `patches/v7.1.3/`, one
  canonical-order experiment series, one local-version-only fragment, and a
  manifest-profile proposal recorded in the handoff. The primary task alone
  integrates the new patch into `patches/series`, adds the profile to
  `kernel/manifest.json`, and owns the workflow ledger, experiment queue and
  roadmap. Do not edit unrelated paths or rewrite historical patches 0081/0087.
- **Model route:** bounded implementation uses `gemini_implementer`,
  `gpt-5.6-luna`, high effort. Predispatch and final integration review use
  `gemini_reasoner`, `gpt-5.6-sol`, medium effort because the effective driver
  behavior spans historical patches and the current profile series.
- **Stop/escalation:** stop on ambiguous effective-source context, a need to
  change reset-controller or recovery-takeover behavior, inability to express
  the result as one isolated experiment patch, or any mismatch between the
  frozen serviceability profile and current manifest. After two repair attempts
  return evidence and the next discriminating check; do not widen scope.
- **Parent:** repository commit
  `f7bc2c9adc1210c58d2dc14e645336f9ae515f42`; Linux 7.1.3 source SHA-256
  `be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc`;
  parent profile `da921x-current-service-control`; parent series
  `patches/series-before-v4-conversion-correction`; historical behavior patches
  0081 and 0087 remain immutable evidence.
- **Dependencies:** the MT6797 compatible must continue to select its existing
  match data. Among ordinary watchdog lifecycle paths, the MT6797 match-data
  auto-start policy is consumed only by `mtk_wdt_restart()`. The separately
  configured recovery takeover continues to set and validate `AUTO_START`
  exactly as established by patches 0386/0489 and is excluded from this claim.
  MT6797 priority must be 130, immediately above arm64 PSCI priority 129; other
  MediaTek watchdogs retain priority 128. The effective reset-controller,
  boot-status, recovery takeover/validation and mutation-lock behavior from
  patches 0090/0303/0386/0489 are frozen. The code policy applies to every
  `mediatek,mt6797-wdt` match; the named profile limits deployment, not SoC-wide
  semantics, and one Gemini result cannot establish generic upstream policy.
  Hardware equivalence is unresolved until an exact built candidate passes a
  separately admitted session.
- **Worktree:** shared small patch-repository checkout only. Do not create or
  copy a Linux source tree. Read-only inspection of a managed prepared source
  is permitted; no Buildbox build belongs to the implementation handoff.
- **Validation:** require JSON/manifest parsing, canonical subsequence checks
  for every profile, patch metadata/source checks, focused semantic fixtures,
  `git diff --check`, and absence of generated artifacts, private data and
  personal absolute paths. The new profile must inherit the exact
  `da921x-current-service-control` fragment list and differ in resolved
  configuration only by its explicit local version. Fixtures must reject
  priority 128/255, loss of the restart-path `AUTO_START` write, changed
  non-MT6797 priority, any MT6797 policy branch or `WDT_MODE` write in
  `mtk_wdt_init()`, any match-data `AUTO_START` write in `mtk_wdt_start()`, and
  any change to the frozen reset-controller, boot-status, recovery
  takeover/validation or mutation-lock behavior.
- **Hardware:** none for this work item. A later session may spend at most one
  physical selection and one ordinary reboot on an exact validated candidate,
  with authenticated serviceability first, no userspace watchdog, changed-boot
  Gemian recovery, and no automatic retry. The device custodian is assigned
  only when that session is admitted. Its decision table is:

  | Observation | Classification and next action |
  | --- | --- |
  | Identity or serviceability mismatch before selection | Refuse; consume no restart action. |
  | Exact candidate, authenticated USB serviceability, no userspace watchdog, attributable restart marker/request, prompt disconnect, and changed-boot-ID Gemian recovery | Pass once; do not repeat. |
  | Prompt or exact USB survives beyond the predeclared bound, or the device hangs | Inconclusive; stop without retry. |
  | Reset occurs without the attributable restart observation, or any userspace watchdog activity is present | Inconclusive; stop without retry. |
  | Changed-ID Gemian recovery fails | Inconclusive; perform recovery only and do not retry. |

  The future session packet must bind the marker, collector and time bound to
  immutable identities before readiness can become `ready`.
- **Upstream:** Linux watchdog subsystem. This experiment delta uses a clearly
  synthetic, non-certifying author identity, has no `Signed-off-by`, and is not
  submission-ready. Actual authorship, DCO, current-tree overlap and policy
  review remain gates. Delete the local diagnostic after a minimal equivalent
  is accepted upstream or its hypothesis is retired.
- **Owner-away work:** implementation, refusal fixtures, repository validation,
  integration review and Buildbox package construction can finish without a
  physical selection. Stop after a validated candidate/session packet is ready;
  do not select or boot it.
- **Device readiness:** planned. Pass means exact USB serviceability followed
  by one ordinary reboot and changed-ID known-good Gemian return. A hang,
  missing attribution, automatic watchdog activity or failed recovery is
  inconclusive and stops without retry. Any patch, profile, package, DT,
  initramfs, installer or observation-tool change invalidates readiness.
- **Handoff:** exact changed paths, patch identity, focused fixture results,
  repository checks, known limits and review-ready UTC timestamp. No commit,
  push, build, device access or support-matrix change by the implementation
  owner.
- **State:** complete offline; accepted after repair 2 at
  `2026-09-06T08:53:09Z`. Repair 1 made the verifier semantic; repair 2 added
  the root-owned manifest and canonical-series identities to the integrated
  receipt. Source replay, Checkpatch, Buildbox compilation, device readiness
  and hardware equivalence remain pending separate gates.
- **Efficiency loop:** recorded as considered sequence 14 / accepted sequence
  10 with unchanged timing, first-review, rework and publication-failure
  measurements. The publication early-signal and item-ten close checkpoints
  are recorded, pilot 01 is closed, pilot 02 is active, and effective decision
  `baseline-01` remains unchanged. The workflow validator passes.
