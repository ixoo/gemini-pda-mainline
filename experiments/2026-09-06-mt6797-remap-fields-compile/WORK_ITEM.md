# Work item: compile checked MT6797 shared-remap field helpers

- **Outcome:** add a separately compiled, pure private helper for the two
  source-established fields in shared register `0x10001340`, proving checked
  encoding and known-state masked replacement without adding a register owner,
  MMIO path or runtime admission.
- **Owner and reviewer:** a Luna High implementation worker owns only this new
  experiment's source, tests and generated proposal patch; `/root` owns shared
  proposal/series/manifest integration and final validation; Sol Medium reviews
  the cross-file ownership and refusal boundary.
- **Scope:** create an original `remap-fields.{c,h}` component beside the
  private MT6797 HIF core and add only its object to the existing private
  Kbuild selection. Implement checked encoding for the common low field
  (base bits 11:0 plus enable bit 12, 1 MiB alignment, 32-bit address space,
  complete first-MiB fit) and the optional WLAN upper field (bits 31:16,
  64 KiB alignment, 32-bit address space). Masked replacement must require an
  exactly known expected value for the owned field and preserve every
  neighboring bit. Refusals must clear a non-null output first; a null output
  refuses, while zero remains a valid exactly known field rather than an
  unknown-state sentinel. Do not add MMIO, regmap, locks, DT, probe, registration,
  exports, callers, power/reset, firmware, MPU/SMC, DMA, IRQ or policy defaults.
  Shared `patches/proposals`, `patches/series`, the compile profile and manifest
  remain integrator-owned.
- **Model route:** Luna High for bounded implementation because the source
  fields and refusal interface are frozen; Sol Medium for integration review.
- **Stop/escalation:** stop if pinned evidence does not determine an encoding,
  if the helper needs a runtime owner/caller to compile, if an unknown current
  field would be accepted, if neighboring bits cannot be proven preserved, or
  if generated patch replay conflicts with proposal 0008. After two failed
  repairs, return exact diagnostics and the smallest discriminating check.
- **Parent:** repository commit
  `ef212d454c7497aa5fcf60ed4182d7d104bd8ca9`; Linux source
  `4d7d9486c04d917265f64c55bd23b2cc4fe7749c`; predecessor series
  `patches/series-mt6797-provider-compile` through proposal 0008; proposal
  0008 has SHA-256
  `ac87496f89b81419bbf2219acf7f9f140fec14d3b4cf37075107f2afa2f396f9`;
  evidence identities `OWNERSHIP.md`
  `5a7044e62fc5688ef7c14f53f536dbf6a18a7e64719dd0236ead39ab540d3435`
  and `SHARED_OWNER_IMPLEMENTATION.md`
  `a71e51e2ff2676b63d21bbd8e83fc6af98c24e77d47f4fe541e60d11be1c1021`.
- **Dependencies:** the pinned offline field-sharing evidence and existing
  private Kbuild directory only. Actual initial register state, serialization,
  readback, client ownership and external-writer exclusion remain unresolved
  provider dependencies and must not be represented as satisfied.
- **Validation:** generated patch exactly matches experiment sources; replay
  every exact entry of the updated named series ending in proposal 0009;
  strict host tests exhaust all 4096 common base encodings in both enable states
  and all 65,536 upper encodings, and cover zero/highest representable bases,
  all alignment residues, the combined 32-bit/first-window overflow boundary,
  malformed expected/replacement fields, expected-state mismatch, both enable
  states, exhaustive outside-mask bit preservation, cleared refusal outputs and
  null-output refusal. Prove the replayed Linux tree has only declarations and
  definitions of the new symbols, with no initcall, probe, export or MMIO path.
  Run Checkpatch and repository gates, then compile after a clean pushed commit
  with `KERNEL_PROFILE=mt6797-hif-parser-compile ./scripts/build-kernel
  --backend buildbox`.
- **Hardware:** none. No Gemini access, boot candidate, partition write, MMIO,
  SMC, mapping, radio, firmware, DMA, power or reset action.
- **Upstream:** eventual target is the MediaTek shared CONSYS resource manager;
  this is an experiment-only synthetic patch without a certifying author or
  DCO sign-off. Remove it when an upstream-reviewed provider subsumes the
  helper.
- **Owner-away work:** all implementation, review and Buildbox validation can
  finish offline. It must not select or prepare a device session.
- **Device readiness:** not applicable; compile evidence is neither a register
  owner nor Wi-Fi/hardware support.
- **Handoff:** exact proposal patch and generated-source identities, exhaustive
  host test counts, Checkpatch limitations, replay result, Buildbox object and
  package evidence, and a source-tree proof that no runtime caller exists.
- **State:** waiting-build. Implementation began at `2026-09-06T04:25:48Z`,
  first became review-ready at `2026-09-06T04:36:03Z`, and passed repaired
  pre-Buildbox integration review at `2026-09-06T04:42:18.834405Z` after one
  provenance rework cycle.
- **Efficiency loop:** if accepted, append exactly one accepted offline item to
  the active workflow-improvement ledger with actual timing, routing, review,
  rework/escalation and measured credits or explicit unavailability.
