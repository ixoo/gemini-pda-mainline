# Work item: compile the MT6797 ordinary-transfer bridge

- **Outcome:** add one original, private, compile-only bridge that sequences a
  structurally prevalidated caller-supplied batch of ordinary MTKE sections through the existing
  real `mt6797_hif_download_section()` kernel API. The bridge must add useful
  whole-batch progress/error accounting. It cannot see a whole-image binding,
  so real ownership, immutable-buffer lifetime, whole-image validation,
  mixed-image refusal and exclusion are explicit caller obligations rather than
  checks or claims of this lower-level helper. Existing plan/binding refusals
  remain unchanged. It is not a firmware loader, owner, probe or runtime
  admission and must have zero production callers.
- **Owner and reviewer:** a Luna High bounded implementer owns only this new
  experiment directory and its proposed patch. The primary task owns shared
  `patches/series`, `patches/series-mt6797-provider-compile`, manifest/profile,
  workflow ledger, Buildbox, integration and publication. Sol Medium reviews
  integration. Astra Medium first resolves the named ownership-interface
  uncertainty below. Every worker is not alone in the repository and must
  preserve and accommodate concurrent changes.
- **Model route:** `gemini_implementer`, `gpt-5.6-luna`, high for bounded C/test
  implementation; `gemini_reasoner`, `gpt-5.6-sol`, medium for cross-file
  integration; `gemini_specialist`, `gpt-6-astra`, medium only for the
  pre-dispatch question of whether any proposed API could bypass or weaken the
  unresolved real-owner lifetime boundary.
- **Frozen parent:** repository commit
  `9019c55e0779b0f12512f3bab5fc3a01561a7688`, equal to `origin/main` at
  dispatch. Linux input is `4d7d9486c04d917265f64c55bd23b2cc4fe7749c`
  (7.3-rc1). The selected provider series has 14 entries and SHA-256
  `fa9471fcf6b041d02af375969d12aa2eb65dbb3a8f3636c59e9106c33e9baff1`;
  canonical `patches/series` is
  `53bc826019fc10610eac5dc0afc8166cc0e8ebe15f39e2eb676700f6c7c6203a`.
  The selected fragment is
  `aaf75f90b158765b0a03b614cf48858dfe528608cc4c3532ccf227b871d5ad87`.
  Existing HIF, parser, plan, START, binding and EMI-service proposal hashes
  are respectively `199052ee...`, `8d296e62...`, `76a93d44...`,
  `5b1ed48e...`, `62edcead...`, and `3cd1c5c8...`; the implementation must
  record their complete hashes in its machine-readable input inventory rather
  than relying on these abbreviations.
- **Evidence contract:** exact design inputs are
  `experiments/2026-09-05-mt6797-wifi-contract/ORDINARY_SECTION.md` SHA-256
  `abdf2ec9ae18cb62fbf44404dcc1a96f2f2496bfd9387f154fba18cdf08c3741`,
  `SHARED_OWNER_IMPLEMENTATION.md`
  `a71e51e2ff2676b63d21bbd8e83fc6af98c24e77d47f4fe541e60d11be1c1021`,
  and the image-binding record
  `b7254a03014aa7679542957354b15e73e64b6b976e2052b9d4b516606c60558d`.
  Existing Buildbox receipts for START/binding and the EMI service gate are
  `6906dfe6e0704557a6c560484a6876fb8228364f010342c716b59030d3695182`
  and `6a8c1f1696b3d24d75e301b00a5baa09f34ed4e4c94b41314bcdf93848299694`.
- **Owned scope:** create only files below this experiment: `README.md`,
  `inputs.json`, original `src/ordinary-transfer.{c,h}`, host compatibility and
  refusal fixtures, deterministic `scripts/generate-patch.py` and `verify.py`,
  `validation.json`, and one review patch named
  `0012-wifi-mediatek-compile-ordinary-transfer-bridge.patch`. The patch may add
  the two new files and one `ordinary-transfer.o` Makefile entry in the private
  MT6797 directory. It may include existing private headers but must not modify
  existing HIF/parser/plan/START/binding/EMI source, Kconfig, DT, drivers,
  manifest, configs or shared series. The integrator alone copies an accepted
  patch to `patches/proposals/` and changes shared ordering.
- **Required interface boundary:** the production bridge must invoke the real
  `mt6797_hif_download_section()` symbol and retain one caller-supplied absolute
  monotonic deadline for the complete batch. The caller must already hold the
  real powered mapping, reset/IRQ/host exclusion, stable whole-image generation,
  immutable source-buffer lifetime and external serialization continuously
  across prevalidation and every HIF call. The individual HIF mutex is not this
  batch-wide exclusion. The helper neither receives nor fabricates an owner or
  generation token and makes no hardware-lifetime claim. It may accept only
  immutable, distinct request/data/context/result storage; it must prevalidate
  the complete bounded ordinary request inventory before the first HIF call,
  execute in original order, use nonzero unique sequences, latch the first
  failure, become terminal after any attempt, and never retry or refund. Limits
  must be derived from pinned parser/HIF contracts, use checked arithmetic and
  have exact boundary fixtures.
- **Concrete API/call-order sketch for review:** use an opaque persistent batch
  object, not a stateless success function. A prepare/allocate operation copies
  at most `MTKE_MAX_SECTIONS` request descriptors after validating that every
  entry is ordinary, nonempty, HIF-size-bounded, uses a nonzero unique sequence,
  passes the existing pure CONFIG validator without mutating a transaction,
  has valid data fields, and has checked aggregate bytes. It copies no
  payload and grants no lifetime. An execute operation takes the prepared batch,
  real HIF context, one absolute deadline and separate result storage. Before
  clearing that result it rejects any byte-range overlap with the batch object,
  retained original caller-request-array range, and every referenced CONFIG/data
  buffer; overflow while computing a range is refusal. All request-array,
  CONFIG, data, batch-object and output spans are pairwise disjoint: a one-byte
  overlap refuses while adjacent endpoints are accepted. The batch retains the
  original request-array address/range for this check, so the caller keeps it
  alive and stable even though the descriptors are copied. It then marks the
  batch attempted before the first HIF call and invokes each copied request once
  in order. Free is allowed only after the caller has joined all users and does
  not release hardware.
  Re-prepare/execute on an attempted or faulted object refuses. Exact symbol and
  struct names are implementation details, but no Boolean/callback admission
  hook or reset API may appear.
- **Result accounting:** initialize visible output only after all alias/range
  validation. Use an explicit no-failure-index sentinel. Record completed
  section and byte totals only after a section returns success. On failure,
  separately retain the failed section index, returned error, firmware status
  and that call's reported partial submitted bytes; do not add them to completed
  totals or imply that no hardware effect occurred. A success reports all
  sections/bytes and no failed index. Context state and first error persist after
  return; caller output mutation cannot reopen it.
- **Hard refusal:** this work must not expose a byte view from
  `mt6797_image_binding`, call or weaken `mt6797_image_binding_begin()`, treat an
  ordinary-only image as real-owner admission, accept a generation number as
  proof, add a Boolean/callback owner bypass, or claim that caller-supplied
  requests match the private immutable binding. It must not accept EMI sections,
  call the EMI service gate, copy EMI, issue/observe START, or manufacture
  whole-image completion. No runtime caller may be added until the real owner
  atomically connects admission, generation validation and retained first-effect
  state across this whole batch. If useful sequencing cannot be expressed
  without one of those actions, stop and return the interface contradiction
  rather than adding a success stub. The result is a dormant lower-level
  ordinary-transfer component awaiting that future atomic connection; it is not
  the complete executor promised by the owner design.
- **No-effect boundary:** no platform probe, registration, initcall, export,
  mapping, IRQ handler, DMA, power/reset, firmware acquisition, SMC, secure-call
  implementation, DT node, WLAN/cfg80211/netdev caller, userspace ABI or default
  enablement. The existing `image_binding_begin()` must remain byte-identical
  and return `-EOPNOTSUPP` after successful prevalidation. No device candidate,
  network/device/VM/private-capture access or hardware-support claim.
- **Validation:** deterministic generation and exact replay; strict C warnings,
  ASan/UBSan host execution of the actual bridge; cases for zero/oversized
  inventories, malformed/EMI requests, aliases and overlaps, duplicate/zero
  sequence, byte-total/range overflow, output overlap before clearing, preflight
  failure before any HIF/test callback, every
  section failure position, partial progress, expired/extended deadlines,
  repeat after success/failure, separate failed-index/error/status/partial-byte
  accounting, result clearing and unchanged input snapshots.
  Record all callbacks and prove no call follows the first failure. Run strict
  Checkpatch without exclusions, preserve missing-DCO/MAINTAINERS findings, and
  inspect generated source for the no-effect boundary. Normal and optimized
  verification must not depend on Python `assert`.
- **Integration and build:** if implementation and Sol review pass, the primary
  appends proposal 0012 exactly after 0011 in canonical and provider series,
  audits every manifest profile for canonical subsequence order, preserves all
  existing selectors, runs the repository gate, commits/pushes a clean exact
  revision and builds only with
  `KERNEL_PROFILE=mt6797-hif-parser-compile ./scripts/build-kernel --backend buildbox`.
  Reuse the managed prepared source under its lock; do not copy a Linux tree or
  use the VM backend. Acceptance requires real AArch64 compilation of the new
  object, undefined linkage to the real HIF function resolving in `vmlinux`,
  nonzero new definitions, archive membership, matching `.cmd` source/options,
  and no initcall/export/registration. Build success is compile/link evidence
  only.
- **Stop/escalation:** stop immediately if the interface needs private binding
  bytes, real-owner success, mixed-image admission, EMI/START effects, a change
  to existing API semantics, invented routing/MPU policy, vendor code, private
  material, device evidence, or a shared-file edit by the worker. After two
  implementation repair cycles, return exact failures and the next
  discriminating check. Any conflict over lifetime/atomic owner exclusion is an
  immediate Astra handoff, not an implementation guess.
- **Rights/upstream:** all new C/test/generator prose must be original and
  GPL-2.0-only or MIT as appropriate. Existing protocol sources are pinned
  evidence/dependencies, not copied vendor implementation. The archive uses a
  clearly synthetic non-certifying author with no invented DCO sign-off and is
  not submission-ready. Actual authorship/certification and integration into a
  real MediaTek owner remain upstream gates.
- **Owner-away/device:** fully offline. It may finish through Buildbox evidence
  while the TOPRGU candidate remains `waiting-owner-boot`; it must not alter the
  queue, device custody or selected candidate.
- **Handoff:** exact parent, changed paths, full input/patch/source/test hashes,
  generated patch identity, compiler/sanitizer and Checkpatch results, every
  refusal count, limitations, review repairs, and build status. Explicitly state
  that the bridge does not prove complete-image execution, firmware readiness,
  real ownership or usable Wi-Fi.
- **State:** Astra Medium ownership-interface review rejected the first draft's
  impossible mixed-image/owner-refusal claim. The corrected contract makes those
  caller obligations, prohibits production callers before atomic owner
  integration, requires batch-wide exclusion, overlap-before-clear and separate
  partial-failure accounting. Astra Medium and Sol Medium accepted the corrected
  boundary for Luna High dispatch at parent `9019c55e...`.
- **Efficiency loop:** once accepted as an offline work item, append one
  sanitized measurement to the active workflow ledger with actual routes,
  timestamps, first-review result, rework/escalation and measured credits or
  explicit unavailability.
