# Work item: compile the MT6797 EMI secure-service gate

- **Outcome:** add one separately compiled, private MT6797 operation gate that
  composes the accepted resource layout and EMI ABI helper with an injected
  secure-service backend, preserves the exact raw/signed result, and enforces a
  one-attempt generation-bound state machine. The proposal has no backend,
  caller, policy choice or runtime registration; it proves interface
  composition and refusal behavior only.
- **Owner and reviewer:** a Luna High implementation worker owns only this
  experiment's source, host fixtures, verifier and generated proposal 0011;
  `/root` owns shared series/manifest integration and Buildbox evidence; Sol
  Medium reviews the cross-file lifetime/effect boundary. The worker is not
  alone in the repository and must preserve every concurrent or unrelated
  edit.
- **Scope:** create original `emi-service-gate.{c,h}` beside the private MT6797
  HIF core and add only its object to that private Kbuild selection. Define a
  private context with a copied `mt6797_resource_layout`, copied backend
  callback/context, expected nonzero generation and closed states `EMPTY`,
  `READY`, `ATTEMPTED`, `COMPLETED`, `FAULT_HELD`.

  `mt6797_emi_service_gate_init(gate, layout, backend)` checks exact pointer
  aliasing without dereferencing; an alias returns `-EINVAL` and leaves storage
  untouched. Otherwise it clears a non-null output gate before reading inputs.
  Null gate/layout/backend returns `-EINVAL`; a missing backend callback returns
  `-EOPNOTSUPP`. Zero generation, reversed/wrapped or smaller-than-1-MiB top
  range, a first-MiB split other than WLAN `[start,start+0x7ffff]` and WMT
  `[start+0x80000,start+0xfffff]`, or an interval outside the top range returns
  `-ERANGE`. Invalid selector, region numbers other than exactly 18/19, selector
  disagreement or any mismatch between top-level intervals and the region
  ranges returns `-EINVAL`. It must call
  `mt6797_remap_encode_common(layout->start, 1, &expected)` and require exact
  equality with `common_field`, propagating that helper's errno and returning
  `-EINVAL` for a different field. A `BIT13_CLEAR` selector with
  `layout->start < 0x40000000` returns `-ERANGE`, preserving the resource-layout
  constructor's selector-specific representability rule. On success it copies the fully enumerated
  validated layout and backend and enters `READY`. Unlisted layout fields do not
  exist in the pinned structure. This is passive descriptor construction from
  a caller-asserted layout, not acquisition or proof of a live reservation, selector, service,
  exclusion or firmware compatibility.

  `mt6797_emi_service_gate_apply(gate, expected_generation, permissions,
  result)` first compares pointers without dereferencing. Null result or exact
  gate/result alias returns `-EINVAL`; the alias leaves both storages untouched.
  Otherwise it clears result before reading the gate. Null gate or `EMPTY`
  returns `-EINVAL`; `ATTEMPTED`, `COMPLETED` or `FAULT_HELD` returns
  `-EALREADY`; zero expected generation returns `-EINVAL`; a nonzero mismatch
  returns `-ESTALE`. Every local refusal leaves a `READY` gate unchanged and
  makes no callback. The exact `-EINVAL` or `-ERANGE` from
  `mt6797_emi_prepare()` is propagated. It always targets
  the copied region 18 and exact copied WLAN inclusive interval; region 19 and
  WMT bytes are unreachable from this API. It calls, not copies,
  `mt6797_emi_prepare()`. After successful prepare, it records `ATTEMPTED`
  before exactly one backend call with the literal prepared SMC32 function ID,
  original 64-bit start/end and packed region/permission word. The callback
  returns the raw 64-bit service result. The gate calls, not copies,
  `mt6797_emi_decode_result()`, stores generation, exact arguments, raw and
  signed-low-word status, then enters `COMPLETED` only for status zero or
  `FAULT_HELD` for every known or unknown nonzero status. The function returns
  the decoded signed status exactly; raw high bits remain only in the result.
  A completed or fault-held gate refuses every repeat with `-EALREADY` and no
  callback. `ULLONG_MAX` is a valid nonzero generation; the gate performs no
  generation increment or wrap check.

  The callback is a compile/test seam, not a default SMC implementation or a
  success stub. It may inspect the gate state through its caller-owned test
  context so fixtures can prove attempt-before-effect ordering, but it may not
  mutate gate storage. Caller-held serialization is an API precondition: the
  gate enforces one attempt only for sequential or externally serialized calls
  and makes no lock-free concurrency claim. The caller must keep the copied
  callback context alive and stable through an apply call; the copied pointer
  is not lifetime ownership. No reset/retry/release API is added. Do not add a
  real SMC instruction or wrapper, policy constants/selection, locks, MMIO/regmap,
  mapping/copy, probe/initcall/registration/export, firmware/HIF/DMA/IRQ,
  power/reset, DT parsing, allocation or userspace ABI. Do not change
  `image_binding_begin()`; its active path remains `-EOPNOTSUPP`.
  All non-identical partial overlaps among gate, layout, backend and result
  storage are caller preconditions and receive no runtime-refusal, clearing or
  preservation guarantee; the implementation claims only exact-address alias
  detection.
- **Model route:** Luna High (`gemini_implementer`, `gpt-5.6-luna`, high) for
  bounded implementation; Sol Medium (`gemini_reasoner`, `gpt-5.6-sol`,
  medium) for pre-dispatch, pre-Buildbox and post-Buildbox review.
- **Stop/escalation:** stop if the gate requires a real backend/caller, policy
  or domain selection, claimed reservation acquisition, new effect/recovery
  semantics, a predecessor-interface edit or a weaker active-entry refusal.
  Stop after two failed repairs and return evidence, attempts, unresolved
  question and next discriminating check rather than widening scope.
- **Parent:** repository commit
  `0550b911e2db3efd5482b96ee7782959ca3926d5`. Linux source is
  `4d7d9486c04d917265f64c55bd23b2cc4fe7749c`. The complete 13-entry
  `patches/series-mt6797-provider-compile` SHA-256 is
  `ca6ec6118f91b609d841a3d77718ef2aea430f139092151c5c745c1ff4091246`.
  Proposal 0008 is
  `ac87496f89b81419bbf2219acf7f9f140fec14d3b4cf37075107f2afa2f396f9`,
  0009 is
  `84e6abef1139e744ecb59846b3fb3160b98ac50df4a59e058250a77b92d09cb6`
  and 0010 is
  `3266942a0b62e61feb525da07faef33e8767f89f7c90e9ff66c44716a3100136`.
  Frozen design evidence: `WHOLE_IMAGE_EMI.md`
  `4e4c7fff4836010db784d3db8f104a83b1b0c3a277175c9d8bcaedf475d7c7ab`,
  `EMI_ABI.md`
  `60bd8c436b22495719512b8a1cd9dae0bffb062511811d67cff436d94a0f0c71`,
  `SHARED_OWNER_IMPLEMENTATION.md`
  `a71e51e2ff2676b63d21bbd8e83fc6af98c24e77d47f4fe541e60d11be1c1021`
  and predecessor Buildbox result
  `ed3059d563fba0fd72c74803c04cc8cb03776f7ebf233c1384f7d8ed9c7d2393`.
- **Dependencies:** only the exact accepted resource-layout and EMI-ABI
  interfaces. The gate's copied context remains descriptive; the real provider
  must independently establish reservation lifetime, selector stability,
  external-writer exclusion, serialization, deployed SMC32 compatibility,
  domain permissions/overlap priority, mapping/copy visibility and recovery.
  Neither status zero nor `COMPLETED` is a lease, hardware-support result or
  permission for START.
- **Worktree:** current small repository checkout and topic; no Linux source
  tree. Shared proposal series and manifest remain integration-owner files.
- **Validation:** generate proposal 0011 reproducibly and replay it after the
  exact 13 predecessors. Compile the gate as a separate host object and link it
  against separately compiled accepted resource-layout/remap/EMI objects with
  strict warnings, conversion/sign warnings and ASan/UBSan. Fixtures cover
  every enumerated init mismatch and exact errno; null/exact aliases, their
  untouched-storage exception and fully cleared non-aliased outputs;
  selector-CLEAR below-`0x40000000` refusal; post-init mutation of every source
  layout field and of the source backend descriptor's callback/context pointers
  proving apply still uses the copied gate values while the selected context
  pointee remains caller-alive and stable;
  zero/stale generations plus valid `ULLONG_MAX`; every permission high bit and
  valid boundary;
  callback absence; exact callback argument values; state observed as
  `ATTEMPTED` inside the callback; exactly-once call count; zero, declared
  -1/-2/-3/-4, unknown negative/positive, `INT_MIN`, `INT_MAX` and nonzero raw
  high words; exact returned signed status; `COMPLETED` versus `FAULT_HELD`;
  repeat refusal; and unchanged READY/no-call state after every local refusal.
  Prove linked calls resolve to predecessor symbols rather than copied logic.
  Static scans prove no real backend/caller/policy/effect/registration and
  unchanged active binding refusal. Run proposal identity/replay, Checkpatch,
  sensitive/right/link/repository checks. Then insert proposal 0011 into
  canonical `patches/series` at the same relative position and append it to the
  named series, audit every manifest profile, commit and push clean inputs, and
  build with
  `KERNEL_PROFILE=mt6797-hif-parser-compile ./scripts/build-kernel --backend
  buildbox`. Fetch only the validated package and record the real AArch64
  `emi-service-gate.o`, command, source and symbol/linkage identities.
- **Hardware:** none. No Gemini SSH, SMC, firmware, MMIO, mapping, radio, DMA,
  power, reset, boot or partition action. Buildbox compilation only.
- **Upstream:** eventual owner belongs under a shared MediaTek CONSYS/EMI
  provider, not permanently in the WLAN tree. This is an experiment-only
  synthetic non-certifying patch with no DCO sign-off. Remove or relocate it
  when a reviewed provider supplies real lifetime, policy and recovery.
- **Owner-away work:** implementation, review and Buildbox compilation can
  finish offline. It must not select or prepare a device session.
- **Device readiness:** not applicable. A mock callback and compiled gate do
  not establish a deployed secure service or firmware admission.
- **Handoff:** exact proposal/source identities; fixture inventory and outputs;
  callback/state/result proof; no-backend/no-caller/no-policy/no-effect proof;
  replay/Checkpatch/manifest/repository results; Buildbox package, object and
  symbol evidence; all unresolved provider dependencies.
- **State:** complete. Contract drafted at `2026-09-06T06:44:29Z`; pending Sol Medium
  pre-dispatch review. Review at `2026-09-06T06:48:08Z` required alias-safe
  clearing, external serialization, exact errnos/generation behavior, complete
  layout invariants and canonical-series integration; repair 1 applies those
  changes. Repeat review at `2026-09-06T06:50:38Z` required the selector-CLEAR
  lower bound, explicit partial-overlap preconditions and source-mutation copy
  fixtures; repair 2 applies those changes. Pending final pre-dispatch review;
  final Sol review passed at `2026-09-06T06:51:27Z`. Implementation began at
  `2026-09-06T06:51:39Z`. The first complete implementation review at
  `2026-09-06T07:16:13Z` found false-positive refusal evidence and a no-network
  scope violation. Repair 1 completed before repeat review at
  `2026-09-06T07:22:21Z`; repair 2 completed at `2026-09-06T07:24:30Z`.
  Final pre-Buildbox Sol acceptance was recorded at
  `2026-09-06T07:25:36Z`. Buildbox generated and validated the exact pushed
  commit's package at `2026-09-06T07:31:35Z`, and final post-Buildbox Sol
  acceptance was recorded at `2026-09-06T07:37:46Z`. This offline compile work
  item is complete.
- **Efficiency loop:** if accepted, append one sanitized observed offline-item
  measurement to the active workflow ledger with actual routes, timestamps,
  review/rework, escalation and measured credits or explicit unavailability.

Validation repair 1 (2026-09-06T07:16:13Z review): strengthened the fixture's
live callback-counter and storage snapshots, added direct EMPTY/ATTEMPTED,
`ULLONG_MAX`, remap-`-ERANGE`, and self-consistent low-CLEAR cases, corrected
inventory counts, and removed verifier network access. Checkpatch remains
integrator-owned and pending against the pinned Linux source; no private,
device, VM, or Buildbox resource was accessed by this repair.

Validation repair 2 (2026-09-06T07:20Z review): added the live callback
snapshot to the 0xffffff terminal repeat, made the inventory categories
disjoint, documented the external-serialization/lifetime/partial-overlap API
preconditions, and retained the fully offline verifier. Final review-ready
handoff remains integrator-owned for canonical replay, Checkpatch and Buildbox.
