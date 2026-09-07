# Work item: resolve the MT6797 TOPRGU restart policy boundary

- **Outcome:** decide from current primary-source and retained project evidence
  whether an upstream MT6797 watchdog restart topic can freeze a narrowly
  justified interface, or must stop for a named missing observation.
- **Owner and reviewer:** hard-risk owner `toprgu_policy_specialist`; integration
  owner `/root`. Any later implementation has a separate Luna High owner only
  after this design is accepted.
- **Model route:** Astra Medium for the named hardware/policy uncertainty:
  MT6797-wide ownership of restart bit 4 and priority relative to PSCI. Sol
  Medium integration review follows before implementation.
- **Frozen inputs:** repository parent `bcfce71133dd70d80b60988000df0a8eb836df19`;
  historical patches [0081](../../patches/v7.1.3/0081-watchdog-mtk-set-MT6797-auto-restart-mode.patch),
  [0087](../../patches/v7.1.3/0087-watchdog-mtk-prioritize-MT6797-TOPRGU-restart.patch)
  and [0090](../../patches/v7.1.3/0090-watchdog-mtk-expose-MT6797-TOPRGU-resets.patch);
  the [2026-09-05 TOPRGU readiness assessment](../2026-09-05-mt6797-toprgu-upstream-preparation/README.md)
  and [source receipt](../2026-09-05-mt6797-toprgu-upstream-preparation/results/source-review.json);
  Candidate AB's [experiment](../2026-07-20-mt6797-kernel-restart-diagnostic/README.md)
  and [single attended result](../2026-07-20-mt6797-kernel-restart-diagnostic/results/runtime-candidate-ab-attempt-1-20260721.txt);
  official current mainline, watchdog and MediaTek sources and public review
  archives observed during this work item. Exact retained-file hashes are in
  [the current receipt](results/source-review.json).
- **Owned scope:** this experiment directory only. The specialist is read-only;
  `/root` owns any records. Patches, manifest, series, profiles, roadmap,
  hardware facts and device state are frozen.
- **Questions:** establish current overlap; separate documented register
  semantics from inference; decide whether restart-only bit-4 policy is safe for
  all MT6797 users; decide whether priority 255, 130, default 128 or no change is
  justified; verify match-data and zero-reset-count behavior; identify the
  smallest coherent patch split and the exact missing evidence for every
  refused claim.
- **Acceptance:** pin exact refs and relevant file/message identities; cite
  primary sources; distinguish observation, source fact and inference; account
  for unchanged non-MT6797 behavior, watchdog start/adoption/pretimeout paths,
  restart-handler ordering, reset-controller registration and pending compatible
  cleanup; return one frozen interface or a precise stop decision with the next
  discriminating check.
- **Stop conditions:** no source edit, build, public contact, device access,
  restart, watchdog operation or private-data publication. Stop rather than
  choosing a global policy when the evidence only proves Gemini behavior, or
  when current overlap makes the interface owner-dependent.
- **Validation:** focused source/hash/link/JSON checks for the eventual record;
  broad repository publication checks run once on frozen integration, not during
  design repair.
- **Hardware:** none. Existing Candidate AB evidence is historical and cannot
  become a modern `Tested-by`.
- **Upstream:** no email or patch submission. Actual author identity, truthful
  DCO certification and assistance disclosure remain external gates.
- **Handoff:** a concise design verdict, exact evidence, unresolved risks and the
  next implementation or observation contract. Do not create runnable device
  artifacts.
- **State:** complete and integration-accepted at `2026-09-07T17:54:39Z` after
  one evidence-traceability repair. Implementation remains refused; no Luna
  contract, kernel change, build or device action was admitted.
