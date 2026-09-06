# Work item: compile the MT6797 EMI ABI helper in Linux

- **Outcome:** integrate the accepted pure EMI argument/result helper as a
  separately compiled private MT6797 Wi-Fi object and prove its Linux include,
  type and warning compatibility without adding any runtime caller or hardware
  admission.
- **Owner and reviewer:** a Luna High implementation worker owns only this new
  experiment's source, tests and generated proposal patch; `/root` owns shared
  series/manifest integration and final validation; Sol Medium reviews the
  cross-file boundary.
- **Scope:** create an original `emi-abi.{c,h}` component beside the private
  MT6797 HIF core, add its object to that private Kbuild selection, and retain
  the accepted arithmetic/refusal contract from
  `../2026-09-05-mt6797-wifi-contract/EMI_ABI.md`. Do not alter image binding,
  HIF transport, DT, runtime probe, secure-call, mapping, power, reset, IRQ,
  DMA or firmware paths. Shared `patches/series`, the compile profile and
  manifest remain integrator-owned.
- **Model route:** Luna High for bounded implementation because the interfaces
  and acceptance boundary are frozen; Sol Medium for integration review.
- **Stop/escalation:** stop if kernel types change the accepted arithmetic, if
  the helper needs a runtime caller merely to compile, if a policy/selector
  default is proposed, or if generated patch replay conflicts with proposal
  0007. After two failed repairs, return exact diagnostics and the smallest
  discriminating check.
- **Parent:** repository commit
  `9e3851500113515392e97fb8d21bf83ed4c6f2a8`; Linux source
  `4d7d9486c04d917265f64c55bd23b2cc4fe7749c`; predecessor series
  `patches/series-mt6797-provider-compile` through proposal 0007; profile
  `mt6797-hif-parser-compile`; accepted helper source
  `../2026-09-05-mt6797-wifi-contract/src/emi_abi.h`.
- **Dependencies:** offline accepted EMI ABI evidence and the existing private
  Kbuild directory only. No device, firmware blob, retained binary, rights
  decision or live secure service is required.
- **Validation:** generated patch exactly matches experiment sources; replay
  proposals 0001 through 0008; strict host tests preserve exhaustive alignment,
  confinement, selector, policy, region and signed-result cases; run
  Checkpatch and repository gates; then compile with
  `./scripts/build-kernel --backend buildbox` after a clean pushed commit.
- **Hardware:** none. No Gemini access, boot candidate, partition write, MMIO,
  SMC, mapping, radio, firmware, DMA, power or reset action.
- **Upstream:** eventual target is the MediaTek wireless/provider split; this is
  an experiment-only synthetic patch without a certifying author or DCO
  sign-off. Remove it when an upstream-reviewed provider subsumes the helper.
- **Owner-away work:** all implementation, review and Buildbox validation can
  finish offline. It must not select or prepare a device session.
- **Device readiness:** not applicable; compile evidence is not Wi-Fi support.
- **Handoff:** exact proposal patch identity, generated-source identity, host
  test counts, Checkpatch limitations, Buildbox object/package evidence, and a
  statement that no runtime caller exists.
- **State:** waiting-build. Implementation began at
  `2026-09-06T03:50:50Z` and was review-ready at
  `2026-09-06T04:09:47Z`. The first integration pass required continuation
  alignment and portable `static_assert` spelling; the second required complete
  pinned Checkpatch dictionaries. Both bounded repairs passed, and Sol Medium
  accepted the frozen pre-Buildbox integration. A clean pushed commit and real
  Buildbox object evidence remain required.
- **Efficiency loop:** if accepted, append one offline item to the active
  workflow-improvement ledger with measured timestamps and credits only when
  available.
