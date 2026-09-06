# Work item: compile the MT6797 reserved-resource layout bridge

- **Outcome:** add one separately compiled, pure private bridge from the
  already validated initialized reserved-memory description to the two fixed
  CONSYS subranges, common remap target field and region-18/19 EMI owner-range
  descriptors. Prove that the compiled bridge composes the existing interfaces
  without selecting a permission policy or adding a hardware effect.
- **Owner and reviewer:** a Luna High implementation worker owns only this new
  experiment's sources, host tests, verifier and generated proposal patch;
  `/root` owns shared proposal/series/manifest integration and Buildbox evidence;
  Sol Medium reviews the cross-file resource and policy boundary.
- **Scope:** create original `resource-layout.{c,h}` beside the private MT6797
  HIF core and add only its object to the existing private Kbuild selection.
  Its single constructor consumes an `mt6797_image_reserved_info`, an explicit
  `mt6797_emi_selector` that is exactly `BIT13_CLEAR` or `BIT13_SET`, and a
  distinct output. It must require a nonzero reserved generation; a
  nonwrapping resource of at least 1 MiB;
  the exact first 512 KiB WLAN and next 512 KiB WMT intervals already reported
  by the reserved owner; and a 1 MiB-aligned base whose complete first 1 MiB
  fits in the 32-bit address space. Bytes after the first MiB remain unassigned,
  regardless of the full resource size. Detect an identical input/output object
  address before reading input, clear the non-null output, and refuse it; every
  other partial byte overlap is an API precondition and is not claimed to be
  detected. It must call, not copy,
  `mt6797_remap_encode_common(base, 1, ...)`,
  produce region-18 and region-19 owner ranges with the supplied selector, and
  retain the reserved generation. Clear non-null output before every refusal.
  Do not add policy words, writable/final
  defaults, SMC calls, MMIO/regmap, locks, DT parsing, mapping, copy, HIF calls,
  probe, registration, exports, power/reset, IRQ, DMA or firmware access. Do
  not use the optional WLAN upper remap field. `image_binding_begin()` must
  continue returning `-EOPNOTSUPP`; no runtime caller is added. Shared proposal
  inventory, named series and manifest remain integrator-owned.
- **Model route:** Luna High because the existing reserved, remap and EMI data
  interfaces freeze this bounded implementation; Sol Medium performs the
  cross-file integration review.
- **Stop/escalation:** stop if exact composition requires changing a predecessor
  interface, if the initialized record cannot distinguish the required
  first-MiB layout,
  if a permission/domain policy would be needed, if the bridge would create an
  access grant or hardware effect, or if proposal replay conflicts with 0009.
  After two failed repairs, return the evidence, attempts, unresolved question
  and smallest discriminating check rather than widening scope.
- **Parent:** repository commit
  `f43a702c107e3685c92c4d275dc3547acf7302ce`; Linux source
  `4d7d9486c04d917265f64c55bd23b2cc4fe7749c`; complete 12-entry predecessor
  `patches/series-mt6797-provider-compile` SHA-256
  `09c60922863e56594c17e22c0bf0d7363af3bab660f2d6aad2e5e7df3e4fac88`;
  proposal 0006 SHA-256
  `2798d49d202edc441c775a78c06ec0d261169f426fdadb04cf6c5e052fba545c`,
  proposal 0007
  `684db9c82d60d42cfbb197ce9f52dd3899f76e1f7c29925554162a73d11aafd0`,
  proposal 0008
  `ac87496f89b81419bbf2219acf7f9f140fec14d3b4cf37075107f2afa2f396f9`,
  and proposal 0009
  `84e6abef1139e744ecb59846b3fb3160b98ac50df4a59e058250a77b92d09cb6`.
  Frozen evidence: `OWNERSHIP.md`
  `5a7044e62fc5688ef7c14f53f536dbf6a18a7e64719dd0236ead39ab540d3435`,
  `SHARED_OWNER_IMPLEMENTATION.md`
  `a71e51e2ff2676b63d21bbd8e83fc6af98c24e77d47f4fe541e60d11be1c1021`,
  and the unresolved domain verdict record
  `458bbd8b15b59dc40663315c8c305829fc1ca9df4d144a2b61166726daf8a63f`.
- **Dependencies:** the exact predecessor declarations only. The input is a
  descriptive initialized-record snapshot, not a reservation/exclusion grant.
  Actual record freshness, external-writer exclusion, common serialization,
  current remap state, selector provenance, MPU policies/priority, secure-call
  service, mapping visibility, firmware lifetime and quiescence remain required
  provider evidence and must not be represented as satisfied.
- **Validation:** generate proposal 0010 reproducibly and prove exact source
  identity; replay every exact predecessor and 0010 in the canonical named
  order; compile the bridge as its own host object with strict warnings and
  ASan/UBSan; exercise zero/null generation, every interval mismatch,
  full-resource wrap, minimum 1 MiB, a larger-than-2-MiB positive resource,
  1 MiB alignment boundaries including a 1 MiB-aligned but not 2 MiB-aligned
  base, exact CLEAR/SET selectors, UNSET, the next and a large invalid selector,
  first-MiB upper 32-bit fit, identical-address refusal before any input read,
  cleared refusals and exact successful output. Partial overlap remains a stated
  caller precondition and receives no runtime-refusal claim. Demonstrate the constructor
  uses the linked predecessor remap function rather than copied encoding, and
  that output contains no permission field. Prove the replayed Linux tree has
  declarations/definition only, no caller, and unchanged active-entry refusal.
  Run Checkpatch and repository gates, then build the clean pushed commit with
  `KERNEL_PROFILE=mt6797-hif-parser-compile ./scripts/build-kernel --backend
  buildbox`; validate/fetch only the exact package and record the real AArch64
  object, undefined-symbol resolution and source/command identities.
- **Hardware:** none. No Gemini SSH, boot candidate, partition, MMIO, SMC,
  mapping, firmware, radio, DMA, power or reset action.
- **Upstream:** eventual target is a MediaTek shared CONSYS resource manager.
  This remains an experiment-only synthetic non-certifying patch without a DCO
  sign-off. Its temporary WLAN-tree placement confers no WLAN authority over
  WMT, remap or MPU resources; move or remove it when an upstream-reviewed
  `drivers/soc/mediatek/` provider owns this composition.
- **Owner-away work:** implementation, review and Buildbox validation can
  finish offline. It must not select or prepare a device session.
- **Device readiness:** not applicable. Layout composition and compilation are
  not resource ownership, firmware execution or Wi-Fi support.
- **Handoff:** exact proposal/source identities, host fixture counts, replay
  and Checkpatch results, no-caller/no-policy/no-effect proof, Buildbox package
  and `resource-layout.o` evidence, and every unresolved provider dependency.
- **State:** complete. Implementation contract drafted at
  `2026-09-06T05:26:51Z`, passed Sol pre-dispatch review at
  `2026-09-06T05:32:26Z`, and implementation began at
  `2026-09-06T05:32:44Z`. The repaired implementation was review-ready at
  `2026-09-06T05:50:22Z` and passed final pre-Buildbox Sol review at
  `2026-09-06T05:51:12Z`. Buildbox generated and validated the exact pushed
  commit's package at `2026-09-06T06:06:49Z`; the package fetch completed by
  `2026-09-06T06:08:34Z`, and final post-Buildbox Sol acceptance was recorded
  at `2026-09-06T06:11:43Z`. This offline compile work item is complete.
- **Efficiency loop:** if accepted, append one sanitized item to the active
  workflow ledger with actual timing, routes, review/rework, escalation and
  measured credits or explicit unavailability.
